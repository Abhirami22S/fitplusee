"""
Builds FitPulse_Faculty_Demo.ipynb (cells only - no outputs).
Outputs are produced by actually executing the notebook:

    python faculty_evidence/build_notebook.py
    python -m jupyter nbconvert --to notebook --execute --inplace FitPulse_Faculty_Demo.ipynb

Kept so the notebook's structure can be regenerated/edited reproducibly.
"""
import nbformat as nbf

cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(text):
    cells.append(nbf.v4.new_code_cell(text.strip("\n")))


# =====================================================================
md(r"""
# FitPulse – Personalized Fitness and Activity Analytics Using Big Data

**Faculty demonstration notebook.** Every number in this notebook is computed live from the
project's actual dataset by the project's actual code (`data/prepare_raw_dataset.py`,
`etl/spark_etl.py`) followed by Apache Spark / Spark MLlib. Nothing is typed in by hand —
re-running the notebook top-to-bottom reproduces every value (fixed seed = 42).

> **How to read this notebook:** each section has (1) a short explanation, (2) code,
> (3) the actual output, (4) an interpretation. All result tables are also saved to
> `faculty_evidence/`.
""")

md(r"""
## 1. Project Overview

FitPulse turns daily wearable fitness data into personalized insights. The pipeline that is
**actually implemented in this repository**:

```
Kaggle FitLife dataset (687,701 rows / 3,000 participants)
        │  data/prepare_raw_dataset.py   (pandas, one-time: sample 437 users, clean, unit conversions)
        ▼
data/raw/fitpulse_raw.csv               Bronze layer – raw landing zone
        │  etl/spark_etl.py              (Apache Spark: cleaning, window/lag features, per-user goals)
        ▼
data/processed/fitpulse_silver/         Silver layer – Parquet, partitioned by month
        │  this notebook                 (Spark MLlib: Random Forest + K-Means)
        ▼
Personalized insights                   models/*.py, models/recommendation_engine.py
        ▼
Dashboard                               dashboard/app.py (Streamlit)
```

**What is and isn't implemented (verified by inspecting the repository):**

| Component | Status in this repo |
|---|---|
| Raw preprocessing | ✅ `data/prepare_raw_dataset.py` (pandas) |
| Apache Spark / PySpark ETL | ✅ `etl/spark_etl.py`, `etl/spark_benchmarks.py` – runs in Spark **local mode** (`local[*]`) |
| Distributed storage | ⚠️ *HDFS-style* partitioned Parquet on the local filesystem. **No HDFS cluster is configured** (see §8.4) |
| Random Forest | ✅ exists in `models/train_goal_achievement.py` (scikit-learn). This notebook re-implements it in **Spark MLlib** with the same target and features |
| K-Means clustering | ❌ did **not** exist in the repo – **added in this notebook** (§7) |
| 70/15/15 split | ❌ the existing script uses a chronological train/test split – **a 70/15/15 split is added in this notebook** (§5), and the original chronological split is reproduced as a robustness check (§6.12) |
| Dashboard | ✅ Streamlit (`dashboard/app.py`). **No Power BI file exists in the repo** |
""")

md(r"""
### Environment setup

Configures Java/Spark for this machine. On this Windows laptop a portable JDK 17 and the
Hadoop Windows binaries (`winutils.exe`, `hadoop.dll`) live in `../tools/` (Spark 4 needs
JDK 17/21; the system JDK 23/25 is too new for Hadoop's security APIs).
""")

code(r"""
import os, sys, re, json, time, shutil, hashlib, subprocess, importlib.util, contextlib, io, warnings
warnings.filterwarnings("ignore", message="IProgress not found")   # harmless tqdm notice from kagglehub
from pathlib import Path

PROJECT_ROOT = Path.cwd()
assert (PROJECT_ROOT / "etl" / "spark_etl.py").exists(), "Start Jupyter from inside the FitPulse/ folder"

TOOLS = PROJECT_ROOT.parent / "tools"          # local JDK 17 + Hadoop winutils for this machine
if (TOOLS / "jdk17").exists():
    os.environ["JAVA_HOME"] = str(TOOLS / "jdk17")
if (TOOLS / "hadoop").exists():
    os.environ["HADOOP_HOME"] = str(TOOLS / "hadoop")
for var in ("HADOOP_HOME", "JAVA_HOME"):
    if var in os.environ:
        os.environ["PATH"] = str(Path(os.environ[var]) / "bin") + os.pathsep + os.environ["PATH"]
if (TOOLS / "tmp").exists():                   # keep Spark temp files off the (full) C: drive
    os.environ["TMP"] = os.environ["TEMP"] = str(TOOLS / "tmp")
os.environ.setdefault("KAGGLEHUB_CACHE", str(TOOLS / "kagglehub"))
os.environ["PYSPARK_PYTHON"] = os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
os.environ["PYTHONIOENCODING"] = "utf-8"

EVIDENCE = PROJECT_ROOT / "faculty_evidence"
EVIDENCE.mkdir(exist_ok=True)
SEED = 42                                       # one seed for every random operation in this notebook

java = shutil.which("java")
java_version = subprocess.run([java, "-version"], capture_output=True, text=True).stderr.splitlines()[0]
print("Project root :", PROJECT_ROOT)
print("Python       :", sys.version.split()[0], "-", sys.executable)
print("Java         :", java_version)
print("JAVA_HOME    :", os.environ.get("JAVA_HOME"))
print("HADOOP_HOME  :", os.environ.get("HADOOP_HOME"))
""")

code(r"""
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 220)

# Chart styling: thin marks, recessive grid, one blue for single-series charts
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.axisbelow": True,
})


def run_project_script(rel_path, log_name):
    # Runs one of the project's own pipeline scripts exactly as `python <script>` would,
    # prints its real stdout, and saves it to faculty_evidence/ as a log.
    t0 = time.time()
    proc = subprocess.run([sys.executable, rel_path], cwd=PROJECT_ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    elapsed = time.time() - t0
    log = f"$ python {rel_path}\nexit code: {proc.returncode}   elapsed: {elapsed:.1f}s\n\n{proc.stdout}"
    (EVIDENCE / log_name).write_text(log, encoding="utf-8")
    print(log)
    if proc.returncode != 0:
        print(proc.stderr[-4000:])
        raise RuntimeError(f"{rel_path} failed")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
""")

# =====================================================================
md(r"""
## 2. Dataset Description

### 2.1 Dataset Source

* **Original source:** Kaggle – [`jijagallery/fitlife-health-and-fitness-tracking-dataset`](https://www.kaggle.com/datasets/jijagallery/fitlife-health-and-fitness-tracking-dataset)
  (version 1). It is a *wearable-style* health & fitness tracking dataset (one row per participant-day).
  Important honesty note: it is a public, research/teaching dataset, not exported from our own devices.
* **Raw preparation:** `data/prepare_raw_dataset.py` samples **437 participants** (seed 42) and keeps each
  one's full yearly time series, then reshapes the columns into a wearable-export schema.
* **Bronze layer:** `data/raw/fitpulse_raw.csv` – the input to Spark.

Below, the project's two pipeline scripts are **actually executed** (not simulated). The SHA-256 hash
of the Bronze file before and after proves the raw preparation is exactly reproducible.
""")

code(r"""
# Step 0 - raw preparation (project script, unchanged logic)
RAW_PATH = "data/raw/fitpulse_raw.csv"
hash_before = sha256(RAW_PATH) if Path(RAW_PATH).exists() else None
run_project_script("data/prepare_raw_dataset.py", "log_prepare_raw_dataset.txt")
hash_after = sha256(RAW_PATH)
print("SHA-256 before:", hash_before)
print("SHA-256 after :", hash_after)
print("Bronze file reproduced byte-for-byte:", hash_before == hash_after)
""")

code(r"""
# Step 1 - Spark ETL, Bronze -> Silver (project script, unchanged)
SILVER_PATH = "data/processed/fitpulse_silver"
run_project_script("etl/spark_etl.py", "log_spark_etl.txt")
""")

md(r"""
**Interpretation:** both pipeline stages ran successfully on this machine. The Spark ETL read the
Bronze CSV, applied its cleaning rules, engineered the features, and wrote the Silver layer as
Parquet partitioned by month. Everything below reads those real outputs.

Now we start this notebook's own Spark session (the ETL script stopped its own session when it finished).
""")

code(r"""
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

builder = (
    SparkSession.builder
    .appName("FitPulse-Faculty-Demo")
    .master("local[*]")                                   # same execution mode as etl/spark_etl.py
    .config("spark.sql.shuffle.partitions", "8")          # same setting as etl/spark_etl.py
    .config("spark.driver.memory", "2g")
    .config("spark.driver.host", "127.0.0.1")
)
if (TOOLS / "tmp").exists():
    builder = builder.config("spark.local.dir", str(TOOLS / "tmp"))
spark = builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("Spark version:", spark.version, "| master:", spark.sparkContext.master,
      "| default parallelism:", spark.sparkContext.defaultParallelism)
""")

code(r"""
# The original Kaggle file - located with the project's own resolve_source() function
spec = importlib.util.spec_from_file_location("prepare_raw_dataset", PROJECT_ROOT / "data" / "prepare_raw_dataset.py")
prepare_raw_dataset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_raw_dataset)
SOURCE_PATH = prepare_raw_dataset.resolve_source()

source = spark.read.csv(SOURCE_PATH, header=True, inferSchema=True)
bronze = spark.read.csv(RAW_PATH, header=True, inferSchema=True)      # identical call to spark_etl.py
silver = spark.read.parquet(SILVER_PATH)

print("Kaggle source file :", SOURCE_PATH)
print("Bronze file        :", RAW_PATH)
print("Silver dataset     :", SILVER_PATH)
""")

