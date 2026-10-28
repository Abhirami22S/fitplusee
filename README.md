# FitPulse — Personalized Fitness & Activity Analytics (Big Data Project)

FitPulse processes wearable fitness-tracker data through a Spark-based big-data batch
pipeline, trains five personalized-insight models, and serves them to individual users
through an interactive dashboard.

For dataset justification, tool-by-tool reasoning, and a full viva Q&A cheat sheet, see
**[viva.md](viva.md)**.

## Architecture (offline pipeline -> Power BI)

```
                         OFFLINE (batch, runs on the full ~100k-row dataset)
┌──────────────────────────────────────────────────────────────────────────┐
│  data/raw/fitpulse_raw.csv  (Bronze; copy in HDFS /fitpulse/bronze) │
│         │                                                                 │
│         ▼  etl/spark_etl.py  (Apache Spark: clean, window/lag features,  │
│            personalized goals via groupBy/agg — MapReduce pattern)       │
│  data/processed/fitpulse_silver/  (Silver — partitioned Parquet)         │
│         │                                                                 │
│         ├──▼ etl/spark_benchmarks.py (Spark SQL PERCENT_RANK — Model 6)  │
│         │   data/population_stats/user_percentiles.parquet (Gold)        │
│         │                                                                 │
│         ├──▼ models/train_goal_achievement.py   (Model 1)                │
│         ├──▼ models/train_forecast.py           (Model 2)                │
│         └──▼ models/train_sleep_quality.py      (Model 3)                │
│             models/artifacts/*.joblib  (pre-trained, saved to disk)      │
│         │                                                                 │
│         ▼  etl/load_to_sqlite.py                                         │
│     dashboard/fitpulse.db  (SQLite, indexed by user_id)                  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                  REPORTING (primary dashboard: Power BI)
┌──────────────────────────────────────────────────────────────────────────┐
│  models (Spark MLlib, Silver read from HDFS or local):                   │
│    sup_e1..sup_e5 (supervised E1-E5, Spark MLlib), run_supervised.ps1    │
│    results: exports/E<n>_results.csv (shown on Power BI pages 4-5)       │
│         │  results saved in faculty_evidence/                            │
│         ▼  powerbi/export_*.py  ->  powerbi/data/*.csv  (validated)      │
│  powerbi/FitPulse_PowerBI_Dashboard.pbix   5 pages, imports CSV          │
│   (Power BI does NOT read HDFS; HDFS is single-node, replication 1)      │
│                                                                          │
│  Legacy / optional: dashboard/app.py (Streamlit) reading dashboard/      │
│  fitpulse.db - kept intact, not part of the required demo                │
└──────────────────────────────────────────────────────────────────────────┘
```

The offline layer (Spark ETL, HDFS/local storage, model training) never runs inside the dashboard; Power BI only imports the validated exports.
The legacy Streamlit app follows the same split (it only reads a small SQLite file and pre-trained models).

## Project structure

```
fitpulse/
├── data/
│   ├── raw/fitpulse_raw.csv          Bronze — HDFS-style landing zone
│   ├── processed/fitpulse_silver/    Silver — Spark output, partitioned by month
│   ├── population_stats/             Gold — percentile benchmark table
│   ├── streaming_inbox/              Optional streaming-simulation landing zone
│   ├── prepare_raw_dataset.py        One-time raw-data preparation (see viva.md)
│   └── data_dictionary.md
├── etl/
│   ├── spark_etl.py                  Main Spark batch ETL (Bronze -> Silver)
│   ├── spark_benchmarks.py           Spark SQL percentile benchmarking (Model 6)
│   ├── streaming_simulation.py       Optional: simplified streaming simulation
│   └── load_to_sqlite.py             Loads Silver + Gold into SQLite for the dashboard
├── models/
│   ├── train_goal_achievement.py     Model 1: classification
│   ├── train_forecast.py             Model 2: time-series forecast
│   ├── train_sleep_quality.py        Model 3: regression
│   ├── recommendation_engine.py      Model 5: rule-based logic
│   ├── metrics_report.md             Real metrics for every model, no fabricated numbers
│   └── artifacts/                    Saved *.joblib model files
├── powerbi/                          PRIMARY dashboard: FitPulse_PowerBI_Dashboard.pbix, generator, CSV exports, validators
├── dashboard/                        LEGACY Streamlit app (optional)
│   ├── app.py
│   └── fitpulse.db                   SQLite database (generated)
├── requirements.txt
├── README.md
└── viva.md
```

