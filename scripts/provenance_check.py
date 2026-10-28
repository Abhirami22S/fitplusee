"""
FitPulse - independent provenance audit (read-only). Re-derives numbers with separate pandas / scikit-learn code to show they come from the
Kaggle source data and from models trained on it, not from typed-in values.

    python scripts/provenance_check.py          # writes faculty_evidence/provenance_check.md ; exit code 1 on any failure
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))
from models import analytics  # noqa: E402
import prepare_raw_dataset as prep  # noqa: E402

rows = []
def chk(name, ok, detail=""):
    rows.append((name, bool(ok), str(detail)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))

# ---------------------------------------------------------------- 1. Kaggle source -> Bronze
src = pd.read_csv(prep.resolve_source())
bronze = pd.read_csv(ROOT / "data" / "raw" / "fitpulse_raw.csv", parse_dates=["date"])
src["date"] = pd.to_datetime(src["date"])
chk("Kaggle source file: 687,701 rows, 3,000 participants", len(src) == 687701 and src.participant_id.nunique() == 3000, f"{len(src):,} rows, {src.participant_id.nunique()} participants")
ids = pd.Series(src.participant_id.unique()).sample(n=prep.N_PARTICIPANTS, random_state=prep.SEED)
chk("the 437 users are exactly a seeded random sample (seed 42) of the 3,000", set(ids) == set(bronze.user_id.unique()))
sub = src[src.participant_id.isin(ids)]
chk("Bronze row count equals the Kaggle rows of those 437 users (full yearly series kept, nothing dropped)", len(sub) == len(bronze) == 100122, f"{len(sub):,} vs {len(bronze):,}")
m = bronze.merge(sub, left_on=["user_id", "date"], right_on=["participant_id", "date"], suffixes=("", "_src"), validate="one_to_one")
same = all((m[c] == m[s]).all() for c, s in [("steps", "daily_steps"), ("age", "age_src"), ("height_cm", "height_cm_src"), ("weight_kg", "weight_kg_src"),
                                              ("activity_type", "activity_type_src"), ("intensity", "intensity_src"), ("avg_heart_rate", "avg_heart_rate_src"),
                                              ("resting_heart_rate", "resting_heart_rate_src"), ("stress_level", "stress_level_src"), ("bmi", "bmi_src")])
chk("source fields in Bronze (steps, age, height, weight, activity, intensity, heart rates, stress, bmi) equal the Kaggle values row by row", same)
met = m.apply(lambda r: prep.MET_TABLE[r.activity_type][r.intensity], axis=1)
cal_unrounded = met * m.weight_kg * (m.duration_minutes / 60)
chk("calories_burned = MET x weight x minutes/60 within rounding to 0.1 kcal (recomputed independently, all rows)",
    ((m.calories_burned - cal_unrounded).abs() <= 0.05 + 1e-9).all())
stride = m.height_cm / 100 * m.intensity.map(prep.STRIDE_MULT)
chk("distance_km = steps x height-based stride (recomputed)", np.allclose(m.distance_km, (m.steps * stride / 1000).round(2)))
chk("sleep_minutes = hours_sleep x 60 and active + sedentary + sleep = 1,440 (recomputed)",
    (m.sleep_minutes == (m.hours_sleep * 60).round(0)).all() and ((m.active_minutes + m.sedentary_minutes + m.sleep_minutes) == 1440).all())

# ---------------------------------------------------------------- 2. Bronze -> Silver (independent pandas re-derivation of the Spark features)
silver = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
silver["date"] = pd.to_datetime(silver["date"])
b = bronze.sort_values(["user_id", "date"]).reset_index(drop=True)
s = silver.sort_values(["user_id", "date"]).reset_index(drop=True)
chk("Silver has the same 100,122 rows and users as Bronze", len(s) == len(b) and (s.user_id.values == b.user_id.values).all() and (s.date.values == b.date.values).all())
chk("Silver source columns equal Bronze (steps, calories, sleep quality)", (s.steps == b.steps).all() and np.allclose(s.calories_burned, b.calories_burned) and np.allclose(s.sleep_quality_score, b.sleep_quality_score))
g = b.groupby("user_id")
lag1 = g.steps.shift(1); lag7 = g.steps.shift(7)
roll = g.steps.transform(lambda x: x.rolling(7, min_periods=1).mean())
chk("steps_lag1 / steps_lag7 recomputed in pandas equal Spark's", np.array_equal(lag1.fillna(-1).values, s.steps_lag1.fillna(-1).values) and np.array_equal(lag7.fillna(-1).values, s.steps_lag7.fillna(-1).values))
chk("steps_roll7_avg (7 logged rows) recomputed equals Spark's", np.allclose(roll.values, s.steps_roll7_avg.values))
goal = (g.steps.transform("mean") * 1.10 / 100).round(0) * 100          # Spark round(x,-2) is half-up; equal except exact .5 ties
goal_match = (abs(goal - s.daily_step_goal) < 1e-6).mean()
chk("personal step goal = 1.10 x user's mean steps rounded to 100 (recomputed)", goal_match > 0.9995, f"{goal_match:.4%} identical")
chk("goal_achieved = steps >= goal (recomputed from Silver goal)", ((s.steps >= s.daily_step_goal).astype(int) == s.goal_achieved).all())

# ---------------------------------------------------------------- 3. Dashboard Logistic Regression: independent re-measurement on the held-out period
NUM = ["steps_lag1", "steps_lag2", "steps_lag7", "steps_roll7_avg", "calories_lag1", "calories_roll7_avg", "active_minutes_roll7_avg", "resting_hr_roll7_avg", "age", "bmi", "month_sin", "month_cos"]
CAT = ["day_of_week", "activity_type", "gender"]
d = s.copy()
d["month_sin"], d["month_cos"] = np.sin(2 * np.pi * d.date.dt.month / 12), np.cos(2 * np.pi * d.date.dt.month / 12)
d["y"] = d.groupby("user_id").goal_achieved.shift(-1)
d["consec"] = (d.groupby("user_id").date.shift(-1) - d.date).dt.days == 1
d = d.dropna(subset=NUM + ["y"])
d = d[d.consec]
test = d[d.date >= "2024-10-15"]
model = joblib.load(ROOT / "models" / "artifacts" / "goal_achievement_model.joblib")
clf = model.steps[-1][1].__class__.__name__
p = model.predict_proba(test[NUM + CAT])[:, 1]
auc, acc, f1 = roc_auc_score(test.y, p), accuracy_score(test.y, p >= 0.5), f1_score(test.y, p >= 0.5)
chk(f"saved goal model ({clf}) re-measured on the held-out period: ROC-AUC {auc:.3f} (reported 0.755), accuracy {acc:.3f} (0.870), F1 {f1:.3f} (0.224)",
    abs(auc - 0.755) < 0.0015 and abs(acc - 0.870) < 0.0015 and abs(f1 - 0.224) < 0.0015, f"{len(test):,} test rows")

# ---------------------------------------------------------------- 4. Web insights: probabilities really come from that model
ins = json.loads((ROOT / "webapp" / "public" / "data" / "insights.json").read_text(encoding="utf-8"))
last = d.sort_values("date").groupby("user_id").tail(1)             # not usable (label NaN last day) -> use the final Silver row instead
fin = s.groupby("user_id").tail(1).copy()
fin["month_sin"], fin["month_cos"] = np.sin(2 * np.pi * fin.date.dt.month / 12), np.cos(2 * np.pi * fin.date.dt.month / 12)
pr = pd.Series(model.predict_proba(fin[NUM + CAT])[:, 1], index=fin.user_id.values)
jp = pd.Series({int(k): v["tomorrow"]["goal_probability"] for k, v in ins["users"].items()})
chk("web page: all 437 'tomorrow' probabilities equal the saved model's output on each user's final Silver row", np.allclose(pr.sort_index(), jp.sort_index(), atol=5e-4))

# ---------------------------------------------------------------- 5. Calorie Linear Regression: independent re-training
pred = pd.read_csv(ROOT / "faculty_evidence" / "regression_predictions.csv", parse_dates=["date"])
cfg = analytics.load_calorie_config()
x = s.merge(pred[["user_id", "date", "split"]], on=["user_id", "date"])
feats = cfg["numeric_features"]
X = x[feats].copy()
X["gender_M"], X["gender_F"] = (x.gender == "M").astype(float), (x.gender == "F").astype(float)
tr, te = x.split == "train", x.split == "test"
lr = LinearRegression().fit(X[tr], x.calories_burned[tr])               # plain OLS, scikit-learn, on the TRAIN rows only
pt = lr.predict(X[te]); yt = x.calories_burned[te]
mae, rmse, r2 = np.abs(yt - pt).mean(), np.sqrt(((yt - pt) ** 2).mean()), 1 - ((yt - pt) ** 2).sum() / ((yt - yt.mean()) ** 2).sum()
tm = cfg["test_metrics"]
chk(f"calorie model re-trained independently (scikit-learn OLS on train rows): test MAE {mae:.1f} / RMSE {rmse:.1f} / R2 {r2:.3f} vs Spark {tm['MAE']:.1f} / {tm['RMSE']:.1f} / {tm['R2']:.3f}",
    abs(mae - tm["MAE"]) < 0.3 and abs(rmse - tm["RMSE"]) < 0.3 and abs(r2 - tm["R2"]) < 0.002)

ok = all(r[1] for r in rows)
md = ["# Provenance check (independent, read-only)", "", f"**{sum(r[1] for r in rows)}/{len(rows)} checks passed.** Script: `scripts/provenance_check.py`.", "",
      "| Check | Result | Detail |", "|---|---|---|"] + [f"| {n} | {'PASS' if o else 'FAIL'} | {dtl} |" for n, o, dtl in rows]
(ROOT / "faculty_evidence" / "provenance_check.md").write_text("\n".join(md), encoding="utf-8")
print("\nALL PASSED" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
