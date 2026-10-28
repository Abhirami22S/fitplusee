"""
FitPulse - REPORT-aligned Random Forest (Spark MLlib): same-day goal  steps >= 8,000
======================================================================================
Implements exactly what REPORT section 2 describes (Listings 1-4, Tables 5, 8-10), which the repository did not
contain (the report's numbers came from scikit-learn). It is a DIFFERENT experiment from
 * the faculty notebook's Random Forest (next-day achievement of a personalised goal, lag features), and
 * the dashboard's Logistic Regression (models/train_goal_achievement.py).

Target  : label = 1 if steps >= 8,000 (same day)
Inputs  : 15 numeric (incl. engineered active_ratio) + 3 categorical (Table 5). steps and distance_km are excluded (leakage).
Split   : DataFrame.randomSplit([0.70, 0.15, 0.15], seed=42)  (as in Listing 2)
Tuning  : numTrees {50,100} x maxDepth {5,10,15,20}, best validation ROC-AUC (as in section 2.2)
Extra   : (a) leakage demonstration (steps + distance_km included), (b) user-held-out check quoted in section 2.5.

Run:  FITPULSE_DRIVER_MEMORY=3g python models/spark_report_classification.py --storage hdfs --hdfs-uri hdfs://localhost:9000
Writes to faculty_evidence/report_aligned/.
"""
import argparse
import time

import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.sql import functions as F

import spark_common as sc

GOAL_STEPS = 8000
NUM = ["active_minutes", "sedentary_minutes", "calories_burned", "avg_heart_rate", "max_heart_rate",
       "resting_heart_rate", "sleep_minutes", "sleep_quality_score", "active_ratio", "age", "bmi", "height_cm",
       "weight_kg", "stress_level", "hydration_level"]
CAT = ["intensity", "activity_type", "gender"]


def pipeline(num, depth, trees):
    idx = [StringIndexer(inputCol=c, outputCol=c + "_idx", handleInvalid="keep") for c in CAT]
    asm = VectorAssembler(inputCols=num + [c + "_idx" for c in CAT], outputCol="features")
    rf = RandomForestClassifier(featuresCol="features", labelCol="label", numTrees=trees, maxDepth=depth,
                                maxBins=32, seed=sc.SEED)
    return Pipeline(stages=idx + [asm, rf])


def full_metrics(pred):
    mc = lambda m, **kw: MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName=m, **kw).evaluate(pred)
    return {
        "Accuracy": mc("accuracy"), "Precision (weighted)": mc("weightedPrecision"), "Recall (weighted)": mc("weightedRecall"),
        "F1 (weighted)": mc("f1"),
        "Precision (goal-achieved class)": mc("precisionByLabel", metricLabel=1.0),
        "Recall (goal-achieved class)": mc("recallByLabel", metricLabel=1.0),
        "F1 (goal-achieved class)": mc("fMeasureByLabel", metricLabel=1.0),
        "ROC AUC": BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC").evaluate(pred),
        "Baseline accuracy (always majority class)": pred.filter("label = 1").count() / pred.count()
        if pred.filter("label = 1").count() >= pred.count() / 2 else pred.filter("label = 0").count() / pred.count(),
    }


