"""
FitPulse - Power BI-ready data export  (PREPARATION for a Power BI dashboard; this script does not create a .pbix)
==================================================================================================================
Reads the LOCAL Silver Parquet (proved row-for-row identical to the HDFS Silver by scripts/verify_hdfs.py), joins the
measured model outputs, and writes flat CSV tables to powerbi/data/ for Power BI Desktop's Text/CSV connector.

    python powerbi/export_powerbi_data.py

Prerequisites (they produce the joined model outputs):
    python models/train_calorie_regression.py      -> faculty_evidence/regression_predictions.csv

Tables
    fact_daily.csv       one row per user-day (100,122 rows): activity, calories actual+predicted, sleep, goal flags
    dim_user.csv         one row per user (437): age group, gender, days logged, average steps and calories
    monthly_summary.csv  month x activity_type roll-up
    model_metrics.csv    the calorie Linear Regression metrics (measured)
Privacy: only the dataset's anonymous numeric user_id is exported (no names, no registered-account data).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "data"
EV = ROOT / "faculty_evidence"


def age_group(a):
    return np.select([a < 25, a < 35, a < 45, a < 55, a < 65], ["18-24", "25-34", "35-44", "45-54", "55-64"], "65+")


def main():
    OUT.mkdir(exist_ok=True)
    s = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
    s["date"] = pd.to_datetime(s["date"])
    pred = pd.read_csv(EV / "regression_predictions.csv", parse_dates=["date"])[["user_id", "date", "predicted_calories", "split"]]

    f = s.merge(pred, on=["user_id", "date"], how="left")
    f["age_group"] = age_group(f["age"])
    f["sleep_hours"] = f["sleep_minutes"] / 60.0
    f["calorie_error"] = f["calories_burned"] - f["predicted_calories"]
    f["month"] = f["date"].dt.strftime("%Y-%m")
    fact = f[["user_id", "date", "month", "day_of_week", "activity_type", "intensity", "steps", "distance_km", "calories_burned",
              "predicted_calories", "calorie_error", "split", "active_minutes", "sedentary_minutes", "sleep_hours",
              "sleep_quality_score", "avg_heart_rate", "daily_step_goal", "goal_achieved", "daily_calorie_goal",
              "calorie_goal_achieved", "age_group", "gender"]].rename(columns={"split": "model_split"})
    fact["date"] = fact["date"].dt.strftime("%Y-%m-%d")
    fact.insert(0, "row_id", np.arange(1, len(fact) + 1))          # unique key: one scatter point per user-day
    # 50-kcal histogram bin of the prediction error (actual - predicted) for the error-distribution visual
    fact["error_bin_kcal"] = (np.floor(fact["calorie_error"] / 50.0) * 50).astype(int)
    fact.round(3).to_csv(OUT / "fact_daily.csv", index=False)

    dim = (f.groupby("user_id").agg(age=("age", "first"), age_group=("age_group", "first"), gender=("gender", "first"),
                                    days=("date", "count"), avg_steps=("steps", "mean"), avg_calories=("calories_burned", "mean"))
           .reset_index())
    dim.round(3).to_csv(OUT / "dim_user.csv", index=False)

    m = (f.groupby(["month", "activity_type"]).agg(days=("date", "count"), users=("user_id", "nunique"), total_steps=("steps", "sum"),
                                                   avg_steps=("steps", "mean"), avg_calories=("calories_burned", "mean"),
                                                   avg_active_min=("active_minutes", "mean"), avg_sedentary_min=("sedentary_minutes", "mean"),
                                                   avg_sleep_hours=("sleep_hours", "mean"), avg_sleep_quality=("sleep_quality_score", "mean"),
                                                   goal_rate=("goal_achieved", "mean")).reset_index())
    m.round(3).to_csv(OUT / "monthly_summary.csv", index=False)

    # calendar table for time intelligence (marked as the date table in the model)
    cal = pd.DataFrame({"Date": pd.date_range("2024-01-01", "2024-12-31")})
    cal["Year"] = cal.Date.dt.year
    cal["MonthNumber"] = cal.Date.dt.month
    cal["Month"] = cal.Date.dt.strftime("%b")
    cal["YearMonth"] = cal.Date.dt.strftime("%Y-%m")
    cal["DayOfWeek"] = cal.Date.dt.day_name()
    cal["DayOfWeekNumber"] = cal.Date.dt.dayofweek + 1
    cal["Date"] = cal.Date.dt.strftime("%Y-%m-%d")
    cal.to_csv(OUT / "dim_date.csv", index=False)

    cfg = json.loads((ROOT / "models" / "artifacts" / "calorie_linreg_config.json").read_text(encoding="utf-8"))
    rows = [("Linear Regression (test)", k, v) for k, v in cfg["test_metrics"].items()] + \
           [("Baseline: training mean (test)", k, v) for k, v in cfg["baseline_mean_test_metrics"].items()]
    pd.DataFrame(rows, columns=["model", "metric", "value"]).to_csv(OUT / "model_metrics.csv", index=False)
    for p in sorted(OUT.glob("*.csv")):
        print(f"{p.name:22s} {sum(1 for _ in open(p, encoding='utf-8')) - 1:>8,} rows  {p.stat().st_size/1024:>8,.0f} KB")


if __name__ == "__main__":
    main()