## Environment setup

This project needs a JVM for PySpark. If `java -version` doesn't work on your machine:

```bash
mkdir -p ~/.local/jdk
curl -sL "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_aarch64_mac_hotspot_17.0.20.1_1.tar.gz" -o /tmp/jdk17.tar.gz
tar -xzf /tmp/jdk17.tar.gz -C ~/.local/jdk
export JAVA_HOME=~/.local/jdk/jdk-17.0.20.1+1/Contents/Home   # adjust folder name if version differs
export PATH="$JAVA_HOME/bin:$PATH"
```

(Use the `x64` asset instead of `aarch64` if you're on an Intel Mac; on Linux, install a JDK
via your package manager instead.) Add the two `export` lines to your shell profile so you
don't need to repeat them every session.

There are two requirements files:
- `requirements.txt` — lean, deployment-only (what `dashboard/app.py` actually imports at
  runtime: Streamlit, pandas, scikit-learn, Plotly, matplotlib, ReportLab). This is what
  Streamlit Community Cloud installs when hosting the app — no Spark/Java needed there.
- `requirements-pipeline.txt` — the full offline pipeline (adds PySpark, PyArrow,
  kagglehub) needed to regenerate the data/models locally.

```bash
pip3 install -r requirements-pipeline.txt   # for running the pipeline locally
# or, if you only want to run the dashboard against the already-generated data/models:
pip3 install -r requirements.txt
```

## HDFS storage (real Hadoop HDFS + Spark)

The Bronze CSV and the Silver Parquet dataset can live in a **real single-node Hadoop HDFS** (Hadoop 3.4.1,
NameNode + DataNode, replication 1) instead of the local disk. Local Parquet remains the default and an explicit
fallback; the two modes are never mixed silently.

```
 data/raw/fitpulse_raw.csv ──hdfs dfs -put──▶ hdfs://localhost:9000/fitpulse/bronze/fitpulse_raw.csv
        │                                              │ Spark reads (hdfs://)
        │                          etl/spark_etl.py --storage hdfs   (clean, window/lag features, goals)
        │                                              │ staged write + read-back check, then rename into place
        │                                              ▼
        │                       hdfs://localhost:9000/fitpulse/silver/month=YYYY-MM/*.parquet   (Silver)
        │                                              │
        │            Spark MLlib (run_supervised.ps1 -Storage hdfs, notebook §11) ── reads Silver from HDFS
        ▼
 python etl/spark_etl.py  (no flags) ──▶ data/processed/fitpulse_silver/   (local fallback, unchanged)
        └─▶ spark_benchmarks / scikit-learn models / SQLite / Power BI exports / legacy Streamlit (all read the LOCAL Silver)
```

**Deployment choice:** Windows-native Hadoop 3.4.1 (matches the Hadoop 3.4.1 client bundled in PySpark 4.0.1),
reusing the project's existing JDK 17 and `winutils.exe`/`hadoop.dll` from `..\tools`. Docker/WSL2 were not needed:
only the Hadoop tarball (~0.9 GB download, ~1.3 GB unpacked) was added, under `..\tools\hadoop-3.4.1`.
Config lives in `hadoop-conf/` (everything binds to 127.0.0.1); HDFS data lives in `..\tools\hdfs-data`.

