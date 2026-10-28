"""
FitPulse - E3 (SUPERVISED): user-level classifier  high_achiever  (replaces the archived K-Means on 437 users)
===========================================================================================================
One row per USER (437). Label: high_achiever = 1 if the user's goal-achievement rate over ALL their days
(share of days with steps >= 8,000) is ABOVE the median rate across users (strict ">", so 218 vs 219 users).
Features (9, none step- or distance-based):  age, bmi, height_cm, baseline weight, avg heart rate, avg sleep minutes,
avg active minutes, avg stress, avg hydration.
 * weight: weight_kg drifts with the calendar inside each user (correlation 0.991 with month), so a user's AVERAGE weight_kg
   mostly measures WHICH MONTHS they logged. It is replaced by baseline weight = bmi x (height/100)^2 (decision recorded with
   the user); the raw-average-weight version is run only as a labelled ablation (REFERENCE).
 * the label threshold (median) uses all 437 users, as specified; this is a label definition, not a feature.
Evaluation: stratified 5-fold cross-validation (seed 42); inside every outer training set the hyper-parameters are chosen on an
inner stratified validation part (nested), so no fold's test users ever influence tuning. Every user is in a test fold once;
metrics are pooled over the out-of-fold predictions (and fold mean / sd are reported too).
Models: Random Forest and Logistic Regression, against the majority-class baseline.
Leakage run: average steps added -> INVALID (the label is a threshold on steps).
Reference runs (NOT valid claims of skill): logging-window coverage alone (mean logged month); raw average weight_kg.

Run:  .\\run_supervised.ps1 -Experiment E3 [-Storage hdfs]
"""
import argparse

import numpy as np
import pandas as pd
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.sql import Window
from pyspark.sql import functions as F

import spark_common as sc
import sup_common as S

EXP = "E3"
GOAL = 8000
FEATURES = ["age", "bmi", "height_cm", "weight_baseline_kg", "avg_heart_rate", "avg_sleep_minutes", "avg_active_minutes",
            "avg_stress", "avg_hydration"]
SPLIT = "stratified 5-fold CV (out-of-fold)"


def user_table(silver):
    d = silver.dropDuplicates(["user_id", "date"])
    u = d.groupBy("user_id").agg(
        F.avg((F.col("steps") >= GOAL).cast("double")).alias("rate"), F.avg("age").alias("age"), F.avg("bmi").alias("bmi"),
        F.avg("height_cm").alias("height_cm"), F.avg("avg_heart_rate").alias("avg_heart_rate"), F.avg("sleep_minutes").alias("avg_sleep_minutes"),
        F.avg("active_minutes").alias("avg_active_minutes"), F.avg("stress_level").alias("avg_stress"), F.avg("hydration_level").alias("avg_hydration"),
        F.avg("weight_kg").alias("avg_weight_kg_raw"), F.avg("steps").alias("avg_steps"), F.avg(F.month("date").cast("double")).alias("mean_logged_month"),
        F.count("*").alias("days_logged"))
    return u.withColumn("weight_baseline_kg", F.col("bmi") * F.pow(F.col("height_cm") / 100.0, 2))


def strat_rank(df, seed, by="label"):
    """Deterministic stratified ranking: users sorted by a hash within each class (no dependence on partition order)."""
    return df.withColumn("rk", F.row_number().over(Window.partitionBy(by).orderBy(F.xxhash64("user_id", F.lit(seed)))))


def cv_eval(users, num, specs, auc_ev, folds=5):
    """Nested stratified CV. specs: name -> (builder(num, **params), grid). Returns {name: (oof_pred_df, [chosen params per fold])}."""
    out = {}
    for name, (builder, pgrid) in specs.items():
        pieces, chosen = [], []
        for k in range(folds):
            tr, te = users.filter(F.col("fold") != k), users.filter(F.col("fold") == k)
            inner = strat_rank(tr, sc.SEED + 7)
            in_val, in_tr = inner.filter(F.col("rk") % 4 == 0).cache(), inner.filter(F.col("rk") % 4 != 0).cache()
            best = None
            for params in pgrid:
                try:
                    m = builder(num, **params).fit(in_tr)
                    v = auc_ev.evaluate(m.transform(in_val))
                except Exception:                                     # noqa: BLE001
                    continue
                if best is None or v > best[0]:
                    best = (v, params)
            model = builder(num, **best[1]).fit(tr)
            pieces.append(model.transform(te).withColumn("fold", F.lit(k)))
            chosen.append(best[1])
        oof = pieces[0]
        for p in pieces[1:]:
            oof = oof.unionByName(p)
        out[name] = (oof.cache(), chosen)
    return out


def summarise(res, name, oof, split, status="VALID", keys=None):
    met, cm = S.cls_metrics(oof)
    res.add_many(name, {k: v for k, v in met.items() if keys is None or k in keys}, split, status)
    # fold mean / sd (accuracy and AUC per fold)
    accs, aucs = [], []
    for k in range(5):
        f = oof.filter(F.col("fold") == k)
        m, _ = S.cls_metrics(f)
        accs.append(m[S.M_ACC]); aucs.append(m[S.M_AUC])
    res.add(name, "Accuracy (mean over folds)", np.mean(accs), split, status)
    res.add(name, "Accuracy (sd over folds)", np.std(accs, ddof=1), split, status)
    res.add(name, "ROC AUC (mean over folds)", np.mean(aucs), split, status)
    res.add(name, "ROC AUC (sd over folds)", np.std(aucs, ddof=1), split, status)
    return met, cm


