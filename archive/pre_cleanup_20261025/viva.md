# FitPulse — Viva Cheat Sheet

Plain-language answers to the questions you're most likely to get asked. Read this after
you've run the pipeline yourself at least once — it'll make more sense with the numbers
in front of you (`models/metrics_report.md` has all of them).

---

## "What big data tools did you use, and why?"

### Apache Spark (PySpark)
**What it is:** a distributed data-processing engine that splits a computation into
partitions and runs them in parallel, whether across many machines or many cores on one.
**Where it's used:** `etl/spark_etl.py` — the entire Bronze → Silver transformation
(cleaning, window functions for lag/rolling features, per-user goal aggregation) runs as
Spark DataFrame operations, not pandas.
**Why not just pandas:** pandas loads everything into memory on one core and computes
row-by-row/column-by-column with no partitioning concept — it has no way to express "do
this independently for each user, in parallel, then combine." Spark's DataFrame API forces
you to express transformations in that partition-then-combine shape from the start, so the
same code that works on 100k rows on a laptop is the same code that would run on a
100-node cluster processing billions of rows — you'd change the `.master()` config, not
the transformation logic. That's the actual point of learning Spark for a small project:
the *pattern*, not the row count.

### HDFS (real, single-node) and the local Parquet fallback
**What it is:** HDFS splits files into blocks held by DataNodes, with metadata on a NameNode; blocks can be
replicated so a node failure does not lose data.
**What we actually run:** Hadoop 3.4.1 on this Windows laptop with **one NameNode and one DataNode, replication factor 1**.
`etl/spark_etl.py --storage hdfs` reads the Bronze CSV from `hdfs://localhost:9000/fitpulse/bronze/` and writes the Silver
Parquet (partitioned by `month`) to `hdfs://localhost:9000/fitpulse/silver/`. The default (no flag) still writes local
Parquet to `data/processed/fitpulse_silver/`; the two modes are never mixed silently, and HDFS mode exits with code 2 if
the NameNode is down. Evidence: `faculty_evidence/hdfs/` and notebook section 11.
**Be precise about the limits:** with one node there is no real fault tolerance or horizontal scaling to demonstrate - the
report's "replication factor 3" describes what HDFS does on a cluster, not what this deployment does. The Streamlit
dashboard, the scikit-learn models and the Power BI exports read **local** files (the local Silver is proven row-for-row
identical to the HDFS Silver), not HDFS.
**Why partition by month:** a query filtering on month opens only the matching folder (partition pruning); Parquet adds
columnar storage and compression.

