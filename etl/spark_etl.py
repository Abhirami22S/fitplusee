"""
FitPulse - Spark Batch ETL (Bronze -> Silver)
================================================
This is the project's core "big data" processing script. It reads the raw
wearable-export CSV (Bronze / HDFS landing-zone layer) with Apache Spark,
cleans it, engineers rolling/lag features, computes personalized goals per
user, and writes the result as a partitioned Parquet dataset — our
HDFS-style storage layer standing in for a real distributed filesystem
(see the "HDFS-style storage" note below).

Every `groupBy().agg()` / window operation below is commented with its
Map step (the per-record/per-partition transformation Spark applies
independently and in parallel) and Reduce step (the aggregation that
combines those results across a group) — this is the MapReduce pattern,
and it is what to point to if asked "where is MapReduce in this project?"
in the viva.

Storage modes (explicit, never silently mixed):
    python etl/spark_etl.py                       # LOCAL Parquet (original behaviour, fallback)
    python etl/spark_etl.py --storage hdfs --hdfs-uri hdfs://localhost:9000
                                                  # reads Bronze from HDFS, writes Silver to HDFS
In HDFS mode the job aborts (exit code 2) if the NameNode is unreachable; it never
falls back to local disk. Output goes to a staging directory and is swapped in only
after the write and a read-back row-count check succeed.

(Needs JAVA_HOME set to a JDK 11/17 — see README.md "Environment setup".)
"""

import argparse
import json
import sys
import time

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

import storage

DAILY_STEP_GOAL_STRETCH = 1.10     # personal goal = 10% above the user's own historical average
DAILY_CALORIE_GOAL_STRETCH = 1.10


def build_spark(extra_conf=None) -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("FitPulse-ETL")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")   # small dataset -> fewer shuffle partitions than the 200 default
        .config("spark.driver.memory", "2g")
        .config("spark.driver.host", "127.0.0.1")      # avoids local hostname-resolution hangs on macOS
    )
    for k, v in (extra_conf or {}).items():
        builder = builder.config(k, v)
    return builder.getOrCreate()


def parse_args():
    ap = argparse.ArgumentParser(description="FitPulse Spark ETL (Bronze -> Silver)")
    ap.add_argument("--storage", choices=["local", "hdfs"], default=None,
                    help="storage backend (default: env FITPULSE_STORAGE, else local)")
    ap.add_argument("--hdfs-uri", default=None, help="e.g. hdfs://localhost:9000 (default: env FITPULSE_HDFS_URI)")
    ap.add_argument("--input", default=None, help="Bronze CSV path (HDFS path/URI in hdfs mode)")
    ap.add_argument("--output", default=None, help="Silver Parquet dir (HDFS path/URI in hdfs mode)")
    ap.add_argument("--report", default=None, help="write a JSON run report to this file")
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        cfg = storage.resolve(args.storage, args.hdfs_uri, args.input, args.output)
        storage.require_hdfs(cfg)
    except storage.HdfsUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    print("=" * 70)
    print(f"STORAGE MODE : {cfg.label()}")
    print(f"Bronze input : {cfg.input_path}")
    print(f"Silver output: {cfg.output_path}")
    print("=" * 70)

    spark = build_spark(storage.spark_hadoop_conf(cfg))
    spark.sparkContext.setLogLevel("WARN")
    try:
        storage.verify_hdfs_reachable(spark, cfg)
        if not storage.path_exists(spark, cfg.input_path):
            raise FileNotFoundError(f"Bronze input not found: {cfg.input_path}")
        run_etl(spark, cfg, args.report)
    except storage.HdfsUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        spark.stop()
        sys.exit(2)
    spark.stop()


