"""
FitPulse - E2 (SUPERVISED): next-day goal prediction  (label for day t = 1 if steps(t) >= 8,000)
================================================================================================
REBUILT. The previous notebook version reused Silver's rolling columns (their window INCLUDES the current row) and was
evaluated headline-wise on a random split. This version:

* builds every history feature with Spark window functions partitioned by user_id, ordered by date, with the frame
  ENDING AT -1 (rowsBetween(-7, -1) / (-3, -1)) or lag(), so a feature of day t only uses rows strictly before day t;
* keeps only rows whose previous logged row is exactly the previous calendar day and that have >= 3 earlier rows;
* uses only information known the evening before: history windows + calendar of day t (day_of_week, month sin/cos) + static
  profile (age, gender, bmi, height, baseline weight). Nothing measured ON day t (no activity, calories, minutes, steps);
* uses a CHRONOLOGICAL split by date (earliest 70% of the date span = train, next 15% = validation, latest 15% = test);
  a random split is shown ONLY as a labelled, non-headline contrast;
* compares Random Forest, Gradient-Boosted Trees and Logistic Regression; tuning on the validation block only.

Weight: weight_kg drifts with the calendar inside each user (correlation 0.991 with month), so it would act as a clock.
It is replaced by the non-drifting baseline weight = bmi x (height_cm/100)^2 (decision recorded with the user).
Leakage test: Silver's steps_roll7_avg (window rowsBetween(-6, 0), i.e. INCLUDING the prediction day) is added -> INVALID.
Not features: steps, distance_km, user_id, date, smoking_status, health_condition (and nothing derived from steps of day t).

Run:  .\\run_supervised.ps1 -Experiment E2 [-Storage hdfs]
"""
import argparse
import time

import pandas as pd
from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.sql import Window
from pyspark.sql import functions as F

import spark_common as sc
import sup_common as S

EXP = "E2"
GOAL = 8000
HIST = ["steps_lag1", "steps_lag2", "steps_mean3", "steps_mean7", "steps_std7", "goal_rate7", "calories_mean7",
        "active_minutes_mean7", "sleep_quality_mean7", "sleep_minutes_mean7", "resting_hr_mean7", "stress_mean7"]
CTX = ["month_sin", "month_cos", "age", "bmi", "height_cm", "weight_baseline_kg"]
NUM = HIST + CTX
CAT = ["day_of_week", "gender"]
LEAK = ["steps_roll7_avg"]                      # Silver column: frame rowsBetween(-6, 0) = includes the prediction day
BASE = "Baseline accuracy (always TRAINING-majority class)"


def build_frame(silver):
    """One row per (user, day t) with features computed ONLY from rows before t. Returns the Spark DataFrame."""
    w = Window.partitionBy("user_id").orderBy("date")
    prev7, prev3 = w.rowsBetween(-7, -1), w.rowsBetween(-3, -1)
    d = silver.dropDuplicates(["user_id", "date"]).select(
        "user_id", "date", "day_of_week", "gender", "age", "bmi", "height_cm", "steps", "calories_burned", "active_minutes",
        "sleep_quality_score", "sleep_minutes", "resting_heart_rate", "stress_level", "steps_roll7_avg")
    d = (d.withColumn("label", (F.col("steps") >= GOAL).cast("double"))
         .withColumn("hit", (F.col("steps") >= GOAL).cast("double"))
         .withColumn("steps_lag1", F.lag("steps", 1).over(w).cast("double"))
         .withColumn("steps_lag2", F.lag("steps", 2).over(w).cast("double"))
         .withColumn("prev_date", F.lag("date", 1).over(w))
         .withColumn("n_prev", F.count(F.lit(1)).over(prev7))
         .withColumn("steps_mean3", F.avg("steps").over(prev3))
         .withColumn("steps_mean7", F.avg("steps").over(prev7))
         .withColumn("steps_std7", F.stddev("steps").over(prev7))
         .withColumn("goal_rate7", F.avg("hit").over(prev7))
         .withColumn("calories_mean7", F.avg("calories_burned").over(prev7))
         .withColumn("active_minutes_mean7", F.avg("active_minutes").over(prev7))
         .withColumn("sleep_quality_mean7", F.avg("sleep_quality_score").over(prev7))
         .withColumn("sleep_minutes_mean7", F.avg("sleep_minutes").over(prev7))
         .withColumn("resting_hr_mean7", F.avg("resting_heart_rate").over(prev7))
         .withColumn("stress_mean7", F.avg("stress_level").over(prev7))
         .withColumn("month_sin", F.sin(2 * 3.141592653589793 * F.month("date") / 12))
         .withColumn("month_cos", F.cos(2 * 3.141592653589793 * F.month("date") / 12))
         .withColumn("weight_baseline_kg", F.col("bmi") * F.pow(F.col("height_cm") / 100.0, 2)))
    keep = (F.datediff("date", "prev_date") == 1) & (F.col("n_prev") >= 3)
    return d.filter(keep).select("user_id", "date", "label", *NUM, *CAT, *LEAK).cache()


