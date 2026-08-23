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

Run with:  python3 etl/spark_etl.py
(Needs JAVA_HOME set to a JDK 11/17 — see README.md "Environment setup".)
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

RAW_PATH = "data/raw/fitpulse_raw.csv"
SILVER_PATH = "data/processed/fitpulse_silver"

DAILY_STEP_GOAL_STRETCH = 1.10     # personal goal = 10% above the user's own historical average
DAILY_CALORIE_GOAL_STRETCH = 1.10


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("FitPulse-ETL")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")   # small dataset -> fewer shuffle partitions than the 200 default
        .config("spark.driver.memory", "2g")
        .config("spark.driver.host", "127.0.0.1")      # avoids local hostname-resolution hangs on macOS
        .getOrCreate()
    )


def main():
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

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

    print("[7/7] Writing Silver layer as partitioned Parquet (HDFS-style storage)")
    # Partitioning by month means any downstream query filtering on month only
    # reads the matching partition's files (partition pruning) — the same
    # benefit a real HDFS + Hive-partitioned table gives at far larger scale.
    (
        df.write.mode("overwrite")
        .partitionBy("month")
        .parquet(SILVER_PATH)
    )

    final_count = df.count()
    print("\n--- Summary ---")
    print(f"Bronze rows read      : {raw_count:,}")
    print(f"Rows after cleaning   : {clean_count:,} ({raw_count - clean_count:,} dropped)")
    print(f"Silver rows written   : {final_count:,}")
    print(f"Silver columns        : {len(df.columns)}")
    print(f"Users                 : {df.select('user_id').distinct().count()}")
    print(f"Written to            : {SILVER_PATH}/ (partitioned by month)")

    spark.stop()


if __name__ == "__main__":
    main()
