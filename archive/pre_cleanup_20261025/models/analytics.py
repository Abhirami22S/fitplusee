"""
FitPulse - personalised analytics helpers (pure pandas/numpy; no Spark or Streamlit needed at serve time)
==========================================================================================================
* predict_calories   - applies the Spark MLlib Linear Regression saved by models/train_calorie_regression.py
                       (coefficients in original units, models/artifacts/calorie_linreg_config.json).
* assign_segment     - nearest-centroid assignment for the user-level K-Means model saved by
                       archive/kmeans/spark_report_kmeans.py (models/artifacts/kmeans_user_segments_model.json; ARCHIVED unsupervised
                       model, kept only because the legacy Streamlit app and scripts/test_analytics.py still read the saved file).
* fitness_score      - transparent 0-100 heuristic (weights shown to the user). Not a validated clinical measure.
* goal_guidance      - REPORT Table 11: model probability band -> coaching action (rule-based).
* monthly_summary    - monthly activity / calorie / sleep roll-up.
Recommendations here follow explicit rules; they are not medical advice.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

# ----------------------------------------------------------------------------------------------------------
# Calorie regression
# ----------------------------------------------------------------------------------------------------------


def load_calorie_config(path=None) -> dict:
    return json.loads(Path(path or ARTIFACTS / "calorie_linreg_config.json").read_text(encoding="utf-8"))


def predict_calories(df: pd.DataFrame, config: dict) -> pd.Series:
    """Predicted same-day calories_burned (kcal) for each row. Needs the config's numeric features and `gender`."""
    x = np.full(len(df), float(config["intercept_original_units"]))
    for name, coef in config["coefficients_original_units"].items():
        if name.startswith("gender="):
            x += coef * (df["gender"].astype(str) == name.split("=", 1)[1]).to_numpy(dtype=float)
        else:
            x += coef * df[name].to_numpy(dtype=float)
    return pd.Series(x, index=df.index, name="predicted_calories")


# ----------------------------------------------------------------------------------------------------------
# User segments (K-Means, user level)
# ----------------------------------------------------------------------------------------------------------
SEG_FEATURES = ["steps", "active_minutes", "sedentary_minutes", "calories_burned", "avg_heart_rate", "sleep_minutes"]


def load_segment_model(path=None) -> dict:
    return json.loads(Path(path or ARTIFACTS / "kmeans_user_segments_model.json").read_text(encoding="utf-8"))


def user_feature_vector(df: pd.DataFrame) -> dict:
    d = df.copy()
    d["intensity_ratio"] = d["active_minutes"] / (d["active_minutes"] + d["sedentary_minutes"])
    return {"AvgSteps": d["steps"].mean(), "AvgActiveMin": d["active_minutes"].mean(),
            "AvgSedentaryMin": d["sedentary_minutes"].mean(), "AvgCalories": d["calories_burned"].mean(),
            "AvgHeartRate": d["avg_heart_rate"].mean(), "AvgSleep": d["sleep_minutes"].mean(),
            "AvgIntensity": d["intensity_ratio"].mean()}


def assign_segment(user_df: pd.DataFrame, model: dict) -> dict:
    """Nearest centroid in standardised space. Returns cluster id, label, feature averages and distance."""
    vec = user_feature_vector(user_df)
    raw = np.array([vec[f] for f in model["features"]], dtype=float)
    z = (raw - np.array(model["mean"])) / np.array(model["std"])
    centers = np.array(model["centers_standardised"])
    dist = np.linalg.norm(centers - z, axis=1)
    c = int(dist.argmin())
    return {"cluster": c, "label": model["labels"][str(c)], "averages": vec, "distance": float(dist[c]),
            "silhouette_of_model": model["silhouette"], "K": model["K"]}


def segment_guidance(label: str) -> str:
    # Wording follows REPORT Table 17 (the segments differ only slightly, so advice stays modest).
    if label.startswith("Lowest"):
        return ("Your averages place you in the lower active-time group: aim for a small, achievable increase in "
                "active minutes (for example one extra 10-minute walk) rather than a large jump.")
    if label.startswith("Highest"):
        return ("Your averages place you in the higher active-time group: keep your consistency and consider a "
                "progressive challenge, with a rest day when you feel run down.")
    return "Keep your routine and compare your progress month to month."


# ----------------------------------------------------------------------------------------------------------
# Fitness score (transparent heuristic)
# ----------------------------------------------------------------------------------------------------------
SCORE_WEIGHTS = {"steps vs your goal": 0.40, "calories vs your goal": 0.20, "sleep quality": 0.25,
                 "active minutes vs 30-minute reference": 0.15}


def fitness_score(df: pd.DataFrame, days: int = 7) -> dict:
    """0-100 score over the last `days` rows. Each component is capped at 100%.
    Transparent heuristic for motivation only - not clinically validated."""
    w = df.tail(days)
    comp = {
        "steps vs your goal": float(np.clip((w["steps"] / w["daily_step_goal"]).mean(), 0, 1)),
        "calories vs your goal": float(np.clip((w["calories_burned"] / w["daily_calorie_goal"]).mean(), 0, 1)),
        "sleep quality": float(np.clip(w["sleep_quality_score"].mean() / 100.0, 0, 1)),
        "active minutes vs 30-minute reference": float(np.clip((w["active_minutes"] / 30.0).mean(), 0, 1)),
    }
    score = 100 * sum(SCORE_WEIGHTS[k] * v for k, v in comp.items())
    return {"score": score, "components": comp, "weights": SCORE_WEIGHTS, "days": len(w)}


# ----------------------------------------------------------------------------------------------------------
# REPORT Table 11: probability band -> action
# ----------------------------------------------------------------------------------------------------------


def goal_guidance(prob: float) -> dict:
    if prob >= 0.65:
        return {"band": "On track (high probability of achieving)", "action":
                "Reinforce the habit with a streak target and offer a stretch goal."}
    if prob <= 0.35:
        return {"band": "At risk (high probability of missing)", "action":
                "Set a smaller intermediate target for tomorrow, plan one short walk, and reduce long sitting blocks."}
    return {"band": "Uncertain (near the decision boundary)", "action":
            "Send a light reminder and re-check after tomorrow's data."}


# ----------------------------------------------------------------------------------------------------------
def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["month"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m")
    g = d.groupby("month").agg(days=("date", "count"), avg_steps=("steps", "mean"), avg_calories=("calories_burned", "mean"),
                               avg_active_min=("active_minutes", "mean"), avg_sedentary_min=("sedentary_minutes", "mean"),
                               avg_sleep_hours=("sleep_minutes", lambda s: s.mean() / 60),
                               avg_sleep_quality=("sleep_quality_score", "mean"),
                               step_goal_rate=("goal_achieved", "mean"))
    return g.reset_index()
