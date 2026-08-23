"""
FitPulse - Model 2: 7-Day Activity Trend Forecast
====================================================
Business question this answers: "How many steps/calories should I expect
over the next week, based on my recent pattern?" — lets a user plan ahead
(e.g. schedule a rest day, or know they need a push to hit a weekly target).

Algorithm: lag-feature-based Gradient Boosting Regressor (scikit-learn's
HistGradientBoostingRegressor — the same algorithm family as XGBoost/
LightGBM, histogram-based gradient boosting). The brief allows Prophet OR a
lag-feature GBM for this task; we use the GBM route since it reuses the
same lag/rolling features already computed by the Spark ETL (steps_lag1/2/7,
steps_roll7_avg, ...) rather than pulling in a separate forecasting library,
and is just as easy to explain: "predict tomorrow from the last few days,
then feed that prediction back in as the new 'yesterday' to predict the day
after, seven times."

Evaluation: for each user, we hold out their last 7 days, forecast them
recursively from the 8th-to-last day, and compute MAE against the actual
values — a genuine walk-forward validation, not an in-sample fit.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

SILVER_PATH = "data/processed/fitpulse_silver"
FORECAST_HORIZON = 7

FEATURES = [
    "steps_lag1", "steps_lag2", "steps_lag7", "steps_roll7_avg",
    "active_minutes_roll7_avg", "resting_hr_roll7_avg", "month_sin", "month_cos",
]


def add_month_cyc(df):
    m = pd.to_datetime(df["date"]).dt.month
    df["month_sin"] = np.sin(2 * np.pi * m / 12)
    df["month_cos"] = np.cos(2 * np.pi * m / 12)
    return df


def build_training_table(df):
    """One row per (user, day) with lag/rolling features -> next day's steps as target."""
    df = df.sort_values(["user_id", "date"]).copy()
    df["target_next_day_steps"] = df.groupby("user_id")["steps"].shift(-1)
    return df.dropna(subset=FEATURES + ["target_next_day_steps"])


def recursive_forecast(model, history: pd.DataFrame, horizon: int) -> list[float]:
    """Forecast `horizon` days ahead by feeding each prediction back in as the new lag-1."""
    hist = history.copy().reset_index(drop=True)
    preds = []
    for step in range(horizon):
        last = hist.iloc[-1]
        next_date = pd.to_datetime(last["date"]) + pd.Timedelta(days=1)
        row = {
            "steps_lag1": last["steps"],
            "steps_lag2": hist.iloc[-2]["steps"] if len(hist) >= 2 else last["steps"],
            "steps_lag7": hist.iloc[-7]["steps"] if len(hist) >= 7 else last["steps"],
            "steps_roll7_avg": hist["steps"].tail(7).mean(),
            "active_minutes_roll7_avg": hist["active_minutes"].tail(7).mean(),
            "resting_hr_roll7_avg": hist["resting_heart_rate"].tail(7).mean(),
        }
        row["month_sin"] = np.sin(2 * np.pi * next_date.month / 12)
        row["month_cos"] = np.cos(2 * np.pi * next_date.month / 12)
        pred = model.predict(pd.DataFrame([row])[FEATURES])[0]
        preds.append(pred)
        hist = pd.concat([hist, pd.DataFrame([{**last, "date": next_date, "steps": pred}])], ignore_index=True)
    return preds


def main():
    df = pd.read_parquet(SILVER_PATH)
    df = add_month_cyc(df)
    df["date"] = pd.to_datetime(df["date"])

    train_table = build_training_table(df)
    # Chronological split, same cutoff as Model 1, for consistency.
    cutoff = pd.Timestamp("2024-10-15")
    train = train_table[train_table.date < cutoff]

    print(f"Training rows: {len(train):,}")
    model = HistGradientBoostingRegressor(max_iter=200, max_depth=5, learning_rate=0.08, random_state=42)
    model.fit(train[FEATURES], train["target_next_day_steps"])

    print("\nWalk-forward evaluation: forecast the last 7 days for each user, held out")
    maes = []
    for uid, udf in df.groupby("user_id"):
        udf = udf.sort_values("date").reset_index(drop=True)
        if len(udf) < 14:
            continue
        history = udf.iloc[:-FORECAST_HORIZON]
        actual = udf.iloc[-FORECAST_HORIZON:]["steps"].values
        preds = recursive_forecast(model, history, FORECAST_HORIZON)
        maes.append(mean_absolute_error(actual, preds))

    overall_mae = float(np.mean(maes))
    avg_steps = df["steps"].mean()
    print(f"Users evaluated: {len(maes)}")
    print(f"7-day-ahead MAE: {overall_mae:.1f} steps (avg daily steps in dataset: {avg_steps:.0f})")
    print(f"MAE as % of average: {overall_mae/avg_steps*100:.1f}%")

    joblib.dump(model, "models/artifacts/forecast_model.joblib")
    print("\nSaved model to models/artifacts/forecast_model.joblib")

    return {"mae_steps": round(overall_mae, 1), "mae_pct_of_avg": round(overall_mae / avg_steps * 100, 1)}


if __name__ == "__main__":
    main()
