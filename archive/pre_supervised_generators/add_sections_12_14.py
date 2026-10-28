"""
Appends sections 12-14 to FitPulse_Faculty_Demo.ipynb without re-running the existing cells:
 12 Calorie-burn Linear Regression (Spark MLlib)
 13 REPORT-aligned Random Forest and K-Means (Spark MLlib) + how they differ from the notebook / dashboard models
 14 Dashboard validation, Power BI status, and the faculty-proof checklist
The new cells only DISPLAY result files that the scripts in models/ and scripts/ wrote when they were actually executed
(same mechanism as section 11.6). They are executed here in a fresh kernel so the saved outputs are real.

    python faculty_evidence/add_sections_12_14.py        (run from FitPulse/ after the scripts have been run)
"""
import copy
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "FitPulse_Faculty_Demo.ipynb"
MARK = "## 12. Calorie-Burn Prediction"
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
new = []

new.append(md("""## 12. Calorie-Burn Prediction - Linear Regression (Spark MLlib)

The report (Table 4) and the presentation promise a Linear Regression calorie model that did not exist in the repository.
It is implemented in `models/train_calorie_regression.py` and was run on the **Silver data read from HDFS**.

* **Target:** `calories_burned` of the same day - an *estimation* model (steps, distance, active minutes, heart rate, body profile -> energy), not a forecast of tomorrow.
* **Features:** steps, distance_km, active_minutes, avg_heart_rate, resting_heart_rate, age, height_cm, weight_kg, bmi, gender (one-hot).
* **Excluded to avoid leakage / collinearity:** `calories_lag1`, `calories_roll7_avg`, `daily_calorie_goal` (built from the target column), `sedentary_minutes` and `sleep_minutes` (active + sedentary + sleep = 1,440).
* **Preprocessing:** one-hot encoding and standardisation are inside the Spark `Pipeline` and fitted on the training split only.
* **Split:** seeded 70/15/15 (same hash method as section 5); regularisation strength chosen on the validation set; test set used once. A chronological check (train before 2024-10-15) is added.
* **Baselines:** predict the training mean; one-feature regression on `active_minutes`."""))
new.append(code("""
import json
import pandas as pd
from IPython.display import Image, display
cfg = json.loads((PROJECT_ROOT / "models/artifacts/calorie_linreg_config.json").read_text(encoding="utf-8"))
print("Storage mode used for this run :", cfg["storage_mode"].upper(), "|", cfg["silver_source"])
print("Rows  train / validation / test :", cfg["rows"])
print("Selected regParam              :", cfg["regParam"], "(chosen by validation RMSE)")
print("Features                       :", cfg["numeric_features"] + cfg["categorical_features"])
res = pd.read_csv(EVIDENCE / "regression_results.csv")
display(res.round(4))
display(pd.read_csv(EVIDENCE / "regression_tuning.csv").round(4))
display(pd.read_csv(EVIDENCE / "regression_coefficients.csv").round(4))
display(Image(filename=str(EVIDENCE / "regression_actual_vs_predicted.png")))
""".strip()))
new.append(code("""
# Independent re-computation of the metrics from the saved predictions (scripts/test_analytics.py was executed separately)
v = json.loads((EVIDENCE / "analytics_validation.json").read_text(encoding="utf-8"))
print(f"analytics validation run {v['timestamp']}: {v['passed']}/{v['total']} checks passed")
for c in v["checks"]:
    print(("PASS " if c["passed"] else "FAIL "), c["check"], "-", c["detail"][:100])
""".strip()))
new.append(md("""**Interpretation.** On held-out test days the model's MAE is about 200 kcal and RMSE about 264 kcal, R-squared 0.63, against an MAE of about 335 kcal
for always predicting the training mean (R-squared 0). The model therefore explains roughly 63% of the day-to-day variation in calories. It is a
moderate estimator. Limits: `steps` and `distance_km` are strongly correlated (r = 0.94), so their individual coefficients have opposite signs and should
not be read one by one; the dataset is partly simulated (REPORT section 2.5 notes implausible weight changes); the chronological check scores lower (R-squared 0.58),
which shows the relationship drifts through the year. The R-squared of 0.63 is a measured value, not a target we tuned toward."""))