def main():
    ap = argparse.ArgumentParser()
    S.add_args(ap)
    args = ap.parse_args()
    exports, evid = S.dirs(args)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-E2-supervised")
    res = S.Results(EXP)

    frame = build_frame(silver)
    n = frame.count()
    dates = sorted(r[0] for r in silver.select("date").distinct().collect())
    c1, c2 = dates[int(len(dates) * 0.70)], dates[int(len(dates) * 0.85)]
    train = frame.filter(F.col("date") < F.lit(c1)).cache()
    val = frame.filter((F.col("date") >= F.lit(c1)) & (F.col("date") < F.lit(c2))).cache()
    test = frame.filter(F.col("date") >= F.lit(c2)).cache()
    sizes = {"train": train.count(), "validation": val.count(), "test": test.count()}
    share = {k: d.agg(F.avg("label")).first()[0] for k, d in (("train", train), ("validation", val), ("test", test))}
    print(f"usable rows {n:,} of {silver.count():,}; chronological split: train < {c1} <= validation < {c2} <= test (to {dates[-1]})")
    print("rows:", sizes, "| share of days meeting 8,000 steps:", {k: round(v, 3) for k, v in share.items()})
    train_majority_acc = share["test"] if share["train"] >= 0.5 else 1 - share["test"]
    pd.DataFrame([{"split": k, "rows": sizes[k], "positive_share": share[k]} for k in sizes]).assign(
        cut_train_end=str(c1), cut_validation_end=str(c2)).to_csv(evid / "E2_split_summary.csv", index=False)

    auc_ev = BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
    val_auc = lambda p: auc_ev.evaluate(p)
    rf_b = lambda num, depth, trees=50: S.make_pipeline(num, CAT, RandomForestClassifier(
        featuresCol="features", labelCol="label", numTrees=trees, maxDepth=depth, maxBins=32, seed=sc.SEED))
    gbt_b = lambda num, depth, iters: S.make_pipeline(num, CAT, GBTClassifier(
        featuresCol="features", labelCol="label", maxDepth=depth, maxIter=iters, stepSize=0.1, maxBins=32, seed=sc.SEED))
    lr_b = lambda num, reg: S.make_pipeline(num, CAT, LogisticRegression(
        featuresCol="features", labelCol="label", regParam=reg, elasticNetParam=0.0, maxIter=300, standardization=False),
        onehot=True, scale=True)

    print("tuning on the VALIDATION block (ROC-AUC)")
    (_, rf_p, rf), g1 = S.tune(lambda depth: rf_b(NUM, depth), S.grid(depth=[5, 8, 12]), train, val, val_auc)
    (_, gbt_p, gbt), g2 = S.tune(lambda depth, iters: gbt_b(NUM, depth, iters), S.grid(depth=[3, 5], iters=[50, 100]), train, val, val_auc)
    (_, lr_p, lr), g3 = S.tune(lambda reg: lr_b(NUM, reg), S.grid(reg=[0.0, 0.01, 0.1, 1.0]), train, val, val_auc)
    pd.concat([g1.assign(model="Random Forest"), g2.assign(model="Gradient-Boosted Trees"), g3.assign(model="Logistic Regression")]
              ).to_csv(evid / "E2_tuning_grid.csv", index=False)
    models = {"Random Forest": (rf, f"numTrees=50, maxDepth={rf_p['depth']}"),
              "Gradient-Boosted Trees": (gbt, f"maxDepth={gbt_p['depth']}, maxIter={gbt_p['iters']}"),
              "Logistic Regression": (lr, f"regParam={lr_p['reg']}")}

    # ---- evaluation: validation block + test block (test scored once per final model) ----
    preds = {}
    for name, (m, setting) in models.items():
        for split_name, d in (("validation", val), ("chronological test", test)):
            p = m.transform(d).cache()
            met, cm = S.cls_metrics(p)
            res.add_many(name, met, split_name)
            res.add(name, BASE, train_majority_acc if split_name == "chronological test" else
                    (share["validation"] if share["train"] >= 0.5 else 1 - share["validation"]), split_name, "BASELINE")
            if split_name == "chronological test":
                preds[name] = p
                print(f"{name:24s} [{setting}] TEST: acc {met[S.M_ACC]:.4f}  P {met[S.M_P1]:.4f}  R {met[S.M_R1]:.4f}  F1 {met[S.M_F11]:.4f}  "
                      f"AUC {met[S.M_AUC]:.4f} | test-majority baseline {met[S.M_BASE]:.4f}, training-majority baseline {train_majority_acc:.4f}  CM(tn,fp,fn,tp)={cm}")

    # ---- leakage run: Silver's rolling mean INCLUDES the prediction day -> INVALID ----
    leak_num = NUM + LEAK
    leaks = {"Random Forest": rf_b(leak_num, rf_p["depth"]), "Gradient-Boosted Trees": gbt_b(leak_num, gbt_p["depth"], gbt_p["iters"]),
             "Logistic Regression": lr_b(leak_num, lr_p["reg"])}
    for name, pipe in leaks.items():
        met, _ = S.cls_metrics(pipe.fit(train).transform(test))
        res.add_many(f"{name} + rolling mean INCLUDING the prediction day (LEAKAGE)", {k: met[k] for k in (S.M_ACC, S.M_F11, S.M_AUC)},
                     "chronological test", "INVALID")
        print(f"LEAKAGE {name:24s} test acc {met[S.M_ACC]:.4f}  F1 {met[S.M_F11]:.4f}  AUC {met[S.M_AUC]:.4f}   -> INVALID")

    # ---- contrast only: a RANDOM split of the same rows (NOT the headline; neighbouring days leak across it) ----
    rtr, _, rte = frame.randomSplit([0.70, 0.15, 0.15], seed=sc.SEED)
    for name, pipe in {"Random Forest": rf_b(NUM, rf_p["depth"]), "Gradient-Boosted Trees": gbt_b(NUM, gbt_p["depth"], gbt_p["iters"]),
                       "Logistic Regression": lr_b(NUM, lr_p["reg"])}.items():
        met, _ = S.cls_metrics(pipe.fit(rtr).transform(rte))
        res.add_many(name, {k: met[k] for k in (S.M_ACC, S.M_F11, S.M_AUC, S.M_BASE)}, "random split (NOT headline)", "REFERENCE")
        print(f"random split (NOT headline) {name:24s} acc {met[S.M_ACC]:.4f}  F1 {met[S.M_F11]:.4f}  AUC {met[S.M_AUC]:.4f}  baseline {met[S.M_BASE]:.4f}")

    # ---- outputs ----
    res.save(exports)
    names = NUM + [c + "_idx" for c in CAT]
    imp = pd.concat([S.feature_importance(rf, names, "Random Forest", EXP), S.feature_importance(gbt, names, "Gradient-Boosted Trees", EXP)]
                    ).sort_values(["model", "importance"], ascending=[True, False])
    imp.to_csv(exports / "E2_feature_importance.csv", index=False)
    S.feature_importance(lr, S.onehot_names(lr, NUM, CAT), "Logistic Regression", EXP).to_csv(evid / "E2_logreg_coefficients.csv", index=False)
    comp = (res.frame().query("split_type == 'chronological test' and status in ['VALID','BASELINE']")
            .pivot_table(index="model", columns="metric", values="value")[[S.M_ACC, S.M_P1, S.M_R1, S.M_F11, S.M_AUC, S.M_BASE, BASE]].dropna(how="all"))
    comp.to_csv(evid / "E2_comparison_table.csv")
    print("\nE2 comparison table (chronological TEST block):")
    print(comp.round(4).to_string())
    for name, p in preds.items():
        S.export_predictions(p, ["user_id", "date"], evid / "predictions" / f"E2_{name.replace(' ', '_')}_test.csv")
    allf = (train.withColumn("split", F.lit("train")).unionByName(val.withColumn("split", F.lit("validation")))
            .unionByName(test.withColumn("split", F.lit("test"))))
    (allf.select("user_id", "date", "split", "label", *NUM, "day_of_week", "gender", *LEAK).toPandas()
     .sort_values(["user_id", "date"]).round(6).to_csv(evid / "predictions" / "E2_features.csv", index=False))
    S.write_run_info(evid / "E2_run_info.json", cfg, experiment=EXP, usable_rows=n, split_cuts=[str(c1), str(c2)], split_sizes=sizes,
                     positive_share=share, settings={"rf": rf_p, "gbt": gbt_p, "logreg": lr_p}, goal_steps=GOAL)
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
