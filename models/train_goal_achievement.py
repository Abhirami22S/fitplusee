"""
FitPulse - Model 1: Next-Day Goal Achievement Prediction
===========================================================
Business question this answers: "Based on my pattern through today, how
likely am I to hit my step goal tomorrow?" Powers the dashboard's forward-
looking outlook badge.

Algorithm: Logistic Regression (baseline, interpretable) vs. Random Forest
Classifier (improved). Both are standard, well-understood choices for a
binary classification problem on tabular data — deliberately NOT XGBoost/
deep learning here, since the brief calls for starting simple/interpretable
for this particular prediction.

IMPORTANT — this predicts TOMORROW, not today, and that is a deliberate
choice we arrived at after checking our own work: an earlier version of
this model was trained to predict the SAME day's outcome from that day's
own rolling-average features (which are computed inclusive of that day).
Applying that same-day model to "predict tomorrow" (feeding it today's
features to guess tomorrow's outcome) only reached ROC-AUC 0.738 — clearly
weaker than its same-day score of ~0.86, because it was never trained for
that task. Rather than ship a same-day model under a "predicts tomorrow"
label, we retrained directly against the actual next-day outcome below,
which is both the more honest choice and the one that matches what the
product actually needs.

Feature design: only information available before tomorrow starts — the
user's own recent history (yesterday's steps, 2-days-ago, a week ago, and
7-day rolling averages of steps/calories/activity/resting heart rate as of
TODAY), plus static context (day of week, activity type, age, gender, BMI).
We never use tomorrow's `steps` itself as a feature (that would be label
leakage, since the label is derived directly from it).

This is trained on the Silver layer written by etl/spark_etl.py.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SILVER_PATH = "data/processed/fitpulse_silver"
TRAIN_CUTOFF = "2024-10-15"  # chronological split: train on the past, test on the future

NUM_FEATURES = [
    "steps_lag1", "steps_lag2", "steps_lag7", "steps_roll7_avg",
    "calories_lag1", "calories_roll7_avg", "active_minutes_roll7_avg",
    "resting_hr_roll7_avg", "age", "bmi", "month_sin", "month_cos",
]
CAT_FEATURES = ["day_of_week", "activity_type", "gender"]
TARGET = "next_day_goal_achieved"


def load_data():
    df = pd.read_parquet(SILVER_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["user_id", "date"])
    # EDA finding: this dataset has a real seasonal swing (avg steps peak ~10,100/day
    # in March, trough ~6,800/day in September/October) — likely a spring-activity /
    # autumn-slowdown pattern. A flat personalized goal (10% above yearly average) is
    # therefore much easier to hit in spring and much harder in autumn. We encode
    # month cyclically (sin/cos) rather than one-hot, so the model generalizes to
    # calendar months it never saw in training (our test period is Oct-Dec).
    month_num = df["date"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * month_num / 12)
    df["month_cos"] = np.cos(2 * np.pi * month_num / 12)

    # The actual training target: NEXT calendar day's goal_achieved, using
    # only features computed as of today. Rows where the "next" row in this
    # user's history isn't literally the following calendar day (a gap in
    # logging) are dropped — those wouldn't be a fair 1-day-ahead example.
    df["next_day_goal_achieved"] = df.groupby("user_id")["goal_achieved"].shift(-1)
    next_date = df.groupby("user_id")["date"].shift(-1)
    df["is_consecutive"] = (next_date - df["date"]).dt.days == 1

    # First 7 days per user have null lag/rolling features (not enough history yet) — drop them.
    df = df.dropna(subset=NUM_FEATURES + [TARGET])
    df = df[df["is_consecutive"]]
    return df


def main():
    df = load_data()
    train = df[df.date < TRAIN_CUTOFF]
    test = df[df.date >= TRAIN_CUTOFF]
    print(f"Train rows: {len(train):,}   Test rows: {len(test):,}  (chronological split at {TRAIN_CUTOFF})")

    X_train, y_train = train[NUM_FEATURES + CAT_FEATURES], train[TARGET]
    X_test, y_test = test[NUM_FEATURES + CAT_FEATURES], test[TARGET]

    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUM_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
    ])

    results = {}

    print("\n=== Baseline: Logistic Regression ===")
    log_pipeline = Pipeline([("prep", preprocess), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])
    log_pipeline.fit(X_train, y_train)
    log_pred = log_pipeline.predict(X_test)
    log_proba = log_pipeline.predict_proba(X_test)[:, 1]
    log_acc, log_f1 = accuracy_score(y_test, log_pred), f1_score(y_test, log_pred)
    log_auc = roc_auc_score(y_test, log_proba)
    print(f"Accuracy: {log_acc:.3f}   F1: {log_f1:.3f}   ROC-AUC: {log_auc:.3f}")
    print(classification_report(y_test, log_pred, target_names=["Missed", "Achieved"]))
    results["logistic_regression"] = {"accuracy": round(log_acc, 3), "f1": round(log_f1, 3), "roc_auc": round(log_auc, 3)}

    print("\n=== Improved: Random Forest Classifier ===")
    rf_pipeline = Pipeline([
        ("prep", preprocess),
        ("clf", RandomForestClassifier(n_estimators=300, max_depth=10, random_state=42, n_jobs=-1, class_weight="balanced")),
    ])
    rf_pipeline.fit(X_train, y_train)
    rf_pred = rf_pipeline.predict(X_test)
    rf_proba = rf_pipeline.predict_proba(X_test)[:, 1]
    rf_acc, rf_f1 = accuracy_score(y_test, rf_pred), f1_score(y_test, rf_pred)
    rf_auc = roc_auc_score(y_test, rf_proba)
    print(f"Accuracy: {rf_acc:.3f}   F1: {rf_f1:.3f}   ROC-AUC: {rf_auc:.3f}")
    print(classification_report(y_test, rf_pred, target_names=["Missed", "Achieved"]))
    results["random_forest"] = {"accuracy": round(rf_acc, 3), "f1": round(rf_f1, 3), "roc_auc": round(rf_auc, 3)}

    best_model = rf_pipeline if rf_auc >= log_auc else log_pipeline
    joblib.dump(best_model, "models/artifacts/goal_achievement_model.joblib")
    joblib.dump(NUM_FEATURES + CAT_FEATURES, "models/artifacts/goal_achievement_features.joblib")
    print(f"\nSaved best model ({'random_forest' if best_model is rf_pipeline else 'logistic_regression'}) "
          f"to models/artifacts/goal_achievement_model.joblib")

    return results


if __name__ == "__main__":
    main()
