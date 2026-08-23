"""
FitPulse - Generate a sample wearable-export CSV for a brand-new user
========================================================================
This is the file handed to a freshly REGISTERED user (no history in the
system yet) so they can test the "upload my wearable export" path without
needing a real device. It is NOT part of the training population (user_id
999001 doesn't exist in data/raw/fitpulse_raw.csv) — it simulates what a
new user's own 45-day Fitbit/Google Fit export might look like.

Uses the exact same generation logic as data/prepare_raw_dataset.py so the
values are physiologically consistent with the rest of the project.

Run with:  python3 data/generate_sample_upload_csv.py
"""

import numpy as np
import pandas as pd

OUT = "data/sample_upload_for_new_user.csv"
NEW_USER_ID = 999001
N_DAYS = 45
SEED = 7

MET_TABLE = {
    "Walking": {"Low": 3.0, "Medium": 3.8, "High": 5.0},
    "Running": {"Low": 7.0, "Medium": 9.8, "High": 12.8},
    "Cycling": {"Low": 4.0, "Medium": 6.8, "High": 10.0},
    "Yoga": {"Low": 2.5, "Medium": 3.0, "High": 4.0},
}
STRIDE_MULT = {"Low": 0.413, "Medium": 0.45, "High": 0.50}


def main():
    rng = np.random.default_rng(SEED)
    dates = pd.date_range("2025-06-01", periods=N_DAYS, freq="D")

    age, gender, height_cm, weight_kg = 29, "F", 165.0, 62.0
    activities = rng.choice(list(MET_TABLE.keys()), size=N_DAYS, p=[0.4, 0.2, 0.25, 0.15])
    intensities = rng.choice(["Low", "Medium", "High"], size=N_DAYS, p=[0.35, 0.45, 0.20])

    rows = []
    for date, activity, intensity in zip(dates, activities, intensities):
        duration = int(rng.integers(20, 90))
        met = MET_TABLE[activity][intensity]
        calories = round(met * weight_kg * (duration / 60), 1)
        steps = int(rng.normal(7800, 1800))
        steps = max(2000, steps)
        stride_m = height_cm / 100 * STRIDE_MULT[intensity]
        distance_km = round(steps * stride_m / 1000, 2)
        resting_hr = round(rng.normal(64, 4), 1)
        avg_hr = int(rng.normal({"Low": 105, "Medium": 128, "High": 150}[intensity], 8))
        max_hr = min(220 - age, avg_hr + {"Low": 8, "Medium": 15, "High": 24}[intensity] + rng.normal(0, 3))
        sleep_minutes = int(rng.normal(430, 45))
        stress = int(rng.integers(1, 9))
        hydration = round(rng.uniform(1.5, 3.2), 1)
        sleep_quality = round(np.clip(
            100 - abs(sleep_minutes / 60 - 8) * 9 - stress * 3.2 - max(0, resting_hr - 60) * 0.6 + rng.normal(0, 4),
            0, 100,
        ), 1)
        sedentary = max(0, 1440 - sleep_minutes - duration)

        rows.append({
            "user_id": NEW_USER_ID, "date": date.strftime("%Y-%m-%d"), "steps": steps,
            "calories_burned": calories, "distance_km": distance_km, "active_minutes": duration,
            "sedentary_minutes": sedentary, "resting_heart_rate": resting_hr, "avg_heart_rate": avg_hr,
            "max_heart_rate": int(max_hr), "sleep_minutes": sleep_minutes, "sleep_quality_score": sleep_quality,
            "activity_type": activity, "intensity": intensity, "stress_level": stress, "hydration_level": hydration,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT}: {len(df)} rows for a simulated new user (user_id={NEW_USER_ID})")
    print("Give this file to a freshly registered user to test the CSV-upload path.")


if __name__ == "__main__":
    main()