def main():
    ap = argparse.ArgumentParser()
    S.add_args(ap)
    args = ap.parse_args()
    exports, evid = S.dirs(args)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-E3-supervised")
    res = S.Results(EXP)

    u = user_table(silver).cache()
    rates = np.array([r[0] for r in u.select("rate").collect()])
    median = float(np.median(rates))
    u = u.withColumn("label", (F.col("rate") > F.lit(median)).cast("double"))
    # stratified fold = rank within class (hash order) mod 5
    ranked = strat_rank(u, sc.SEED)
    users = ranked.withColumn("fold", (F.col("rk") - 1) % 5).cache()
    n, pos = users.count(), int(users.agg(F.sum("label")).first()[0])
    print(f"users {n}; median goal rate {median:.4f}; high achievers {pos} / {n} (majority baseline {max(pos, n - pos) / n:.3f}); "
          f"rate range {rates.min():.3f}-{rates.max():.3f}")
    print("users per fold:", {r["fold"]: r["count"] for r in users.groupBy("fold").count().collect()})
    auc_ev = BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")

    rf_b = lambda num, trees, depth: S.make_pipeline(num, [], RandomForestClassifier(
        featuresCol="features", labelCol="label", numTrees=trees, maxDepth=depth, seed=sc.SEED))
    lr_b = lambda num, reg: S.make_pipeline(num, [], LogisticRegression(
        featuresCol="features", labelCol="label", regParam=reg, elasticNetParam=0.0, maxIter=300, standardization=False), scale=True)
    specs = {"Random Forest": (rf_b, S.grid(trees=[100], depth=[2, 4])),
             "Logistic Regression": (lr_b, S.grid(reg=[0.01, 0.1, 1.0, 10.0]))}

    # ---- main experiment ----
    out = cv_eval(users, FEATURES, specs, auc_ev)
    for name, (oof, chosen) in out.items():
        met, cm = summarise(res, name, oof, SPLIT)
        print(f"{name:20s} OOF acc {met[S.M_ACC]:.4f}  F1w {met[S.M_F1W]:.4f}  AUC {met[S.M_AUC]:.4f} | majority baseline {met[S.M_BASE]:.4f}  "
              f"CM(tn,fp,fn,tp)={cm}  chosen per fold: {chosen}")
        S.export_predictions(oof, ["user_id"], evid / "predictions" / f"E3_{name.replace(' ', '_')}_oof.csv")
    mode_params = {name: max(chosen, key=chosen.count) for name, (_, chosen) in out.items()}

    # ---- leakage run: average steps added -> INVALID ----
    leak = cv_eval(users, FEATURES + ["avg_steps"], {n_: (b, [mode_params[n_]]) for n_, (b, _) in specs.items()}, auc_ev)
    for name, (oof, _) in leak.items():
        met, _ = summarise(res, f"{name} + average steps (LEAKAGE)", oof, SPLIT, "INVALID", keys=(S.M_ACC, S.M_AUC, S.M_BASE))
        print(f"LEAKAGE {name:20s} OOF acc {met[S.M_ACC]:.4f}  AUC {met[S.M_AUC]:.4f}   -> INVALID (label = threshold on steps)")

    # ---- reference runs (not valid claims of skill) ----
    cover = cv_eval(users, ["mean_logged_month"], {n_: (b, [mode_params[n_]]) for n_, (b, _) in specs.items()}, auc_ev)
    for name, (oof, _) in cover.items():
        met, _ = summarise(res, f"{name}: logging-window coverage ONLY (mean logged month)", oof, SPLIT, "REFERENCE", keys=(S.M_ACC, S.M_AUC, S.M_BASE))
        print(f"REFERENCE coverage-only {name:20s} acc {met[S.M_ACC]:.4f}  AUC {met[S.M_AUC]:.4f}")
    raw_feats = [f if f != "weight_baseline_kg" else "avg_weight_kg_raw" for f in FEATURES]
    rawabl = cv_eval(users, raw_feats, {n_: (b, [mode_params[n_]]) for n_, (b, _) in specs.items()}, auc_ev)
    for name, (oof, _) in rawabl.items():
        met, _ = summarise(res, f"{name}: raw average weight_kg instead of baseline weight (ablation)", oof, SPLIT, "REFERENCE", keys=(S.M_ACC, S.M_AUC, S.M_BASE))
        print(f"REFERENCE raw weight {name:20s} acc {met[S.M_ACC]:.4f}  AUC {met[S.M_AUC]:.4f}")

    # ---- outputs ----
    res.save(exports)
    rf_full = rf_b(FEATURES, **mode_params["Random Forest"]).fit(users)
    lr_full = lr_b(FEATURES, **mode_params["Logistic Regression"]).fit(users)
    S.feature_importance(rf_full, FEATURES, "Random Forest", EXP).sort_values("importance", ascending=False).to_csv(
        exports / "E3_feature_importance.csv", index=False)
    S.feature_importance(lr_full, FEATURES, "Logistic Regression", EXP).to_csv(evid / "E3_logreg_coefficients.csv", index=False)
    comp = (res.frame().query("split_type == @SPLIT and status == 'VALID'").pivot(index="model", columns="metric", values="value")
            [[S.M_ACC, S.M_F1W, S.M_AUC, S.M_BASE]])
    comp.to_csv(evid / "E3_comparison_table.csv")
    print("\nE3 comparison table (pooled out-of-fold, stratified 5-fold):")
    print(comp.round(4).to_string())
    (users.select("user_id", "fold", "label", "rate", *FEATURES, "avg_weight_kg_raw", "avg_steps", "mean_logged_month", "days_logged")
     .toPandas().sort_values("user_id").to_csv(evid / "predictions" / "E3_user_table.csv", index=False))
    S.write_run_info(evid / "E3_run_info.json", cfg, experiment=EXP, users=n, high_achievers=pos, median_rate=median,
                     chosen_settings_per_fold={k: v[1] for k, v in out.items()}, mode_settings=mode_params, features=FEATURES)
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
