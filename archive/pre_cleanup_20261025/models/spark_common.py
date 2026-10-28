"""
Shared helpers for the Spark MLlib model scripts (supervised experiments E1-E5 and the calorie regression; the archived K-Means scripts in archive/kmeans/ use it too).
Reuses etl/storage.py so every script has the same explicit storage modes as the ETL:

    --storage local|hdfs  --hdfs-uri hdfs://localhost:9000  [--silver <path>]

The Silver dataset is the single source (it is a superset of the raw columns), so no ETL logic is duplicated.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
import storage  # noqa: E402

EVIDENCE = ROOT / "faculty_evidence"
ARTIFACTS = ROOT / "models" / "artifacts"
SEED = 42


def add_storage_args(ap: argparse.ArgumentParser):
    ap.add_argument("--storage", choices=["local", "hdfs"], default=None)
    ap.add_argument("--hdfs-uri", default=None)
    ap.add_argument("--silver", default=None, help="Silver Parquet dir/URI (default depends on storage mode)")
    ap.add_argument("--out", default=None, help="evidence output directory (default faculty_evidence/)")


def open_silver(args, app_name):
    """Returns (spark, silver_df, cfg). Exits with code 2 if HDFS mode is selected but unavailable."""
    from pyspark.sql import SparkSession
    try:
        cfg = storage.resolve(args.storage, args.hdfs_uri, output_path=args.silver)
        storage.require_hdfs(cfg)
    except storage.HdfsUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    b = (SparkSession.builder.appName(app_name).master("local[*]")
         .config("spark.sql.shuffle.partitions", "8").config("spark.driver.memory", os.environ.get("FITPULSE_DRIVER_MEMORY", "2g"))
         .config("spark.driver.host", "127.0.0.1"))
    for k, v in storage.spark_hadoop_conf(cfg).items():
        b = b.config(k, v)
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    print("=" * 70)
    print(f"STORAGE MODE : {cfg.label()}")
    print(f"Silver source: {cfg.output_path}")
    silver = spark.read.parquet(cfg.output_path)
    print(f"Rows / columns: {silver.count():,} / {len(silver.columns)}")
    print("=" * 70)
    return spark, silver, cfg


def out_dir(args) -> Path:
    d = Path(args.out) if args.out else EVIDENCE
    d.mkdir(parents=True, exist_ok=True)
    return d
