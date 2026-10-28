# FitPulse – Faculty Demo Notes

Numbers for the supervised experiments E1-E5 come from `exports/E<n>_results.csv` and the executed notebook `FitPulse_Faculty_Demo.ipynb` sections 5-7 (seed 42).
Numbers marked **[PREVIOUS]** belong to the archived pre-supervised notebook (`archive/FitPulse_Faculty_Demo_pre_supervised.ipynb`); the old report-value file and the other pre-supervised evidence are archived under `archive/` (see `archive/README.md`).

## 0a. Power BI dashboard - the primary dashboard (demo first, 5 min)

File: `D:\bigdata\fitpulsee\FitPulse\powerbi\FitPulse_PowerBI_Dashboard.pbix` (Power BI Desktop is installed on this laptop). **Re-save it from the regenerated project first**: open `powerbi\project\FitPulse_PowerBI_Dashboard.pbip`, Refresh, Save as that `.pbix` (details in `powerbi/README.md`). After that, double-click it; the data is cached.
Walk through the five page tabs:
1. **Fitness Overview** - 437 users, 1,00,122 user-days, 8,625 average steps, 662.2 kcal, 69.9 active minutes, 33.8% goal rate. Say: the goal is 1.10 x each user's own average, not a fixed 8,000.
2. **Activity and Sleep** - distance, active vs sedentary minutes, sleep hours and quality, intensity and activity type.
3. **Calorie Prediction** - Linear Regression: test MAE 199.7 kcal, RMSE 263.6, R-squared 0.6296 against a mean baseline MAE of 334.5; actual-vs-predicted scatter and error histogram (test days only).
4. **Supervised Results E3 and E4** - the two supervised experiments that replaced the earlier segmentation views, one chart per experiment: ROC-AUC by model, accuracy against the majority baseline, the 5-fold spread (E3) and the INVALID leakage runs. Everything is read from `exports/E3_results.csv` and `exports/E4_results.csv`; both are near chance once label-encoding columns are removed.
5. **Model Evaluation** - all five experiments E1-E5: comparison table with baselines, ROC-AUC by experiment and evaluation split, INVALID leakage runs and the independent cross-check (103/103 checks passed, HDFS rerun). Results of different experiments are never combined.
Try the **Activity type** slicer on page 1 (for example Cycling: 10,740 user-days, 8,595 average steps) - these figures match the CSV.
If asked how it connects to the big data stack: Power BI imports CSV exports of the Silver data and saved model results; it does **not** read HDFS. HDFS is real but single-node, replication factor 1.
Refresh after rerunning the pipeline: `.\powerbi\build_powerbi.ps1`, then Home > Refresh in Desktop.
Automated validation of the regenerated project: `faculty_evidence/powerbi/project_validation.md`. What Power BI Desktop renders from the regenerated file has not been checked yet (the earlier Desktop check applied to the previous `.pbix`). Streamlit is legacy/optional and is **not** needed for the demo.

## 0d. Supervised experiments E1-E5 (READ FIRST - this supersedes the older notes marked [PREVIOUS] below)

The faculty asked for supervised learning, so **all five experiments are now supervised** and the notebook sections 5-7 (and 9-10) were rebuilt:
E1 same-day goal (RF, Logistic Regression, GBT), E2 next-day goal (history only, chronological split), E3 user-level `high_achiever`, E4 user-day `activity_level`, E5 calories (Linear Regression + RF + GBT regressors).
The two earlier segmentation experiments were removed (archived, see `archive/README.md`). Numbers and 10 viva questions: `SUPERVISED_REPORT.md` (project root); results: `exports/E<n>_results.csv`.

Say these things yourself, before they are asked:
* Calories, distance, active/sedentary minutes, max heart rate and sleep quality are **partly derived** in this demonstration dataset, so some scores are formula recovery.
* Every experiment has a leakage run with a forbidden feature; it scores much higher and is marked **INVALID** (never cited).
* E2 is honest but weak: accuracy has to be compared with the always-'missed' baseline of the test block; ROC-AUC is the fairer number. A random split would have looked much better.
* E3 (users) and E4 (activity level) are near chance once label-encoding columns are removed: that is a valid negative result, shown with its baseline.
* Power BI pages 4 and 5 now show only the supervised results, and the web page no longer shows a user grouping; the saved `.pbix` must be re-saved from the regenerated project (section 0a).

