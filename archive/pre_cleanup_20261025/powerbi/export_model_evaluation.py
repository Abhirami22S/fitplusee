"""
FitPulse - Power BI tables for Page 5 (Model Evaluation) and Page 4 (K selection). Reads ONLY result files written by
actual evaluation runs; nothing is typed in. Each row carries its experiment, target, granularity, split and source file so
that different experiments are never silently merged.

    python powerbi/export_model_evaluation.py
Writes powerbi/data/: model_evaluation.csv, confusion_matrices.csv, kmeans_k_selection.csv, experiments.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "faculty_evidence"
RA = EV / "report_aligned"
OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/")

EXPERIMENTS = [
    # id, name, algorithm, target, granularity, split method
    ("E1", "Random Forest - REPORT experiment", "Random Forest (Spark MLlib)", "same-day goal: steps >= 8,000",
     "user-day (100,122 rows)", "Spark randomSplit 70/15/15, seed 42"),
    ("E2", "Random Forest - NOTEBOOK experiment", "Random Forest (Spark MLlib)", "next-day achievement of the personalised step goal",
     "user-day with lag features (62,786 rows)", "seeded hash 70/15/15 of (user_id, date)"),
    ("E3", "K-Means - REPORT experiment", "K-Means (Spark MLlib)", "none (unsupervised)", "USER (437 per-user averages)", "none (all users)"),
    ("E4", "K-Means - NOTEBOOK experiment", "K-Means (Spark MLlib)", "none (unsupervised)", "user-DAY (100,122 points)", "none (all days)"),
    ("E5", "Linear Regression - calories", "Linear Regression (Spark MLlib)", "same-day calories_burned (kcal)",
     "user-day (100,122 rows)", "seeded hash 70/15/15 of (user_id, date); chronological check train < 2024-10-15"),
]
exp = pd.DataFrame(EXPERIMENTS, columns=["experiment_id", "experiment_name", "algorithm", "target", "data_granularity", "split_method"])
meta = exp.set_index("experiment_id")
rows = []


def add(eid, eset, metric, value, src, baseline=False, algorithm=None):
    m = meta.loc[eid]
    rows.append({"experiment_id": eid, "experiment_name": m.experiment_name, "algorithm": algorithm or m.algorithm, "target": m.target,
                 "data_granularity": m.data_granularity, "evaluation_set": eset, "metric": metric, "value": float(value),
                 "is_baseline": int(baseline), "source_file": src})


NAME = {"Precision (goal-achieved class)": "Precision (positive class)", "Recall (goal-achieved class)": "Recall (positive class)",
        "F1 (goal-achieved class)": "F1 (positive class)", "Baseline accuracy (always majority class)": "Baseline accuracy (always majority class)"}

# E1 - report-aligned Random Forest
p = RA / "rf_metrics.csv"
for _, r in pd.read_csv(p).iterrows():
    for s in ("Validation", "Test"):
        add("E1", s.lower(), NAME.get(r["Metric"], r["Metric"]), r[s], rel(p))

# E2 - notebook Random Forest (original local-Parquet run; the HDFS re-run differs only in ROC-AUC at 1e-6)
p = EV / "classification_results.csv"
MAP2 = {"Accuracy": "Accuracy", "Precision (class 1 = achieved)": "Precision (positive class)", "Recall (class 1 = achieved)": "Recall (positive class)",
        "F1 Score (class 1 = achieved)": "F1 (positive class)", "ROC-AUC": "ROC AUC", "Weighted precision (both classes)": "Precision (weighted)",
        "Weighted recall (both classes)": "Recall (weighted)", "Weighted F1 (both classes)": "F1 (weighted)",
        "Baseline: always predict majority class": "Baseline accuracy (always majority class)"}
for _, r in pd.read_csv(p).iterrows():
    add("E2", "test", MAP2[r["Metric"]], r["Value"], rel(p))

# E3 - report-aligned K-Means (selected K = 2)
ev = pd.read_csv(RA / "kmeans_evaluation.csv").set_index("K")
chk = pd.read_csv(RA / "kmeans_silhouette_definition_check.csv").set_index("K")
info = json.loads((RA / "kmeans_run_info.json").read_text())
K = int(info["selected_K"])
add("E3", f"all users, K={K}", "Silhouette (Euclidean, scikit-learn)", chk.loc[K, "sklearn_silhouette_euclidean"], rel(RA / "kmeans_silhouette_definition_check.csv"))
add("E3", f"all users, K={K}", "Silhouette (Spark squaredEuclidean)", ev.loc[K, "Silhouette"], rel(RA / "kmeans_evaluation.csv"))
add("E3", f"all users, K={K}", "WCSS (Spark)", ev.loc[K, "WCSS"], rel(RA / "kmeans_evaluation.csv"))
add("E3", f"all users, K={K}", "Number of users clustered", info["users"], rel(RA / "kmeans_run_info.json"))
add("E3", f"all users, K={K}", "Selected K", K, rel(RA / "kmeans_run_info.json"))
for _, r in pd.read_csv(RA / "kmeans_cluster_summary.csv").iterrows():
    add("E3", f"cluster {int(r.cluster)}", "Users in cluster", r.Users, rel(RA / "kmeans_cluster_summary.csv"))

# E4 - notebook K-Means on user-days (K = 2)
sil = pd.read_csv(EV / "silhouette_scores.csv").set_index("K")
cs = pd.read_csv(EV / "cluster_summary.csv")
add("E4", "all user-days, K=2", "Silhouette (Spark squaredEuclidean)", sil.loc[2, "Silhouette Score"], rel(EV / "silhouette_scores.csv"))
add("E4", "all user-days, K=2", "WSSSE (Spark)", sil.loc[2, "WSSSE"], rel(EV / "silhouette_scores.csv"))
add("E4", "all user-days, K=2", "Selected K", 2, rel(EV / "silhouette_scores.csv"))
for _, r in cs.iterrows():
    add("E4", f"cluster {int(r.Cluster)}", "User-days in cluster", r.Count, rel(EV / "cluster_summary.csv"))

# E5 - calorie Linear Regression
p = EV / "regression_results.csv"
for _, r in pd.read_csv(p).iterrows():
    base = r["Model"].startswith("Baseline") or "baseline" in r["Model"]
    chrono = r["Model"].startswith("Chronological")
    eset = "chronological test" if chrono else r["Set"]
    algo = "Training-mean baseline" if "training" in r["Model"].lower() and base else ("LinReg on active_minutes only (baseline)" if "active_minutes" in r["Model"] else "Linear Regression (Spark MLlib)")
    for col, nm in (("MAE (kcal)", "MAE (kcal)"), ("RMSE (kcal)", "RMSE (kcal)"), ("R2", "R2")):
        add("E5", eset, nm, r[col], rel(p), baseline=base, algorithm=algo)

me = pd.DataFrame(rows)
# compact row label for the Power BI matrix: baselines of E5 carry their algorithm name, everything else keeps the metric name
short = {"Training-mean baseline": "mean baseline", "LinReg on active_minutes only (baseline)": "1-feature baseline"}
me["metric_label"] = np.where(me.algorithm.isin(short.keys()) & (me.experiment_id == "E5"), me.metric + " - " + me.algorithm.map(short).fillna(""), me.metric)
me.to_csv(OUT / "model_evaluation.csv", index=False)
exp.to_csv(OUT / "experiments.csv", index=False)

# confusion matrices (test set)
cm_rows = []
cm1 = pd.read_csv(RA / "rf_confusion_matrix.csv", index_col=0)
cm2 = pd.read_csv(EV / "confusion_matrix.csv", index_col=0)
lab = ["Not achieved (0)", "Achieved (1)"]
for eid, cm in (("E1", cm1), ("E2", cm2)):
    v = cm.to_numpy()
    for i in range(2):
        for j in range(2):
            cm_rows.append({"experiment_id": eid, "evaluation_set": "test", "actual": lab[i], "predicted": lab[j], "count": int(v[i, j]),
                            "share_of_actual": float(v[i, j] / v[i].sum())})
pd.DataFrame(cm_rows).to_csv(OUT / "confusion_matrices.csv", index=False)

# K selection curves
kr = []
for K_, r in ev.iterrows():
    kr += [("E3", K_, "Silhouette (Spark squaredEuclidean)", r["Silhouette"]), ("E3", K_, "WCSS (Spark)", r["WCSS"])]
for K_, r in chk.iterrows():
    kr += [("E3", K_, "Silhouette (Euclidean, scikit-learn)", r["sklearn_silhouette_euclidean"]), ("E3", K_, "WCSS (scikit-learn)", r["sklearn_WCSS"])]
for K_, r in sil.iterrows():
    kr += [("E4", K_, "Silhouette (Spark squaredEuclidean)", r["Silhouette Score"]), ("E4", K_, "WSSSE (Spark)", r["WSSSE"])]
pd.DataFrame(kr, columns=["experiment_id", "K", "metric", "value"]).to_csv(OUT / "kmeans_k_selection.csv", index=False)

for f in ("model_evaluation.csv", "confusion_matrices.csv", "kmeans_k_selection.csv", "experiments.csv"):
    print(f"{f:26s} {sum(1 for _ in open(OUT / f, encoding='utf-8')) - 1:>5} rows")
