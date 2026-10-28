# FitPulse - Project Implementation Audit

Sources inspected: `D:\bigdata\FitPulse_Report_Updated (1).docx` (the report, "REPORT"), `D:\bigdata\actualfitpulseppt.pptx` ("PPT"),
the older `Downloads\FitPulse_Report.docx` (not used - superseded), and the repository at `D:\bigdata\fitpulsee\FitPulse`.
No `.pbix`, `.pbip` or Power BI Desktop installation exists on this machine (checked: Program Files, Store packages, winget).

**Initial inventory (before any change in this task).** The "Status at inventory" column is frozen; the final status
is in section 3 and in `FINAL_ACCEPTANCE_TABLE.md`.

## 1. Headline findings

1. **The REPORT and the notebook describe different experiments.** REPORT section 2 predicts *same-day* `steps >= 8,000` with 17 same-day features;
   the notebook / `train_goal_achievement.py` predict *next-day* achievement of a *personalised* goal (1.10 x the user's average steps) from lag/rolling features.
   REPORT section 3 clusters 437 **users** (K = 2..10, silhouette 0.2018); the notebook clusters 100,122 **user-days** (K = 2..6, silhouette 0.3528).
2. **REPORT numbers were produced with scikit-learn**, not Spark MLlib (REPORT 2.3 / 3.3 say so). The listings are Spark code with `<HDFS_PATH>` placeholders; that code was never run in this repo.
3. **Linear Regression for calories does not exist** (only an unrelated Linear Regression baseline for sleep quality in `models/train_sleep_quality.py`). REPORT says "not evaluated here"; PPT promises RMSE / MAE / R2.
4. **Power BI does not exist.** REPORT, PPT and the user brief name it; no deliverable and no Power BI Desktop.
5. **HDFS** is now real but single node, replication 1; REPORT Table 2 / 1.6 describe replication factor 3 and multi-node fault tolerance.
6. Streamlit dashboard had never been launched (Streamlit is not installed in the venv).

## 2. Claim inventory

| # | Claim (REPORT/PPT) | Implementation file(s) | Status at inventory | Evidence at inventory | Needed to complete |
|---|---|---|---|---|---|
| 1 | Dataset: 100,122 rows, 437 users, 23 attributes, 2024-01-01..2024-12-25, no duplicate user-date, active+sedentary+sleep = 1,440, health_condition blank 69.7%, corr(steps, distance)=0.94 | `data/raw/fitpulse_raw.csv`, `data/prepare_raw_dataset.py` | Implemented, verified | Re-computed from the CSV in this audit (all match; 61.3% of days >= 8,000 steps) | none |
| 2 | HDFS stores the data | `etl/storage.py`, `hadoop-conf/`, `*_hdfs.ps1` | Implemented (single node) | `faculty_evidence/hdfs/*`, notebook s.11 | State single-node / replication 1 in REPORT |
| 3 | Replication factor 3, fault tolerance via block replication | - | Not demonstrable | one DataNode | Reword REPORT 1.6 / Table 2 |
| 4 | Spark/PySpark cleaning + feature engineering | `etl/spark_etl.py` | Implemented, tested | ETL log, 100,122 rows | none |
| 5 | Cleaning removed nothing | `etl/spark_etl.py` | Implemented, tested | "0 dropped" | none |
| 6 | Feature engineering: active-time ratio, steps per active minute | `etl/spark_etl.py` has lag/rolling/goal features, **not** these two | Partial | REPORT 2.1 itself says steps-per-active-minute is not used | Add `active_ratio` in the report-aligned scripts |
| 7 | Normalisation / correlation analysis | notebook s.4, s.7.2 | Implemented | notebook | none |
| 8 | 70/15/15 split with fixed seed (RF, LR) | notebook (seeded hash split) | Implemented for the notebook's task | `split_summary.csv` | Report-aligned script uses its own seeded split |
| 9 | RF classification: same-day `steps>=8000`, features of Table 5, Spark MLlib | not in repo | **Missing** (as described) | REPORT numbers are scikit-learn | Spark script `models/spark_report_classification.py` |
| 10 | RF tuned over numTrees {50,100} x maxDepth {5,10,15,20}; best 100/20, val AUC 0.759 | not in repo | Unverified | - | Run the same grid in Spark |
| 11 | Table 8 test metrics (acc 0.7303, AUC 0.7580 ...), Table 9 confusion matrix, Table 10 importances (weight_kg 0.2446) | not in repo | Unverified | - | Re-measure; update REPORT if different |
| 12 | RF = Spark MLlib in the notebook (next-day, personalised goal) | `FitPulse_Faculty_Demo.ipynb` s.6 | Implemented, tested (local + HDFS) | `classification_results.csv`, `hdfs/ml/` | keep; document as a *different* experiment |
| 13 | Dashboard model = Logistic Regression | `models/train_goal_achievement.py`, joblib | Implemented | `models/metrics_report.md` (ROC-AUC 0.755 vs RF 0.718) | document distinct roles |
| 14 | K-Means on 437 user averages, 7 features of Table 13, standardised, K=2..10, elbow + silhouette, PCA plot | not in repo | **Missing** (as described) | - | `models/spark_report_kmeans.py` |
| 15 | K=2 chosen, silhouette 0.2018, clusters 210/227 | not in repo | Unverified | - | Re-measure |
| 16 | K-Means (notebook): day-level, K=2..6, K=2 (0.3528), 45,306/54,816 | notebook s.7 | Implemented, tested | `silhouette_scores.csv`, `hdfs/ml/` | keep; document as a *different* experiment |
| 17 | Cluster membership shown on dashboard; label used as classifier feature | - | Missing | - | Add segment to dashboard + exports |
| 18 | Linear Regression predicts calories from steps, distance, active minutes, heart rate; MAE/RMSE/R2 | not in repo | **Missing** | - | `models/train_calorie_regression.py` |
| 19 | Power BI dashboard (goals, segments, calorie trends) | - | **Missing / blocked** | no Desktop, no file | PBI-ready exports + spec; real `.pbix` needs Desktop and GUI authoring |
| 20 | Personalised recommendations (Table 11: prediction -> action) | `models/recommendation_engine.py`, dashboard "Recommendations" tab | Partial | rule-based Steps/Calories/Sleep sections | add probability-band guidance + segment guidance, transparent rules |
| 21 | PPT dashboard metrics: steps/distance/active/sedentary, calories, HR, sleep, goal prediction, recommendations, sedentary alerts | `dashboard/app.py` tabs Today / Trends & Forecast / Sleep / Health Alerts / Recommendations / Benchmarks / Reports | Implemented in Streamlit, **untested** | none | launch + AppTest |
| 22 | PPT "fitness score" | - | Missing | grep: no such feature | decide: implement transparent score or reword |
| 23 | PPT "Fitbit / Kaggle dataset", "millions of records" | - | Wording | dataset is a Kaggle wearable dataset, 100,122 rows | reword |
| 24 | PPT results slide "to be populated" | - | Pending | - | fill with measured values |
| 25 | REPORT 2.6 / 3.6 Implementation URL, platform, notebook name = `[Insert ...]` | - | Placeholder | - | **Needs the user** (no repository URL known) |
| 26 | Actual-vs-predicted calories | - | Missing | - | produced by item 18 + dashboard tab + exports |
| 27 | Daily / monthly trends, step-goal progress, sleep analytics | dashboard | Implemented, untested | - | AppTest |

## 3. Final status

**Update 2026-10-13:** claim 19 (Power BI dashboard) is now implemented: `powerbi/FitPulse_PowerBI_Dashboard.pbix`, built and checked in Power BI Desktop (`faculty_evidence/powerbi/POWERBI_VALIDATION.md`). Streamlit is legacy/optional.


See `FINAL_ACCEPTANCE_TABLE.md` (written at the end of this task, from executed tests only).