Sections of this file that describe the previous next-day Random Forest or the report-aligned experiments are marked **[PREVIOUS]**: they document the archived notebook (`archive/FitPulse_Faculty_Demo_pre_supervised.ipynb`).

## 0a-2. Per-user insights page (the main goal, 3 min)

Run `.\webapp\run_local.ps1` (or open the Vercel URL). Choose a user: tomorrow's goal probability, personal step goal, percentile vs all users, recommendations, 60-day charts.
Say: all 437 users' data trains the models; each person's insight is that model applied to their own history. It shows pre-computed results (not a live service); data is a public Kaggle dataset; not medical advice.

## 0. Notebook (optional, 5 min)

```powershell
cd D:\bigdata\fitpulsee\FitPulse
.\run_faculty_demo.ps1            # opens the notebook in Jupyter Lab (outputs already saved inside)
```
If PowerShell blocks the script: `powershell -ExecutionPolicy Bypass -File .\run_faculty_demo.ps1`.
In VS Code, open the `.ipynb` and pick the interpreter `D:\bigdata\fitpulsee\.venv\Scripts\python.exe`.

The notebook already contains real saved outputs, so you can present it without re-running. If faculty ask
you to run it live, use **Run All**. It takes about 5–7 minutes, because it re-runs `prepare_raw_dataset.py`
and `spark_etl.py` and then trains all models. Close other heavy apps first, because the laptop has little free RAM.

## 0b. HDFS demo (extra 3 min)

```powershell
.\start_hdfs.ps1                 # NameNode + DataNode up, waits for a live DataNode
.\run_fitpulse_hdfs.ps1          # Bronze -> HDFS, Spark ETL in HDFS mode, 16 verification checks (exit code != 0 on failure)
. .\scripts\hdfs_env.ps1; hdfs dfs -ls -R /fitpulse; hdfs dfs -du -h /fitpulse     # live listing
.\stop_hdfs.ps1                  # when finished (data stays)
```
Then open notebook **§11**. Say plainly: single node, replication 1, Spark in local[*]; ROC-AUC re-measured from HDFS differs
from the local run only in the 7th decimal for the supervised experiments the HDFS rerun matches the local run within 6.76e-05 at most (`faculty_evidence/supervised/local_vs_hdfs_summary.md`).
Do **not** run `hdfs namenode -format` again; it would erase HDFS contents.

## 0c. Other additions [PREVIOUS notes; the notebook is now sections 5-7, 11 and 12]

* **Linear Regression for calories** (now E5, §7.2): test MAE 199.7 kcal, RMSE 263.6 kcal, R2 0.630; baseline MAE 334.5 kcal.
* **[PREVIOUS] Report-aligned experiment** (old §13, archived): same-day `steps >= 8,000` Random Forest (accuracy 0.735, ROC-AUC 0.759; now E1).
  100 trees at depth 15/20 ran out of memory here, so the report's "best = 100 trees, depth 20" is **not reproduced**.
* **Power BI is the primary dashboard** (section 0a): automated validation of the regenerated project is in `faculty_evidence/powerbi/project_validation.md`; re-check the saved `.pbix` in Power BI Desktop after re-saving it.
* **Streamlit is legacy/optional**: tested earlier (`python scripts/test_dashboard.py`, 15/15; a Windows-only `%-d` crash was fixed), not required for the demo.
* Corrected copies of the report and slides: `D:\bigdata\FitPulse_Report_Updated_v3.docx`, `D:\bigdata\actualfitpulseppt_v2.pptx` (originals untouched; `faculty_evidence/REPORT_AND_PPT_CHANGE_LOG.md`).

## 1. What to show first (suggested order)