new.append(md("""## 13. REPORT-aligned Random Forest and K-Means (Spark MLlib)

The report (sections 2-3) describes experiments that differ from the ones in sections 5-7 of this notebook. Both are now implemented and measured:

| | Notebook (sections 5-7) | **REPORT-aligned** (this section) | Dashboard model |
|---|---|---|---|
| Classifier target | next-day achievement of the *personalised* goal (1.10 x own average) | **same-day `steps >= 8,000`** | next-day personalised goal |
| Algorithm | Random Forest (Spark MLlib) | **Random Forest (Spark MLlib)** | **Logistic Regression** (scikit-learn, `models/train_goal_achievement.py`) |
| Features | lag / rolling features | **15 numeric + 3 categorical same-day features (steps, distance excluded)** | lag / rolling features |
| Split | seeded hash 70/15/15 | **`randomSplit([.7,.15,.15], seed=42)`** | chronological (cutoff 2024-10-15) |
| K-Means unit | 100,122 user-**days**, K = 2..6 | **437 users** (per-user averages), K = 2..10 | - |

Scripts: `models/spark_report_classification.py`, `models/spark_report_kmeans.py`; outputs in `faculty_evidence/report_aligned/`; both read Silver from HDFS."""))
new.append(code("""
RA = EVIDENCE / "report_aligned"
info = json.loads((RA / "rf_run_info.json").read_text())
print("Report-aligned Random Forest | storage:", info["storage_mode"].upper(), "|", info["silver_source"])
print(f"records {info['records']:,}; share meeting the 8,000-step goal {info['positive_share']:.4f}; selected numTrees={info['numTrees']}, maxDepth={info['maxDepth']}")
display(pd.read_csv(RA / "rf_split_sizes.csv"))
grid = pd.read_csv(RA / "rf_tuning_grid.csv")
display(grid)
display(pd.read_csv(RA / "rf_metrics.csv").round(4))
display(pd.read_csv(RA / "rf_confusion_matrix.csv", index_col=0))
display(pd.read_csv(RA / "rf_feature_importance.csv").head(8).round(4))
display(pd.read_csv(RA / "rf_extra_checks.csv"))
""".strip()))
new.append(md("""**Interpretation and comparison with the report's printed numbers** (the report's values came from scikit-learn):

| Quantity | Report | Measured here (Spark MLlib) | Reading |
|---|---|---|---|
| Test accuracy | 0.7303 | 0.7352 | same level |
| Test ROC AUC | 0.7580 | 0.7585 | same level |
| Always-majority baseline | 0.6114 | 0.6144 | same |
| Goal-achieved precision / recall | 0.7751 / 0.7875 | 0.7801 / 0.7923 | same level |
| Top feature | weight_kg 0.2446 | weight_kg 0.2822 | same top feature, as the report says it proxies time of year |
| User-held-out accuracy / AUC | 0.725 / 0.755 | 0.723 / 0.750 | confirmed |
| Leakage demo (steps + distance included) | "100% accuracy" | 98.95% | confirmed (the report's "100%" should read "about 99%") |
| Best hyper-parameters | numTrees 100, maxDepth 20 (val AUC 0.759) | numTrees 50, maxDepth 15 (val AUC 0.7549) | **not reproduced**: (100 trees, depth 15) and (100, 20) crashed the JVM with `OutOfMemoryError` on this laptop (3 GB driver), see the grid above and `log_report_rf_hdfs_attempt1_full_grid.txt`; the other 6 of 8 grid points were measured |
| Split sizes | 70,084 / 15,019 / 15,019 | 70,383 / 14,943 / 14,796 | Spark `randomSplit` differs from scikit-learn's split |"""))
new.append(code("""
kev = pd.read_csv(RA / "kmeans_evaluation.csv")
display(kev.round(4))
display(pd.read_csv(RA / "kmeans_cluster_summary.csv"))
display(pd.read_csv(RA / "kmeans_user_range.csv").round(2))
print("Why Spark's silhouette (0.3413 at K=2) differs from the report's 0.2018:")
print((RA / "kmeans_silhouette_definition_check.txt").read_text(encoding="utf-8"))
display(Image(filename=str(RA / "kmeans_elbow_silhouette.png")))
display(Image(filename=str(RA / "kmeans_pca.png")))
""".strip()))
new.append(md("""**Interpretation.** K = 2 has the highest silhouette on the 437 user vectors (K = 2..10 evaluated), giving two groups of 209 and 228 users. The group labels come from the
*measured* average active minutes (68.7 vs 71.1), not from an assumed Sedentary / Moderate / Active scheme: the two segments differ by only about 2.4 active minutes,
5.5 sedentary minutes and 28 kcal, and average steps are the same (8,631 vs 8,621), so the report's honest conclusion stands.
**The 0.3413 vs 0.2018 difference is explained, not a discrepancy in the model:** Spark's `ClusteringEvaluator(distanceMeasure="squaredEuclidean")` and scikit-learn's Euclidean silhouette are
different definitions. Scoring the same Spark assignment with scikit-learn's Euclidean silhouette gives 0.2018, and scikit-learn reproduces the report's values for every K from 2 to 10.
The report's WCSS is 0.2% higher than Spark's because scikit-learn standardises with the population standard deviation (n) and Spark with the sample standard deviation (n-1).
The report text should therefore say *Euclidean silhouette (scikit-learn) 0.2018*, or quote Spark's squared-Euclidean 0.3413; it currently attributes 0.2018 to Spark's ClusteringEvaluator."""))

