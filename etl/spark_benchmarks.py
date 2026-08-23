"""
FitPulse - Spark SQL Percentile Benchmarking (Silver -> Gold)
================================================================
Demonstrates the Hive/SQL-on-big-data pattern: the Silver Parquet layer is
registered as a Spark SQL temp view and queried with plain SQL (not
DataFrame method calls) to compute each user's percentile rank against a
cohort of similar users (same age group + gender).

IMPORTANT: this is explicitly NOT a machine learning model — it is a
statistical computation (percentile rank within a cohort), run once here as
a batch job. If asked in the viva "which of your 6 predictions is ML and
which isn't", this is the one that isn't.

Output: data/population_stats/user_percentiles.parquet — a small Gold table
(one row per user) that the dashboard looks up by user_id at request time,
instead of ever touching the full Silver dataset live.
"""

from pyspark.sql import SparkSession

SILVER_PATH = "data/processed/fitpulse_silver"
OUT_PATH = "data/population_stats/user_percentiles.parquet"


def main():
    spark = (
        SparkSession.builder
        .appName("FitPulse-Benchmarks")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("[1/3] Loading Silver layer and registering as a SQL temp view")
    silver = spark.read.parquet(SILVER_PATH)
    silver.createOrReplaceTempView("fitpulse_silver")

    # --- age_group bucket (needed to define the benchmarking cohort) ---
    spark.sql(
        """
        CREATE OR REPLACE TEMP VIEW fitpulse_with_cohort AS
        SELECT *,
            CASE
                WHEN age < 25 THEN '18-24'
                WHEN age < 35 THEN '25-34'
                WHEN age < 45 THEN '35-44'
                WHEN age < 55 THEN '45-54'
                ELSE '55-64'
            END AS age_group
        FROM fitpulse_silver
        """
    )

    print("[2/3] Per-user averages (Spark SQL GROUP BY = the Reduce step)")
    user_avgs = spark.sql(
        """
        SELECT
            user_id,
            ANY_VALUE(age_group) AS age_group,
            ANY_VALUE(gender)    AS gender,
            AVG(steps)           AS avg_steps,
            AVG(calories_burned) AS avg_calories_burned,
            AVG(sleep_quality_score) AS avg_sleep_quality,
            AVG(goal_achieved) * 100 AS goal_achievement_rate_pct
        FROM fitpulse_with_cohort
        GROUP BY user_id
        """
    )
    user_avgs.createOrReplaceTempView("user_avgs")

    print("[3/3] Percentile rank within each (age_group, gender) cohort — Spark SQL window functions")
    # PERCENT_RANK() OVER (PARTITION BY cohort ORDER BY metric) is the SQL-native
    # way to compute "what fraction of my cohort do I outperform" — exactly the
    # percentile benchmarking the dashboard needs, expressed as plain SQL.
    percentiles = spark.sql(
        """
        SELECT
            user_id,
            age_group,
            gender,
            avg_steps,
            avg_calories_burned,
            avg_sleep_quality,
            goal_achievement_rate_pct,
            ROUND(PERCENT_RANK() OVER (PARTITION BY age_group, gender ORDER BY avg_steps) * 100, 1)
                AS steps_percentile,
            ROUND(PERCENT_RANK() OVER (PARTITION BY age_group, gender ORDER BY avg_calories_burned) * 100, 1)
                AS calories_percentile,
            ROUND(PERCENT_RANK() OVER (PARTITION BY age_group, gender ORDER BY avg_sleep_quality) * 100, 1)
                AS sleep_quality_percentile
        FROM user_avgs
        """
    )

    percentiles.write.mode("overwrite").parquet(OUT_PATH)
    n = percentiles.count()
    print(f"\nWrote {n} user percentile rows to {OUT_PATH}")
    percentiles.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