md(r"""
### 2.2 Dataset Dimensions
""")

code(r"""
def dims(df, name):
    users_col = "participant_id" if "participant_id" in df.columns else "user_id"
    agg = df.agg(F.countDistinct(users_col).alias("users"), F.min("date").alias("first"),
                 F.max("date").alias("last")).first()
    return {"Layer": name, "Rows": df.count(), "Columns": len(df.columns), "Users": agg["users"],
            "First date": str(agg["first"])[:10], "Last date": str(agg["last"])[:10]}

dataset_summary = pd.DataFrame([dims(source, "Kaggle source"), dims(bronze, "Bronze (raw CSV)"),
                                dims(silver, "Silver (Spark output)")])
dataset_summary.to_csv(EVIDENCE / "dataset_summary.csv", index=False)
display(dataset_summary)
""")

code(r"""
# Equivalent direct calls on the Bronze DataFrame
print("bronze.count()      =", bronze.count())
print("len(bronze.columns) =", len(bronze.columns))
print("bronze.columns      =", bronze.columns)
print()
print("silver.count()      =", silver.count())
print("len(silver.columns) =", len(silver.columns))
print("Columns added by Spark ETL:", [c for c in silver.columns if c not in bronze.columns])
""")

md(r"""
**Interpretation:** the project works on a 437-user subset of the Kaggle dataset, keeping each user's
complete year of daily records so that per-user time-series features (lags, rolling averages) are
meaningful. The Spark ETL keeps every Bronze row and adds the engineered columns listed above.
""")

md(r"""
### 2.3 Dataset Schema
""")

code(r"""
print("BRONZE schema (raw CSV, types inferred by Spark):")
bronze.printSchema()
""")

code(r"""
print("SILVER schema (after etl/spark_etl.py):")
silver.printSchema()
_ = (EVIDENCE / "schemas.txt").write_text(
    "BRONZE\n" + bronze._jdf.schema().treeString() + "\nSILVER\n" + silver._jdf.schema().treeString(),
    encoding="utf-8")
""")

md(r"""
### 2.4 Sample Records
""")

code(r"""
print("First 10 Bronze records:")
bronze.show(10, truncate=False)
""")

code(r"""
print("First 10 Silver records (one user, ordered by date) - engineered columns shown:")
(silver.filter(F.col("user_id") == silver.agg(F.min("user_id")).first()[0])
       .orderBy("date")
       .select("user_id", "date", "day_of_week", "month", "steps", "steps_lag1", "steps_lag7",
               "steps_roll7_avg", "daily_step_goal", "goal_achieved")
       .show(10, truncate=False))
""")

md(r"""
**Interpretation:** each row is one user-day. Activity (`steps`, `active_minutes`, `calories_burned`),
heart-rate, sleep and profile columns are present. In the Silver rows the lag/rolling columns are null
for a user's earliest days because there is no earlier history yet. That is expected, and §3.1 quantifies it.
""")

# =====================================================================
md(r"""
## 3. Data Quality Analysis

### 3.1 Missing Values
""")

code(r"""
def missing_table(df):
    total = df.count()
    row = df.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in df.columns]).first().asDict()
    out = pd.DataFrame({"Column": list(row), "Missing": list(row.values())})
    out["Missing %"] = (out["Missing"] / total * 100).round(2)
    return out

src_missing = missing_table(source)
bronze_missing = missing_table(bronze)
silver_missing = missing_table(silver)
src_missing.to_csv(EVIDENCE / "missing_values_source.csv", index=False)
bronze_missing.to_csv(EVIDENCE / "missing_values_bronze.csv", index=False)
silver_missing.to_csv(EVIDENCE / "missing_values_silver.csv", index=False)

print("Kaggle source - columns with missing values:")
display(src_missing[src_missing.Missing > 0])
print("Kaggle source - health_condition values (literal text, not nulls):")
source.groupBy("health_condition").count().orderBy("count", ascending=False).show()
print(f"Bronze - total missing cells: {bronze_missing.Missing.sum():,}")
display(bronze_missing.T)
""")

code(r"""
print("Silver - columns with missing values:")
display(silver_missing[silver_missing.Missing > 0])
n_users = silver.select("user_id").distinct().count()
print(f"Users = {n_users}.  Expected nulls: lag1 = 1 x users = {n_users}, lag2 = 2 x users = {2*n_users}, "
      f"lag7 = 7 x users = {7*n_users}")
""")

md(r"""
**Interpretation:**
* The **Kaggle source** has no true nulls (Spark count = 0). Note that `health_condition` holds the literal
  text `"None"` for participants without a condition (cell below). pandas parses that text as NaN by
  default, which is why `prepare_raw_dataset.py` restores it with `fillna("None")`.
* The **Bronze** file has no missing values.
* In **Silver**, the only nulls are in the lag columns and they exactly equal *k × number of users*
  (the first *k* days of each user have no *k*-days-ago value). These are structural nulls, not data errors.
  They are not imputed. Rows with incomplete lag features are excluded from model training (§5).
""")

md(r"""
### 3.2 Duplicate Records
""")

code(r"""
def duplicate_report(df, key, name):
    total = df.count()
    return {"Layer": name, "Rows": total,
            "Exact duplicate rows": total - df.dropDuplicates().count(),
            "Duplicate (user, date) keys": total - df.dropDuplicates(key).count()}

dup = pd.DataFrame([
    duplicate_report(source, ["participant_id", "date"], "Kaggle source"),
    duplicate_report(bronze, ["user_id", "date"], "Bronze"),
    duplicate_report(silver, ["user_id", "date"], "Silver"),
])
dup.to_csv(EVIDENCE / "duplicate_analysis.csv", index=False)
display(dup)
""")

md(r"""
**Interpretation:** there are no exact duplicate rows and no repeated (user, date) pairs at any layer,
so every row is a unique user-day. Duplicate removal is still part of the pipeline
(`drop_duplicates()` in the raw preparation, `dropDuplicates()` in Spark). It is a safeguard that
would matter for a real device export, where re-syncs can duplicate days.
""")

md(r"""
### 3.3 Statistical Summary
""")

code(r"""
KEY_NUMERIC = ["steps", "active_minutes", "sedentary_minutes", "calories_burned",
               "avg_heart_rate", "resting_heart_rate", "sleep_minutes", "sleep_quality_score"]
bronze.select(KEY_NUMERIC).describe().show()
""")

code(r"""
numeric_cols = [f.name for f in bronze.schema.fields
                if isinstance(f.dataType, (T.IntegerType, T.DoubleType, T.LongType)) and f.name != "user_id"]
stats = bronze.select(numeric_cols).describe().toPandas().set_index("summary").T.astype(float).round(2)
stats.to_csv(EVIDENCE / "statistical_summary.csv")
display(stats)
""")

md(r"""
**Interpretation:** values fall inside physiologically plausible ranges (the ranges are enforced by the
cleaning filters in §4.1). Steps average about 8,600/day. Every row has a logged activity session of at least
20 minutes. This matters later: `is_rest_day` (< 15 active minutes) is always 0 in this dataset.
""")

# =====================================================================
md(r"""
## 4. Data Preprocessing

### 4.1 Data Cleaning

Cleaning happens in **two places** in the existing code. Only operations that exist in the code are listed.

| # | Operation | Why it is necessary | Where in the code |
|---|---|---|---|
| 1 | Sample 437 participants (seed 42), keeping each one's full time series | Manageable scale while preserving complete per-user histories for lag/rolling features | `data/prepare_raw_dataset.py` L84–86 |
| 2 | Exact-duplicate removal (`drop_duplicates`) | A re-synced device export can repeat days, which would double-count activity | `prepare_raw_dataset.py` L89 |
| 3 | Drop rows missing `participant_id`, `date`, `activity_type`, `duration_minutes` | These fields are required to place a record in a user's timeline | `prepare_raw_dataset.py` L90 |
| 4 | Physiological range filters (age 15–100, height 120–220 cm, weight 30–200 kg, session 0–300 min, avg HR 40–220, resting HR 35–120, sleep 0–14 h, steps 0–60,000) | Removes sensor glitches / impossible values | `prepare_raw_dataset.py` L91–96 |
| 5 | `health_condition` NaN → `"None"` | The source stores the text "None" (= no condition). pandas reads it as NaN, so it is restored | `prepare_raw_dataset.py` L97 |
| 6 | Recompute `calories_burned` with the MET formula (MET × kg × hours) | Source column was ~30× too low to be plausible | `prepare_raw_dataset.py` L99–101 |
| 7 | Unit conversions / derived raw columns: `distance_km`, `active_minutes`, `sleep_minutes`, `sedentary_minutes`, `max_heart_rate`, `sleep_quality_score` | Map the source schema onto a wearable-export schema | `prepare_raw_dataset.py` L103–126 |
| 8 | Spark `dropDuplicates()` | Same safeguard, enforced again inside the big-data pipeline | `etl/spark_etl.py` L55 |
| 9 | Spark `dropna` on `user_id`, `date`, `activity_type`, `steps` | Required fields | `spark_etl.py` L56 |
| 10 | Spark range filters (age, resting HR, avg HR, steps, sleep 0–840 min) | Re-validate physiology inside Spark | `spark_etl.py` L57–63 |
| 11 | Spark `coalesce(health_condition, "None")` | Same null rule | `spark_etl.py` L64 |
| 12 | Type conversion: `date` → Spark `DateType` (`to_date`) | Enables date arithmetic, ordering and window functions | `spark_etl.py` L65 |

**Honesty notes:** `max_heart_rate` and `sleep_quality_score` are *modelled* in step 7: they come from
formulas with seeded random noise, not from raw sensor readings. No outlier capping, imputation or
normalisation of the Silver data happens in the existing ETL. Scaling is done only inside the ML
pipelines below.

The cell below re-evaluates each cleaning rule and counts how many rows it actually removes.
""")

