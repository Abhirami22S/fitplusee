# FitPulse — Personalized Fitness & Activity Analytics (Big Data Project)

FitPulse processes wearable fitness-tracker data through a Spark-based big-data batch
pipeline, trains six personalized-insight models, and serves them to individual users
through an interactive dashboard.

For dataset justification, tool-by-tool reasoning, and a full viva Q&A cheat sheet, see
**[viva.md](viva.md)**.

## Two-layer architecture

```
                         OFFLINE (batch, runs on the full ~100k-row dataset)
┌──────────────────────────────────────────────────────────────────────────┐
│  data/raw/fitpulse_raw.csv  (Bronze — HDFS-style landing zone)           │
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
│         ├──▼ models/train_sleep_quality.py      (Model 3)                │
│         └──▼ models/train_anomaly_detection.py  (Model 4)                │
│             models/artifacts/*.joblib  (pre-trained, saved to disk)      │
│         │                                                                 │
│         ▼  etl/load_to_sqlite.py                                         │
│     dashboard/fitpulse.db  (SQLite, indexed by user_id)                  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ONLINE (per request, one user at a time)
┌──────────────────────────────────────────────────────────────────────────┐
│  dashboard/app.py  (Streamlit)                                           │
│   - loads pre-trained models (no retraining)                             │
│   - queries SQLite for ONE user_id + the small Gold percentile table     │
│   - OR: a user uploads their own CSV -> pandas feature engineering       │
│     (models/recommendation_engine.py runs rule-based logic on top)       │
└──────────────────────────────────────────────────────────────────────────┘
```

The offline layer never runs per-request; the online layer never touches the full dataset
or retrains anything. That split is the core architectural idea of this project.

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
│   ├── train_anomaly_detection.py    Model 4: unsupervised anomaly detection
│   ├── recommendation_engine.py      Model 5: rule-based logic
│   ├── metrics_report.md             Real metrics for every model, no fabricated numbers
│   └── artifacts/                    Saved *.joblib model files
├── dashboard/
│   ├── app.py                        Streamlit app (the online layer)
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

## Running the full pipeline

```bash
# 0. (one-time) build the raw dataset from the Kaggle source
python3 data/prepare_raw_dataset.py

# 1. Offline: Spark ETL  (Bronze -> Silver)
python3 etl/spark_etl.py

# 2. Offline: Spark SQL percentile benchmarking  (Model 6, Silver -> Gold)
python3 etl/spark_benchmarks.py

# 3. Offline: train all 4 ML models
python3 models/train_goal_achievement.py
python3 models/train_forecast.py
python3 models/train_sleep_quality.py
python3 models/train_anomaly_detection.py

# 4. Offline: load Silver + Gold into SQLite for the dashboard
python3 etl/load_to_sqlite.py

# 5. (optional) demo the streaming simulation
python3 etl/streaming_simulation.py

# 6. Online: launch the dashboard
streamlit run dashboard/app.py
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
| 4 | Anomaly Flagging | "Was anything about my heart rate today unusual for me?" |
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
