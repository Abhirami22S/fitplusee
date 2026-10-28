"""
FitPulse - E1 (SUPERVISED): same-day goal classification  (label = 1 if steps >= 8,000)
=======================================================================================
Experiment E1 is UNCHANGED: the Random Forest, its 18 features (15 numeric incl. engineered active_ratio + 3 categorical),
the 70/15/15 DataFrame.randomSplit(seed 42) and its selected setting (numTrees 50, maxDepth 15, read from
faculty_evidence/report_aligned/rf_run_info.json) come from models/spark_report_classification.py, which is imported, not edited.
This script ADDS two more supervised models on exactly the same rows and features:
    Logistic Regression (one-hot + standardised, regParam tuned on validation)
    Gradient-Boosted Trees (maxDepth x maxIter tuned on validation)
and prints/saves ONE comparison table: accuracy, weighted F1, ROC-AUC and the majority baseline.

Leakage rules: steps, distance_km, user_id, date, smoking_status, health_condition are never features.
Checks run here:  (1) reproduction of the existing RF numbers,  (2) leakage run (steps + distance_km added)  -> INVALID,
(3) user-held-out run (15% of users never seen in training),  (4) test predictions saved for the scikit-learn cross-check.

Run (PowerShell, from the project folder):  .\\run_supervised.ps1 -Experiment E1 [-Storage hdfs]
"""
import argparse
import json
import time

import pandas as pd
from pyspark.ml.classification import GBTClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.sql import functions as F

import spark_common as sc
import spark_report_classification as old          # E1 Random Forest code, unchanged
import sup_common as S

EXP = "E1"
RA = sc.EVIDENCE / "report_aligned"
OLD_TO_NEW = {"Accuracy": S.M_ACC, "F1 (weighted)": S.M_F1W, "ROC AUC": S.M_AUC, "Baseline accuracy (always majority class)": S.M_BASE,
              "Precision (goal-achieved class)": S.M_P1, "Recall (goal-achieved class)": S.M_R1, "F1 (goal-achieved class)": S.M_F11}