code(r"""
# (a) Raw-preparation rules, re-evaluated on the Kaggle rows of the 437 sampled participants.
#     The filter expressions are copied verbatim from data/prepare_raw_dataset.py.
src = pd.read_csv(SOURCE_PATH)
sampled_ids = pd.Series(src.participant_id.unique()).sample(n=prepare_raw_dataset.N_PARTICIPANTS,
                                                            random_state=prepare_raw_dataset.SEED)
d = src[src.participant_id.isin(sampled_ids)].copy()
steps_log = [("Kaggle rows for the 437 sampled participants", len(d))]
d = d.drop_duplicates();                                   steps_log.append(("after drop_duplicates()", len(d)))
d = d.dropna(subset=["participant_id", "date", "activity_type", "duration_minutes"])
steps_log.append(("after dropna(required fields)", len(d)))
d = d[d.age.between(15, 100) & d.height_cm.between(120, 220) & d.weight_kg.between(30, 200)
      & d.duration_minutes.between(0, 300) & d.avg_heart_rate.between(40, 220)
      & d.resting_heart_rate.between(35, 120) & d.hours_sleep.between(0, 14)
      & d.daily_steps.between(0, 60000)]
steps_log.append(("after physiological range filters", len(d)))
print("health_condition values read as NaN by pandas (text 'None') and restored by fillna:", int(d.health_condition.isna().sum()))

# (b) Spark ETL rules, re-evaluated with Spark on the Bronze DataFrame (same expressions as spark_etl.py)
b = bronze
spark_log = [("Bronze rows read by Spark", b.count())]
b = b.dropDuplicates();                                    spark_log.append(("after dropDuplicates()", b.count()))
b = b.dropna(subset=["user_id", "date", "activity_type", "steps"]); spark_log.append(("after dropna(required)", b.count()))
b = b.filter(F.col("age").between(15, 100) & F.col("resting_heart_rate").between(35, 120)
             & F.col("avg_heart_rate").between(40, 220) & F.col("steps").between(0, 60000)
             & F.col("sleep_minutes").between(0, 840))
spark_log.append(("after range filters", b.count()))

clean = pd.DataFrame([("prepare_raw_dataset.py (pandas)",) + s for s in steps_log]
                     + [("spark_etl.py (Spark)",) + s for s in spark_log], columns=["Stage", "Step", "Rows"])
clean["Removed by step"] = clean.groupby("Stage")["Rows"].diff().fillna(0).astype(int).abs()
clean.to_csv(EVIDENCE / "preprocessing_summary.csv", index=False)
display(clean)
print("Bronze 'date' type:", dict(bronze.dtypes)["date"], " ->  Silver 'date' type:", dict(silver.dtypes)["date"])
""")

md(r"""
**Interpretation:** the table shows how many rows each rule actually removed on this dataset. The raw
preparation already does the cleaning, so the Spark ETL's identical checks remove nothing. They serve as a
second validation gate inside the big-data pipeline. The type conversion makes `date` a real date type,
which the window functions in §4.2 depend on.
""")

md(r"""
### 4.2 Feature Engineering

Features engineered in **`etl/spark_etl.py`** (Spark), plus the few added for modelling:

| Feature | Definition | Why | Where |
|---|---|---|---|
| `day_of_week` | Monday…Sunday from `date` | Weekly activity rhythm | `spark_etl.py` L69 |
| `month` | `yyyy-MM`; also the Parquet partition key | Seasonality + partition pruning | `spark_etl.py` L70 |
| `is_rest_day` | 1 if `active_minutes` < 15 | Rest-day indicator. **Always 0 in this dataset** (shown below) | `spark_etl.py` L72 |
| `steps_lag1/2/7`, `calories_lag1`, `sleep_quality_lag1` | Value 1/2/7 days earlier for the same user (`lag()` over a user window) | Recent personal history | `spark_etl.py` L79–86 |
| `steps_roll7_avg`, `calories_roll7_avg`, `active_minutes_roll7_avg`, `resting_hr_roll7_avg` | Trailing 7-row average per user | Smoothed personal trend | `spark_etl.py` L80, L88–91 |
| `daily_step_goal`, `daily_calorie_goal` | 1.10 × user's own average, rounded (to 100 steps / 10 kcal), via `groupBy(user_id).agg()` + broadcast join | **Personalized** goals (MapReduce pattern) | `spark_etl.py` L99–115 |
| `goal_achieved`, `calorie_goal_achieved` | 1 if the day's value ≥ the personal goal | Daily goal labels | `spark_etl.py` L118–121 |
| `month_sin`, `month_cos` | Cyclical month encoding | Seasonality without one-hot (same as `models/train_goal_achievement.py` L69–70) | added in §5 |
| `label` (next-day goal achieved) | `goal_achieved` of the user's *next consecutive* day | Classification target (§6.1). Same rule as `train_goal_achievement.py` L76–82 | added in §5 |

The cell below checks the Spark features by recomputing them by hand for one user.
""")

code(r"""
DEMO_USER = 1503      # the user behind dashboard login `demo1` (etl/setup_auth.py)
u = (silver.filter(F.col("user_id") == DEMO_USER).orderBy("date")
           .select("date", "day_of_week", "month", "steps", "steps_lag1", "steps_lag2", "steps_lag7",
                   "steps_roll7_avg", "active_minutes", "is_rest_day", "daily_step_goal", "goal_achieved")
           .toPandas())
display(u.head(9))

# Manual re-computation for the 8th record of this user
i = 7
manual_roll = u.steps.iloc[i-6:i+1].mean()
print(f"Row {i+1}: steps_roll7_avg (Spark) = {u.steps_roll7_avg.iloc[i]:.2f}   manual mean of last 7 steps = {manual_roll:.2f}")
print(f"Row {i+1}: steps_lag7 (Spark)      = {u.steps_lag7.iloc[i]:.0f}   manual steps 7 rows earlier = {u.steps.iloc[i-7]}")
user_avg = u.steps.mean()
print(f"Personal goal: round(1.10 x {user_avg:.2f}, -2) = {round(user_avg * 1.10, -2):.0f}   Spark daily_step_goal = {u.daily_step_goal.iloc[0]:.0f}")
assert np.isclose(manual_roll, u.steps_roll7_avg.iloc[i]) and u.steps_lag7.iloc[i] == u.steps.iloc[i-7]
""")

code(r"""
print("is_rest_day value counts in Silver:")
silver.groupBy("is_rest_day").count().show()
print("Minimum active_minutes in the dataset:", silver.agg(F.min("active_minutes")).first()[0])
goal_rate = silver.agg(F.avg("goal_achieved")).first()[0]
print(f"Share of user-days where the personalized step goal was achieved: {goal_rate:.2%}")
""")

md(r"""
**Interpretation:** the Spark lag/rolling/goal features match the manual calculation exactly.
`is_rest_day` exists in the code but is constant (0) here, because every row in this dataset has a logged
session of at least 20 minutes. It is therefore **not** used as a model feature. Note that "7-day" lag
and rolling features are computed over the user's previous 7 *records*, and users have gaps between
records, as `spark_etl.py` implements it.
""")

md(r"""
### 4.3 Final Feature Set
""")

code(r"""
# Classification features - identical to models/train_goal_achievement.py (NUM_FEATURES + CAT_FEATURES)
CLS_NUM = ["steps_lag1", "steps_lag2", "steps_lag7", "steps_roll7_avg", "calories_lag1",
           "calories_roll7_avg", "active_minutes_roll7_avg", "resting_hr_roll7_avg",
           "age", "bmi", "month_sin", "month_cos"]
CLS_CAT = ["day_of_week", "activity_type", "gender"]
CLS_TARGET = "label"   # = next consecutive day's goal_achieved

# Clustering features - daily behaviour (justified in §7.2)
KM_FEATURES = ["steps", "active_minutes", "calories_burned", "avg_heart_rate", "sleep_minutes"]

feature_set = pd.DataFrame(
    [("Random Forest", f, "numeric") for f in CLS_NUM] + [("Random Forest", f, "categorical") for f in CLS_CAT]
    + [("Random Forest", CLS_TARGET, "TARGET")] + [("K-Means", f, "numeric (standardised)") for f in KM_FEATURES],
    columns=["Model", "Column", "Role"])
feature_set.to_csv(EVIDENCE / "final_feature_set.csv", index=False)
display(feature_set)
""")

# =====================================================================
md(r"""
## 5. Dataset Splitting

**What the project presentation says:** 70% train / 15% validation / 15% test.
**What the existing code does:** `models/train_goal_achievement.py` uses a *chronological*
train/test split at 2024-10-15, with no validation set. So the 70/15/15 claim was **not** implemented.

**What this notebook does:**
1. Builds the classification dataset with the same rules as the existing script: next-day label, only
   consecutive-day pairs, and only rows with complete lag features.
2. Splits it **70 / 15 / 15** using a seeded hash of (`user_id`, `date`, seed = 42). This is a random but
   fully reproducible assignment. Unlike `randomSplit`, it does not depend on how Spark happens to
   partition the data, so every run gives exactly the same split.
3. Uses the **validation** set only to choose Random Forest hyper-parameters. The **test** set is used
   once, for the final metrics.
4. Repeats the original **chronological** split as a robustness check (§6.12).
""")

