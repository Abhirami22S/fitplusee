"""
FitPulse - E5 (SUPERVISED regression): same-day calories_burned  - Linear Regression kept, two tree regressors added
===================================================================================================================
E5 is KEPT: the Linear Regression, its features (steps, distance_km, active_minutes, avg/resting heart rate, age, height, weight_kg,
bmi, gender), its seeded hash split of (user_id, date) 70/15/15 and its validation-chosen regParam come from
models/train_calorie_regression.py, which is imported, not edited. Added on exactly the same rows and features:
    Random Forest Regressor   (maxDepth tuned on validation RMSE)
    Gradient-Boosted Trees Regressor (maxDepth x maxIter tuned on validation RMSE)
Baselines: training-mean prediction (MAE 334.5 kcal on the test set) and the one-feature Linear Regression on active_minutes.
Metrics: MAE, RMSE, R2 (test used once per final model). A chronological check (train < 2024-10-15) is repeated for all models.

Weight: weight_kg is KEPT here because E5 is unchanged; it is the true body weight in the calorie formula, and the target is the
same-day value (a calendar clock does not leak the label of a regression on calories). Stated as a limitation in the report.

DERIVED-DATA NOTE: calories_burned = MET(activity_type, intensity) x weight_kg x duration/60 and duration == active_minutes
(data/prepare_raw_dataset.py). The target is therefore a FORMULA of columns that are in the dataset. Linear models cannot represent the
product MET x weight x minutes, tree models can approximate it; two extra runs show the effect:
    + calories_roll7_avg  (Silver rolling mean whose window includes the day itself)       -> INVALID (leakage)
    + activity_type + intensity (these two fix the MET value)                            -> REFERENCE (formula recovery, not a skill claim)

Run:  .\\run_supervised.ps1 -Experiment E5 [-Storage hdfs]
"""
import argparse

import pandas as pd
from pyspark.ml.regression import GBTRegressor, RandomForestRegressor
from pyspark.sql import functions as F

import spark_common as sc
import sup_common as S
import train_calorie_regression as old          # E5 Linear Regression code, unchanged

EXP = "E5"
T = old.TARGET
NUM, CAT = old.NUM, old.CAT
CUTOFF = old.CUTOFF
EV = sc.EVIDENCE