def main():
    ap = argparse.ArgumentParser()
    sc.add_storage_args(ap)
    ap.add_argument("--depths", default="5,10,15,20")
    ap.add_argument("--trees", default="50,100")
    ap.add_argument("--skip", default="", help="comma list like 100x15,100x20 of grid points NOT run because they "
                    "crashed the JVM with OutOfMemoryError on this laptop (recorded as such in the grid CSV)")
    args = ap.parse_args()
    out = sc.out_dir(args) / "report_aligned"
    out.mkdir(parents=True, exist_ok=True)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-Report-RF")

    df = (silver.dropDuplicates(["user_id", "date"])
          .withColumn("label", (F.col("steps") >= GOAL_STEPS).cast("double"))
          .withColumn("active_ratio", F.col("active_minutes") / (F.col("active_minutes") + F.col("sedentary_minutes")))
          .select("user_id", "date", "label", "steps", "distance_km", *NUM, *CAT).cache())
    n = df.count()
    pos = df.filter("label = 1").count() / n
    print(f"records {n:,}; share meeting goal = {pos:.4f}")
    train, val, test = df.randomSplit([0.70, 0.15, 0.15], seed=sc.SEED)
    train, val, test = train.cache(), val.cache(), test.cache()
    split = pd.DataFrame([("Training", train.count()), ("Validation", val.count()), ("Test", test.count())], columns=["Set", "Records"])
    print(split.to_string(index=False))
    split.to_csv(out / "rf_split_sizes.csv", index=False)

    auc = BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC")
    grid, best = [], None
    for trees in [int(x) for x in args.trees.split(",")]:
        for depth in [int(x) for x in args.depths.split(",")]:
            t0 = time.time()
            if f"{trees}x{depth}" in args.skip.split(","):
                grid.append({"numTrees": trees, "maxDepth": depth, "validation_ROC_AUC": float("nan"), "seconds": 0,
                             "status": "NOT RUN: OutOfMemoryError (JVM heap) in the first full-grid attempt, see log_report_rf_hdfs_attempt1_full_grid.txt"})
                print(grid[-1])
                continue
            try:
                m = pipeline(NUM, depth, trees).fit(train)
                v = auc.evaluate(m.transform(val))
                status = "ok"
            except Exception as e:      # e.g. JVM out-of-memory at depth 20 on this laptop - recorded, not hidden
                m, v, status = None, float("nan"), f"FAILED: {type(e).__name__}"
            grid.append({"numTrees": trees, "maxDepth": depth, "validation_ROC_AUC": v, "seconds": round(time.time() - t0, 1), "status": status})
            print(grid[-1])
            if m is not None and (best is None or v > best[0]):
                best = (v, trees, depth, m)
    pd.DataFrame(grid).to_csv(out / "rf_tuning_grid.csv", index=False)
    _, b_trees, b_depth, model = best
    print(f"selected numTrees={b_trees}, maxDepth={b_depth}")

    rows = []
    preds = {}
    for name, d in [("Validation", val), ("Test", test)]:
        p = model.transform(d).cache()
        preds[name] = p
        for k, v in full_metrics(p).items():
            rows.append({"Metric": k, "Set": name, "Value": v})
    metrics = pd.DataFrame(rows).pivot(index="Metric", columns="Set", values="Value").reset_index()
    metrics.to_csv(out / "rf_metrics.csv", index=False)
    print(metrics.round(4).to_string(index=False))

    cm = (preds["Test"].groupBy("label", "prediction").count().toPandas()
          .pivot(index="label", columns="prediction", values="count").fillna(0).astype(int))
    cm.index = ["Actual 0 (not achieved)", "Actual 1 (achieved)"]
    cm.columns = ["Predicted 0", "Predicted 1"]
    cm.to_csv(out / "rf_confusion_matrix.csv")
    print(cm)

    rf = model.stages[-1]
    names = NUM + [c + "_idx" for c in CAT]
    imp = pd.DataFrame({"feature": names, "importance": list(rf.featureImportances.toArray())}).sort_values("importance", ascending=False)
    imp.to_csv(out / "rf_feature_importance.csv", index=False)
    print(imp.head(8).round(4).to_string(index=False))

    # (a) leakage demonstration: add steps + distance_km
    leak = pipeline(NUM + ["steps", "distance_km"], b_depth, b_trees).fit(train)
    la = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy").evaluate(leak.transform(test))
    # (b) user-held-out: 15% of users never seen in training
    u = df.withColumn("u", (F.abs(F.xxhash64("user_id", F.lit(sc.SEED))) % 1000) / 1000.0)
    utr, ute = u.filter("u < 0.85"), u.filter("u >= 0.85")
    um = pipeline(NUM, b_depth, b_trees).fit(utr)
    up = um.transform(ute)
    ua = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy").evaluate(up)
    uauc = auc.evaluate(up)
    extra = pd.DataFrame([
        ("RF with steps + distance_km included (leakage demo), test accuracy", la),
        ("User-held-out (15% of users unseen), accuracy", ua), ("User-held-out, ROC AUC", uauc),
        ("User-held-out: users in held-out set", ute.select("user_id").distinct().count())],
        columns=["Check", "Value"])
    extra.to_csv(out / "rf_extra_checks.csv", index=False)
    print(extra.to_string(index=False))
    pd.Series({"storage_mode": cfg.mode, "silver_source": cfg.output_path, "numTrees": b_trees, "maxDepth": b_depth,
               "records": n, "positive_share": pos}).to_json(out / "rf_run_info.json", indent=2)
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