code(r"""
user_window = Window.partitionBy("user_id").orderBy("date")
model_base = (
    silver
    .withColumn("month_num", F.month("date"))
    .withColumn("month_sin", F.sin(2 * np.pi * F.col("month_num") / 12))
    .withColumn("month_cos", F.cos(2 * np.pi * F.col("month_num") / 12))
    .withColumn("next_date", F.lead("date", 1).over(user_window))
    .withColumn(CLS_TARGET, F.lead("goal_achieved", 1).over(user_window).cast("double"))
)
funnel = [("Silver rows", silver.count())]
step = model_base.filter(F.col(CLS_TARGET).isNotNull());             funnel.append(("has a next record", step.count()))
step = step.filter(F.datediff("next_date", "date") == 1);            funnel.append(("next record is the next calendar day", step.count()))
model_df = step.dropna(subset=CLS_NUM).cache();                      funnel.append(("all lag/rolling features present", model_df.count()))
display(pd.DataFrame(funnel, columns=["Filter", "Rows remaining"]))
""")

md(r"""
**Why rows drop:** users log about 229 of the ~360 days, so many records have no record for the
*following calendar day*. Those cannot be fair one-day-ahead examples, and the existing script
drops them too.
""")

code(r"""
# Seeded, partition-independent 70/15/15 assignment
model_df = model_df.withColumn(
    "split_u", (F.abs(F.xxhash64("user_id", "date", F.lit(SEED))) % 1_000_000) / 1_000_000.0)
train = model_df.filter("split_u < 0.70").cache()
val = model_df.filter("split_u >= 0.70 AND split_u < 0.85").cache()
test = model_df.filter("split_u >= 0.85").cache()

total = model_df.count()
rows = []
for name, part in [("Training", train), ("Validation", val), ("Test", test)]:
    n = part.count()
    pos = part.filter(F.col(CLS_TARGET) == 1).count()
    rows.append({"Set": name, "Records": n, "Percentage": f"{n / total:.2%}",
                 "Goal achieved (1)": pos, "Goal missed (0)": n - pos, "Positive rate": f"{pos / n:.2%}"})
rows.append({"Set": "Total", "Records": total, "Percentage": "100.00%",
             "Goal achieved (1)": sum(r["Goal achieved (1)"] for r in rows),
             "Goal missed (0)": sum(r["Goal missed (0)"] for r in rows), "Positive rate": ""})
split_summary = pd.DataFrame(rows)
split_summary.to_csv(EVIDENCE / "split_summary.csv", index=False)
assert sum(r["Records"] for r in rows[:3]) == total
display(split_summary)
""")

md(r"""
### 5.1 Training Set
### 5.2 Validation Set
### 5.3 Test Set

**Interpretation:** the table above gives the actual counts. The percentages are computed from those
counts and come out very close to 70/15/15 (a random assignment is never exactly 70.00%). The class
balance is nearly identical in all three sets, so the split is not biased.
**Limitation to state honestly:** this is a *record-level* split, so the same user appears in all three
sets, and a test day can be next to a training day. That is acceptable for "predict a known user's next
day", but it is a more optimistic setting than an out-of-time split. That is why §6.12 also reports the chronological split.
""")

# =====================================================================
md(r"""
## 6. Classification Problem – Random Forest

### 6.1 Problem Statement

**Question:** *Based on a user's pattern up to today, will they reach their personalized step goal tomorrow?*

**Target definition (taken from the existing code, not invented):**
1. `daily_step_goal` = round(1.10 × the user's own average daily steps, nearest 100). Source: `etl/spark_etl.py` L106–107.
2. `goal_achieved` = 1 if `steps` ≥ `daily_step_goal`, else 0. Source: `etl/spark_etl.py` L118.
3. `label` = `goal_achieved` of the user's **next consecutive calendar day**. Source: `models/train_goal_achievement.py` L76–82.

**Why this target:** it is the project's actual Model 1 target. It has no leakage, because tomorrow's steps
are never an input. And it is actionable: the dashboard can warn a user today.
(A *same-day* label would be leaky. `steps_roll7_avg` includes today's steps, which define the label.)
""")

md(r"""
### 6.2 Features and Target
""")

code(r"""
print("Numeric features    :", CLS_NUM)
print("Categorical features:", CLS_CAT)
print("Target              :", CLS_TARGET, "(1 = next-day goal achieved, 0 = missed)")
model_df.groupBy(CLS_TARGET).count().orderBy(CLS_TARGET).show()
""")

md(r"""
### 6.3 Model Configuration

* **Spark MLlib Pipeline:** `StringIndexer` (categorical → index) → `VectorAssembler` → `RandomForestClassifier`.
* **Class weights:** the classes are imbalanced (~37% positive). Each training row gets the weight
  `0.5 / class_share`, the Spark equivalent of scikit-learn's `class_weight="balanced"` used in the
  existing `train_goal_achievement.py`.
* **Hyper-parameter selection:** `numTrees = 100`, with `maxDepth` ∈ {6, 8, 10} compared on the
  **validation** set by ROC-AUC (threshold-independent). The cap of 10 matches the existing script's
  `max_depth=10` and also fits this laptop's 2 GB Spark heap. Deeper trees ran out of memory here.
""")

code(r"""
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import (BinaryClassificationEvaluator, MulticlassClassificationEvaluator,
                                   ClusteringEvaluator)
from pyspark.ml.functions import vector_to_array

def add_balanced_weights(df):
    pos_share = df.filter(F.col(CLS_TARGET) == 1).count() / df.count()
    weighted = df.withColumn("class_weight", F.when(F.col(CLS_TARGET) == 1, 0.5 / pos_share)
                                              .otherwise(0.5 / (1 - pos_share)))
    return weighted, pos_share

train_w, pos_share = add_balanced_weights(train)
print(f"Training positive share = {pos_share:.4f}  ->  weight(1) = {0.5/pos_share:.4f}, weight(0) = {0.5/(1-pos_share):.4f}")

indexers = [StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep") for c in CLS_CAT]
assembler = VectorAssembler(inputCols=CLS_NUM + [f"{c}_idx" for c in CLS_CAT], outputCol="features")

def make_rf(max_depth):
    return RandomForestClassifier(labelCol=CLS_TARGET, featuresCol="features", weightCol="class_weight",
                                  numTrees=100, maxDepth=max_depth, maxBins=32, impurity="gini",
                                  featureSubsetStrategy="auto", subsamplingRate=1.0, seed=SEED)

auc_eval = BinaryClassificationEvaluator(labelCol=CLS_TARGET, rawPredictionCol="rawPrediction", metricName="areaUnderROC")
mc_eval = MulticlassClassificationEvaluator(labelCol=CLS_TARGET, predictionCol="prediction")
def mc(pred, metric, label=None):
    params = {mc_eval.metricName: metric}
    if label is not None:
        params[mc_eval.metricLabel] = label
    return mc_eval.evaluate(pred, params)
""")

md(r"""
### 6.4 Model Training

Train one model per `maxDepth` on the **training** set, compare them on the **validation** set, and keep the best.
""")

code(r"""
tuning, best = [], None
for depth in [6, 8, 10]:
    t0 = time.time()
    fitted = Pipeline(stages=indexers + [assembler, make_rf(depth)]).fit(train_w)
    vp = fitted.transform(val)
    row = {"maxDepth": depth, "numTrees": 100, "Validation ROC-AUC": auc_eval.evaluate(vp),
           "Validation accuracy": mc(vp, "accuracy"), "Validation F1 (class 1)": mc(vp, "fMeasureByLabel", 1.0),
           "Train time (s)": round(time.time() - t0, 1)}
    tuning.append(row)
    if best is None or row["Validation ROC-AUC"] > best[0]["Validation ROC-AUC"]:
        best = (row, fitted)
tuning_df = pd.DataFrame(tuning).round(4)
tuning_df.to_csv(EVIDENCE / "rf_validation_tuning.csv", index=False)
display(tuning_df)

best_row, rf_pipeline_model = best
BEST_DEPTH = best_row["maxDepth"]
rf_model = rf_pipeline_model.stages[-1]
print(f"Selected maxDepth = {BEST_DEPTH} (highest validation ROC-AUC)")
print("\nFinal model configuration:")
for p in ["numTrees", "maxDepth", "maxBins", "impurity", "featureSubsetStrategy", "subsamplingRate",
          "minInstancesPerNode", "seed", "weightCol"]:
    print(f"  {p:22s} = {rf_model.getOrDefault(p)}")
print("  feature columns        =", assembler.getInputCols())
""")

md(r"""
**Interpretation:** the validation set, not the test set, picks the tree depth, so the test metrics
below remain an unbiased estimate.
""")

md(r"""
### 6.5 Test Predictions
""")

code(r"""
pred = (rf_pipeline_model.transform(test)
        .withColumn("p_goal_achieved", F.round(vector_to_array("probability")[1], 4))
        .cache())
print(f"Test predictions generated: {pred.count():,}")
(pred.select("user_id", "date", "next_date", F.col(CLS_TARGET).cast("int").alias("actual_label"),
             F.col("prediction").cast("int").alias("predicted_label"), "p_goal_achieved")
     .orderBy("user_id", "date").show(15, truncate=False))

(pred.select("user_id", "date", "next_date", CLS_TARGET, "prediction", "p_goal_achieved")
     .toPandas().to_csv(EVIDENCE / "rf_test_predictions.csv", index=False))
""")

