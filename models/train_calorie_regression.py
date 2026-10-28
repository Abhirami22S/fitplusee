"""
FitPulse - Model: Calorie-burn prediction with Linear Regression (Spark MLlib)
================================================================================
Task (REPORT 1.5 / PPT slide 3): estimate a day's `calories_burned` from step count, distance, active duration,
heart rate and demographic features.

Target       : calories_burned (same-day estimation, kcal). This is an *estimation* model for the day just recorded
               (e.g. a wearable that reports steps/heart rate but no energy figure), NOT a forecast of tomorrow.
Features     : steps, distance_km, active_minutes, avg_heart_rate, resting_heart_rate, age, height_cm, weight_kg,
               bmi, gender (one-hot).
Not used     : sedentary_minutes / sleep_minutes (active + sedentary + sleep = 1,440, so they are linearly dependent),
               calories_lag1 / calories_roll7_avg / daily_calorie_goal (derived from the target's own column or its
               user average -> leakage), user_id, date.
Preprocessing: StringIndexer/OneHotEncoder + StandardScaler are fitted on the TRAINING split only (they sit inside the
               Pipeline that is fitted on `train`).
Split        : seeded hash 70/15/15 of (user_id, date)  [same method as the faculty notebook];
               robustness check: chronological split (train < 2024-10-15, test >= 2024-10-15).
Selection    : regParam in {0, 0.01, 0.1, 1.0} (elasticNet 0 = ridge) chosen on the validation set by RMSE.
Baselines    : (a) predict the training-set mean; (b) one-feature Linear Regression on active_minutes.

Run:  python models/train_calorie_regression.py [--storage hdfs --hdfs-uri hdfs://localhost:9000]
Outputs: faculty_evidence/regression_results.csv, regression_coefficients.csv, regression_predictions.csv,
         regression_actual_vs_predicted.png, models/artifacts/calorie_linreg_config.json,
         models/artifacts/calorie_linreg_spark/ (saved Spark PipelineModel)
"""
import argparse
import json
import shutil
import time

import numpy as np
import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.sql import functions as F

import spark_common as sc

TARGET = "calories_burned"
NUM = ["steps", "distance_km", "active_minutes", "avg_heart_rate", "resting_heart_rate",
       "age", "height_cm", "weight_kg", "bmi"]
CAT = ["gender"]
CUTOFF = "2024-10-15"


def build_pipeline(num, cat, reg):
    stages = [StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="error") for c in cat]
    if cat:
        stages.append(OneHotEncoder(inputCols=[f"{c}_idx" for c in cat], outputCols=[f"{c}_ohe" for c in cat]))
    stages.append(VectorAssembler(inputCols=num + [f"{c}_ohe" for c in cat], outputCol="raw"))
    stages.append(StandardScaler(inputCol="raw", outputCol="features", withMean=True, withStd=True))
    stages.append(LinearRegression(featuresCol="features", labelCol=TARGET, predictionCol="prediction",
                                   regParam=reg, elasticNetParam=0.0, maxIter=200, standardization=False))
    return Pipeline(stages=stages)


def metrics(df, pred_col="prediction"):
    out = {}
    for m, name in [("mae", "MAE"), ("rmse", "RMSE"), ("r2", "R2")]:
        out[name] = RegressionEvaluator(labelCol=TARGET, predictionCol=pred_col, metricName=m).evaluate(df)
    return out


