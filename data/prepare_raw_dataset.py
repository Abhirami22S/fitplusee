"""
FitPulse - Raw dataset preparation (run ONCE, outside the big-data pipeline)
-----------------------------------------------------------------------------
This script is NOT part of the Spark ETL. It exists only to reshape our
source (a Kaggle health/fitness dataset with a different column schema) into
the column schema a wearable export would actually have — the same role
a Fitbit/Google Fit CSV export already plays before ANY big-data processing
touches it. Everything downstream (etl/, models/) starts from the output of
this script, i.e. `data/raw/fitpulse_raw.csv` — that file is the Bronze /
HDFS landing-zone layer.

Source: Kaggle dataset jijagallery/fitlife-health-and-fitness-tracking-dataset
(687,701 rows / 3,000 participants). We sample 437 participants and keep each
one's FULL yearly time series intact (~100,000 rows total) so per-user
rolling/lag features computed later in Spark are meaningful.

Derivations applied here (simple unit conversions / well-known formulas —
NOT feature engineering, which is the Spark ETL's job):
  - distance_km   : steps x stride length. Stride length uses the standard
                    biomechanics approximation stride_m ~= height_cm x 0.413/100
                    for walking-pace activity, scaled up for higher-intensity
                    activity types (running lengthens stride).
  - active_minutes: the logged session duration for that day.
  - sedentary_minutes: remaining minutes in the day not spent sleeping or
                    active (1440 - sleep_minutes - active_minutes), floored at 0.
  - max_heart_rate: modelled as the average heart rate plus an intensity-
                    scaled margin, capped at the age-predicted maximum heart
                    rate (220 - age), a standard exercise-physiology formula.
  - sleep_minutes : hours_sleep x 60.
  - sleep_quality_score (0-100): a deterministic formula combining sleep
                    duration (closer to the 8h ideal = better), stress level,
                    and resting heart rate (a fitness proxy) — this
                    intentionally builds in a REAL, learnable relationship
                    between daytime activity/stress and sleep quality, which
                    Model 3 (Sleep Quality Prediction) depends on.

Per-user personalized daily_step_goal / daily_calorie_goal are deliberately
NOT set here — they are computed in etl/spark_etl.py via a Spark groupBy/agg
over each user's own history, so that computation is visibly part of the
big-data pipeline (see the Map/Reduce comments there).
"""

import os

import numpy as np
import pandas as pd

SRC = "/Users/praj1n/.cache/kagglehub/datasets/jijagallery/fitlife-health-and-fitness-tracking-dataset/versions/1/health_fitness_dataset.csv"
KAGGLE_DATASET = "jijagallery/fitlife-health-and-fitness-tracking-dataset/versions/1"
OUT = "data/raw/fitpulse_raw.csv"
N_PARTICIPANTS = 437  # ~229 rows/participant x 437 ~= 100,000 rows
SEED = 42

MET_TABLE = {
    "Walking":         {"Low": 3.0, "Medium": 3.8, "High": 5.0},
    "Running":         {"Low": 7.0, "Medium": 9.8, "High": 12.8},
    "Cycling":         {"Low": 4.0, "Medium": 6.8, "High": 10.0},
    "Swimming":        {"Low": 5.0, "Medium": 7.0, "High": 9.8},
    "Yoga":            {"Low": 2.5, "Medium": 3.0, "High": 4.0},
    "Weight Training": {"Low": 3.0, "Medium": 5.0, "High": 6.0},
    "HIIT":            {"Low": 6.0, "Medium": 8.0, "High": 12.0},
    "Dancing":         {"Low": 3.0, "Medium": 4.8, "High": 6.5},
    "Basketball":      {"Low": 4.5, "Medium": 6.5, "High": 8.0},
    "Tennis":          {"Low": 5.0, "Medium": 7.0, "High": 8.0},
}
STRIDE_MULT = {"Low": 0.413, "Medium": 0.45, "High": 0.50}  # x height_cm/100 = stride metres