md(r"""
**Interpretation:** each test row shows the actual next-day outcome, the model's predicted class, and the
model's probability that the goal is achieved. The predicted class is 1 when that probability is above 0.5.
All test predictions are saved in `faculty_evidence/rf_test_predictions.csv`.
""")

md(r"""
### 6.6 Confusion Matrix
""")

code(r"""
cm_counts = {(int(r[CLS_TARGET]), int(r["prediction"])): r["count"]
             for r in pred.groupBy(CLS_TARGET, "prediction").count().collect()}
TN, FP = cm_counts.get((0, 0), 0), cm_counts.get((0, 1), 0)
FN, TP = cm_counts.get((1, 0), 0), cm_counts.get((1, 1), 0)
N = TP + TN + FP + FN

cm = pd.DataFrame([[TN, FP], [FN, TP]],
                  index=["Actual: Missed (0)", "Actual: Achieved (1)"],
                  columns=["Predicted: Missed (0)", "Predicted: Achieved (1)"])
cm.to_csv(EVIDENCE / "confusion_matrix.csv")
display(cm)
print(f"TP (achieved, predicted achieved) = {TP:,}")
print(f"TN (missed,   predicted missed)   = {TN:,}")
print(f"FP (missed,   predicted achieved) = {FP:,}")
print(f"FN (achieved, predicted missed)   = {FN:,}")
print(f"Total = {N:,}  (equals test-set size: {N == test.count()})")
""")

code(r"""
from matplotlib.colors import LinearSegmentedColormap
blues = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#86b6ef", "#2a78d6", "#184f95"])
fig, ax = plt.subplots(figsize=(6.0, 4.6))
mat = np.array([[TN, FP], [FN, TP]])
ax.imshow(mat, cmap=blues)
ax.grid(False)
names = [["TN", "FP"], ["FN", "TP"]]
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{names[i][j]}\n{mat[i, j]:,}\n({mat[i, j] / N:.1%})", ha="center", va="center",
                color="white" if mat[i, j] > mat.max() * 0.55 else INK, fontsize=11)
ax.set_xticks([0, 1], ["Missed (0)", "Achieved (1)"]); ax.set_yticks([0, 1], ["Missed (0)", "Achieved (1)"])
ax.set_xlabel("Predicted label"); ax.set_ylabel("Actual label")
ax.set_title(f"Confusion matrix – test set (n={N:,})")
fig.tight_layout(); fig.savefig(EVIDENCE / "confusion_matrix.png"); plt.show()
""")

md(r"""
**Interpretation:** the diagonal (TN, TP) holds the correct predictions. FP are days the model expected
the user to hit the goal but they missed it. FN are days the user hit the goal but the model predicted a miss.
""")

md(r"""
### 6.7 Accuracy

$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
""")

code(r"""
accuracy_manual = (TP + TN) / N
accuracy_spark = mc(pred, "accuracy")
print(f"Accuracy = ({TP} + {TN}) / ({TP} + {TN} + {FP} + {FN}) = {TP + TN} / {N} = {accuracy_manual:.4f}")
print(f"Spark MulticlassClassificationEvaluator(metricName='accuracy') = {accuracy_spark:.4f}")
assert np.isclose(accuracy_manual, accuracy_spark)
""")

md(r"""
### 6.8 Precision

Precision for the positive class (goal achieved): of all days predicted "achieved", how many really were.

$$\text{Precision} = \frac{TP}{TP + FP}$$
""")

code(r"""
precision_manual = TP / (TP + FP)
precision_spark = mc(pred, "precisionByLabel", 1.0)
print(f"Precision = {TP} / ({TP} + {FP}) = {precision_manual:.4f}")
print(f"Spark evaluator (precisionByLabel, metricLabel=1) = {precision_spark:.4f}")
assert np.isclose(precision_manual, precision_spark)
""")

md(r"""
### 6.9 Recall

Recall for the positive class: of all days where the goal was really achieved, how many the model caught.

$$\text{Recall} = \frac{TP}{TP + FN}$$
""")

code(r"""
recall_manual = TP / (TP + FN)
recall_spark = mc(pred, "recallByLabel", 1.0)
print(f"Recall = {TP} / ({TP} + {FN}) = {recall_manual:.4f}")
print(f"Spark evaluator (recallByLabel, metricLabel=1) = {recall_spark:.4f}")
assert np.isclose(recall_manual, recall_spark)
""")

md(r"""
### 6.10 F1 Score

$$F_1 = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
""")

code(r"""
f1_manual = 2 * precision_manual * recall_manual / (precision_manual + recall_manual)
f1_spark = mc(pred, "fMeasureByLabel", 1.0)
print(f"F1 = 2 x {precision_manual:.4f} x {recall_manual:.4f} / ({precision_manual:.4f} + {recall_manual:.4f}) = {f1_manual:.4f}")
print(f"Spark evaluator (fMeasureByLabel, metricLabel=1) = {f1_spark:.4f}")
assert np.isclose(f1_manual, f1_spark)
""")

md(r"""
**Interpretation (6.7–6.10):** each metric was computed twice, once by hand from the confusion-matrix
counts and once by Spark MLlib's evaluator, and the `assert` statements prove the two agree. This is the
answer to *"How exactly did you calculate the accuracy?"*
""")

md(r"""
### 6.11 Classification Results
""")

code(r"""
roc_auc = auc_eval.evaluate(pred)
majority_share = max(TP + FN, TN + FP) / N
classification_results = pd.DataFrame([
    ("Accuracy", accuracy_spark, "(TP+TN)/N"),
    ("Precision (class 1 = achieved)", precision_spark, "TP/(TP+FP)"),
    ("Recall (class 1 = achieved)", recall_spark, "TP/(TP+FN)"),
    ("F1 Score (class 1 = achieved)", f1_spark, "2PR/(P+R)"),
    ("ROC-AUC", roc_auc, "BinaryClassificationEvaluator"),
    ("Weighted precision (both classes)", mc(pred, "weightedPrecision"), "class-size weighted"),
    ("Weighted recall (both classes)", mc(pred, "weightedRecall"), "class-size weighted"),
    ("Weighted F1 (both classes)", mc(pred, "f1"), "class-size weighted"),
    ("Baseline: always predict majority class", majority_share, "reference only"),
], columns=["Metric", "Value", "Formula / source"])
classification_results["Actual Score"] = classification_results["Value"].map(lambda v: f"{v:.2%}")
classification_results.to_csv(EVIDENCE / "classification_results.csv", index=False)
display(classification_results[["Metric", "Actual Score", "Formula / source"]])
""")

code(r"""
fi = pd.DataFrame({"Feature": assembler.getInputCols(), "Importance": rf_model.featureImportances.toArray()})
fi = fi.sort_values("Importance", ascending=False).reset_index(drop=True)
fi.to_csv(EVIDENCE / "rf_feature_importance.csv", index=False)

fig, ax = plt.subplots(figsize=(7, 4.2))
top = fi.head(10).iloc[::-1]
ax.barh(top.Feature, top.Importance, color=BLUE, height=0.6)
for y, v in enumerate(top.Importance):
    ax.text(v + fi.Importance.max() * 0.01, y, f"{v:.3f}", va="center", color=MUTED, fontsize=9)
ax.set_xlabel("Spark RF feature importance (mean impurity decrease)")
ax.set_title("Top 10 features – next-day goal model"); ax.grid(axis="y", visible=False)
fig.tight_layout(); fig.savefig(EVIDENCE / "rf_feature_importance.png"); plt.show()
""")

md(r"""
**Interpretation:** accuracy must be compared with the majority-class baseline ("always predict
missed", the last row). The model is above that baseline, and its ROC-AUC shows it ranks achieved days
above missed days far better than chance (50%). Because of the class weighting, the model favours
**recall** over precision: it catches most days on which the goal will be achieved, at the cost of some false
alarms (FP). For a motivational fitness app that is a reasonable trade-off.
The feature importances show the prediction is driven mostly by **seasonality** (`month_sin`),
**day of week** and the user's **recent 7-day step trend**. The dataset has a real seasonal and weekly
rhythm, and a goal based on the yearly average is easier to hit in high-activity months.
""")

md(r"""
### 6.12 Robustness Check – Chronological (Out-of-Time) Split

The existing project script trains on dates **before 2024-10-15** and tests on dates **on or after** it.
Here we rerun that same methodology with the Spark Random Forest (same features and the selected depth),
to show how much performance depends on the split strategy.
""")

code(r"""
CUTOFF = "2024-10-15"   # models/train_goal_achievement.py TRAIN_CUTOFF
chrono_train, chrono_test = model_df.filter(F.col("date") < CUTOFF), model_df.filter(F.col("date") >= CUTOFF)
chrono_train_w, chrono_pos = add_balanced_weights(chrono_train)
chrono_model = Pipeline(stages=indexers + [assembler, make_rf(BEST_DEPTH)]).fit(chrono_train_w)
cp = chrono_model.transform(chrono_test).cache()
chrono = pd.DataFrame([{
    "Split": "Random 70/15/15 (this notebook, test set)", "Train rows": train.count(), "Test rows": N,
    "Test positive rate": f"{(TP + FN) / N:.2%}", "Accuracy": accuracy_spark, "Precision": precision_spark,
    "Recall": recall_spark, "F1": f1_spark, "ROC-AUC": roc_auc}, {
    "Split": f"Chronological (train < {CUTOFF})", "Train rows": chrono_train.count(), "Test rows": cp.count(),
    "Test positive rate": f"{cp.filter(F.col(CLS_TARGET) == 1).count() / cp.count():.2%}",
    "Accuracy": mc(cp, "accuracy"), "Precision": mc(cp, "precisionByLabel", 1.0),
    "Recall": mc(cp, "recallByLabel", 1.0), "F1": mc(cp, "fMeasureByLabel", 1.0), "ROC-AUC": auc_eval.evaluate(cp)}])
chrono.to_csv(EVIDENCE / "classification_split_comparison.csv", index=False)
display(chrono.round(4))
""")

