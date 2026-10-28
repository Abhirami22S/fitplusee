"""Validate webapp/public/data/insights.json against the Silver data and the saved model outputs. Exit code 1 on any failure."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import analytics  # noqa: E402

d = json.loads((Path(__file__).resolve().parent / "public" / "data" / "insights.json").read_text(encoding="utf-8"))
s = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
s["date"] = pd.to_datetime(s["date"])
s = s.sort_values(["user_id", "date"])
cfg = analytics.load_calorie_config()
bad = []
def chk(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    if not ok: bad.append(name)

U = d["users"]
chk("437 users exported", len(U) == 437 and set(map(int, U)) == set(s.user_id.unique()))
g_ok = p_ok = cal_ok = ser_ok = rec_ok = rate_ok = pct_ok = True
for uid, gdf in s.groupby("user_id"):
    u = U[str(uid)]; last = gdf.iloc[-1]
    g_ok &= abs(u["summary"]["daily_step_goal"] - last["daily_step_goal"]) < 1e-6
    pr = u["tomorrow"]["goal_probability"]; p_ok &= pr is not None and 0 <= pr <= 1
    n = len(u["series"]["date"]); tail = gdf.tail(60)
    ser_ok &= n == min(60, len(gdf)) and u["series"]["date"][-1] == str(last["date"].date()) and u["series"]["steps"] == [int(x) for x in tail.steps]
    cal_ok &= np.allclose(u["series"]["predicted_calories"], analytics.predict_calories(tail, cfg).round(1), atol=0.06)
    rec_ok &= len(u["recommendations"]) == 3
    rate_ok &= abs(u["summary"]["goal_rate_pct"] - gdf.goal_achieved.mean() * 100) < 0.06
    pct_ok &= all(0 <= u["summary"][k] <= 100 for k in ("steps_percentile", "calories_percentile", "sleep_percentile"))
chk("personal step goal equals Silver daily_step_goal (all users)", g_ok)
chk("tomorrow's goal probability present and within 0..1 (all users)", p_ok)
chk("every user record has exactly the expected fields and model_info lists only the goal and calorie models (no extra grouping field)",
    all(set(u) == {"profile", "summary", "tomorrow", "recommendations", "series"} for u in U.values()) and set(d["model_info"]) == {"goal_model", "calorie_model"})
chk("60-day (or full) steps series and last date equal Silver (all users)", ser_ok)
chk("model calorie estimate equals Linear Regression formula (all users)", cal_ok)
chk("goal rate equals Silver mean of goal_achieved (all users)", rate_ok)
chk("percentiles within 0..100 (all users)", pct_ok)
chk("3 rule-based recommendation cards per user (steps, calories, sleep)", rec_ok)
chk("population averages equal Silver", abs(d["population"]["avg_steps"] - s.steps.mean()) < 0.06 and d["population"]["users"] == 437)
print("\nALL PASSED" if not bad else f"\nFAILED: {bad}")
sys.exit(1 if bad else 0)
