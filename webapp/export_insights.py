"""
FitPulse - per-user insights export for the web dashboard.

    python webapp/export_insights.py

Every user's insight is produced by models trained on ALL users' data (the Silver dataset):
  * tomorrow's step-goal probability  : Logistic Regression (models/artifacts/goal_achievement_model.joblib)
  * calorie estimate                  : Linear Regression (Spark MLlib, coefficients in calorie_linreg_config.json)
  * percentile vs other users         : rank of the user's average among all users
  * recommendations                   : transparent rules (models/recommendation_engine.py, models/analytics.py)
Output: webapp/public/data/insights.json  (static file read by the page; no server code needed).
Not medical advice.
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import analytics  # noqa: E402
from models.recommendation_engine import recommend  # noqa: E402

OUT = Path(__file__).resolve().parent / "public" / "data" / "insights.json"
DAYS = 60                                   # days of history shown per user


def main():
    df = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["user_id", "date"]).reset_index(drop=True)
    m = df["date"].dt.month
    df["month_sin"], df["month_cos"] = np.sin(2 * np.pi * m / 12), np.cos(2 * np.pi * m / 12)

    goal_model = joblib.load(ROOT / "models" / "artifacts" / "goal_achievement_model.joblib")
    feats = joblib.load(ROOT / "models" / "artifacts" / "goal_achievement_features.joblib")
    cal_cfg = analytics.load_calorie_config()
    df["pred_cal"] = analytics.predict_calories(df, cal_cfg)

    per_user = df.groupby("user_id").agg(avg_steps=("steps", "mean"), avg_cal=("calories_burned", "mean"), avg_sleepq=("sleep_quality_score", "mean"))
    pct = per_user.rank(pct=True) * 100                        # percentile among all users
    pop = {"users": int(len(per_user)), "avg_steps": round(float(df.steps.mean()), 1), "avg_calories": round(float(df.calories_burned.mean()), 1),
           "avg_sleep_quality": round(float(df.sleep_quality_score.mean()), 1)}

    users = {}
    for uid, g in df.groupby("user_id"):
        g = g.reset_index(drop=True)
        today = g.iloc[-1]
        row = pd.DataFrame([{k: today[k] for k in feats}])
        prob = None if row.isnull().any(axis=1).iloc[0] else float(goal_model.predict_proba(row)[0][1])
        fs = analytics.fitness_score(g)
        recs = recommend(today.to_dict(), g.iloc[:-1], float(g["sleep_quality_score"].tail(7).mean()))
        guidance = analytics.goal_guidance(prob) if prob is not None else None
        tail = g.tail(DAYS)
        users[str(int(uid))] = {
            "profile": {"age": int(today["age"]), "gender": today["gender"], "days_logged": int(len(g)), "last_date": str(today["date"].date())},
            "summary": {
                "avg_steps": round(float(g.steps.mean()), 0), "daily_step_goal": float(today["daily_step_goal"]),
                "goal_rate_pct": round(float(g.goal_achieved.mean() * 100), 1), "last7_avg_steps": round(float(g.steps.tail(7).mean()), 0),
                "avg_calories": round(float(g.calories_burned.mean()), 0), "avg_sleep_hours": round(float(g.sleep_minutes.mean() / 60), 2),
                "avg_sleep_quality": round(float(g.sleep_quality_score.mean()), 1),
                "steps_percentile": round(float(pct.loc[uid, "avg_steps"]), 0), "calories_percentile": round(float(pct.loc[uid, "avg_cal"]), 0),
                "sleep_percentile": round(float(pct.loc[uid, "avg_sleepq"]), 0),
                "calorie_mae_user": round(float((g.calories_burned - g.pred_cal).abs().mean()), 0),
                "fitness_score": round(fs["score"], 0),
            },
            "tomorrow": {"goal_probability": None if prob is None else round(prob, 3),
                         "band": None if guidance is None else guidance["band"], "action": None if guidance is None else guidance["action"]},
            "recommendations": [{"topic": r["topic"], "status": r["status"], "metric": r["metric"], "what": r["what"], "why": r["why"], "how": r["how"]} for r in recs],
            "series": {"date": [str(d.date()) for d in tail["date"]], "steps": [int(x) for x in tail["steps"]],
                       "goal": [float(x) for x in tail["daily_step_goal"]], "calories": [round(float(x), 1) for x in tail["calories_burned"]],
                       "predicted_calories": [round(float(x), 1) for x in tail["pred_cal"]], "sleep_quality": [round(float(x), 1) for x in tail["sleep_quality_score"]]},
        }
    payload = {"population": pop, "model_info": {
        "goal_model": "Logistic Regression trained on all users (next-day personal step goal; chronological test ROC-AUC 0.755, models/metrics_report.md)",
        "calorie_model": f"Linear Regression (Spark MLlib), test MAE {cal_cfg['test_metrics']['MAE']:.1f} kcal, R2 {cal_cfg['test_metrics']['R2']:.2f}"},
        "users": users}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT}: {len(users)} users, {OUT.stat().st_size/1024:,.0f} KB")


if __name__ == "__main__":
    main()