def main():
    ap = argparse.ArgumentParser()
    sc.add_storage_args(ap)
    args = ap.parse_args()
    out = sc.out_dir(args)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-CalorieLinReg")

    cols = ["user_id", "date", "month", "activity_type"] + NUM + CAT + [TARGET]
    df = silver.select(*cols).dropna(subset=NUM + CAT + [TARGET])
    n_all = df.count()
    df = df.withColumn("split_u", (F.abs(F.xxhash64("user_id", "date", F.lit(sc.SEED))) % 1_000_000) / 1_000_000.0)
    train = df.filter("split_u < 0.70").cache()
    val = df.filter("split_u >= 0.70 AND split_u < 0.85").cache()
    test = df.filter("split_u >= 0.85").cache()
    n_tr, n_va, n_te = train.count(), val.count(), test.count()
    print(f"rows used {n_all:,} -> train {n_tr:,} / val {n_va:,} / test {n_te:,}")

    # ---- baselines ----
    mean_tr = train.agg(F.avg(TARGET)).first()[0]
    base_mean = {k: v for k, v in metrics(test.withColumn("prediction", F.lit(float(mean_tr)))).items()}
    base_mean_val = metrics(val.withColumn("prediction", F.lit(float(mean_tr))))
    one = Pipeline(stages=[VectorAssembler(inputCols=["active_minutes"], outputCol="raw"),
                           LinearRegression(featuresCol="raw", labelCol=TARGET, predictionCol="prediction")]).fit(train)
    base_one = metrics(one.transform(test))
    base_one_val = metrics(one.transform(val))

    # ---- tuning on validation ----
    rows, best = [], None
    for reg in [0.0, 0.01, 0.1, 1.0]:
        t0 = time.time()
        m = build_pipeline(NUM, CAT, reg).fit(train)
        v = metrics(m.transform(val))
        rows.append({"regParam": reg, **{f"val_{k}": v[k] for k in v}, "fit_seconds": round(time.time() - t0, 1)})
        if best is None or v["RMSE"] < best[0]["RMSE"]:
            best = (v, reg, m)
    tuning = pd.DataFrame(rows)
    print(tuning.round(4).to_string(index=False))
    _, best_reg, model = best

    # ---- final test evaluation (test used once) ----
    pred_test = model.transform(test)
    mt = metrics(pred_test)
    mv = metrics(model.transform(val))
    mtr = metrics(model.transform(train))

    # ---- chronological robustness check (same pipeline/hyper-parameters, refit on the earlier period only) ----
    chrono_tr = df.filter(F.col("date") < F.lit(CUTOFF).cast("date"))
    chrono_te = df.filter(F.col("date") >= F.lit(CUTOFF).cast("date"))
    chrono_model = build_pipeline(NUM, CAT, best_reg).fit(chrono_tr)
    mc = metrics(chrono_model.transform(chrono_te))
    mean_c = chrono_tr.agg(F.avg(TARGET)).first()[0]
    mc_base = metrics(chrono_te.withColumn("prediction", F.lit(float(mean_c))))

    res = pd.DataFrame([
        ("Linear Regression (selected)", "validation", mv["MAE"], mv["RMSE"], mv["R2"], n_va),
        ("Linear Regression (selected)", "test", mt["MAE"], mt["RMSE"], mt["R2"], n_te),
        ("Linear Regression (selected)", "train (in-sample)", mtr["MAE"], mtr["RMSE"], mtr["R2"], n_tr),
        ("Baseline: training mean", "validation", base_mean_val["MAE"], base_mean_val["RMSE"], base_mean_val["R2"], n_va),
        ("Baseline: training mean", "test", base_mean["MAE"], base_mean["RMSE"], base_mean["R2"], n_te),
        ("Baseline: LinReg on active_minutes only", "validation", base_one_val["MAE"], base_one_val["RMSE"], base_one_val["R2"], n_va),
        ("Baseline: LinReg on active_minutes only", "test", base_one["MAE"], base_one["RMSE"], base_one["R2"], n_te),
        (f"Chronological check: Linear Regression (train<{CUTOFF})", "test (>= cutoff)", mc["MAE"], mc["RMSE"], mc["R2"], chrono_te.count()),
        (f"Chronological check: training-mean baseline", "test (>= cutoff)", mc_base["MAE"], mc_base["RMSE"], mc_base["R2"], chrono_te.count()),
    ], columns=["Model", "Set", "MAE (kcal)", "RMSE (kcal)", "R2", "Rows"])
    res.to_csv(out / "regression_results.csv", index=False)
    tuning.to_csv(out / "regression_tuning.csv", index=False)
    print(res.round(4).to_string(index=False))

    # ---- coefficients (on standardised inputs and in original units) ----
    lr = model.stages[-1]
    scaler = model.stages[-2]
    cat_labels = model.stages[0].labelsArray[0]            # StringIndexer labels (frequency order)
    # OneHotEncoder drops the last category by default -> labels[:-1] are encoded
    names = NUM + [f"{CAT[0]}={l}" for l in cat_labels[:-1]]
    coef_std = np.array(lr.coefficients)
    sd = np.array(scaler.std)
    mu = np.array(scaler.mean)
    coef_raw = coef_std / sd
    intercept_raw = float(lr.intercept - np.sum(coef_std * mu / sd))
    coef_df = pd.DataFrame({"feature": names, "coef_per_std": coef_std, "coef_original_units": coef_raw})
    coef_df.to_csv(out / "regression_coefficients.csv", index=False)
    print(coef_df.round(4).to_string(index=False))

    # ---- predictions for every row (split label kept: in-sample rows are flagged) ----
    allp = model.transform(df).select("user_id", "date", "month", "activity_type", F.col(TARGET).alias("actual_calories"),
                                      F.round("prediction", 2).alias("predicted_calories"),
                                      F.when(F.col("split_u") < 0.70, "train").when(F.col("split_u") < 0.85, "validation")
                                      .otherwise("test").alias("split"))
    pdf = allp.orderBy("user_id", "date").toPandas()
    pdf.to_csv(out / "regression_predictions.csv", index=False)
    t = pdf[pdf.split == "test"]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    s = t.sample(min(4000, len(t)), random_state=sc.SEED)
    ax[0].scatter(s.actual_calories, s.predicted_calories, s=5, alpha=0.35, color="#2a78d6")
    lim = [0, max(s.actual_calories.max(), s.predicted_calories.max())]
    ax[0].plot(lim, lim, color="#eb6834", lw=1)
    ax[0].set(xlabel="Actual calories (kcal)", ylabel="Predicted calories (kcal)", title="Test set: actual vs predicted")
    resid = t.actual_calories - t.predicted_calories
    ax[1].hist(resid, bins=60, color="#2a78d6")
    ax[1].set(xlabel="Residual = actual - predicted (kcal)", ylabel="Days", title="Test-set residuals")
    fig.tight_layout()
    fig.savefig(out / "regression_actual_vs_predicted.png", dpi=130)

    # ---- save model + exact configuration ----
    sc.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    mdir = sc.ARTIFACTS / "calorie_linreg_spark"
    if mdir.exists():
        shutil.rmtree(mdir)                      # only this script's own artifact directory
    model.write().overwrite().save(sc.storage.local_uri(str(mdir)))
    config = {
        "task": "same-day calorie-burn estimation (not a forecast)", "target": TARGET, "numeric_features": NUM,
        "categorical_features": CAT, "excluded_for_leakage_or_collinearity":
            ["sedentary_minutes", "sleep_minutes", "calories_lag1", "calories_roll7_avg", "daily_calorie_goal"],
        "split": "seeded xxhash64(user_id, date, 42) -> 70/15/15", "seed": sc.SEED, "regParam": best_reg, "elasticNetParam": 0.0,
        "rows": {"train": n_tr, "validation": n_va, "test": n_te},
        "storage_mode": cfg.mode, "silver_source": cfg.output_path,
        "intercept_original_units": intercept_raw,
        "coefficients_original_units": dict(zip(names, map(float, coef_raw))),
        "test_metrics": mt, "baseline_mean_test_metrics": base_mean,
        "gender_labels_encoded": list(cat_labels[:-1]), "gender_reference_category": cat_labels[-1],
    }
    (sc.ARTIFACTS / "calorie_linreg_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("\nSaved model + config. Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
