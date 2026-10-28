"""
FitPulse - E4 (SUPERVISED): user-day classifier  activity_level = High / Low  (replaces the earlier user-day segmentation experiment, archived)
=========================================================================================================================
Label: High (1) if the day's active_minutes is ABOVE the median, otherwise Low (0). The median is taken from the TRAINING
users' rows only (it is 70 minutes; High share ~49%).
Split: USER-HELD-OUT 70/15/15 (a hash of user_id: no user appears in two sets).
Features (no label-encoding column):  avg/max/resting heart rate, sleep minutes, sleep quality, stress, hydration, steps, distance_km,
age, bmi, height_cm, baseline weight (bmi x height^2), and categoricals intensity, activity_type, gender.
EXCLUDED because they encode the label (this is a derived-data demonstration, see below):
  active_minutes (the label itself) | sedentary_minutes (= 1440 - sleep_minutes - active_minutes) | active_ratio |
  active_minutes_roll7_avg (window includes the day) | calories_burned (calories = MET(activity_type, intensity) x weight_kg x
  duration/60 and duration IS active_minutes, so calories + weight + activity_type + intensity reconstruct the label).
DERIVED-DATA NOTE: calories, distance, minutes, max heart rate and sleep quality are partly derived in this dataset
(data/prepare_raw_dataset.py). That is exactly why the leakage runs below look "excellent" - and are INVALID.
Models: Random Forest, Gradient-Boosted Trees, Logistic Regression (tuned on the validation users only).
Metrics: accuracy, macro F1, ROC-AUC, confusion matrix, majority baseline.
Leakage runs (INVALID): + calories_burned ; + sedentary_minutes.

Run:  .\\run_supervised.ps1 -Experiment E4 [-Storage hdfs]
"""
import argparse

import pandas as pd
from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.sql import functions as F

import spark_common as sc
import sup_common as S

EXP = "E4"
NUM = ["avg_heart_rate", "max_heart_rate", "resting_heart_rate", "sleep_minutes", "sleep_quality_score", "stress_level",
       "hydration_level", "steps", "distance_km", "age", "bmi", "height_cm", "weight_baseline_kg"]
CAT = ["intensity", "activity_type", "gender"]
SPLIT = "test (user-held-out)"