def main():
    ap = argparse.ArgumentParser()
    S.add_args(ap)
    args = ap.parse_args()
    exports, evid = S.dirs(args)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-E5-supervised")
    res = S.Results(EXP)

    df = (silver.select("user_id", "date", *NUM, *CAT, T, "calories_roll7_avg", "intensity", "activity_type")
          .dropna(subset=NUM + CAT + [T]))
    df = S.row_hash(df)
    train, val, test = (df.filter("split_u < 0.70").cache(), df.filter("split_u >= 0.70 AND split_u < 0.85").cache(),
                        df.filter("split_u >= 0.85").cache())
    n_tr, n_va, n_te = train.count(), val.count(), test.count()
    print(f"rows train {n_tr:,} / val {n_va:,} / test {n_te:,}")
    cfg_old = __import__("json").loads((sc.ARTIFACTS / "calorie_linreg_config.json").read_text())
    same_split = [cfg_old["rows"][k] for k in ("train", "validation", "test")] == [n_tr, n_va, n_te]
    print("split sizes equal to the existing E5 run:", same_split)

    neg_rmse = lambda p: -S.reg_metrics(p, T)["RMSE (kcal)"]
    rf_b = lambda num, cat, depth: S.make_pipeline(num, cat, RandomForestRegressor(
        featuresCol="features", labelCol=T, numTrees=50, maxDepth=depth, maxBins=32, seed=sc.SEED))
    gbt_b = lambda num, cat, depth, iters: S.make_pipeline(num, cat, GBTRegressor(
        featuresCol="features", labelCol=T, maxDepth=depth, maxIter=iters, stepSize=0.1, maxBins=32, seed=sc.SEED))

    print("tuning on the VALIDATION set (RMSE)")
    (_, lr_p, lr), g0 = S.tune(lambda reg: old.build_pipeline(NUM, CAT, reg), S.grid(reg=[0.0, 0.01, 0.1, 1.0]), train, val, neg_rmse)
    # depth 12 exhausted the 3 GB JVM heap on this laptop (faculty_evidence/supervised/E5_run_attempt1_rf_depth12_OOM.log), so the grid stops at 10
    (_, rf_p, rf), g1 = S.tune(lambda depth: rf_b(NUM, CAT, depth), S.grid(depth=[5, 8, 10]), train, val, neg_rmse)
    (_, gbt_p, gbt), g2 = S.tune(lambda depth, iters: gbt_b(NUM, CAT, depth, iters), S.grid(depth=[3, 5], iters=[50, 100]), train, val, neg_rmse)
    pd.concat([g0.assign(model="Linear Regression"), g1.assign(model="Random Forest Regressor"),
               g2.assign(model="GBT Regressor")]).to_csv(evid / "E5_tuning_grid.csv", index=False)
    models = {"Linear Regression": (lr, f"regParam={lr_p['reg']}"), "Random Forest Regressor": (rf, f"numTrees=50, maxDepth={rf_p['depth']}"),
              "GBT Regressor": (gbt, f"maxDepth={gbt_p['depth']}, maxIter={gbt_p['iters']}")}

    # ---- baselines ----
    mean_tr = train.agg(F.avg(T)).first()[0]
    for split_name, d in (("validation", val), ("test", test)):
        res.add_many("Baseline: training mean", S.reg_metrics(d.withColumn("prediction", F.lit(float(mean_tr))), T), split_name, "BASELINE")
    one = old.Pipeline(stages=[old.VectorAssembler(inputCols=["active_minutes"], outputCol="raw"),
                               old.LinearRegression(featuresCol="raw", labelCol=T, predictionCol="prediction")]).fit(train)
    for split_name, d in (("validation", val), ("test", test)):
        res.add_many("Baseline: Linear Regression on active_minutes only", S.reg_metrics(one.transform(d), T), split_name, "BASELINE")

    # ---- evaluation ----
    preds = {}
    for name, (m, setting) in models.items():
        for split_name, d in (("validation", val), ("test", test)):
            p = m.transform(d).cache()
            met = S.reg_metrics(p, T)
            res.add_many(name, met, split_name)
            if split_name == "test":
                preds[name] = p
                print(f"{name:26s} [{setting}] test: MAE {met['MAE (kcal)']:.2f}  RMSE {met['RMSE (kcal)']:.2f}  R2 {met['R2']:.4f}")
    base_test = res.frame().query("model == 'Baseline: training mean' and split_type == 'test'").set_index("metric").value
    print(f"training-mean baseline test MAE {base_test['MAE (kcal)']:.2f} (expected 334.51)")

    # ---- reproduction of the existing E5 Linear Regression ----
    old_res = pd.read_csv(EV / "regression_results.csv")
    o = old_res[(old_res.Model == "Linear Regression (selected)") & (old_res.Set == "test")].iloc[0]
    mine = res.frame().query("model == 'Linear Regression' and split_type == 'test'").set_index("metric").value
    rep = pd.DataFrame([{"metric": k, "existing_E5": float(o[k]), "this_run": float(mine[k])} for k in ("MAE (kcal)", "RMSE (kcal)", "R2")])
    rep["abs_diff"] = (rep.existing_E5 - rep.this_run).abs()
    rep.to_csv(evid / "E5_reproduction_check.csv", index=False)
    print(f"reproduction of the existing Linear Regression test metrics: max |difference| = {rep.abs_diff.max():.2e}")

    # ---- chronological robustness check (train before the cutoff, test on/after it) ----
    ctr, cte = df.filter(F.col("date") < F.lit(CUTOFF).cast("date")).cache(), df.filter(F.col("date") >= F.lit(CUTOFF).cast("date")).cache()
    ctr_mean = ctr.agg(F.avg(T)).first()[0]
    split_c = f"chronological test (>= {CUTOFF})"
    res.add_many("Baseline: training mean", S.reg_metrics(cte.withColumn("prediction", F.lit(float(ctr_mean))), T), split_c, "BASELINE")
    for name, pipe in {"Linear Regression": old.build_pipeline(NUM, CAT, lr_p["reg"]), "Random Forest Regressor": rf_b(NUM, CAT, rf_p["depth"]),
                       "GBT Regressor": gbt_b(NUM, CAT, gbt_p["depth"], gbt_p["iters"])}.items():
        met = S.reg_metrics(pipe.fit(ctr).transform(cte), T)
        res.add_many(name, met, split_c)
        print(f"chronological {name:26s} MAE {met['MAE (kcal)']:.2f}  RMSE {met['RMSE (kcal)']:.2f}  R2 {met['R2']:.4f}")

    # ---- leakage run (INVALID) and formula-recovery reference ----
    leak_num = NUM + ["calories_roll7_avg"]
    for name, pipe in {"Linear Regression": old.build_pipeline(leak_num, CAT, lr_p["reg"]), "Random Forest Regressor": rf_b(leak_num, CAT, rf_p["depth"]),
                       "GBT Regressor": gbt_b(leak_num, CAT, gbt_p["depth"], gbt_p["iters"])}.items():
        met = S.reg_metrics(pipe.fit(train).transform(test), T)
        res.add_many(f"{name} + calories_roll7_avg incl. the day itself (LEAKAGE)", met, "test", "INVALID")
        print(f"LEAKAGE {name:26s} test MAE {met['MAE (kcal)']:.2f}  R2 {met['R2']:.4f}   -> INVALID")
    cat2 = CAT + ["activity_type", "intensity"]
    for name, pipe in {"Linear Regression": old.build_pipeline(NUM, cat2, lr_p["reg"]), "Random Forest Regressor": rf_b(NUM, cat2, rf_p["depth"]),
                       "GBT Regressor": gbt_b(NUM, cat2, gbt_p["depth"], gbt_p["iters"])}.items():
        met = S.reg_metrics(pipe.fit(train).transform(test), T)
        res.add_many(f"{name} + activity_type & intensity (formula recovery)", met, "test", "REFERENCE")
        print(f"REFERENCE formula recovery {name:26s} test MAE {met['MAE (kcal)']:.2f}  R2 {met['R2']:.4f}   (MET x weight x minutes can be reconstructed)")

    # ---- outputs ----
    res.save(exports)
    names = NUM + [c + "_idx" for c in CAT]
    pd.concat([S.feature_importance(rf, names, "Random Forest Regressor", EXP), S.feature_importance(gbt, names, "GBT Regressor", EXP)]
              ).sort_values(["model", "importance"], ascending=[True, False]).to_csv(exports / "E5_feature_importance.csv", index=False)
    S.feature_importance(lr, S.onehot_names(lr, NUM, CAT), "Linear Regression", EXP).to_csv(evid / "E5_linreg_coefficients.csv", index=False)
    comp = (res.frame().query("split_type == 'test' and status in ['VALID','BASELINE']").pivot(index="model", columns="metric", values="value")
            [["MAE (kcal)", "RMSE (kcal)", "R2"]])
    comp.to_csv(evid / "E5_comparison_table.csv")
    print("\nE5 comparison table (test set):")
    print(comp.round(4).to_string())
    for name, p in preds.items():
        S.export_predictions(p, ["user_id", "date"], evid / "predictions" / f"E5_{name.replace(' ', '_')}_test.csv", label_col=T)
    (df.select("user_id", "date", F.when(F.col("split_u") < 0.70, "train").when(F.col("split_u") < 0.85, "validation").otherwise("test").alias("split"))
     .toPandas().sort_values(["user_id", "date"]).to_csv(evid / "predictions" / "E5_splits.csv", index=False))
    S.write_run_info(evid / "E5_run_info.json", cfg, experiment=EXP, rows={"train": n_tr, "validation": n_va, "test": n_te}, same_split_as_existing_E5=same_split,
                     settings={"linreg": lr_p, "rf": rf_p, "gbt": gbt_p}, reproduction_max_abs_diff=float(rep.abs_diff.max()),
                     train_mean_kcal=float(mean_tr))
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