md(r"""
**Interpretation:** the chronological test period (mid-October to December) falls in the dataset's
seasonal low-activity period. Far fewer test days reach the yearly-average-based goal (see "Test positive
rate"), and the model must extrapolate to months it never saw.
* **Accuracy looks *higher* under the chronological split, but that is misleading.** Most test days are
  "missed", so predicting "missed" is already right most of the time. The class-1 **precision, recall, F1
  and ROC-AUC are all lower**, and those are the honest measures here.
* For cross-checking: `models/metrics_report.md` documents the existing *scikit-learn* Random Forest on
  this same chronological split as F1 0.344 / ROC-AUC 0.718. The Spark MLlib model above lands in the same range.

**Both results are real and both should be reported.** The random split measures "predict a known user's
next day". The chronological split is the stricter forecast-the-future test that the original project
script used.
""")

# =====================================================================
md(r"""
## 7. Clustering Problem – K-Means

### 7.1 Problem Statement

**Question:** *What distinct types of activity day exist in the data, and how does each user's mix of
day types differ?* K-Means is unsupervised: no label is used, and quality is judged with the internal
silhouette score. K-Means did **not** exist in the repository before this notebook.
""")

md(r"""
### 7.2 Clustering Features

**Day-level or user-level?** We first check whether *users* actually differ in their average behaviour.
""")

code(r"""
CANDIDATES = ["steps", "active_minutes", "sedentary_minutes", "calories_burned", "avg_heart_rate",
              "resting_heart_rate", "sleep_minutes"]
per_user = silver.groupBy("user_id").agg(*[F.avg(c).alias(c) for c in CANDIDATES])
spread = pd.DataFrame({
    "Feature": CANDIDATES,
    "Std across daily records": [silver.agg(F.stddev(c)).first()[0] for c in CANDIDATES],
    "Std across per-user averages": [per_user.agg(F.stddev(c)).first()[0] for c in CANDIDATES],
    "Avg within-user std": [silver.groupBy("user_id").agg(F.stddev(c).alias("s")).agg(F.avg("s")).first()[0]
                            for c in CANDIDATES],
}).round(2)
display(spread)
viol = silver.filter(F.col("sedentary_minutes") != 1440 - F.col("sleep_minutes") - F.col("active_minutes")).count()
print("Rows where sedentary_minutes != 1440 - sleep_minutes - active_minutes:", viol)
""")

md(r"""
**Interpretation and feature choice (based on the output above):**
* Per-user **average** steps, active minutes, sedentary minutes and sleep are almost identical across
  users (tiny std across per-user averages). Clustering *users* on averages would separate them mainly on
  body-weight-driven calories, not on behaviour. The real behavioural variation is **day to day**, so we
  cluster the **daily records**, then profile each user by their mix of day types (§7.9).
* `resting_heart_rate` has zero within-user variation. It is a constant per-user trait, not daily behaviour,
  so it is **excluded** as an input.
* `sedentary_minutes` is an exact linear function of sleep and active minutes (0 violations), so it adds no
  new information and would double-weight those two. It is **excluded** as an input but **kept** for describing clusters.
* **Final inputs:** steps, active_minutes, calories_burned, avg_heart_rate, sleep_minutes.
""")

md(r"""
### 7.3 Feature Scaling

The features have very different units (≈8,600 steps vs ≈70 minutes). Without scaling, K-Means
distances would be dominated by `steps`. `StandardScaler(withMean=True, withStd=True)` puts every
feature on mean 0, standard deviation 1.
""")

code(r"""
km_assembler = VectorAssembler(inputCols=KM_FEATURES, outputCol="km_raw")
km_scaler = StandardScaler(inputCol="km_raw", outputCol="km_features", withMean=True, withStd=True)
km_raw = km_assembler.transform(silver)
scaler_model = km_scaler.fit(km_raw)
km_data = scaler_model.transform(km_raw).cache()

scaling = pd.DataFrame({"Feature": KM_FEATURES, "Mean (original units)": scaler_model.mean.toArray(),
                        "Std (original units)": scaler_model.std.toArray()}).round(2)
display(scaling)
check = km_data.select(vector_to_array("km_features").alias("z")).select(
    *[F.col("z")[i].alias(f) for i, f in enumerate(KM_FEATURES)])
print("After scaling (should be mean ~0, std ~1):")
check.describe().show()
""")

md(r"""
### 7.4 K Selection

Train K-Means for **K = 2…6** (seed 42) on all daily records. For each K we compute the **silhouette
score** (Spark `ClusteringEvaluator`, squared Euclidean distance) and the within-cluster sum of squares
(WSSSE, the elbow curve). Silhouette ranges from −1 to 1. Higher means points sit closer to their own
cluster than to the nearest other cluster.
""")

code(r"""
sil_eval = ClusteringEvaluator(featuresCol="km_features", predictionCol="cluster",
                               metricName="silhouette", distanceMeasure="squaredEuclidean")
from pyspark.ml.clustering import KMeans
k_rows, km_models = [], {}
for k in range(2, 7):
    km = KMeans(k=k, seed=SEED, featuresCol="km_features", predictionCol="cluster", maxIter=50).fit(km_data)
    km_models[k] = km
    k_rows.append({"K": k, "Silhouette Score": sil_eval.evaluate(km.transform(km_data)),
                   "WSSSE": km.summary.trainingCost, "Cluster sizes": km.summary.clusterSizes})
k_eval = pd.DataFrame(k_rows)
""")

md(r"""
### 7.5 Silhouette Score
""")

code(r"""
silhouette_scores = k_eval[["K", "Silhouette Score", "WSSSE"]].copy()
silhouette_scores["Silhouette Score"] = silhouette_scores["Silhouette Score"].round(4)
silhouette_scores["WSSSE"] = silhouette_scores["WSSSE"].round(1)
silhouette_scores.to_csv(EVIDENCE / "silhouette_scores.csv", index=False)
display(k_eval.assign(**{"Silhouette Score": k_eval["Silhouette Score"].round(4),
                         "WSSSE": k_eval["WSSSE"].round(1)}))

BEST_K = int(k_eval.loc[k_eval["Silhouette Score"].idxmax(), "K"])

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
ax = axes[0]
ax.plot(k_eval.K, k_eval["Silhouette Score"], color=BLUE, lw=2, marker="o", ms=8)
for k, s in zip(k_eval.K, k_eval["Silhouette Score"]):
    ax.annotate(f"{s:.3f}", (k, s), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
ax.scatter([BEST_K], [k_eval["Silhouette Score"].max()], s=160, facecolors="none", edgecolors=ORANGE, lw=2, zorder=3)
ax.margins(y=0.18); ax.set_xticks(k_eval.K); ax.set_xlabel("K"); ax.set_ylabel("Silhouette score"); ax.set_title("Silhouette by K (higher is better)")
ax = axes[1]
ax.plot(k_eval.K, k_eval["WSSSE"], color=BLUE, lw=2, marker="o", ms=8)
ax.set_xticks(k_eval.K); ax.set_xlabel("K"); ax.set_ylabel("WSSSE"); ax.set_title("Elbow curve (within-cluster SSE)")
fig.tight_layout(); fig.savefig(EVIDENCE / "silhouette_scores.png"); plt.show()
print(f"Selected K = {BEST_K} (highest silhouette score: {k_eval['Silhouette Score'].max():.4f})")
""")

md(r"""
**Interpretation:** K is chosen by the **highest actual silhouette score** (circled in orange), not
assumed in advance. The elbow curve always decreases as K grows, so it is shown only as supporting
context. The silhouette values are moderate rather than high, meaning the day types overlap: daily
behaviour forms a continuum rather than perfectly separate groups. We state that openly.
""")

md(r"""
### 7.6 Final K-Means Model
""")

code(r"""
final_km = km_models[BEST_K]
clustered = final_km.transform(km_data).cache()
centers_scaled = np.array(final_km.clusterCenters())
centers_original = centers_scaled * scaler_model.std.toArray() + scaler_model.mean.toArray()
centers = pd.DataFrame(centers_original, columns=KM_FEATURES).round(1)
centers.index.name = "cluster"
print(f"Final model: K = {BEST_K}, seed = {SEED}, distance = squared Euclidean, iterations = {final_km.summary.numIter}")
print("Cluster centers converted back to original units:")
display(centers)
print("Sample cluster assignments:")
clustered.select("user_id", "date", *KM_FEATURES, "cluster").show(10)
""")

md(r"""
### 7.7 Cluster Distribution
""")

code(r"""
total_days = clustered.count()
dist = (clustered.groupBy("cluster")
        .agg(F.count("*").alias("Daily records"), F.countDistinct("user_id").alias("Distinct users"))
        .orderBy("cluster").toPandas())
dist["Share of records"] = (dist["Daily records"] / total_days).map(lambda v: f"{v:.2%}")
assert dist["Daily records"].sum() == total_days
display(dist)

fig, ax = plt.subplots(figsize=(5.5, 3.2))
ax.bar(dist.cluster.astype(str), dist["Daily records"], color=BLUE, width=0.55)
for x, v in enumerate(dist["Daily records"]):
    ax.text(x, v, f"{v:,}", ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xlabel("Cluster"); ax.set_ylabel("Daily records"); ax.set_title("Records per cluster"); ax.grid(axis="x", visible=False)
fig.tight_layout(); fig.savefig(EVIDENCE / "cluster_sizes.png"); plt.show()
""")