def main():
    ap = argparse.ArgumentParser()
    S.add_args(ap)
    args = ap.parse_args()
    exports, evid = S.dirs(args)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-E4-supervised")
    res = S.Results(EXP)

    df = (silver.dropDuplicates(["user_id", "date"])
          .withColumn("weight_baseline_kg", F.col("bmi") * F.pow(F.col("height_cm") / 100.0, 2))
          .select("user_id", "date", "active_minutes", "calories_burned", "sedentary_minutes", *NUM, *CAT).dropna())
    df = S.user_hash(df)
    train_raw = df.filter("u_hash < 0.70")
    median = float(train_raw.agg(F.expr("percentile(active_minutes, 0.5)")).first()[0])
    df = df.withColumn("label", (F.col("active_minutes") > F.lit(median)).cast("double"))
    train = df.filter("u_hash < 0.70").cache()
    val = df.filter("u_hash >= 0.70 AND u_hash < 0.85").cache()
    test = df.filter("u_hash >= 0.85").cache()
    sizes = {"train": train.count(), "validation": val.count(), "test": test.count()}
    users = {k: d.select("user_id").distinct().count() for k, d in (("train", train), ("validation", val), ("test", test))}
    share = {k: d.agg(F.avg("label")).first()[0] for k, d in (("train", train), ("validation", val), ("test", test))}
    print(f"median active_minutes (training users) = {median}; rows {sizes}; users {users}; High share {({k: round(v, 3) for k, v in share.items()})}")
    overlap = train.select("user_id").intersect(test.select("user_id")).count()
    print("users present in BOTH train and test (must be 0):", overlap)

    auc_ev = BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
    val_auc = lambda p: auc_ev.evaluate(p)
    rf_b = lambda num, depth: S.make_pipeline(num, CAT, RandomForestClassifier(
        featuresCol="features", labelCol="label", numTrees=50, maxDepth=depth, maxBins=32, seed=sc.SEED))
    gbt_b = lambda num, depth, iters: S.make_pipeline(num, CAT, GBTClassifier(
        featuresCol="features", labelCol="label", maxDepth=depth, maxIter=iters, stepSize=0.1, maxBins=32, seed=sc.SEED))
    lr_b = lambda num, reg: S.make_pipeline(num, CAT, LogisticRegression(
        featuresCol="features", labelCol="label", regParam=reg, elasticNetParam=0.0, maxIter=300, standardization=False),
        onehot=True, scale=True)

    print("tuning on the VALIDATION users (ROC-AUC)")
    (_, rf_p, rf), g1 = S.tune(lambda depth: rf_b(NUM, depth), S.grid(depth=[5, 10]), train, val, val_auc)
    (_, gbt_p, gbt), g2 = S.tune(lambda depth, iters: gbt_b(NUM, depth, iters), S.grid(depth=[3, 5], iters=[50, 100]), train, val, val_auc)
    (_, lr_p, lr), g3 = S.tune(lambda reg: lr_b(NUM, reg), S.grid(reg=[0.0, 0.01, 0.1, 1.0]), train, val, val_auc)
    pd.concat([g1.assign(model="Random Forest"), g2.assign(model="Gradient-Boosted Trees"), g3.assign(model="Logistic Regression")]
              ).to_csv(evid / "E4_tuning_grid.csv", index=False)
    models = {"Random Forest": (rf, f"numTrees=50, maxDepth={rf_p['depth']}"),
              "Gradient-Boosted Trees": (gbt, f"maxDepth={gbt_p['depth']}, maxIter={gbt_p['iters']}"),
              "Logistic Regression": (lr, f"regParam={lr_p['reg']}")}

    preds, cms = {}, []
    for name, (m, setting) in models.items():
        for split_name, d in (("validation (user-held-out)", val), (SPLIT, test)):
            p = m.transform(d).cache()
            met, cm = S.cls_metrics(p)
            res.add_many(name, met, split_name)
            if split_name == SPLIT:
                preds[name] = p
                tn, fp, fn, tp = cm
                for lab, v in (("Confusion: actual Low, predicted Low", tn), ("Confusion: actual Low, predicted High", fp),
                               ("Confusion: actual High, predicted Low", fn), ("Confusion: actual High, predicted High", tp)):
                    res.add(name, lab, v, split_name)
                cms.append({"model": name, "TN (Low->Low)": tn, "FP (Low->High)": fp, "FN (High->Low)": fn, "TP (High->High)": tp})
                print(f"{name:24s} [{setting}] TEST: acc {met[S.M_ACC]:.4f}  macro-F1 {met[S.M_F1M]:.4f}  AUC {met[S.M_AUC]:.4f} | baseline {met[S.M_BASE]:.4f}  CM(tn,fp,fn,tp)={cm}")
    pd.DataFrame(cms).to_csv(evid / "E4_confusion_matrices.csv", index=False)

    # ---- leakage runs: columns that encode the label -> INVALID ----
    for extra, why in (("calories_burned", "calories = MET x weight x duration; duration = active_minutes"),
                       ("sedentary_minutes", "sedentary = 1440 - sleep - active")):
        leak_num = NUM + [extra]
        for name, pipe in {"Random Forest": rf_b(leak_num, rf_p["depth"]), "Gradient-Boosted Trees": gbt_b(leak_num, gbt_p["depth"], gbt_p["iters"]),
                           "Logistic Regression": lr_b(leak_num, lr_p["reg"])}.items():
            met, _ = S.cls_metrics(pipe.fit(train).transform(test))
            res.add_many(f"{name} + {extra} (LEAKAGE)", {k: met[k] for k in (S.M_ACC, S.M_F1M, S.M_AUC)}, SPLIT, "INVALID")
            print(f"LEAKAGE +{extra:18s} {name:24s} test acc {met[S.M_ACC]:.4f}  macro-F1 {met[S.M_F1M]:.4f}  AUC {met[S.M_AUC]:.4f}   -> INVALID ({why})")

    res.save(exports)
    names = NUM + [c + "_idx" for c in CAT]
    pd.concat([S.feature_importance(rf, names, "Random Forest", EXP), S.feature_importance(gbt, names, "Gradient-Boosted Trees", EXP)]
              ).sort_values(["model", "importance"], ascending=[True, False]).to_csv(exports / "E4_feature_importance.csv", index=False)
    S.feature_importance(lr, S.onehot_names(lr, NUM, CAT), "Logistic Regression", EXP).to_csv(evid / "E4_logreg_coefficients.csv", index=False)
    comp = (res.frame().query("split_type == @SPLIT and status == 'VALID' and metric in ['Accuracy','F1 (macro)','ROC AUC','Baseline accuracy (always majority class)']")
            .pivot(index="model", columns="metric", values="value"))
    comp.to_csv(evid / "E4_comparison_table.csv")
    print("\nE4 comparison table (user-held-out TEST users):")
    print(comp.round(4).to_string())
    for name, p in preds.items():
        S.export_predictions(p, ["user_id", "date"], evid / "predictions" / f"E4_{name.replace(' ', '_')}_test.csv")
    (df.select("user_id", "u_hash").distinct().withColumn("split", F.when(F.col("u_hash") < 0.70, "train").when(F.col("u_hash") < 0.85, "validation").otherwise("test"))
     .toPandas().sort_values("user_id").to_csv(evid / "predictions" / "E4_splits.csv", index=False))
    S.write_run_info(evid / "E4_run_info.json", cfg, experiment=EXP, median_active_minutes=median, rows=sizes, users=users, high_share=share,
                     users_in_train_and_test=overlap, settings={"rf": rf_p, "gbt": gbt_p, "logreg": lr_p})
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
