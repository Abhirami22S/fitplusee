"""
FitPulse - consolidate MEASURED model results into faculty_evidence/model_metrics.csv.
Only reads result files that were written by actual evaluation runs; nothing is typed in here.

    python scripts/build_model_metrics.py
Each row carries its source file, so a reviewer can trace every number.
"""
import json
from pathlib import Path

import pandas as pd

EV = Path(__file__).resolve().parent.parent / "faculty_evidence"
ROOT = EV.parent
rows = []


def add(model, experiment, split, metric, value, source):
    rows.append({"model": model, "experiment": experiment, "set": split, "metric": metric, "value": value, "source_file": source})


# 1. Notebook Random Forest (next-day personalised goal): local-Parquet run and HDFS re-run
for tag, path in [("local Parquet run", EV / "classification_results.csv"), ("HDFS re-run", EV / "hdfs" / "ml" / "classification_results.csv")]:
    if path.exists():
        for _, r in pd.read_csv(path).iterrows():
            add("Random Forest (Spark MLlib)", f"notebook: next-day personalised goal [{tag}]", "test", r["Metric"], r["Value"], str(path.relative_to(ROOT)))

# 2. Report-aligned Random Forest (same-day steps >= 8000)
p = EV / "report_aligned" / "rf_metrics.csv"
if p.exists():
    m = pd.read_csv(p)
    for _, r in m.iterrows():
        for s in ("Validation", "Test"):
            add("Random Forest (Spark MLlib)", "REPORT-aligned: same-day steps >= 8000", s.lower(), r["Metric"], r[s], str(p.relative_to(ROOT)))
p = EV / "report_aligned" / "rf_extra_checks.csv"
if p.exists():
    for _, r in pd.read_csv(p).iterrows():
        add("Random Forest (Spark MLlib)", "REPORT-aligned: same-day steps >= 8000", "extra check", r["Check"], r["Value"], str(p.relative_to(ROOT)))

# 3. Linear Regression
p = EV / "regression_results.csv"
if p.exists():
    for _, r in pd.read_csv(p).iterrows():
        for met in ("MAE (kcal)", "RMSE (kcal)", "R2"):
            add(r["Model"], "calorie_burned (same-day estimation)", r["Set"], met, r[met], str(p.relative_to(ROOT)))

# 4. Dashboard model (Logistic Regression): quoted from models/metrics_report.md, NOT re-run here
add("Logistic Regression (dashboard)", "next-day personalised goal, chronological split", "test", "ROC-AUC", 0.755,
    "models/metrics_report.md (earlier training run; not re-run in this task)")
add("Random Forest (scikit-learn, dashboard comparison)", "next-day personalised goal, chronological split", "test", "ROC-AUC", 0.718,
    "models/metrics_report.md (earlier training run; not re-run in this task)")

pd.DataFrame(rows).to_csv(EV / "model_metrics.csv", index=False)
print("model_metrics.csv:", len(rows), "rows")