md(r"""
### 7.8 Cluster Characteristics

Average values per cluster for **all** relevant columns, including the ones not used as inputs, plus how far
each is from the overall mean.
""")

code(r"""
PROFILE = ["steps", "active_minutes", "sedentary_minutes", "calories_burned", "avg_heart_rate",
           "max_heart_rate", "resting_heart_rate", "sleep_minutes", "sleep_quality_score", "distance_km"]
profile = (clustered.groupBy("cluster").agg(F.count("*").alias("records"), *[F.avg(c).alias(c) for c in PROFILE])
           .orderBy("cluster").toPandas().set_index("cluster"))
overall = clustered.agg(*[F.avg(c).alias(c) for c in PROFILE]).toPandas().iloc[0]
rel = ((profile[PROFILE] / overall - 1) * 100).round(1)
display(profile.round(1))
print("Difference from overall mean (%):")
display(rel)

intensity_mix = (clustered.groupBy("cluster").pivot("intensity", ["Low", "Medium", "High"]).count()
                 .orderBy("cluster").toPandas().set_index("cluster"))
intensity_mix = (intensity_mix.div(intensity_mix.sum(axis=1), axis=0) * 100).round(1)
print("Intensity mix per cluster (% of the cluster's days):")
display(intensity_mix)
act = clustered.groupBy("cluster", "activity_type").count().toPandas()
act_mix = act.pivot(index="cluster", columns="activity_type", values="count").fillna(0)
act_mix = (act_mix.div(act_mix.sum(axis=1), axis=0) * 100).round(1)
print("Activity-type mix per cluster (%):")
display(act_mix)
""")

code(r"""
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
div = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#eb6834"])
lim = float(np.abs(rel.values).max())
fig, ax = plt.subplots(figsize=(10, 0.9 + 0.55 * len(rel)))
ax.imshow(rel.values, cmap=div, norm=TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim), aspect="auto")
ax.grid(False)
for i in range(rel.shape[0]):
    for j in range(rel.shape[1]):
        ax.text(j, i, f"{rel.values[i, j]:+.0f}%", ha="center", va="center", fontsize=9, color=INK)
ax.set_xticks(range(len(PROFILE)), PROFILE, rotation=30, ha="right")
ax.set_yticks(range(len(rel)), [f"Cluster {c}" for c in rel.index])
ax.set_title("Cluster mean vs overall mean (orange = above, blue = below)")
fig.tight_layout(); fig.savefig(EVIDENCE / "cluster_profile_heatmap.png"); plt.show()
""")

md(r"""
### 7.9 Cluster Interpretation

Labels are assigned by a **transparent rule applied to the computed averages**, not by cluster number:
clusters are ranked by mean `active_minutes` (session length). Each label is then explained by listing
the features that differ by more than 5% from the overall mean.
""")

code(r"""
order = profile["active_minutes"].sort_values().index.tolist()          # lowest -> highest session length
tier_names = {2: ["Light / short-session days", "High-effort / long-session days"],
              3: ["Light days", "Moderate days", "High-effort days"]}
names = tier_names.get(BEST_K, [f"Effort tier {i+1} of {BEST_K}" for i in range(BEST_K)])
cluster_label = {c: names[r] for r, c in enumerate(order)}

summary_rows = []
for c in profile.index:
    notable = [f"{f} {rel.loc[c, f]:+.1f}% ({profile.loc[c, f]:,.1f})" for f in PROFILE if abs(rel.loc[c, f]) > 5]
    summary_rows.append({"Cluster": c, "Count": int(profile.loc[c, "records"]),
                         "Share": f"{profile.loc[c, 'records'] / total_days:.2%}",
                         "Main characteristics (vs overall mean)": "; ".join(notable) or "close to overall mean",
                         "Interpretation": cluster_label[c]})
cluster_summary = pd.DataFrame(summary_rows)
cluster_summary.to_csv(EVIDENCE / "cluster_summary.csv", index=False)
pd.set_option("display.max_colwidth", 200)
display(cluster_summary)
""")

md(r"""
**Personalization: each user's mix of day types.** Because clusters describe *days*, every user gets a
personal profile, the share of their own days that fall in each cluster. This is what turns clustering
into a per-user insight (for example, "only X% of your days are high-effort days, versus a typical user's Y%").
""")

code(r"""
user_mix = (clustered.groupBy("user_id").pivot("cluster", sorted(cluster_label)).count().fillna(0).toPandas()
            .set_index("user_id"))
user_mix = user_mix.div(user_mix.sum(axis=1), axis=0) * 100
user_mix.columns = [f"% days in cluster {c} ({cluster_label[int(c)]})" for c in user_mix.columns]
user_mix.round(2).to_csv(EVIDENCE / "user_cluster_mix.csv")
print("Distribution across all users of the share of their days in each cluster:")
display(user_mix.describe().round(1))
print("Dashboard demo users (demo1=1503, demo2=2759, demo3=2373):")
display(user_mix.loc[[1503, 2759, 2373]].round(1))
""")

md(r"""
**Interpretation (read with the tables in 7.8 and 7.9):**
* The clusters separate mainly on **session length and energy expenditure**. `active_minutes` and
  `calories_burned` are the only features more than 5% from the overall mean. The high-effort cluster also has
  a larger share of *High*-intensity sessions and of HIIT/Running, and the light cluster has more
  Yoga/Walking/Weight-training days (activity-type table).
* **Steps, sleep, heart rate and sleep quality barely differ** between clusters. In this dataset a
  high-effort day means a longer and harder workout, not more walking, so labelling the clusters by step count
  ("highly active walkers") would be wrong.
* Sedentary minutes are only slightly lower on high-effort days, as expected from the 1440-minute identity.
* Every user has days in both clusters, and the share of high-effort days varies by user (table above).
  That share is the personalized signal: for example, a recommendation can target users whose
  high-effort share is below the population median.
""")

# =====================================================================
md(r"""
## 8. Big Data / Spark Evidence

### 8.1 Spark Session
""")

code(r"""
sc = spark.sparkContext
jvm = spark._jvm
hadoop_conf = sc._jsc.hadoopConfiguration()
spark_info = {
    "Spark version": spark.version,
    "Application name": sc.appName,
    "Application id": sc.applicationId,
    "Master": sc.master,
    "Default parallelism (cores used)": sc.defaultParallelism,
    "spark.sql.shuffle.partitions": spark.conf.get("spark.sql.shuffle.partitions"),
    "Spark UI": sc.uiWebUrl,
    "JVM Java version": jvm.System.getProperty("java.version"),
    "Hadoop client library version": jvm.org.apache.hadoop.util.VersionInfo.getVersion(),
    "fs.defaultFS (default filesystem)": hadoop_conf.get("fs.defaultFS"),
}
display(pd.DataFrame(spark_info.items(), columns=["Property", "Value"]))
""")

md(r"""
### 8.2 Distributed Data Processing

The physical plans show how Spark parallelises the ETL's operations. The window functions use an
`Exchange hashpartitioning(user_id)` (shuffle) followed by `Window`. The per-user goal aggregation runs as
a partial `HashAggregate` on each partition (map side), an `Exchange` (shuffle), then a final
`HashAggregate` (reduce side), which is the MapReduce pattern. The join with the per-user table is a
`BroadcastHashJoin`.
""")

code(r"""
def plan_of(df):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        df.explain()
    return buf.getvalue()

etl_like = (bronze.withColumn("steps_lag1", F.lag("steps", 1).over(Window.partitionBy("user_id").orderBy("date"))))
goals = bronze.groupBy("user_id").agg(F.avg("steps").alias("user_avg_steps"))
joined = bronze.join(F.broadcast(goals), "user_id")
plans = {"Window / lag feature (spark_etl.py L79-82)": plan_of(etl_like),
         "groupBy(user_id).agg - personalized goal (spark_etl.py L99-104)": plan_of(goals),
         "Broadcast join (spark_etl.py L115)": plan_of(joined)}
for title, p in plans.items():
    print("=" * 100, "\n", title, "\n", "=" * 100, "\n", p, sep="")
""")

code(r"""
mllib_stages = pd.DataFrame(
    [("Classification", type(s).__name__) for s in rf_pipeline_model.stages]
    + [("Clustering", type(s).__name__) for s in (km_assembler, scaler_model, final_km)],
    columns=["Workflow", "Spark MLlib stage"])
print("Spark MLlib components used in this notebook:")
display(mllib_stages)
""")

md(r"""
### 8.3 Partitions
""")

code(r"""
silver_files = sorted(Path(SILVER_PATH).rglob("*.parquet"))
by_month = pd.Series([f.parent.name for f in silver_files]).value_counts().sort_index()
storage = pd.DataFrame({"Parquet files": by_month,
                        "Size (KB)": [round(sum(f.stat().st_size for f in silver_files if f.parent.name == m) / 1024, 1)
                                      for m in by_month.index]})
print(f"Silver layer on disk: {len(silver_files)} Parquet files in {len(by_month)} month partitions, "
      f"{sum(f.stat().st_size for f in silver_files) / 1024 / 1024:.2f} MB total")
display(storage)

print("Bronze DataFrame in-memory partitions :", bronze.rdd.getNumPartitions())
print("Silver DataFrame in-memory partitions :", silver.rdd.getNumPartitions())
print("Records per in-memory Silver partition:")
(silver.groupBy(F.spark_partition_id().alias("partition_id")).count().orderBy("partition_id").show(50))
""")

