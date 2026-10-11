# FitPulse – Faculty Demo Notes

All numbers here come from the executed notebook `FitPulse_Faculty_Demo.ipynb` (seed 42, reproduced
identically across 3 full runs). Values for the report are in `faculty_evidence/REPORT_VALUES.md`.

## 0. Before the review (5 min)

```powershell
cd D:\bigdata\fitpulsee\FitPulse
.\run_faculty_demo.ps1            # opens the notebook in Jupyter Lab (outputs already saved inside)
```
If PowerShell blocks the script: `powershell -ExecutionPolicy Bypass -File .\run_faculty_demo.ps1`.
In VS Code, open the `.ipynb` and pick the interpreter `D:\bigdata\fitpulsee\.venv\Scripts\python.exe`.

The notebook already contains real saved outputs, so you can present it without re-running. If faculty ask
you to run it live, use **Run All**. It takes about 5–7 minutes, because it re-runs `prepare_raw_dataset.py`
and `spark_etl.py` and then trains all models. Close other heavy apps first, because the laptop has little free RAM.

## 1. What to show first (suggested order)

1. **§1 table "What is and isn't implemented".** It sets honest expectations up front.
2. **§2.1 pipeline execution.** The real `spark_etl.py` output, plus the SHA-256 proof that the raw file reproduces byte-for-byte.
3. **§2.2–2.4.** 100,122 rows × 23 columns (Bronze), 39 columns (Silver), 437 users, schema, first 10 rows.
4. **§6.6–6.10 confusion matrix → formulas.** The strongest "this is real" evidence: every metric is computed by hand from TP/TN/FP/FN and asserted equal to Spark's evaluator.
5. **§7.4–7.5 silhouette table and plot.** K was chosen by the data (K=2), not assumed.
6. **§8 Spark evidence.** The physical plans (shuffle `Exchange`, partial/final `HashAggregate`, `BroadcastHashJoin`), 96 Parquet files in 12 month partitions, and partition pruning.

## 2. What each section proves

| Section | Proves |
|---|---|
| 2 Dataset | Real source (Kaggle, 687,701 rows / 3,000 participants), real subset (100,122 rows / 437 users, 2024-01-01 to 2024-12-25) |
| 3 Data quality | 0 missing cells and 0 duplicates in Bronze. Silver nulls are only structural lag nulls (437 / 874 / 3,059 = 1×/2×/7× users) |
| 4 Preprocessing | Every cleaning and feature step, with file and line number. Spark lag/rolling/goal values verified by hand |
| 5 Split | 70.07% / 14.95% / 14.98% = 43,996 / 9,384 / 9,406 of 62,786 rows, reproducible (seeded hash) |
| 6 Random Forest | Spark MLlib RF: accuracy 71.87%, precision 58.49%, recall 81.39%, F1 68.07%, ROC-AUC 82.47% |
| 6.12 | The same model on the original chronological split: lower F1 (34.44%) and AUC (72.62%), shown honestly |
| 7 K-Means | Silhouette for K=2..6, K=2 selected (0.3528), cluster sizes 45,306 / 54,816 |
| 8 Big Data | Spark 4.0.1, local[*] with 12 cores, MLlib, shuffles, broadcast join, partitioned Parquet. **No HDFS** |

## 3. Things to say proactively (they protect you)

* **The 70/15/15 split was added for this review.** The original project script used a chronological
  train/test split (cutoff 2024-10-15). The notebook shows both.
* **K-Means was added for this review.** It did not exist in the repo before.
* **The Random Forest in the notebook is Spark MLlib.** The dashboard's saved model
  (`models/artifacts/goal_achievement_model.joblib`) is the scikit-learn pipeline from
  `models/train_goal_achievement.py`, and by its own report the deployed winner there is *Logistic Regression*.
* **There is no HDFS and no Power BI.** Storage is HDFS-style partitioned Parquet on the local disk. The dashboard is Streamlit.

## 4. Likely questions and short answers

**Why did you use Spark?**
Its window functions (per-user lags and rolling averages), groupBy/agg (per-user goals) and MLlib all run
partition-parallel, and the same code scales from a laptop (`local[*]`, 12 cores here) to a cluster by changing
only `.master()` and the storage path. pandas would need a rewrite to scale.

**Why HDFS?**
Be careful: **HDFS is not running in this project** (§8.4 shows `hdfs` is not installed and `fs.defaultFS = file:///`).
What we implemented is HDFS-*style* storage: columnar Parquet, Hive-style `month=` partitions, and partition pruning
(the §8.3 plan shows `PartitionFilters: month = 2024-03`). Spark reads it through Hadoop's FileSystem API, so pointing
the path at `hdfs://…` is the only change needed. HDFS would add replication and fault tolerance across machines.

**Why Random Forest?**
The data is tabular and mixes numeric and categorical features. RF handles non-linear interactions such as
season × weekday × recent trend without scaling, resists overfitting by averaging 100 trees, gives feature
importances, and is built into Spark MLlib.

