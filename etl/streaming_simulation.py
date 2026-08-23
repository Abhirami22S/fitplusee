"""
FitPulse - Streaming Simulation (OPTIONAL, simplified)
=========================================================
This is explicitly a SIMPLIFIED SIMULATION of a streaming pipeline, not a
real one. A production version of this would use Kafka (or a wearable's
push webhook) as the message queue and Spark Structured Streaming to
process each micro-batch as it arrives. We don't have a live wearable
device or a Kafka cluster in a student environment, so this script
reproduces the *shape* of that pipeline locally:

  1. `simulate_incoming_batch()` mimics a wearable syncing a new day of
     data for a few random users — i.e. what would otherwise arrive as a
     Kafka message — and drops it as a new small CSV file into
     data/streaming_inbox/ (our stand-in for a Kafka topic's landing zone).
  2. `process_new_batches()` uses Spark's `readStream`/`writeStream` API
     in "trigger once" mode to pick up ONLY the new files since the last
     run and append them to the Silver table — this is genuinely Spark
     Structured Streaming, just triggered manually instead of running
     continuously, which is a standard and realistic way to demo streaming
     without needing a long-lived cluster.

Run with:  python3 etl/streaming_simulation.py
"""

import random
import time
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, DateType

INBOX = Path("data/streaming_inbox")
SILVER_PATH = "data/processed/fitpulse_silver_streamed"
RAW_PATH = "data/raw/fitpulse_raw.csv"

SCHEMA = StructType([
    StructField("user_id", IntegerType()),
    StructField("date", DateType()),
    StructField("steps", IntegerType()),
    StructField("calories_burned", DoubleType()),
    StructField("distance_km", DoubleType()),
    StructField("active_minutes", IntegerType()),
    StructField("sedentary_minutes", IntegerType()),
    StructField("resting_heart_rate", DoubleType()),
    StructField("avg_heart_rate", IntegerType()),
    StructField("max_heart_rate", IntegerType()),
    StructField("sleep_minutes", IntegerType()),
    StructField("sleep_quality_score", DoubleType()),
    StructField("activity_type", StringType()),
    StructField("intensity", StringType()),
])


def simulate_incoming_batch(n_users: int = 5):
    """Mimic a small batch of wearables syncing a new day's data (stand-in for a Kafka message)."""
    base = pd.read_csv(RAW_PATH)
    sample = base.sample(n=n_users, random_state=random.randint(0, 99999))
    sample = sample[[f.name for f in SCHEMA.fields]]
    INBOX.mkdir(parents=True, exist_ok=True)
    fname = INBOX / f"batch_{time.time_ns()}.csv"
    sample.to_csv(fname, index=False)
    print(f"[simulate] wrote incoming batch: {fname} ({len(sample)} rows)")
    return fname


def process_new_batches():
    """Structured Streaming, trigger-once mode: pick up any files in the inbox not yet processed."""
    spark = (
        SparkSession.builder.appName("FitPulse-Streaming-Sim").master("local[*]")
        .config("spark.driver.host", "127.0.0.1").config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    stream_df = (
        spark.readStream.schema(SCHEMA).option("header", True).csv(str(INBOX))
    )

    query = (
        stream_df.writeStream
        .format("parquet")
        .option("path", SILVER_PATH)
        .option("checkpointLocation", str(INBOX / "_checkpoint"))
        .trigger(availableNow=True)   # process everything currently available, then stop (no live loop)
        .start()
    )
    query.awaitTermination()

    result = spark.read.parquet(SILVER_PATH)
    print(f"[process] streamed Silver table now has {result.count()} rows total")
    spark.stop()


if __name__ == "__main__":
    print("=== FitPulse streaming simulation (simplified — see module docstring) ===")
    for _ in range(3):
        simulate_incoming_batch()
    process_new_batches()