def resolve_source() -> str:
    # The original path above is the author's local kagglehub cache. On any other
    # machine, download the same Kaggle dataset (same version) via kagglehub.
    if os.path.exists(SRC):
        return SRC
    import kagglehub
    return os.path.join(kagglehub.dataset_download(KAGGLE_DATASET), "health_fitness_dataset.csv")


def main():
    rng = np.random.default_rng(SEED)
    src = resolve_source()
    print(f"Source: {src}")
    df = pd.read_csv(src)

    ids = pd.Series(df.participant_id.unique())
    sampled_ids = ids.sample(n=N_PARTICIPANTS, random_state=SEED)
    df = df[df.participant_id.isin(sampled_ids)].copy()

    # --- basic cleaning (dedupe / drop rows missing essentials) ---
    df = df.drop_duplicates()
    df = df.dropna(subset=["participant_id", "date", "activity_type", "duration_minutes"])
    df = df[
        df.age.between(15, 100) & df.height_cm.between(120, 220) & df.weight_kg.between(30, 200)
        & df.duration_minutes.between(0, 300) & df.avg_heart_rate.between(40, 220)
        & df.resting_heart_rate.between(35, 120) & df.hours_sleep.between(0, 14)
        & df.daily_steps.between(0, 60000)
    ]
    df["health_condition"] = df["health_condition"].fillna("None")

    # --- calories_burned: recompute via MET formula (raw column was ~30x too low) ---
    met = df.apply(lambda r: MET_TABLE.get(r.activity_type, {}).get(r.intensity, 5.0), axis=1)
    df["calories_burned"] = (met * df["weight_kg"] * (df["duration_minutes"] / 60)).round(1)

    # --- distance_km from steps + height-based stride length ---
    stride_m = df["height_cm"] / 100 * df["intensity"].map(STRIDE_MULT)
    df["distance_km"] = (df["daily_steps"] * stride_m / 1000).round(2)

    # --- active / sedentary minutes ---
    df["active_minutes"] = df["duration_minutes"]
    df["sleep_minutes"] = (df["hours_sleep"] * 60).round(0).astype(int)
    df["sedentary_minutes"] = (1440 - df["sleep_minutes"] - df["active_minutes"]).clip(lower=0).astype(int)

    # --- max_heart_rate: avg + intensity-scaled margin, capped at age-predicted max ---
    intensity_margin = df["intensity"].map({"Low": 8, "Medium": 15, "High": 24})
    noise = rng.normal(0, 3, size=len(df))
    theoretical_max = 220 - df["age"]
    df["max_heart_rate"] = np.minimum(
        theoretical_max, df["avg_heart_rate"] + intensity_margin + noise
    ).round(0).astype(int)
    df["max_heart_rate"] = np.maximum(df["max_heart_rate"], df["avg_heart_rate"])  # never below avg

    # --- sleep_quality_score: deterministic formula w/ built-in real relationships ---
    duration_penalty = (df["hours_sleep"] - 8).abs() * 9
    stress_penalty = df["stress_level"] * 3.2
    hr_penalty = (df["resting_heart_rate"] - 60).clip(lower=0) * 0.6
    score_noise = rng.normal(0, 4, size=len(df))
    df["sleep_quality_score"] = (100 - duration_penalty - stress_penalty - hr_penalty + score_noise).clip(0, 100).round(1)

    df = df.rename(columns={"participant_id": "user_id", "daily_steps": "steps"})

    cols = [
        "user_id", "date", "steps", "calories_burned", "distance_km", "active_minutes",
        "sedentary_minutes", "resting_heart_rate", "avg_heart_rate", "max_heart_rate",
        "sleep_minutes", "sleep_quality_score", "activity_type", "intensity",
        "age", "gender", "height_cm", "weight_kg", "bmi", "health_condition",
        "smoking_status", "stress_level", "hydration_level",
    ]
    df = df[cols].sort_values(["user_id", "date"])

    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT}: {len(df):,} rows, {df.shape[1]} columns, {df.user_id.nunique()} users")
    print(f"Date range: {df.date.min()} to {df.date.max()}")


if __name__ == "__main__":
    main()