**Why K-Means?**
It is simple, scalable (Spark MLlib), interpretable through its centers, and the silhouette score gives an
objective way to choose K. We cluster *days* because per-user averages barely differ (std of per-user average
steps is 115, versus 2,057 across days, §7.2).

**Why this target variable?**
`label` = whether the user hits their **personalized** goal (1.10 × their own average steps, from `spark_etl.py`)
**tomorrow**. It is the project's existing Model 1 target, it is actionable (warn the user today), and it has no
leakage. A same-day label would leak, because `steps_roll7_avg` includes today's steps.

**Why these features?**
Classification uses only information known before tomorrow: steps from 1, 2 and 7 records earlier, 7-record rolling
averages, age, BMI, gender, activity type, day of week and cyclical month. These are the same features as the
existing `train_goal_achievement.py`. For clustering, see §7.2: resting HR is excluded because it is constant per
user, and sedentary minutes because it equals 1440 − sleep − active exactly.

**How did you split the dataset?**
62,786 usable rows (consecutive next-day pairs with complete lag features). Each row is assigned by a seeded hash
of (user_id, date): <0.70 train, <0.85 validation, otherwise test. That gives 43,996 / 9,384 / 9,406
(70.07% / 14.95% / 14.98%). Validation was used only to choose maxDepth (6/8/10 → 8). Test was used once.

**How was accuracy calculated?**
Accuracy = (TP + TN) / total = (2,820 + 3,940) / 9,406 = 6,760 / 9,406 = **71.87%**. Show §6.7: the hand calculation
equals Spark's `MulticlassClassificationEvaluator`.

**What is the difference between precision and recall?**
Precision = TP / (TP + FP) = 2,820 / 4,821 = **58.49%**: when the model says "you'll hit your goal", it is right 58% of the time.
Recall = TP / (TP + FN) = 2,820 / 3,465 = **81.39%**: of the days the goal was really hit, the model caught 81%.
Class weighting makes the model favour recall. F1 = 2PR/(P+R) = **68.07%** balances the two.

**What does the confusion matrix show?**
TN 3,940 (correctly predicted misses), TP 2,820 (correctly predicted hits), FP 2,001 (predicted hit but missed,
the main error type), FN 645 (predicted miss but hit).

**Is 71.87% accuracy good?**
Always predicting "missed" would already score 63.16%. The model beats that, and its ROC-AUC of 82.47% shows real
ranking ability. Under the stricter chronological split, accuracy is 86.08% but that is misleading: only 11.8% of
those test days are positives, and F1 drops to 34.44%. The scikit-learn RF in `models/metrics_report.md` (F1 0.344,
AUC 0.718) agrees with that.

**What drives the prediction?**
Feature importance: `month_sin` (0.374), `day_of_week` (0.249) and `steps_roll7_avg` (0.191). The data has strong
seasonal and weekly rhythms, and the goal is based on the yearly average, so it is easier to hit in high-activity months.

**Why did you select this K?**
K=2 has the highest silhouette (0.3528, versus 0.2879, 0.2676, 0.2664 and 0.2777 for K=3–6). The elbow curve has no
clear elbow, so silhouette decides. 0.35 is moderate: daily behaviour is a continuum, and we say so.

**What does each cluster represent?**
* Cluster 0 – **High-effort / long-session days** (45,306 days, 45.25%): 95.5 active minutes (+36.6%), 994 kcal (+50.2%),
  more High-intensity, HIIT and Running sessions.
* Cluster 1 – **Light / short-session days** (54,816 days, 54.75%): 48.8 active minutes (−30.3%), 388 kcal (−41.5%),
  more Yoga, Walking and Weight-training.
* Steps, sleep and heart rate barely differ (within ±3%), so the clusters are about workout length and intensity, not walking.

**How does this qualify as a Big Data project?**
It uses the Big Data stack and patterns: Spark DataFrames, window functions, MapReduce-style partial/final aggregation
with a shuffle, a broadcast join, columnar partitioned Parquet with pruning, Spark SQL (`spark_benchmarks.py`) and Spark
MLlib. The architecture is the medallion design (Bronze → Silver → Gold). Be honest about scale: 100k rows run on one
machine in local mode, and the design scales out unchanged.

**How can the model produce personalized recommendations?**
(1) Goals are personal (1.10 × the user's own average). (2) The RF gives each user a daily probability of hitting
tomorrow's goal; if it is low, the recommendation engine (`models/recommendation_engine.py`) suggests extra minutes
based on that user's own pace. (3) K-Means gives each user's share of high-effort days, for example demo1 (user 1503)
55.7%, demo2 (user 2759) 35.7%, against a population median of 45.0%, so a low-share user can be nudged toward one more long session per week.

## 5. Known limitations (say them before they are asked)

* Kaggle data, not our own devices. `max_heart_rate` and `sleep_quality_score` are formula-derived in `prepare_raw_dataset.py`.
* `is_rest_day` is always 0 (every day has a ≥20-minute session), so it is unused.
* The random split is record-level (same users in train and test). The chronological result is the stricter estimate.
* The per-user goal uses the user's full-year average, which includes test-period days.
