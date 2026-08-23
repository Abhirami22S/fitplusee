"""
FitPulse - Load Gold/Silver outputs into SQLite (the dashboard's serving store)
==================================================================================
The dashboard never reads the Spark Parquet output directly at request time —
Spark's startup cost (JVM boot) is far too slow for an interactive app. Instead,
this script runs once after the ETL/benchmark jobs and loads their results into
a lightweight SQLite database with an index on `user_id`, so the dashboard's
per-user queries are indexed lookups, not full scans, and touch only:
  (a) the selected user's own rows, and
  (b) the small precomputed population_percentiles table
— never the full 100k-row dataset, matching the brief's storage requirement.

Run with:  python3 etl/load_to_sqlite.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

SILVER_PATH = "data/processed/fitpulse_silver"
PERCENTILES_PATH = "data/population_stats/user_percentiles.parquet"
DB_PATH = "dashboard/fitpulse.db"


def main():
    print("[1/3] Loading Silver + Gold Parquet outputs")
    silver = pd.read_parquet(SILVER_PATH)
    percentiles = pd.read_parquet(PERCENTILES_PATH)

    Path("dashboard").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    print("[2/3] Writing tables")
    silver.to_sql("user_daily_metrics", conn, if_exists="replace", index=False)
    percentiles.to_sql("population_percentiles", conn, if_exists="replace", index=False)

    print("[3/3] Creating indexes for fast per-user lookup")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_date ON user_daily_metrics(user_id, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pct_user ON population_percentiles(user_id)")
    conn.commit()

    n_rows = conn.execute("SELECT COUNT(*) FROM user_daily_metrics").fetchone()[0]
    n_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_daily_metrics").fetchone()[0]
    print(f"\nWrote {n_rows:,} rows across {n_users} users to {DB_PATH}")
    print("Tables: user_daily_metrics (indexed on user_id, date), population_percentiles (indexed on user_id)")

    conn.close()


if __name__ == "__main__":
    main()