1. **§1 table "What is and isn't implemented".** It sets honest expectations up front.
2. **§2.1 pipeline execution.** The real `spark_etl.py` output, plus the SHA-256 proof that the raw file reproduces byte-for-byte.
3. **§2.2–2.4.** 100,122 rows × 23 columns (Bronze), 39 columns (Silver), 437 users, schema, first 10 rows.
4. **§5 protocol and §6.1 (E1).** Seed, validation-only tuning, leakage rules, derived-data note, then the model comparison table against the majority baseline and the INVALID leakage run.
5. **§6.2 (E2) and §7.3.** The chronological split and why it is the headline, then the verification table (leakage, baselines, scikit-learn cross-check, HDFS rerun).
6. **§8 Spark evidence.** The physical plans (shuffle `Exchange`, partial/final `HashAggregate`, `BroadcastHashJoin`), 96 Parquet files in 12 month partitions, and partition pruning.

## 2. What each section proves

| Section | Proves |
|---|---|
| 2 Dataset | Real source (Kaggle, 687,701 rows / 3,000 participants), real subset (100,122 rows / 437 users, 2024-01-01 to 2024-12-25) |
| 3 Data quality | 0 missing cells and 0 duplicates in Bronze. Silver nulls are only structural lag nulls (437 / 874 / 3,059 = 1×/2×/7× users) |
| 4 Preprocessing | Every cleaning and feature step, with file and line number. Spark lag/rolling/goal values verified by hand |
| 5 Protocol | Seed 42, validation-only tuning, leakage rules, baselines, the derived-data note, the seasonal pattern in the data |
| 6 Goal prediction (E1-E3) | Same-day, next-day (history only, chronological) and user-level classifiers, each against its baseline, with INVALID leakage runs |
| 7 Activity level and calories (E4-E5) + 7.3 | User-held-out activity classifier, calorie regression, and the verification table (leakage, baselines, scikit-learn cross-check) |
| [PREVIOUS] old 5-7 | Old 70/15/15 next-day RF (ROC-AUC 82.47%, random split): archived, not supervised-compliant |
| 8 Big Data | Spark 4.0.1, local[*] with 12 cores, MLlib, shuffles, broadcast join, partitioned Parquet. Sections 1-10 used local Parquet; **§11 = real single-node HDFS 3.4.1** (verified) |
| 11 HDFS | Live `hdfs` CLI output, Spark read of `hdfs://localhost:9000/fitpulse/silver` (100,122 rows, 12 month partitions), write/read-back test, HDFS-vs-local identical rows, ML re-run from HDFS, behaviour when HDFS is down |

## 3. Things to say proactively (they protect you)

* **The experiments were rebuilt as supervised for this review** (E1-E5). The previous 70/15/15 next-day RF and the two earlier segmentation experiments are archived.
* **The Random Forest in the notebook is Spark MLlib.** The dashboard's saved model
  (`models/artifacts/goal_achievement_model.joblib`) is the scikit-learn pipeline from
  `models/train_goal_achievement.py`, and by its own report the deployed winner there is *Logistic Regression*.
* **The dashboard is Power BI** (`.pbix`, imports CSV; Streamlit is legacy). **HDFS is real but single-node** (one NameNode + one DataNode, replication 1): it stores Bronze and Silver and Spark reads/writes it, but it gives no fault tolerance on one machine. Sections 1-10 of the notebook were produced from local Parquet; §11 is the HDFS evidence. Power BI reads CSV exports; the legacy Streamlit app, scikit-learn models and SQLite use local files.

## 4. Likely questions and short answers

**Why supervised only?** The faculty asked for supervised learning: every experiment predicts a labelled target (goal reached, high achiever, High/Low activity, calories) and is scored against held-out labels and a baseline.
**How do you know there is no leakage?** Forbidden features are never used, E2's windows end at -1 (checked by rebuilding the features in pandas and by changing day *t* and later days), and each experiment runs once *with* a leaky feature to show the inflated score, which is stored as INVALID.
More (10 viva questions with answers): `SUPERVISED_REPORT.md` (project root). The questions below marked **[PREVIOUS]** are about the archived experiments.

**Why did you use Spark?**
Its window functions (per-user lags and rolling averages), groupBy/agg (per-user goals) and MLlib all run
partition-parallel, and the same code scales from a laptop (`local[*]`, 12 cores here) to a cluster by changing
only `.master()` and the storage path. pandas would need a rewrite to scale.