| Step | Command (PowerShell, from this folder) |
|---|---|
| One-time setup (install, validate config, format NameNode **only if never initialised**) | `.\setup_hdfs.ps1` |
| Start HDFS and wait until a DataNode is live | `.\start_hdfs.ps1` |
| Upload Bronze (skipped if unchanged) + ETL in HDFS mode + verification checks | `.\run_fitpulse_hdfs.ps1` |
| Re-run only the verification (exit code ≠ 0 if a check fails) | `.\run_fitpulse_hdfs.ps1 -SkipEtl` |
| Supervised experiments E1-E5 reading Silver from HDFS (results go to `faculty_evidence\supervised\hdfs_rerun\`, never over `exports\`) | `.\run_supervised.ps1 -Experiment All -Storage hdfs` |
| "HDFS is down" behaviour test (stops and restarts HDFS) | `.\scripts\test_hdfs_down.ps1` |
| Stop HDFS (data is kept) | `.\stop_hdfs.ps1` |
| Local fallback (original behaviour) | `python etl\spark_etl.py` |

Manual inspection (after `. .\scripts\hdfs_env.ps1` puts `hdfs` on PATH): `hdfs dfs -ls -R /fitpulse`,
`hdfs dfs -du -h /fitpulse`, `hdfs dfsadmin -report`; NameNode UI http://localhost:9870.

ETL options: `--storage local|hdfs` (or env `FITPULSE_STORAGE`), `--hdfs-uri` (or `FITPULSE_HDFS_URI`; the run
script reads it from `hdfs getconf -confKey fs.defaultFS`), `--input`, `--output`, `--report <json>`. In HDFS mode
the output is written to `/fitpulse/silver._staging_<ts>`, its row count is checked, and only then it is renamed into
place, so a failed write leaves the previous Silver untouched. The job exits with code **2** if the NameNode is
unreachable and never falls back to local disk. Real command output and Spark checks are saved in
`faculty_evidence/hdfs/`; notebook section 11 shows them.

**Troubleshooting**
* `start_hdfs.ps1` reports a dead process: read `..\tools\hdfs-logs\NameNode.out.log` / `DataNode.out.log`.
* `Incompatible clusterID` on DataNode start (only if the NameNode was re-formatted by hand): move
  `..\tools\hdfs-data\datanode` aside (do not delete it blindly) and restart.
* `hdfs fsck` returns HTTP 400: the Windows account name contains a space; run it with `HADOOP_USER_NAME=fitpulse` (the verifier does).
* Port in use (9000 / 9870 / 9866): stop the other service, or change `hadoop-conf/*.xml` and re-check `hdfs getconf -confKey fs.defaultFS`.
* "Python worker exited unexpectedly" when building a DataFrame from Python lists on this machine: use Spark SQL / `spark.read` (the ETL and verifier already do).

## Models and evaluation overview (what exists, what each is for)

| Id | Task / label | Models (Spark MLlib) | Evaluation | Script |
|---|---|---|---|---|
| **E1** | same-day goal, `steps >= 8,000` | Random Forest (unchanged), Logistic Regression, GBT | random 70/15/15 (seed 42) + user-held-out check | `models/sup_e1_goal_same_day.py` |
| **E2** | next-day goal from history strictly before the day | Random Forest, GBT, Logistic Regression | **chronological** train / validation / test | `models/sup_e2_goal_next_day.py` |
| **E3** | `high_achiever` per user (437 users) | Random Forest, Logistic Regression | stratified 5-fold cross-validation | `models/sup_e3_user_high_achiever.py` |
| **E4** | `activity_level` High/Low per user-day | Random Forest, GBT, Logistic Regression | **user-held-out** 70/15/15 | `models/sup_e4_activity_level.py` |
| **E5** | same-day `calories_burned` (regression) | Linear Regression (unchanged), Random Forest Regressor, GBT Regressor | hash split 70/15/15 + chronological check | `models/sup_e5_calories.py` |

Every experiment is **supervised**. The two earlier user-segmentation experiments (old E3 and E4) were replaced by E3 and E4 above; their code and outputs are kept in `archive/` (see `archive/README.md`).
The legacy Streamlit app keeps its own scikit-learn models (`models/train_*.py`); they are not part of E1-E5.
Measured results, limitations and viva questions: `SUPERVISED_REPORT.md` (project root). The numbers are in `exports/E<n>_results.csv`.

### Running the supervised experiments

```powershell
.\run_supervised.ps1 -Experiment All                    # E1..E5 on local Silver Parquet, then the scikit-learn cross-check
.\run_supervised.ps1 -Experiment E3                     # one experiment
.\run_fitpulse_hdfs.ps1 -SkipEtl                        # verify HDFS + Silver first (16 checks)
.\run_supervised.ps1 -Experiment All -Storage hdfs      # same experiments reading Silver from HDFS -> faculty_evidence\supervised\hdfs_rerun\
```

Outputs: `exports/E<n>_results.csv` (experiment_id, model, metric, value, split_type, status; status VALID / INVALID = leakage demonstration / BASELINE / REFERENCE),
`exports/E<n>_feature_importance.csv` (tree models), and logs, predictions, tuning grids and `sklearn_crosscheck.csv` in `faculty_evidence/supervised/`.
Data note: calories, distance, minutes, max heart rate and sleep quality are **partly derived** in this demonstration dataset (`data/prepare_raw_dataset.py`).

## Per-user insights web dashboard (`webapp/`)

Pick a user and see their personal insights (tomorrow's goal probability, goal progress, calories vs model estimate, percentile vs all users, recommendations),
produced by models trained on all users. One static page + one JSON file; run on localhost with `.\webapp\run_local.ps1` or host with the Vercel CLI. See `webapp/README.md`.
Power BI stays the population-level dashboard; this page is the per-user view.

## Dashboards

**Primary dashboard: Power BI** - `powerbi/FitPulse_PowerBI_Dashboard.pbix` (five pages: *Fitness Overview*, *Activity and Sleep*, *Calorie Prediction*,
*Supervised Results E3 and E4*, *Model Evaluation*; 68 visuals, 29 DAX measures). It imports validated **CSV tables** (`powerbi/data/*.csv`) made from the Silver data and the
saved results; **it does not read HDFS** (HDFS here is single-node, replication factor 1). Pages 4 and 5 show only the supervised experiments: they read
`exports/E<n>_results.csv` (copied row for row into `powerbi/data/supervised_results.csv`) plus the cross-check counts from
`faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv`, and every visual names its experiment, evaluation split and status.
**Status:** the generated project `powerbi/project/` is rebuilt and passes `powerbi/validate_powerbi_project.py`; the saved `.pbix` must still be re-opened in Power BI Desktop,
refreshed and re-saved from `powerbi/project/FitPulse_PowerBI_Dashboard.pbip` so that the file matches it (steps in `powerbi/README.md`).
Refresh after a pipeline rerun: `.\powerbi\build_powerbi.ps1`, then Refresh in Desktop. Automated validation record: `faculty_evidence/powerbi/project_validation.md`; build/refresh details: `powerbi/README.md`, `powerbi/AUTOMATED_BUILD.md`.

**Legacy / optional: Streamlit** (`dashboard/app.py`) - the earlier per-user web dashboard, kept intact but no longer part of the required demo or deliverable.
Tested earlier (`python scripts/test_dashboard.py`, 15 checks). Data source: local SQLite `dashboard/fitpulse.db` and local joblib/JSON models. Start: `streamlit run dashboard/app.py`
(logins `demo1`/`demo2`/`demo3`, password `demo123`).

## Tests

| Command | What it checks |
|---|---|
| `.\run_fitpulse_hdfs.ps1 -SkipEtl` | 16 HDFS / Spark / local-vs-HDFS checks |
| `python scripts/test_analytics.py` | calorie model, score, guidance vs independent recomputation (13 checks) |
| `python scripts/test_dashboard.py` | Streamlit AppTest: login, all tabs, wrong password, missing files (15 checks) |
| `python powerbi/validate_exports.py` | Power BI tables vs Silver, and `supervised_results` vs `exports/E<n>_results.csv` row for row |
| `python powerbi/validate_powerbi_project.py` | generated Power BI project: schema, references, measures, Microsoft PBIR and TMDL validators |
| `python webapp/validate_insights.py` | web page data vs Silver and the saved models |
| `python scripts/build_model_metrics.py` | rebuilds `faculty_evidence/model_metrics.csv` from the PREVIOUS (pre-supervised) result files |
| `python scripts/sup_sklearn_crosscheck.py` | independent scikit-learn re-computation / refit for E1-E5 (`faculty_evidence/supervised/sklearn_crosscheck.csv`) |

## Faculty demo notebook

`FitPulse_Faculty_Demo.ipynb` re-runs `prepare_raw_dataset.py` + `spark_etl.py`, then demonstrates the
dataset, preprocessing and the five supervised experiments E1-E5 (sections 5-7: Random Forest, Gradient-Boosted Trees,
Logistic / Linear Regression, with baselines, leakage tests and cross-checks) with real, saved outputs; it is regenerated by `python scripts/build_supervised_notebook.py`. Evidence tables/plots go to `faculty_evidence/`; presenter notes are in
`faculty_demo_notes.md`. On Windows, `.\run_faculty_demo.ps1` sets up JDK 17 + winutils from `..\tools`
and opens it (`pipeline` / `execute` arguments run the pipeline or re-execute the notebook headless).

## Running the full pipeline

```bash
# 0. (one-time) build the raw dataset from the Kaggle source
python3 data/prepare_raw_dataset.py

# 1. Offline: Spark ETL  (Bronze -> Silver)
python3 etl/spark_etl.py

# 2. Offline: Spark SQL percentile benchmarking  (Model 6, Silver -> Gold)
python3 etl/spark_benchmarks.py

# 3. Offline: train the 3 ML models of the legacy dashboard
python3 models/train_goal_achievement.py
python3 models/train_forecast.py
python3 models/train_sleep_quality.py

# 4. Offline: load Silver + Gold into SQLite for the dashboard
python3 etl/load_to_sqlite.py

# 5. (optional) demo the streaming simulation
python3 etl/streaming_simulation.py

# 6. Power BI (primary dashboard): rebuild the exports and project, then open the .pbix in Power BI Desktop and click Refresh
#    .\powerbi\build_powerbi.ps1   (PowerShell)
# 6b. (legacy, optional) Streamlit: streamlit run dashboard/app.py
```

Steps 0–4 only need to be re-run if the data or models change — the dashboard (step 6)
always reads their saved outputs (`dashboard/fitpulse.db`, `models/artifacts/*.joblib`),
never recomputing them live.

## Logging in

The dashboard now sits behind a real login/register screen (`dashboard/auth.py` +
`etl/setup_auth.py`, salted `hashlib.pbkdf2_hmac` password hashing — a simple, demo-
appropriate choice, not what a production auth system would use).

**Demo accounts** (pre-loaded with a full year of Spark-processed history):

| Username | Password |
|---|---|
| `demo1` | `demo123` |
| `demo2` | `demo123` |
| `demo3` | `demo123` |

**New users** register with no history and land on an onboarding screen with two
options: upload a wearable CSV export (a ready-made sample is at
`data/sample_upload_for_new_user.csv`, generated by `data/generate_sample_upload_csv.py`),
or log days one at a time through a form. Either way, predictions stay locked until 8+
days of history exist (the models' lag/rolling features need that much), exactly like a
real fitness app would behave for a brand-new user — this is not a bug, it's an honest
cold-start limitation. Uploaded/logged rows are written to a `user_daily_raw` SQLite
table and re-run through the same pandas feature-engineering function used for the CSV
upload path (`engineer_features_pandas` in `dashboard/app.py`), separate from the Spark
pipeline that only ever processes the 437 pre-existing demo users.

(Re)build the auth tables with:

```bash
python3 etl/setup_auth.py
```

## What each prediction means to a user

| # | Prediction | The question it answers |
|---|---|---|
| 1 | Goal Achievement | "Am I on track to hit today's step goal?" |
| 2 | 7-Day Forecast | "How active should I expect to be this week, so I can plan?" |
| 3 | Sleep Quality | "Which of my habits are helping or hurting my sleep?" |
| 4 | (removed) | Heart-rate anomaly flagging was removed from the live project; its script is in `archive/anomaly/` |
| 5 | Recommendations | "What's one concrete thing I should do differently today?" |
| 6 | Percentile Benchmarking | "How do I compare to people like me?" |

Full algorithm choices, metrics, and reasoning: `models/metrics_report.md` and `viva.md`.

## Deploying (free)

The dashboard deploys to **[Streamlit Community Cloud](https://share.streamlit.io)** —
not Vercel, which only runs stateless serverless functions and can't host a
persistent, WebSocket-based app like Streamlit. Community Cloud is free, built for
exactly this, and needs zero server config:

1. Push this repo to GitHub (public or private both work).
2. Sign in at share.streamlit.io with your GitHub account.
3. Click "New app" → pick this repo/branch → set the main file path to `dashboard/app.py`.
4. Deploy. It installs `requirements.txt` (the lean one — no Spark/Java needed to serve
   the app) and gives you a public `*.streamlit.app` URL.

**Known limitation:** Community Cloud's free tier filesystem is not guaranteed to persist
forever — an app can restart after inactivity, which resets any writes made directly to
`dashboard/fitpulse.db` since the last deploy. The three demo accounts are unaffected
(they're baked into the repo), but a visitor's own registration or manually logged days
may not survive a restart. For a persistent multi-user deployment, swap SQLite for a
hosted database (see `viva.md`'s "what would you use instead of SQLite in production"
answer) — out of scope for a free student-project deployment.