def run_etl(spark, cfg, report_path=None):
    t0 = time.time()
    RAW_PATH, SILVER_PATH = cfg.input_path, cfg.output_path

    print("[1/7] Reading Bronze layer (raw CSV) into a Spark DataFrame")
    df = spark.read.csv(RAW_PATH, header=True, inferSchema=True)
    raw_count = df.count()

    print("[2/7] Cleaning & validation")
    # MAP step: each row is independently checked against physiological bounds
    # and either kept or dropped — no cross-row communication needed yet.
    df = df.dropDuplicates()
    df = df.dropna(subset=["user_id", "date", "activity_type", "steps"])
    df = df.filter(
        (F.col("age").between(15, 100))
        & (F.col("resting_heart_rate").between(35, 120))
        & (F.col("avg_heart_rate").between(40, 220))
        & (F.col("steps").between(0, 60000))
        & (F.col("sleep_minutes").between(0, 840))
    )
    df = df.withColumn("health_condition", F.coalesce(F.col("health_condition"), F.lit("None")))
    df = df.withColumn("date", F.to_date("date"))
    clean_count = df.count()

    print("[3/7] Feature engineering — day-of-week, rest-day flag, month partition key")
    df = df.withColumn("day_of_week", F.date_format("date", "EEEE"))
    df = df.withColumn("month", F.date_format("date", "yyyy-MM"))
    # Any day where less than 15 minutes of activity was logged counts as a "rest day".
    df = df.withColumn("is_rest_day", (F.col("active_minutes") < 15).cast("int"))

    print("[4/7] Rolling averages & lag features (Spark Window functions)")
    # A Window PARTITIONed by user_id keeps each user's time series independent
    # (this is itself a Map-like partitioning step: Spark can compute every
    # user's window independently and in parallel), ORDERed by date so
    # `lag()` and the rolling frame are chronological within each partition.
    user_window = Window.partitionBy("user_id").orderBy("date")
    rolling_7d = user_window.rowsBetween(-6, 0)

    df = df.withColumn("steps_lag1", F.lag("steps", 1).over(user_window))
    df = df.withColumn("steps_lag2", F.lag("steps", 2).over(user_window))
    df = df.withColumn("steps_lag7", F.lag("steps", 7).over(user_window))
    df = df.withColumn("calories_lag1", F.lag("calories_burned", 1).over(user_window))
    df = df.withColumn("sleep_quality_lag1", F.lag("sleep_quality_score", 1).over(user_window))

    df = df.withColumn("steps_roll7_avg", F.avg("steps").over(rolling_7d))
    df = df.withColumn("calories_roll7_avg", F.avg("calories_burned").over(rolling_7d))
    df = df.withColumn("active_minutes_roll7_avg", F.avg("active_minutes").over(rolling_7d))
    df = df.withColumn("resting_hr_roll7_avg", F.avg("resting_heart_rate").over(rolling_7d))

    print("[5/7] Personalized goals — per-user MapReduce aggregation")
    # MAP step: emit (user_id, steps) and (user_id, calories_burned) pairs for
    # every row in the dataset (implicit — this is just the existing columns).
    # REDUCE step: groupBy(user_id).agg(avg(...)) combines every row belonging
    # to the same user into one summary value per user — the textbook
    # MapReduce shape (map over records, reduce-by-key to a per-key result).
    user_baseline = (
        df.groupBy("user_id")
        .agg(
            F.avg("steps").alias("user_avg_steps"),
            F.avg("calories_burned").alias("user_avg_calories"),
        )
    )
    user_baseline = user_baseline.withColumn(
        "daily_step_goal", F.round(F.col("user_avg_steps") * DAILY_STEP_GOAL_STRETCH, -2)
    ).withColumn(
        "daily_calorie_goal", F.round(F.col("user_avg_calories") * DAILY_CALORIE_GOAL_STRETCH, -1)
    ).select("user_id", "daily_step_goal", "daily_calorie_goal")

    # Broadcast join: user_baseline is tiny (one row per user), so Spark ships
    # it to every executor instead of shuffling the large fact table — the
    # standard big-data join optimization for a "small dimension x large fact" join.
    df = df.join(F.broadcast(user_baseline), on="user_id", how="left")

    print("[6/7] Deriving goal_achieved / calorie_goal_achieved labels")
    df = df.withColumn("goal_achieved", (F.col("steps") >= F.col("daily_step_goal")).cast("int"))
    df = df.withColumn(
        "calorie_goal_achieved", (F.col("calories_burned") >= F.col("daily_calorie_goal")).cast("int")
    )

    print(f"[7/7] Writing Silver layer as partitioned Parquet ({cfg.label()})")
    # Partitioning by month means any downstream query filtering on month only
    # reads the matching partition's files (partition pruning) — the same
    # benefit a real HDFS + Hive-partitioned table gives at far larger scale.
    # Written to a staging directory first, then swapped in (storage.staged_replace).
    staging = SILVER_PATH.rstrip("/") + f"._staging_{int(time.time())}"
    (
        df.write.mode("errorifexists")
        .partitionBy("month")
        .parquet(staging)
    )
    written = spark.read.parquet(staging).count()
    final_count = df.count()
    if written != final_count:
        raise RuntimeError(f"read-back check failed: staged {written:,} rows, expected {final_count:,}; "
                           f"existing Silver left untouched (staging kept at {staging})")
    storage.staged_replace(spark, staging, SILVER_PATH)
    readback = spark.read.parquet(SILVER_PATH).count()
    if readback != final_count:
        raise RuntimeError(f"post-swap read-back mismatch: {readback:,} != {final_count:,}")
    print("\n--- Summary ---")
    print(f"Bronze rows read      : {raw_count:,}")
    print(f"Rows after cleaning   : {clean_count:,} ({raw_count - clean_count:,} dropped)")
    print(f"Silver rows written   : {final_count:,}")
    print(f"Silver columns        : {len(df.columns)}")
    print(f"Users                 : {df.select('user_id').distinct().count()}")
    print(f"Read back from storage: {readback:,} rows (matches)")
    print(f"Written to            : {SILVER_PATH}/ (partitioned by month)")
    print(f"Storage mode used     : {cfg.mode.upper()}  [{cfg.label()}]")

    if report_path:
        report = {
            "storage_mode": cfg.mode, "hdfs_uri": cfg.hdfs_uri,
            "input_path": RAW_PATH, "output_path": SILVER_PATH,
            "bronze_rows": raw_count, "clean_rows": clean_count,
            "silver_rows_written": final_count, "silver_rows_read_back": readback,
            "silver_columns": len(df.columns), "elapsed_seconds": round(time.time() - t0, 1),
        }
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Run report            : {report_path}")


if __name__ == "__main__":
    main()