code(r"""
march = silver.filter(F.col("month") == "2024-03")
march_plan = plan_of(march)
print("Partition pruning - query for month = 2024-03 only reads that folder:")
scan = [line for line in march_plan.splitlines() if "FileScan parquet" in line][0]
print("PartitionFilters:", re.search(r"PartitionFilters: \[(.*?)\]", scan).group(1))
print("Location        :", re.search(r"Location: InMemoryFileIndex\(\d+ paths\)\[(.*?)\]", scan).group(1))
print("\nRows in 2024-03 partition:", march.count())
""")

md(r"""
### 8.4 HDFS Evidence

The check below looks for a Hadoop/HDFS installation and the configured default filesystem, and does not
assume either.
""")

code(r"""
hdfs_bin = shutil.which("hdfs")
print("`hdfs` command on PATH :", hdfs_bin)
print("fs.defaultFS           :", hadoop_conf.get("fs.defaultFS"))
if hdfs_bin:
    out = subprocess.run([hdfs_bin, "dfs", "-ls", "/"], capture_output=True, text=True)
    print(out.stdout or out.stderr)
else:
    print("\nRESULT: HDFS is NOT installed/configured on this machine. The Silver layer is stored as\n"
          "partitioned Parquet on the local filesystem through Hadoop's FileSystem API (file:///),\n"
          "i.e. the same storage format/partition layout HDFS would hold, but not HDFS itself.")

evidence_txt = ["SPARK SESSION"] + [f"{k}: {v}" for k, v in spark_info.items()]
evidence_txt += ["", f"hdfs command on PATH: {hdfs_bin}", "",
                 f"Silver: {len(silver_files)} parquet files, {len(by_month)} month partitions",
                 storage.to_string(), "", "Bronze partitions: " + str(bronze.rdd.getNumPartitions()),
                 "Silver partitions: " + str(silver.rdd.getNumPartitions()), ""]
evidence_txt += [f"--- {t} ---\n{p}" for t, p in plans.items()] + ["--- Partition pruning ---", march_plan]
(EVIDENCE / "spark_hdfs_evidence.txt").write_text("\n".join(evidence_txt), encoding="utf-8")
print("Saved faculty_evidence/spark_hdfs_evidence.txt")
""")

md(r"""
**What can honestly be claimed:**
* ✅ Processing is done with **Apache Spark** (DataFrames, window functions, shuffles, broadcast joins,
  Spark SQL in `etl/spark_benchmarks.py`) and **Spark MLlib** (pipelines, Random Forest, K-Means, evaluators).
* ✅ Storage uses the Big Data columnar format (**Parquet**) with **Hive-style partitioning** and partition pruning.
* ⚠️ Spark runs in **local mode** (`local[*]`), using all CPU cores of one machine as parallel executors.
  The code is cluster-ready: only `.master()` and the storage URI (`hdfs://…`) would change.
* ❌ **HDFS is not running.** Do not present HDFS screenshots. Describe it as "HDFS-style partitioned storage, HDFS-ready".
""")

# =====================================================================
md(r"""
## 9. Final Results

All values below are generated from the variables computed above. The same tables are written to
`faculty_evidence/REPORT_VALUES.md`, marked for transfer into the report.
""")

code(r"""
def pct(v): return f"{v:.2%}"
sil_tbl = "\n".join(f"| {int(r.K)} | {r['Silhouette Score']:.4f} |" for _, r in k_eval.iterrows())
clu_tbl = "\n".join(f"| {r['Cluster']} | {r['Count']:,} | {r['Main characteristics (vs overall mean)']} | {r['Interpretation']} |"
                    for _, r in cluster_summary.iterrows())
split_tbl = "\n".join(f"| {r['Set']} | {r['Records']:,} | {r['Percentage']} |" for _, r in split_summary.iterrows())
cr = chrono.iloc[1]

report = f'''# FitPulse – ACTUAL values for the faculty report
<!-- Generated by FitPulse_Faculty_Demo.ipynb. REPLACE the report placeholders with these values. -->

## [REPLACE IN REPORT] Dataset
| Item | Actual value |
|---|---:|
| Kaggle source rows / participants | {dataset_summary.iloc[0]['Rows']:,} / {dataset_summary.iloc[0]['Users']:,} |
| Bronze rows / columns / users | {dataset_summary.iloc[1]['Rows']:,} / {dataset_summary.iloc[1]['Columns']} / {dataset_summary.iloc[1]['Users']} |
| Silver rows / columns | {dataset_summary.iloc[2]['Rows']:,} / {dataset_summary.iloc[2]['Columns']} |
| Date range | {dataset_summary.iloc[1]['First date']} to {dataset_summary.iloc[1]['Last date']} |
| Exact duplicate rows (Bronze) | {int(dup.iloc[1]['Exact duplicate rows'])} |
| Missing cells (Bronze) | {int(bronze_missing.Missing.sum())} |
| Classification dataset (after next-day / lag filtering) | {total:,} |

## [REPLACE IN REPORT] Train / Validation / Test split (seeded hash, seed={SEED})
| Set | Records | Percentage |
|---|---:|---:|
{split_tbl}

## [REPLACE IN REPORT] Random Forest classification (Spark MLlib, test set)
Target: next consecutive day's `goal_achieved` (steps >= 1.10 x user's average). numTrees=100, maxDepth={BEST_DEPTH}, seed={SEED}.

| Metric | Actual Result |
|---|---:|
| Accuracy | {pct(accuracy_spark)} |
| Precision | {pct(precision_spark)} |
| Recall | {pct(recall_spark)} |
| F1 Score | {pct(f1_spark)} |
| ROC-AUC | {pct(roc_auc)} |
| Majority-class baseline accuracy | {pct(majority_share)} |

Confusion matrix (test set): TP={TP:,}, TN={TN:,}, FP={FP:,}, FN={FN:,} (n={N:,})

Robustness – chronological split (train < {CUTOFF}): accuracy {pct(cr['Accuracy'])}, precision {pct(cr['Precision'])},
recall {pct(cr['Recall'])}, F1 {pct(cr['F1'])}, ROC-AUC {pct(cr['ROC-AUC'])}.

## [REPLACE IN REPORT] K-Means clustering (Spark MLlib, {total_days:,} daily records)
Inputs (standardised): {", ".join(KM_FEATURES)}

| K | Silhouette Score |
|---:|---:|
{sil_tbl}

**Selected K = {BEST_K}** (highest silhouette).

| Cluster | Count | Main Characteristics | Interpretation |
|---|---:|---|---|
{clu_tbl}
'''
(EVIDENCE / "REPORT_VALUES.md").write_text(report, encoding="utf-8")
display(Markdown(report))
""")

# =====================================================================
md(r"""
## 10. Final Inference
""")

code(r"""
best_cluster = order[-1]
print(f'''1. DATA: {dataset_summary.iloc[1]['Rows']:,} daily records from {dataset_summary.iloc[1]['Users']} users were processed by
   Apache Spark (Bronze CSV -> Silver partitioned Parquet, {len(silver_files)} files / {len(by_month)} month partitions),
   with 0 duplicates and 0 missing values in the Bronze layer.

2. CLASSIFICATION: a Spark MLlib Random Forest predicts whether a user will reach their personalised
   step goal TOMORROW with accuracy {accuracy_spark:.2%}, precision {precision_spark:.2%}, recall {recall_spark:.2%},
   F1 {f1_spark:.2%} and ROC-AUC {roc_auc:.2%} on {N:,} held-out test days (majority baseline {majority_share:.2%}).
   Under the stricter chronological split it reaches ROC-AUC {cr['ROC-AUC']:.2%} - lower because the test
   months are a seasonal low-activity period not seen in training.

3. CLUSTERING: K-Means on standardised daily behaviour found K = {BEST_K} (best silhouette
   {k_eval['Silhouette Score'].max():.4f}). The groups differ mainly in session length and calories:
   '{cluster_label[best_cluster]}' average {profile.loc[best_cluster, 'active_minutes']:.1f} active minutes and
   {profile.loc[best_cluster, 'calories_burned']:.0f} kcal vs {profile.loc[order[0], 'active_minutes']:.1f} min and
   {profile.loc[order[0], 'calories_burned']:.0f} kcal for '{cluster_label[order[0]]}'.

4. PERSONALISATION: per-user goals (Spark groupBy/agg), next-day goal probabilities (Random Forest) and
   each user's mix of day types (K-Means) give user-specific, explainable insights that the dashboard and
   recommendation engine can act on.''')
""")

md(r"""
**Limitations (stated honestly):**
* The data is a public Kaggle dataset. `max_heart_rate` and `sleep_quality_score` are modelled columns.
* Spark runs in local mode. HDFS is not deployed; storage is HDFS-style partitioned Parquet.
* The 70/15/15 split is record-level. The chronological split (§6.12) is the stricter estimate.
* The silhouette scores indicate moderately separated clusters, not sharply distinct groups.
* `is_rest_day` is constant in this dataset, so it carries no information.
""")

code(r"""
spark.stop()
print("Spark session stopped. Evidence files:")
for f in sorted(EVIDENCE.iterdir()):
    print("  ", f.name)
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                  "language_info": {"name": "python"}}
nbf.write(nb, "FitPulse_Faculty_Demo.ipynb")
print(f"Wrote FitPulse_Faculty_Demo.ipynb with {len(cells)} cells")