**Why HDFS?**
HDFS splits files into blocks, keeps them on DataNodes (metadata on the NameNode) and can replicate them, so a dataset
can outgrow one disk and survive a node failure. Here it is a **single-node** demo (replication 1): we can show the
storage layer and Spark integration really work (`hdfs://localhost:9000/fitpulse/...`), but not fault tolerance.
Spark's DataFrame code did not change; only the path/URI did (`--storage hdfs`). Local Parquet stays as an explicit fallback.
If HDFS is down, HDFS mode exits with code 2 rather than silently writing locally (notebook §11.7).

**Why Random Forest?**
The data is tabular and mixes numeric and categorical features. RF handles non-linear interactions such as
season × weekday × recent trend without scaling, resists overfitting by averaging 100 trees, gives feature
importances, and is built into Spark MLlib.

**[PREVIOUS] Why this target variable?**
`label` = whether the user hits their **personalized** goal (1.10 × their own average steps, from `spark_etl.py`)
**tomorrow**. It is the project's existing Model 1 target, it is actionable (warn the user today), and it has no
leakage. A same-day label would leak, because `steps_roll7_avg` includes today's steps.

**[PREVIOUS] Why these features?**
Classification uses only information known before tomorrow: steps from 1, 2 and 7 records earlier, 7-record rolling
averages, age, BMI, gender, activity type, day of week and cyclical month. These are the same features as the
existing `train_goal_achievement.py`.

**[PREVIOUS] How did you split the dataset?**
62,786 usable rows (consecutive next-day pairs with complete lag features). Each row is assigned by a seeded hash
of (user_id, date): <0.70 train, <0.85 validation, otherwise test. That gives 43,996 / 9,384 / 9,406
(70.07% / 14.95% / 14.98%). Validation was used only to choose maxDepth (6/8/10 → 8). Test was used once.

**[PREVIOUS] How was accuracy calculated?**
Accuracy = (TP + TN) / total = (2,820 + 3,940) / 9,406 = 6,760 / 9,406 = **71.87%**. Show §6.7: the hand calculation
equals Spark's `MulticlassClassificationEvaluator`.

**What is the difference between precision and recall?**
Precision = TP / (TP + FP) = 2,820 / 4,821 = **58.49%**: when the model says "you'll hit your goal", it is right 58% of the time.
Recall = TP / (TP + FN) = 2,820 / 3,465 = **81.39%**: of the days the goal was really hit, the model caught 81%.
Class weighting makes the model favour recall. F1 = 2PR/(P+R) = **68.07%** balances the two.

**[PREVIOUS] What does the confusion matrix show?**
TN 3,940 (correctly predicted misses), TP 2,820 (correctly predicted hits), FP 2,001 (predicted hit but missed,
the main error type), FN 645 (predicted miss but hit).

**[PREVIOUS] What drives the prediction?**
Feature importance: `month_sin` (0.374), `day_of_week` (0.249) and `steps_roll7_avg` (0.191). The data has strong
seasonal and weekly rhythms, and the goal is based on the yearly average, so it is easier to hit in high-activity months.

**How does this qualify as a Big Data project?**
It uses the Big Data stack and patterns: Spark DataFrames, window functions, MapReduce-style partial/final aggregation
with a shuffle, a broadcast join, columnar partitioned Parquet with pruning, Spark SQL (`spark_benchmarks.py`) and Spark
MLlib. The architecture is the medallion design (Bronze → Silver → Gold). Be honest about scale: 100k rows run on one
machine in local mode, and the design scales out unchanged.

**[PREVIOUS] How can the model produce personalized recommendations?**
(1) Goals are personal (1.10 × the user's own average). (2) The RF gives each user a daily probability of hitting
tomorrow's goal; if it is low, the recommendation engine (`models/recommendation_engine.py`) suggests extra minutes
based on that user's own pace.

## 5. Known limitations (say them before they are asked)

* Kaggle data, not our own devices. `max_heart_rate` and `sleep_quality_score` are formula-derived in `prepare_raw_dataset.py`.
* `is_rest_day` is always 0 (every day has a ≥20-minute session), so it is unused.
* The random split is record-level (same users in train and test). The chronological result is the stricter estimate.
* The per-user goal uses the user's full-year average, which includes test-period days.
