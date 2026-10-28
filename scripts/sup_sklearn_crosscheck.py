"""
FitPulse - independent scikit-learn cross-check of the SUPERVISED experiments E1-E5 (nothing here uses Spark)
==============================================================================================================
For every experiment whose evidence exists, two kinds of check are made:

 (a) METRIC RECOMPUTATION - the metrics are recomputed with sklearn.metrics from the test predictions Spark saved
     (faculty_evidence/supervised/predictions/). They must equal the numbers in exports/E<n>_results.csv.
     Tolerance: 1e-9 for accuracy / F1 / MAE / RMSE / R2; 2e-3 for ROC-AUC (Spark's evaluator bins scores).
 (b) INDEPENDENT REFIT - a model is fitted again in scikit-learn on exactly the same rows (same split, same features) and its
     test metric is compared with Spark's. Linear / logistic regression are convex, so they must agree closely (tolerance stated
     per row). Tree models are different implementations, so only APPROXIMATE agreement is expected (wide tolerance, labelled).

Silver is read from the LOCAL Parquet (proven row-for-row identical to the HDFS Silver by scripts/verify_hdfs.py).

    python scripts/sup_sklearn_crosscheck.py [--dir faculty_evidence/supervised/hdfs_rerun]
Writes <dir>/sklearn_crosscheck.csv; exit code 1 if any check fails, 0 otherwise (checks for missing experiments are skipped).
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
                             precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
SEED = 42
rows = []


def check(exp, name, spark_v, sk_v, tol, kind="recompute"):
    ok = abs(float(spark_v) - float(sk_v)) <= tol
    rows.append({"experiment": exp, "check": name, "kind": kind, "spark_value": float(spark_v), "sklearn_value": float(sk_v),
                 "abs_diff": abs(float(spark_v) - float(sk_v)), "tolerance": tol, "pass": ok})
    print(f"[{'PASS' if ok else 'FAIL'}] {exp} {name}: spark {float(spark_v):.6f} vs sklearn {float(sk_v):.6f} (tol {tol})")


def silver():
    s = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
    s["date"] = pd.to_datetime(s["date"])
    return s.drop_duplicates(["user_id", "date"])


def read_pred(ev, name):
    p = pd.read_csv(ev / "predictions" / name)
    if "date" in p.columns:
        p["date"] = pd.to_datetime(p["date"])
    return p


def result(res, model, metric, split):
    r = res[(res.model == model) & (res.metric == metric) & (res.split_type == split) & (res.status == "VALID")]
    return float(r.value.iloc[0])


# ------------------------------------------------------------------------------------------------------------- E1
def e1(ev, ex):
    res = pd.read_csv(ex / "E1_results.csv")
    info = json.loads((ev / "E1_run_info.json").read_text())
    names = {"Random Forest": "Random_Forest", "Logistic Regression": "Logistic_Regression", "Gradient-Boosted Trees": "Gradient-Boosted_Trees"}
    for model, f in names.items():
        for split in ("validation", "test"):
            p = read_pred(ev, f"E1_{f}_{split}.csv")
            y, yhat, sc = p.label.astype(int), p.prediction.astype(int), p.score
            check("E1", f"{model}: {split} accuracy recomputed", result(res, model, "Accuracy", split), accuracy_score(y, yhat), 1e-9)
            check("E1", f"{model}: {split} weighted F1 recomputed", result(res, model, "F1 (weighted)", split), f1_score(y, yhat, average="weighted"), 1e-9)
            check("E1", f"{model}: {split} ROC-AUC recomputed", result(res, model, "ROC AUC", split), roc_auc_score(y, sc), 2e-3)
            check("E1", f"{model}: {split} majority baseline recomputed", result(res, model, "Baseline accuracy (always majority class)", split),
                  max(y.mean(), 1 - y.mean()), 1e-9)
    # independent refit on the SAME rows (split file exported by Spark)
    import importlib.util
    spec = importlib.util.spec_from_file_location("old_e1", ROOT / "models" / "spark_report_classification.py")
    src = (ROOT / "models" / "spark_report_classification.py").read_text()
    NUM = eval(src.split("NUM = ")[1].split("\nCAT")[0])
    CAT = eval(src.split("CAT = ")[1].split("\n")[0])
    s = silver()
    s["label"] = (s.steps >= 8000).astype(int)
    s["active_ratio"] = s.active_minutes / (s.active_minutes + s.sedentary_minutes)
    sp = read_pred(ev, "E1_splits.csv")
    d = s.merge(sp, on=["user_id", "date"], how="inner")
    X = pd.get_dummies(d[NUM + CAT], columns=CAT).astype(float)
    tr, te = (d.split == "train").to_numpy(), (d.split == "test").to_numpy()
    scaler = StandardScaler().fit(X[tr])
    reg = info["logreg_setting"]["reg"]
    lr = LogisticRegression(C=1.0 / (reg * tr.sum()) if reg > 0 else 1e12, max_iter=2000).fit(scaler.transform(X[tr]), d.label[tr])
    prob = lr.predict_proba(scaler.transform(X[te]))[:, 1]
    check("E1", "Logistic Regression: independent sklearn refit, test accuracy", result(res, "Logistic Regression", "Accuracy", "test"),
          accuracy_score(d.label[te], prob >= .5), 0.005, "refit")
    check("E1", "Logistic Regression: independent sklearn refit, test ROC-AUC", result(res, "Logistic Regression", "ROC AUC", "test"),
          roc_auc_score(d.label[te], prob), 0.005, "refit")
    Xc = d[NUM].copy()
    for c in CAT:
        Xc[c] = d[c].astype("category").cat.codes
    st = info["rf_setting"]
    rf = RandomForestClassifier(n_estimators=st["numTrees"], max_depth=st["maxDepth"], random_state=SEED, n_jobs=-1).fit(Xc[tr], d.label[tr])
    check("E1", "Random Forest: independent sklearn refit (approximate, different implementation), test ROC-AUC",
          result(res, "Random Forest", "ROC AUC", "test"), roc_auc_score(d.label[te], rf.predict_proba(Xc[te])[:, 1]), 0.03, "refit (approx.)")


# ------------------------------------------------------------------------------------------------------------- E2
E2_NUM = ["steps_lag1", "steps_lag2", "steps_mean3", "steps_mean7", "steps_std7", "goal_rate7", "calories_mean7", "active_minutes_mean7",
          "sleep_quality_mean7", "sleep_minutes_mean7", "resting_hr_mean7", "stress_mean7", "month_sin", "month_cos", "age", "bmi",
          "height_cm", "weight_baseline_kg"]
E2_CAT = ["day_of_week", "gender"]


def e2_features(s):
    """Independent pandas implementation of the E2 features: every history value is shift(1)-ed BEFORE it is rolled."""
    s = s.sort_values(["user_id", "date"]).copy()
    g = s.groupby("user_id", sort=False)
    s["hit"] = (s.steps >= 8000).astype(float)
    sh = lambda c: g[c].shift(1)
    roll = lambda c, k, how, mp=1: g[c].transform(lambda x: getattr(x.shift(1).rolling(k, min_periods=mp), how)())
    s["steps_lag1"], s["steps_lag2"] = sh("steps"), g["steps"].shift(2)
    s["prev_date"] = sh("date")
    s["n_prev"] = roll("steps", 7, "count")
    s["steps_mean3"], s["steps_mean7"] = roll("steps", 3, "mean"), roll("steps", 7, "mean")
    s["steps_std7"] = roll("steps", 7, "std", 2)
    s["goal_rate7"] = roll("hit", 7, "mean")
    for out, c in (("calories_mean7", "calories_burned"), ("active_minutes_mean7", "active_minutes"), ("sleep_quality_mean7", "sleep_quality_score"),
                   ("sleep_minutes_mean7", "sleep_minutes"), ("resting_hr_mean7", "resting_heart_rate"), ("stress_mean7", "stress_level")):
        s[out] = roll(c, 7, "mean")
    s["month_sin"], s["month_cos"] = np.sin(2 * np.pi * s.date.dt.month / 12), np.cos(2 * np.pi * s.date.dt.month / 12)
    s["weight_baseline_kg"] = s.bmi * (s.height_cm / 100.0) ** 2
    s["label"] = (s.steps >= 8000).astype(int)
    keep = ((s.date - s.prev_date).dt.days == 1) & (s.n_prev >= 3)
    return s[keep]


def e2(ev, ex):
    res = pd.read_csv(ex / "E2_results.csv")
    info = json.loads((ev / "E2_run_info.json").read_text())
    for model, f in {"Random Forest": "Random_Forest", "Gradient-Boosted Trees": "Gradient-Boosted_Trees", "Logistic Regression": "Logistic_Regression"}.items():
        p = read_pred(ev, f"E2_{f}_test.csv")
        y, yhat = p.label.astype(int), p.prediction.astype(int)
        sp = "chronological test"
        check("E2", f"{model}: test accuracy recomputed", result(res, model, "Accuracy", sp), accuracy_score(y, yhat), 1e-9)
        check("E2", f"{model}: test precision (positive) recomputed", result(res, model, "Precision (positive class)", sp), precision_score(y, yhat, zero_division=0), 1e-9)
        check("E2", f"{model}: test recall (positive) recomputed", result(res, model, "Recall (positive class)", sp), recall_score(y, yhat, zero_division=0), 1e-9)
        check("E2", f"{model}: test F1 (positive) recomputed", result(res, model, "F1 (positive class)", sp), f1_score(y, yhat, zero_division=0), 1e-9)
        check("E2", f"{model}: test ROC-AUC recomputed", result(res, model, "ROC AUC", sp), roc_auc_score(y, p.score), 2e-3)
        check("E2", f"{model}: test-majority baseline recomputed", result(res, model, "Baseline accuracy (always majority class)", sp), max(y.mean(), 1 - y.mean()), 1e-9)
    # (b) independent re-implementation of the window features: Spark's == pandas'
    s = silver()
    mine = e2_features(s)
    sp_f = pd.read_csv(ev / "predictions" / "E2_features.csv", parse_dates=["date"])
    m = mine.merge(sp_f, on=["user_id", "date"], suffixes=("_pd", "_sp"))
    check("E2", "feature rows: same (user, day) set in pandas and Spark", len(sp_f), len(m), 0, "features")
    check("E2", "feature rows: pandas keeps no extra row", len(mine), len(m), 0, "features")
    worst = max(float((m[c + "_pd"].astype(float) - m[c + "_sp"].astype(float)).abs().max()) for c in E2_NUM)
    check("E2", "all 18 numeric features: max |pandas - Spark|", 0.0, worst, 2e-5, "features")
    # (c) no-future-information property of the (verified-equal) feature definition
    rng = np.random.default_rng(SEED)
    users = rng.choice(s.user_id.unique(), 25, replace=False)
    worst_leak = 0.0
    for u in users:
        su = s[s.user_id == u].sort_values("date")
        if len(su) < 40:
            continue
        cut = su.date.iloc[len(su) // 2]
        pert = s.copy()
        msk = (pert.user_id == u) & (pert.date >= cut)
        for c in ("steps", "calories_burned", "active_minutes", "sleep_quality_score", "sleep_minutes", "resting_heart_rate", "stress_level"):
            pert.loc[msk, c] = pert.loc[msk, c] * 3 + 1000
        a = e2_features(s[s.user_id == u]).set_index("date")
        b = e2_features(pert[pert.user_id == u]).set_index("date")
        # compare only days up to and INCLUDING the cut day (the first altered day): their features use rows strictly before them.
        # A kept day AFTER the cut may legitimately use altered days; the earlier window added such a day when the cut day was not a kept row.
        idx = [i for i in a.index[a.index <= cut] if i in b.index]
        worst_leak = max(worst_leak, float((a.loc[idx, E2_NUM[:12]] - b.loc[idx, E2_NUM[:12]]).abs().max().max()))
    check("E2", "features of day t unchanged when day t and all LATER days are altered (25 users)", 0.0, worst_leak, 1e-9, "no-future-info")
    # (d) independent LR refit on pandas-built features, chronological split from the run info
    c1, c2 = pd.Timestamp(info["split_cuts"][0]), pd.Timestamp(info["split_cuts"][1])
    d = mine.copy()
    X = pd.get_dummies(d[E2_NUM + E2_CAT], columns=E2_CAT).astype(float)
    tr, te = (d.date < c1).to_numpy(), (d.date >= c2).to_numpy()
    scaler = StandardScaler().fit(X[tr])
    reg = info["settings"]["logreg"]["reg"]
    lr = LogisticRegression(C=1.0 / (reg * tr.sum()) if reg > 0 else 1e12, max_iter=3000).fit(scaler.transform(X[tr]), d.label[tr])
    prob = lr.predict_proba(scaler.transform(X[te]))[:, 1]
    check("E2", "Logistic Regression: independent sklearn refit, chronological test ROC-AUC", result(res, "Logistic Regression", "ROC AUC", "chronological test"),
          roc_auc_score(d.label[te], prob), 0.01, "refit")
    check("E2", "Logistic Regression: independent sklearn refit, chronological test accuracy", result(res, "Logistic Regression", "Accuracy", "chronological test"),
          accuracy_score(d.label[te], prob >= .5), 0.02, "refit")
    Xc = d[E2_NUM].copy()
    for c in E2_CAT:
        Xc[c] = d[c].astype("category").cat.codes
    rf = RandomForestClassifier(n_estimators=50, max_depth=info["settings"]["rf"]["depth"], random_state=SEED, n_jobs=-1).fit(Xc[tr], d.label[tr])
    check("E2", "Random Forest: independent sklearn refit (approximate), chronological test ROC-AUC", result(res, "Random Forest", "ROC AUC", "chronological test"),
          roc_auc_score(d.label[te], rf.predict_proba(Xc[te])[:, 1]), 0.05, "refit (approx.)")


# ------------------------------------------------------------------------------------------------------------- E3
def e3(ev, ex):
    res = pd.read_csv(ex / "E3_results.csv")
    info = json.loads((ev / "E3_run_info.json").read_text())
    sp = "stratified 5-fold CV (out-of-fold)"
    for model, f in {"Random Forest": "Random_Forest", "Logistic Regression": "Logistic_Regression"}.items():
        p = read_pred(ev, f"E3_{f}_oof.csv")
        y, yhat = p.label.astype(int), p.prediction.astype(int)
        check("E3", f"{model}: OOF accuracy recomputed", result(res, model, "Accuracy", sp), accuracy_score(y, yhat), 1e-9)
        check("E3", f"{model}: OOF weighted F1 recomputed", result(res, model, "F1 (weighted)", sp), f1_score(y, yhat, average="weighted"), 1e-9)
        check("E3", f"{model}: OOF ROC-AUC recomputed", result(res, model, "ROC AUC", sp), roc_auc_score(y, p.score), 2e-3)
        check("E3", f"{model}: majority baseline recomputed", result(res, model, "Baseline accuracy (always majority class)", sp), max(y.mean(), 1 - y.mean()), 1e-9)
    # label recomputed from Silver, independently
    s = silver()
    rate = (s.steps >= 8000).groupby(s.user_id).mean()
    label = (rate > rate.median()).astype(int)
    ut = pd.read_csv(ev / "predictions" / "E3_user_table.csv").set_index("user_id")
    check("E3", "high_achiever label equals the independently recomputed label (mismatches)", 0, int((ut.label.astype(int) != label.reindex(ut.index)).sum()), 0, "label")
    check("E3", "no step- or distance-based feature among the model features (count)", 0,
          sum(("step" in f or "distance" in f) for f in info["features"]), 0, "leakage rule")
    # independent CV with the SAME folds and the modal settings of the Spark run
    feats = info["features"]
    oof = {}
    for model in ("Logistic Regression", "Random Forest"):
        pred = pd.Series(index=ut.index, dtype=float)
        for k in range(5):
            tr, te = ut[ut.fold != k], ut[ut.fold == k]
            if model == "Logistic Regression":
                reg = info["mode_settings"][model]["reg"]
                sc_ = StandardScaler().fit(tr[feats])
                m = LogisticRegression(C=1.0 / (reg * len(tr)) if reg > 0 else 1e12, max_iter=3000).fit(sc_.transform(tr[feats]), tr.label)
                pred[te.index] = m.predict_proba(sc_.transform(te[feats]))[:, 1]
            else:
                st = info["mode_settings"][model]
                m = RandomForestClassifier(n_estimators=st["trees"], max_depth=st["depth"], random_state=SEED, n_jobs=-1).fit(tr[feats], tr.label)
                pred[te.index] = m.predict_proba(te[feats])[:, 1]
        oof[model] = pred
        check("E3", f"{model}: independent sklearn CV (same folds), pooled OOF accuracy", result(res, model, "Accuracy", sp),
              accuracy_score(ut.label, pred >= .5), 0.05, "refit (approx.)")
        check("E3", f"{model}: independent sklearn CV (same folds), pooled OOF ROC-AUC", result(res, model, "ROC AUC", sp),
              roc_auc_score(ut.label, pred), 0.05, "refit (approx.)")


# ------------------------------------------------------------------------------------------------------------- E4
E4_NUM = ["avg_heart_rate", "max_heart_rate", "resting_heart_rate", "sleep_minutes", "sleep_quality_score", "stress_level", "hydration_level",
          "steps", "distance_km", "age", "bmi", "height_cm", "weight_baseline_kg"]
E4_CAT = ["intensity", "activity_type", "gender"]


def e4(ev, ex):
    res = pd.read_csv(ex / "E4_results.csv")
    info = json.loads((ev / "E4_run_info.json").read_text())
    sp = "test (user-held-out)"
    for model, f in {"Random Forest": "Random_Forest", "Gradient-Boosted Trees": "Gradient-Boosted_Trees", "Logistic Regression": "Logistic_Regression"}.items():
        p = read_pred(ev, f"E4_{f}_test.csv")
        y, yhat = p.label.astype(int), p.prediction.astype(int)
        check("E4", f"{model}: test accuracy recomputed", result(res, model, "Accuracy", sp), accuracy_score(y, yhat), 1e-9)
        check("E4", f"{model}: test macro F1 recomputed", result(res, model, "F1 (macro)", sp), f1_score(y, yhat, average="macro"), 1e-9)
        check("E4", f"{model}: test ROC-AUC recomputed", result(res, model, "ROC AUC", sp), roc_auc_score(y, p.score), 2e-3)
        tn, fp, fn, tp = confusion_matrix(y, yhat).ravel()
        check("E4", f"{model}: confusion matrix TP recomputed", result(res, model, "Confusion: actual High, predicted High", sp), tp, 0)
        check("E4", f"{model}: confusion matrix FN recomputed", result(res, model, "Confusion: actual High, predicted Low", sp), fn, 0)
        check("E4", f"{model}: majority baseline recomputed", result(res, model, "Baseline accuracy (always majority class)", sp), max(y.mean(), 1 - y.mean()), 1e-9)
    s = silver()
    s["weight_baseline_kg"] = s.bmi * (s.height_cm / 100.0) ** 2
    splits = pd.read_csv(ev / "predictions" / "E4_splits.csv").set_index("user_id").split
    s["split"] = s.user_id.map(splits)
    check("E4", "users present in both train and test (user-held-out)", 0, len(set(s[s.split == "train"].user_id) & set(s[s.split == "test"].user_id)), 0, "split")
    med = info["median_active_minutes"]
    check("E4", "median active_minutes of TRAINING users recomputed", med, float(s[s.split == "train"].active_minutes.median()), 1e-9, "label")
    s["label"] = (s.active_minutes > med).astype(int)
    tr, te = (s.split == "train").to_numpy(), (s.split == "test").to_numpy()
    X = pd.get_dummies(s[E4_NUM + E4_CAT], columns=E4_CAT).astype(float)
    reg = info["settings"]["logreg"]["reg"]
    scaler = StandardScaler().fit(X[tr])
    lr = LogisticRegression(C=1.0 / (reg * tr.sum()) if reg > 0 else 1e12, max_iter=3000).fit(scaler.transform(X[tr]), s.label[tr])
    prob = lr.predict_proba(scaler.transform(X[te]))[:, 1]
    check("E4", "Logistic Regression: independent sklearn refit, test ROC-AUC", result(res, "Logistic Regression", "ROC AUC", sp), roc_auc_score(s.label[te], prob), 0.02, "refit")
    check("E4", "Logistic Regression: independent sklearn refit, test accuracy", result(res, "Logistic Regression", "Accuracy", sp), accuracy_score(s.label[te], prob >= .5), 0.02, "refit")
    # the leakage run is reproduced independently: sedentary_minutes (= 1440 - sleep - active) gives a near-perfect classifier
    X2 = pd.get_dummies(s[E4_NUM + ["sedentary_minutes"] + E4_CAT], columns=E4_CAT).astype(float)
    sc2 = StandardScaler().fit(X2[tr])
    # like-for-like: the same L2 strength as the Spark model (regParam from the leak-free tuning); an unregularised fit separates the classes perfectly
    lr2 = LogisticRegression(C=1.0 / (reg * tr.sum()) if reg > 0 else 1e12, max_iter=3000).fit(sc2.transform(X2[tr]), s.label[tr])
    leak_acc = accuracy_score(s.label[te], lr2.predict(sc2.transform(X2[te])))
    spark_leak = float(res[(res.model == "Logistic Regression + sedentary_minutes (LEAKAGE)") & (res.metric == "Accuracy")].value.iloc[0])
    check("E4", "LEAKAGE run (+ sedentary_minutes, status INVALID) reproduces in sklearn", spark_leak, leak_acc, 0.03, "leakage")
    ri = res[res.model.str.contains("LEAKAGE")]
    check("E4", "every leakage row is marked INVALID (rows not INVALID)", 0, int((ri.status != "INVALID").sum()), 0, "status")


# ------------------------------------------------------------------------------------------------------------- E5
E5_NUM = ["steps", "distance_km", "active_minutes", "avg_heart_rate", "resting_heart_rate", "age", "height_cm", "weight_kg", "bmi"]


def e5(ev, ex):
    res = pd.read_csv(ex / "E5_results.csv")
    info = json.loads((ev / "E5_run_info.json").read_text())
    for model, f in {"Linear Regression": "Linear_Regression", "Random Forest Regressor": "Random_Forest_Regressor", "GBT Regressor": "GBT_Regressor"}.items():
        p = read_pred(ev, f"E5_{f}_test.csv")
        check("E5", f"{model}: test MAE recomputed", result(res, model, "MAE (kcal)", "test"), mean_absolute_error(p.label, p.prediction), 1e-6)
        check("E5", f"{model}: test RMSE recomputed", result(res, model, "RMSE (kcal)", "test"), mean_squared_error(p.label, p.prediction) ** 0.5, 1e-6)
        check("E5", f"{model}: test R2 recomputed", result(res, model, "R2", "test"), r2_score(p.label, p.prediction), 1e-9)
    p = read_pred(ev, "E5_Linear_Regression_test.csv")
    base_mae = float(np.abs(p.label - info["train_mean_kcal"]).mean())
    b = res[(res.model == "Baseline: training mean") & (res.metric == "MAE (kcal)") & (res.split_type == "test")].value.iloc[0]
    check("E5", "training-mean baseline test MAE recomputed (expected 334.5 kcal)", b, base_mae, 1e-6)
    # independent OLS on the same rows
    s = silver()
    sp = read_pred(ev, "E5_splits.csv")
    d = s.merge(sp, on=["user_id", "date"])
    X = pd.get_dummies(d[E5_NUM + ["gender"]], columns=["gender"]).astype(float)
    tr, te = (d.split == "train").to_numpy(), (d.split == "test").to_numpy()
    ols = LinearRegression().fit(X[tr], d.calories_burned[tr])
    yp = ols.predict(X[te])
    check("E5", "Linear Regression: independent sklearn OLS, test MAE", result(res, "Linear Regression", "MAE (kcal)", "test"), mean_absolute_error(d.calories_burned[te], yp), 0.5, "refit")
    check("E5", "Linear Regression: independent sklearn OLS, test R2", result(res, "Linear Regression", "R2", "test"), r2_score(d.calories_burned[te], yp), 0.002, "refit")
    st = info["settings"]["rf"]
    rf = RandomForestRegressor(n_estimators=50, max_depth=st["depth"], random_state=SEED, n_jobs=-1).fit(X[tr], d.calories_burned[tr])
    check("E5", "Random Forest Regressor: independent sklearn refit (approximate), test R2", result(res, "Random Forest Regressor", "R2", "test"),
          r2_score(d.calories_burned[te], rf.predict(X[te])), 0.05, "refit (approx.)")


EXPERIMENTS = {"E1": e1, "E2": e2, "E3": e3, "E4": e4, "E5": e5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="evidence directory (default faculty_evidence/supervised); its exports/ holds the result CSVs when given")
    a = ap.parse_args()
    ev = Path(a.dir) if a.dir else ROOT / "faculty_evidence" / "supervised"
    ex = ev / "exports" if a.dir else ROOT / "exports"
    for exp, fn in EXPERIMENTS.items():
        if (ex / f"{exp}_results.csv").exists() and (ev / "predictions").exists():
            print(f"--- {exp}")
            fn(ev, ex)
        else:
            print(f"--- {exp}: no results in {ex} - skipped")
    out = pd.DataFrame(rows)
    out.to_csv(ev / "sklearn_crosscheck.csv", index=False)
    bad = out[~out["pass"]] if len(out) else out
    print(f"\n{len(out) - len(bad)}/{len(out)} cross-checks passed -> {ev / 'sklearn_crosscheck.csv'}")
    sys.exit(1 if len(bad) else 0)


if __name__ == "__main__":
    main()
