"""
FitPulse - Power BI tables for pages 4 and 5 (the SUPERVISED experiments E1-E5). Reads ONLY result files written by actual
runs; nothing is typed in except the five short experiment labels below.

  * exports/E1_results.csv ... E5_results.csv       -> supervised_results.csv (every row, plus the file it came from)
  * faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv -> crosscheck.csv (the independent scikit-learn cross-check;
    the only source outside exports/, used for the cross-check counts on page 5)

    python powerbi/export_model_evaluation.py
Writes powerbi/data/: supervised_results.csv, experiments.csv, crosscheck.csv
Every row carries its experiment id, evaluation split and status (VALID / BASELINE / REFERENCE / INVALID), so different
experiments and leakage runs are never silently merged.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"
CROSSCHECK = ROOT / "faculty_evidence" / "supervised" / "hdfs_rerun" / "sklearn_crosscheck.csv"
OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/")

LABELS = {"E1": "E1 same-day goal", "E2": "E2 next-day goal", "E3": "E3 user-level high_achiever",
          "E4": "E4 activity level", "E5": "E5 same-day calories"}

frames = []
for eid in LABELS:
    p = EXPORTS / f"{eid}_results.csv"
    d = pd.read_csv(p)
    assert (d.experiment_id == eid).all(), f"{p} contains rows of another experiment"
    d["source_file"] = rel(p)
    frames.append(d)
res = pd.concat(frames, ignore_index=True)[["experiment_id", "model", "metric", "value", "split_type", "status", "source_file"]]
assert not res.duplicated(["experiment_id", "model", "metric", "split_type", "status"]).any(), "duplicate result rows"
res.to_csv(OUT / "supervised_results.csv", index=False)
pd.DataFrame({"experiment_id": list(LABELS), "experiment_name": list(LABELS.values())}).to_csv(OUT / "experiments.csv", index=False)

cc = pd.read_csv(CROSSCHECK)
pd.DataFrame({"experiment_id": cc.experiment, "kind": cc.kind, "check": cc.check, "abs_diff": cc.abs_diff, "tolerance": cc.tolerance,
              "passed": cc["pass"].astype(int), "source_file": rel(CROSSCHECK)}).to_csv(OUT / "crosscheck.csv", index=False)

for f in ("supervised_results.csv", "experiments.csv", "crosscheck.csv"):
    print(f"{f:26s} {sum(1 for _ in open(OUT / f, encoding='utf-8')) - 1:>5} rows")