new.append(md("""## 14. Dashboards, Power BI status and faculty-proof checklist

**Streamlit** (`dashboard/app.py`) is the working dashboard. It was never launched before this task; testing found and fixed a real Windows crash (`strftime('%-d')` is not valid on Windows)
and added a clear error when required files are missing. Its data source is the **local** SQLite database `dashboard/fitpulse.db` (built from the local Silver), not HDFS. A new tab,
*Calories & Segments*, adds the fitness score, actual-vs-predicted calories, the user's K-Means segment and monthly trends.

**Power BI is NOT implemented.** Power BI Desktop is not installed on this machine and a `.pbix` can only be authored and validated inside it. `powerbi/` contains only *preparation*:
validated CSV exports, DAX measures and a page-by-page specification (`powerbi/DASHBOARD_SPEC.md`). Streamlit and Power BI are separate tools."""))
new.append(code("""
d = json.loads((EVIDENCE / "dashboard" / "dashboard_validation.json").read_text(encoding="utf-8"))
print(f"Streamlit AppTest run {d['timestamp']}: {d['passed']}/{d['total']} checks passed")
print("Data source:", d["data_source"])
for c in d["checks"]:
    print(("PASS " if c["passed"] else "FAIL "), c["check"])
print()
import subprocess, sys
r = subprocess.run([sys.executable, str(PROJECT_ROOT / "powerbi" / "validate_exports.py")], capture_output=True, text=True, cwd=PROJECT_ROOT)
print("Power BI export validation (executed now, exit code %d):" % r.returncode)
print(r.stdout)
print("Power BI .pbix files found in the project:", [str(p) for p in PROJECT_ROOT.rglob("*.pbix")] or "none (dashboard NOT built)")
""".strip()))
new.append(code("""
mm = pd.read_csv(EVIDENCE / "model_metrics.csv")
print("faculty_evidence/model_metrics.csv - every row carries its source file; rows:", len(mm))
display(mm[mm.metric.isin(["Accuracy", "ROC AUC", "ROC-AUC", "F1 (goal-achieved class)", "MAE (kcal)", "RMSE (kcal)", "R2"])]
        .drop(columns=["source_file"]).round(4).reset_index(drop=True))
print("\\nKnown limits: RF experiments differ between notebook and report (sections 13); the dashboard classifier is Logistic Regression "
      "(ROC-AUC 0.755 from models/metrics_report.md, an earlier training run that was not repeated); HDFS is single node; Power BI is not built.")
""".strip()))


def main():
    nb = nbf.read(NB, as_version=4)
    if any(MARK in c.source for c in nb.cells if c.cell_type == "markdown"):
        sys.exit("sections 12-14 already present - refusing to add twice")
    setup = [copy.deepcopy(nb.cells[i]) for i in (3, 4)]
    for c in setup:
        c.outputs, c.execution_count = [], None
    scratch = nbf.v4.new_notebook(cells=setup + [copy.deepcopy(c) for c in new])
    scratch.metadata = nb.metadata
    NotebookClient(scratch, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    executed = scratch.cells[len(setup):]
    last = max((c.get("execution_count") or 0) for c in nb.cells if c.cell_type == "code")
    for c in executed:
        if c.cell_type == "code":
            last += 1
            c.execution_count = last
            for o in c.outputs:
                if o.get("output_type") == "execute_result":
                    o["execution_count"] = last
    at = len(nb.cells) - 1
    assert "spark.stop()" in nb.cells[at].source
    nb.cells[at:at] = executed
    swaps = [
        ("| Random Forest | ✅ exists in `models/train_goal_achievement.py` (scikit-learn). This notebook re-implements it in **Spark MLlib** with the same target and features |",
         "| Random Forest | ✅ `models/train_goal_achievement.py` (scikit-learn); this notebook re-implements it in **Spark MLlib** (§6); the REPORT's different same-day experiment is implemented in `models/spark_report_classification.py` (§13) |"),
        ("| K-Means clustering | ❌ did **not** exist in the repo – **added in this notebook** (§7) |",
         "| K-Means clustering | ✅ added in this notebook (§7, user-days); the REPORT's user-level version is `models/spark_report_kmeans.py` (§13) |\n| Linear Regression (calories) | ✅ `models/train_calorie_regression.py`, Spark MLlib (§12) |"),
        ("| Dashboard | ✅ Streamlit (`dashboard/app.py`). **No Power BI file exists in the repo** |",
         "| Dashboard | ✅ Streamlit (`dashboard/app.py`), tested in §14. ❌ **Power BI is not built** (no Desktop, no `.pbix`); only validated exports and a spec exist in `powerbi/` |"),
    ]
    hits = 0
    for c in nb.cells:
        if c.cell_type == "markdown":
            for old, newt in swaps:
                if old in c.source:
                    c.source = c.source.replace(old, newt)
                    hits += 1
    print("table updates:", hits, "of", len(swaps), "| inserted cells:", len(executed))
    nbf.write(nb, NB)


if __name__ == "__main__":
    main()