def main():
    ap = argparse.ArgumentParser()
    S.add_args(ap)
    args = ap.parse_args()
    exports, evid = S.dirs(args)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-E1-supervised")
    res = S.Results(EXP)

    # ---- data and split: identical to models/spark_report_classification.py ----
    df = (silver.dropDuplicates(["user_id", "date"])
          .withColumn("label", (F.col("steps") >= old.GOAL_STEPS).cast("double"))
          .withColumn("active_ratio", F.col("active_minutes") / (F.col("active_minutes") + F.col("sedentary_minutes")))
          .select("user_id", "date", "label", "steps", "distance_km", *old.NUM, *old.CAT).cache())
    n = df.count()
    train, val, test = df.randomSplit([0.70, 0.15, 0.15], seed=sc.SEED)
    train, val, test = train.cache(), val.cache(), test.cache()
    sizes = {"Training": train.count(), "Validation": val.count(), "Test": test.count()}
    print(f"records {n:,}; positive share {df.filter('label = 1').count() / n:.4f}; split {sizes}")
    old_sizes = pd.read_csv(RA / "rf_split_sizes.csv").set_index("Set").Records.to_dict()
    same_split = all(int(old_sizes[k]) == v for k, v in sizes.items())
    print("split sizes equal to the existing E1 run:", same_split, "(existing:", old_sizes, ")")
    features = old.NUM + [c + "_idx" for c in old.CAT]

    # ---- 1. Random Forest: the existing E1 model, setting taken from its own run info ----
    info = json.loads((RA / "rf_run_info.json").read_text())
    trees, depth = int(info["numTrees"]), int(info["maxDepth"])
    t0 = time.time()
    rf = old.pipeline(old.NUM, depth, trees).fit(train)
    print(f"RF numTrees={trees} maxDepth={depth} fitted in {time.time() - t0:.0f}s")

    # ---- 2. Logistic Regression and 3. GBT: tuned on VALIDATION ROC-AUC only ----
    lr_builder = lambda reg: S.make_pipeline(old.NUM, old.CAT, LogisticRegression(
        featuresCol="features", labelCol="label", regParam=reg, elasticNetParam=0.0, maxIter=200, standardization=False),
        onehot=True, scale=True)
    gbt_builder = lambda depth, iters: S.make_pipeline(old.NUM, old.CAT, GBTClassifier(
        featuresCol="features", labelCol="label", maxDepth=depth, maxIter=iters, stepSize=0.1, maxBins=32, seed=sc.SEED))
    auc = BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
    val_auc = lambda p: auc.evaluate(p)
    print("tuning Logistic Regression (validation ROC-AUC)")
    (_, lr_p, lr), lr_grid = S.tune(lr_builder, S.grid(reg=[0.0, 0.01, 0.1, 1.0]), train, val, val_auc)
    print("tuning Gradient-Boosted Trees (validation ROC-AUC)")
    (_, gbt_p, gbt), gbt_grid = S.tune(gbt_builder, S.grid(depth=[3, 5], iters=[50, 100]), train, val, val_auc)
    pd.concat([lr_grid.assign(model="Logistic Regression"), gbt_grid.assign(model="Gradient-Boosted Trees")]).to_csv(
        evid / "E1_tuning_grid.csv", index=False)

    models = {"Random Forest": (rf, f"numTrees={trees}, maxDepth={depth} (existing E1 setting)"),
              "Logistic Regression": (lr, f"regParam={lr_p['reg']}"),
              "Gradient-Boosted Trees": (gbt, f"maxDepth={gbt_p['depth']}, maxIter={gbt_p['iters']}")}

    # ---- evaluation: validation + test (test scored once per final model) ----
    preds = {}
    for name, (m, setting) in models.items():
        for split_name, d in (("validation", val), ("test", test)):
            p = m.transform(d).cache()
            met, cm = S.cls_metrics(p)
            res.add_many(name, met, split_name)
            S.export_predictions(p, ["user_id", "date"], evid / "predictions" / f"E1_{name.replace(' ', '_')}_{split_name}.csv")
            if split_name == "test":
                preds[name] = p
                print(f"{name:24s} [{setting}] test: acc {met[S.M_ACC]:.4f}  F1w {met[S.M_F1W]:.4f}  AUC {met[S.M_AUC]:.4f}  "
                      f"baseline {met[S.M_BASE]:.4f}  CM(tn,fp,fn,tp)={cm}")

    # ---- check 1: the existing RF numbers are reproduced (E1 unchanged) ----
    old_m = pd.read_csv(RA / "rf_metrics.csv").set_index("Metric")
    rep = []
    for split_name, col in (("validation", "Validation"), ("test", "Test")):
        mine = res.frame().query("model == 'Random Forest' and split_type == @split_name").set_index("metric").value
        for om, nm in OLD_TO_NEW.items():
            rep.append({"split": split_name, "metric": nm, "existing_E1": float(old_m.loc[om, col]), "this_run": float(mine[nm])})
    rep = pd.DataFrame(rep).assign(abs_diff=lambda d: (d.existing_E1 - d.this_run).abs())
    rep.to_csv(evid / "E1_reproduction_check.csv", index=False)
    print(f"reproduction of existing RF metrics: max |difference| = {rep.abs_diff.max():.2e}")
    # also: my confusion-count formulas equal Spark's own evaluators on the RF test predictions
    spark_eval = old.full_metrics(preds["Random Forest"])
    mine_t = res.frame().query("model == 'Random Forest' and split_type == 'test'").set_index("metric").value
    fdiff = max(abs(spark_eval[o] - mine_t[nm]) for o, nm in OLD_TO_NEW.items())
    print(f"my metric formulas vs Spark MulticlassClassificationEvaluator on RF test predictions: max |difference| = {fdiff:.2e}")

    # ---- check 2: leakage run (steps + distance_km added) -> INVALID ----
    leak_num = old.NUM + ["steps", "distance_km"]
    leaks = {"Random Forest": old.pipeline(leak_num, depth, trees),
             "Logistic Regression": S.make_pipeline(leak_num, old.CAT, LogisticRegression(
                 featuresCol="features", labelCol="label", regParam=lr_p["reg"], elasticNetParam=0.0, maxIter=200, standardization=False),
                 onehot=True, scale=True),
             "Gradient-Boosted Trees": S.make_pipeline(leak_num, old.CAT, GBTClassifier(
                 featuresCol="features", labelCol="label", maxDepth=gbt_p["depth"], maxIter=gbt_p["iters"], stepSize=0.1, maxBins=32, seed=sc.SEED))}
    for name, pipe in leaks.items():
        met, _ = S.cls_metrics(pipe.fit(train).transform(test))
        res.add_many(f"{name} + steps & distance_km (LEAKAGE)", {k: met[k] for k in (S.M_ACC, S.M_F1W, S.M_AUC)}, "test", "INVALID")
        print(f"LEAKAGE {name:24s} test acc {met[S.M_ACC]:.4f}  AUC {met[S.M_AUC]:.4f}   -> INVALID (the label is a threshold on steps)")

    # ---- check 3: user-held-out (15% of users never seen in training) ----
    u = S.user_hash(df)
    utr, ute = u.filter("u_hash < 0.85").cache(), u.filter("u_hash >= 0.85").cache()
    n_users_out = ute.select("user_id").distinct().count()
    for name in models:
        pipe = {"Random Forest": old.pipeline(old.NUM, depth, trees), "Logistic Regression": lr_builder(lr_p["reg"]),
                "Gradient-Boosted Trees": gbt_builder(gbt_p["depth"], gbt_p["iters"])}[name]
        met, _ = S.cls_metrics(pipe.fit(utr).transform(ute))
        res.add_many(name, {k: met[k] for k in (S.M_ACC, S.M_F1W, S.M_AUC, S.M_BASE)}, "test (user-held-out)")
        print(f"user-held-out ({n_users_out} unseen users) {name:24s} acc {met[S.M_ACC]:.4f}  AUC {met[S.M_AUC]:.4f}  baseline {met[S.M_BASE]:.4f}")

    # ---- outputs ----
    res.save(exports)
    imp = pd.concat([S.feature_importance(rf, features, "Random Forest", EXP),
                     S.feature_importance(gbt, features, "Gradient-Boosted Trees", EXP)]).sort_values(["model", "importance"], ascending=[True, False])
    imp.to_csv(exports / "E1_feature_importance.csv", index=False)
    S.feature_importance(lr, S.onehot_names(lr, old.NUM, old.CAT), "Logistic Regression", EXP).to_csv(evid / "E1_logreg_coefficients.csv", index=False)
    comp = (res.frame().query("split_type == 'test' and status == 'VALID'")
            .pivot(index="model", columns="metric", values="value")[[S.M_ACC, S.M_F1W, S.M_AUC, S.M_BASE]])
    comp.to_csv(evid / "E1_comparison_table.csv")
    print("\nE1 comparison table (test set, 70/15/15 random split, seed 42):")
    print(comp.round(4).to_string())
    splits =(train.select("user_id", "date").withColumn("split", F.lit("train"))
              .unionByName(val.select("user_id", "date").withColumn("split", F.lit("validation")))
              .unionByName(test.select("user_id", "date").withColumn("split", F.lit("test"))))
    splits.toPandas().sort_values(["user_id", "date"]).to_csv(evid / "predictions" / "E1_splits.csv", index=False)
    S.write_run_info(evid / "E1_run_info.json", cfg, experiment=EXP, records=n, split_sizes=sizes, same_split_as_existing_E1=same_split,
                     rf_setting={"numTrees": trees, "maxDepth": depth}, logreg_setting=lr_p, gbt_setting=gbt_p,
                     reproduction_max_abs_diff=float(rep.abs_diff.max()), users_held_out=int(n_users_out))
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