### Spark SQL (the Hive/SQL-on-big-data pattern)
**What it is:** the ability to register a distributed DataFrame as a temporary SQL table
and query it with plain SQL, which Spark then executes using the same distributed engine
underneath — this is exactly how Hive and Presto let you SQL-query big data.
**Where it's used:** `etl/spark_benchmarks.py` registers the Silver layer as a temp view
and computes each user's cohort percentile rank using `PERCENT_RANK() OVER (PARTITION BY
age_group, gender ORDER BY avg_steps)` — plain SQL, not DataFrame method chaining.
**Why SQL here specifically:** percentile/window ranking logic reads far more clearly as
SQL than as chained DataFrame calls, and it demonstrates that Spark isn't just a
programmatic API — it's also a full SQL engine over distributed data, the same mental
model as querying a data warehouse.

### The MapReduce pattern
**What it is:** the two-step shape underlying most distributed batch processing — Map
(transform each record independently, in parallel) then Reduce (combine records that
share a key into one result per key).
**Where it's used, concretely:** in `etl/spark_etl.py`, the personalized-goal computation
is textbook MapReduce — Map: each row implicitly carries a `(user_id, steps)` pair; Reduce:
`df.groupBy("user_id").agg(avg("steps"))` combines every row for the same user into one
average. The code has an inline comment marking exactly this at that line.
**Why point to this specifically if asked:** it's the clearest, smallest example of the
pattern in the whole project — good to have memorized as your one-sentence answer.

### Streaming simulation (optional, explicitly simplified)
**What it is:** Kafka + Spark Structured Streaming is the standard way real systems
process data as it arrives continuously, rather than in one big nightly batch.
**Where it's used:** `etl/streaming_simulation.py` — a script writes small new CSV
"batches" into `data/streaming_inbox/` (standing in for messages arriving on a Kafka
topic), and Spark's actual `readStream`/`writeStream` API (in `trigger(availableNow=True)`
mode) picks up only the new files and appends them.
**Be upfront if asked:** this genuinely uses Spark's streaming API, but it's a simplified
simulation — there's no real Kafka broker and no continuously-running cluster, since
neither is available in a student environment. Say this plainly if asked; don't imply more
than what's actually built.

---

## "Isn't 100,000 rows too small to need big data tools?"

Yes — and that's an intentional, honest tradeoff to be upfront about, not something to
dodge. **This project demonstrates the architecture and processing patterns that matter
at real big-data scale — distributed transformations, partitioned columnar storage, batch
ETL pipelines, SQL-on-distributed-data — using a dataset small enough to run and explain
interactively.** None of the code changes if the dataset were 1,000x larger: the same
`spark_etl.py` script, the same partitioning strategy, the same `groupBy().agg()` calls
would run on a cluster instead of a laptop by changing `.master("local[*]")` to point at a
cluster manager (YARN/Kubernetes) and pointing the storage paths at real HDFS/S3 instead
of a local folder. What we're being graded on is whether the pipeline is *built the right
way* for scale, not whether this particular dataset requires it yet.

---

## "What ML did you use, and why?"

### Model 1 — Next-Day Goal Achievement Prediction
**Business question:** "Based on my pattern through today, how likely am I to hit my step
goal tomorrow?"
**Algorithm:** Logistic Regression (won over Random Forest — see below).
**How it works, plainly:** it looks at the user's recent activity (yesterday's steps, a
week's rolling average, etc.) and the calendar month, and draws a straight-line-style
boundary between "likely to hit tomorrow's goal" and "not," based on patterns learned from
every other consecutive-day pair in the training data.
**Result:** ROC-AUC 0.755 on a genuine out-of-time test split (trained on Jan–mid-Oct,
tested on mid-Oct–Dec). Random Forest scored lower (ROC-AUC 0.718) — the simpler model
won, which is itself a fine, explainable outcome: the relationship is close to linear once
seasonality is encoded.
**A mistake we found and fixed:** the dashboard originally showed this as a same-day
prediction ("likely to hit *today's* goal") using a model trained on same-day features —
which produced a visibly broken-looking UI when someone had already exceeded today's step
count but the badge still showed a low probability (the model deliberately never sees
today's own steps, to avoid leakage). Renaming the label to "tomorrow" fixed the apparent
contradiction, but we then checked whether the underlying model was actually any good at
that task — it wasn't (ROC-AUC dropped to 0.738 when repurposed) — so we retrained it
directly against real next-day outcomes instead. See `models/metrics_report.md` for the
full before/after comparison.

### Model 2 — 7-Day Activity Trend Forecast
**Business question:** "How active should I expect to be this week?"
**Algorithm:** Gradient Boosting Regression (scikit-learn's HistGradientBoostingRegressor
— same family as XGBoost/LightGBM), using lag features.
**How it works, plainly:** it predicts tomorrow's steps from the last few days' steps and
rolling averages, then treats that prediction as the new "yesterday" to predict the day
after — repeated seven times to get a week-long forecast.
**Result:** mean absolute error of 1,436 steps over a 7-day-ahead forecast, evaluated with
genuine walk-forward validation (each user's last 7 real days held out and predicted from
real history before them) — about 16.6% of the dataset's average daily steps.

### Model 3 — Sleep Quality Prediction
**Business question:** "Which of my daytime habits help or hurt my sleep?"
**Algorithm:** Linear Regression (baseline) and Random Forest Regression (improved,
winner).
**How it works, plainly:** it learns how sleep-quality score moves with stress level,
sedentary time, and heart rate across all users, then applies that same relationship to
predict one user's tonight from their own day.
**Result:** Random Forest R² = 0.876 (MAE 3.49 points on a 0–100 scale), clearly better
than Linear Regression's R² = 0.812. Feature importance shows `stress_level` (59%) and
`sedentary_minutes` (27%) are by far the two biggest drivers — a genuinely useful,
explainable insight for the user.

### Model 4 — Abnormal Heart Rate / Health Risk Flagging
**Business question:** "Was anything about my heart rate today unusual, for ME
specifically?"
**Algorithm:** Isolation Forest (unsupervised anomaly detection), fit separately per user.
**How it works, plainly:** it learns the "normal shape" of a user's own heart rate data
and flags days that sit apart from that shape — no labels needed, since we never know in
advance which days are actually anomalous.
**Result:** flags 3.1% of days; a much simpler z-score threshold rule (flag if >2.5
standard deviations from that user's own mean) flags 0.9% and **agrees with Isolation
Forest on 97.6% of days** — strong evidence the model isn't flagging noise.
**Explicitly not a diagnosis:** the dashboard copy always frames this as "worth a look,"
never a medical claim — say this plainly if asked.

### Model 5 — Personalized Recommendation Engine
**Business question:** "What's one concrete thing I should do differently today?"
**Algorithm:** none — deliberately rule-based logic (`models/recommendation_engine.py`),
sitting on top of Models 1 and 3's outputs.
**Why not ML here:** a recommendation needs to be *traceable* — "you're 1,751 steps short,
at your usual pace that's 14 more minutes" is something a user can verify and trust. A
model that outputs "walk more" with no inspectable reasoning is a worse product decision,
not just a simpler one.

### Model 6 — Percentile Benchmarking
**Business question:** "How do I compare to people like me?"
**Method:** NOT machine learning — a statistical computation, `PERCENT_RANK()` in Spark
SQL, computed once per user against their (age group, gender) cohort.
**If asked for its "accuracy":** there isn't one, because it isn't a trained model — it's
descriptive statistics computed in a batch job. Saying this plainly is the correct answer.

---

### Model 7 - Calorie-burn Linear Regression (Spark MLlib)
*(Now experiment **E5**: Random Forest and GBT regressors were added for comparison - see the supervised section below.)*
**Task:** estimate a day's `calories_burned` (same day, not a forecast) from steps, distance, active minutes, heart rate and body profile.
**Where:** `models/train_calorie_regression.py`; coefficients saved in `models/artifacts/calorie_linreg_config.json`; used live by the dashboard.
**Result (held-out test days):** MAE 199.7 kcal, RMSE 263.6 kcal, R-squared 0.630. The "always predict the training mean" baseline has MAE 334.5 kcal and R-squared 0.
**Why it is honest:** scaling and one-hot encoding are fitted on the training split only; calorie-derived columns and the dependent minute columns are excluded;
a chronological check (train before 2024-10-15) gives R-squared 0.58, so the relationship drifts over the year.
**Expected questions:** *Why are the steps and distance coefficients of opposite sign?* They are 94% correlated, so only their combination is identifiable.
*Is 0.63 good?* It is moderate: a useful estimate, not a measurement. *Why not predict tomorrow's calories?* That is a different problem; the report asks for a calorie-burn estimate.

### Supervised experiments E1-E5 (this replaces the old "report experiments vs notebook experiments" split)
Every experiment is now **supervised**; the two K-Means experiments were replaced and their code is in `archive/kmeans/`.
* **E1** same-day goal (`steps >= 8,000`): Random Forest (unchanged) + Logistic Regression + Gradient-Boosted Trees, random 70/15/15, seed 42.
* **E2** next-day goal from history strictly before the day (window frames end at -1), **chronological** split; accuracy must be read against the test-block baseline, ROC-AUC is the fairer summary.
* **E3** user-level `high_achiever` (above-median goal rate), 437 users, stratified 5-fold CV; **E4** `activity_level` High/Low from `active_minutes`, user-held-out split.
* **E5** calories: the Linear Regression above plus Random Forest and GBT regressors.
Say first: calories, distance, active/sedentary minutes, max heart rate and sleep quality are **partly derived** in this demonstration dataset; every leakage run is stored with status INVALID and is never a result.
All numbers, limitations and 10 viva questions with answers: `faculty_evidence/supervised/SUPERVISED_REPORT.md`; raw results: `exports/E<n>_results.csv`.
The legacy Streamlit app uses **Logistic Regression** for its goal probability (ROC-AUC 0.755 in `models/metrics_report.md`, an earlier run that was not repeated) and still contains an unsupervised Isolation Forest for heart-rate flagging; neither is part of E1-E5.

### Is there a Power BI dashboard?
Yes - it is the primary dashboard: `powerbi/FitPulse_PowerBI_Dashboard.pbix`, five pages (Fitness Overview, Activity and Sleep, Calorie Prediction, User Segmentation, Model Evaluation).
It was built from a generated Power BI Project and saved by Power BI Desktop; it imports validated CSV exports of the Silver data and the saved model results.
Say precisely: Power BI does **not** read HDFS; the cards were checked against independent pandas values; one slicer (Activity type) was tested by clicking; other slicers were not individually tested.
The earlier Streamlit app is legacy and optional.

## "How is the dashboard connected to the big-data pipeline?"

Two layers that never touch each other at the wrong time:

- **Offline (batch, runs on the full dataset):** `etl/spark_etl.py` and
  `etl/spark_benchmarks.py` process all 100,122 rows / 437 users with Spark, and
  `models/train_*.py` train the four ML models against that processed data. This all runs
  ahead of time, on a schedule, not per user request — exactly like a real production
  system wouldn't retrain a model every time a user opens the app.
- **Online (per request, one user at a time):** `dashboard/app.py` loads the *already
  trained* model files (`models/artifacts/*.joblib`) and queries SQLite for *one* user's
  rows plus the small precomputed percentile table — never the full dataset, never a
  live Spark job. A Streamlit session starting a fresh Spark cluster on every page load
  would be far too slow for an interactive app; that's precisely why the two layers are
  separated and why SQLite (not Parquet/Spark) is the serving store.

---

## Likely follow-up questions

**"Why not deep learning (LSTM) for the forecast?"**
Gradient boosting on lag/rolling features gets a defensible, low error (16.6% of average)
on a dataset of this size, and — critically — its behavior is easy to explain in a
sentence ("predict tomorrow from the last few days, repeat"). An LSTM needs far more data
to train well and its internal reasoning is much harder to describe simply, which matters
more for a viva than a marginal accuracy gain would.

**"How would this scale to millions of users?"**
The Spark code doesn't change — swap `.master("local[*]")` for a real cluster manager,
point the Parquet paths at S3/HDFS instead of a local folder, and the same
transformations run distributed. The one piece that would need to change is the serving
store: SQLite doesn't handle concurrent writes well at that scale, so it'd become
Postgres or a managed key-value store (see below).

**"What would you use instead of SQLite in production?"**
Postgres (or a managed equivalent like Amazon RDS/Aurora) for the per-user serving data,
and possibly a cache layer (Redis) in front of it for the hottest lookups (today's stats,
the latest percentile row) — SQLite is a single-file, single-writer database, fine for a
student demo, not for concurrent multi-user traffic.

**"Why Isolation Forest instead of a simpler anomaly method?"**
We actually built both and compare them (`models/train_anomaly_detection.py`) — a
per-user z-score threshold is the simple fallback, and it agrees with Isolation Forest
97.6% of the time. Isolation Forest is used as the primary method because it can catch
multivariate anomalies (an unusual *combination* of resting/avg/max heart rate) that a
per-column z-score threshold, checked independently per column, could miss.

**"Why personalize the step/calorie goals instead of using a fixed target like 10,000
steps?"**
A flat population-wide goal isn't equally fair or achievable across different users —
someone whose baseline is 5,000 steps/day and someone whose baseline is 14,000 steps/day
shouldn't have the same target. Setting each user's goal at 10% above their own historical
average makes "goal achievement" a meaningful, personalized measure of *improvement*,
which is also what makes Model 1 genuinely learnable (a fixed global threshold, uncorrelated
with a user's own baseline, would carry almost no learnable signal — we found this out
directly during an earlier iteration of this project).

**"How does login/registration work, and is it secure?"**
It's a real login flow — `dashboard/auth.py` stores salted, hashed passwords
(`hashlib.pbkdf2_hmac`, 100,000 iterations) in a `users` SQLite table, not plaintext. Be
upfront that this is demo-appropriate, not production-grade: a real product would use
bcrypt/Argon2 (slower, more resistant to GPU cracking) behind a proper identity provider
(Auth0/Cognito/Firebase Auth), over HTTPS, with rate-limiting on login attempts — none of
which a student project needs to implement to demonstrate the concept.

**"What happens if a brand-new user has very little data?"**
The lag/rolling features need at least 7-8 days of history to be non-null; the dashboard
checks for this (`if len(user_df) < 8: st.warning(...)`) and won't attempt a prediction
without enough history — this is a real, unavoidable cold-start limitation of any
history-based personalization system, not something the models can be tuned to fix.

**"Why does the goal-achievement model behave differently in different months?"**
A real finding from the data, not a bug: this dataset has a strong seasonal swing (average
steps peak ~10,100/day in March, dip to ~6,800/day in September/October). Because the
personalized goal is a flat number derived from the full year, it is much harder to hit in
low-activity months. We handle this by encoding month cyclically (sine/cosine of month
number) as a feature rather than ignoring it — see `models/train_goal_achievement.py`.

**"Why didn't you use a real, recorded (non-synthetic) dataset?"**
Real wearable/health data at population scale is protected under privacy law (HIPAA/GDPR)
and essentially impossible to obtain publicly. The one real dataset we found (Fitbit, 30
users) has only ~940 rows and 4 basic columns — two orders of magnitude short of this
project's volume requirement, with none of the demographic/vitals richness needed. Every
Kaggle dataset with this project's required row count and column richness is
synthetic-but-realistic, which is standard, accepted practice for coursework — the same
reasoning researchers use synthetic data for method development before ever touching
real, restricted records. We treated the ingestion the same way you'd treat a real
external source regardless: we found and fixed an actual data-quality bug in the raw file
(the `calories_burned` column implied ~30x too few calories burned per minute of exercise;
we recomputed it using the standard MET formula — see `data/prepare_raw_dataset.py`).
