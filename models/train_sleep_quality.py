"""
FitPulse - Model 3: Sleep Quality Prediction
===============================================
Business question this answers: "Which of my daytime habits help or hurt
my sleep?" — lets the dashboard tell a user something like "your sleep
quality tends to drop on high-stress, high-sedentary days."

Algorithm: Linear Regression (baseline, fully interpretable — coefficients
directly show which features help/hurt) vs. Random Forest Regressor
(improved — captures non-linear effects), exactly the "simple vs better"
comparison the brief asks for on this prediction.

Features are all DAYTIME variables (activity, heart rate, sedentary time,
stress, hydration) — i.e. things a user could act on today to influence
tonight's sleep. `sleep_minutes` itself is excluded as a feature (using
sleep duration to predict a sleep-duration-derived score would be
circular); we predict quality from behavior/physiology, not from sleep
duration alone.
"""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

SILVER_PATH = "data/processed/fitpulse_silver"

FEATURES = [
    "active_minutes", "sedentary_minutes", "avg_heart_rate", "resting_heart_rate",
    "max_heart_rate", "stress_level", "hydration_level", "calories_burned", "age", "bmi",
]
TARGET = "sleep_quality_score"


def main():
    df = pd.read_parquet(SILVER_PATH).dropna(subset=FEATURES + [TARGET])
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}

    print("=== Baseline: Linear Regression ===")
    lin = LinearRegression()
    lin.fit(X_train, y_train)
    lin_pred = lin.predict(X_test)
    lin_mae, lin_r2 = mean_absolute_error(y_test, lin_pred), r2_score(y_test, lin_pred)
    print(f"MAE: {lin_mae:.2f}   R2: {lin_r2:.3f}")
    print("Coefficients (positive = improves sleep quality, negative = hurts it):")
    for feat, coef in sorted(zip(FEATURES, lin.coef_), key=lambda x: -abs(x[1])):
        print(f"  {feat:24s} {coef:+.3f}")
    results["linear_regression"] = {"mae": round(lin_mae, 2), "r2": round(lin_r2, 3)}

    print("\n=== Improved: Random Forest Regressor ===")
    rf = RandomForestRegressor(n_estimators=300, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_mae, rf_r2 = mean_absolute_error(y_test, rf_pred), r2_score(y_test, rf_pred)
    print(f"MAE: {rf_mae:.2f}   R2: {rf_r2:.3f}")
    fi = sorted(zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1])
    print("Feature importances:")
    for feat, imp in fi:
        print(f"  {feat:24s} {imp:.3f}")
    results["random_forest"] = {"mae": round(rf_mae, 2), "r2": round(rf_r2, 3)}

    best_model = rf if rf_r2 >= lin_r2 else lin
    joblib.dump(best_model, "models/artifacts/sleep_quality_model.joblib")
    joblib.dump(FEATURES, "models/artifacts/sleep_quality_features.joblib")
    print(f"\nSaved best model ({'random_forest' if best_model is rf else 'linear_regression'}) "
          f"to models/artifacts/sleep_quality_model.joblib")

    return results


if __name__ == "__main__":
    main()
