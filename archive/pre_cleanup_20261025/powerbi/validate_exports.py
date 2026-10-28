"""
FitPulse - validate the Power BI export tables against the source Silver data, and write the EXPECTED values that the
Power BI measures (measures.dax) must show once the dashboard is built.  Exit code 1 if an export check fails.

    python powerbi/validate_exports.py
Writes powerbi/EXPECTED_VALUES.csv  (computed here with pandas from the Silver Parquet - independent of Power BI).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = Path(__file__).resolve().parent / "data"
bad = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        bad.append(name)


s = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
s["date"] = pd.to_datetime(s["date"])
f = pd.read_csv(D / "fact_daily.csv", parse_dates=["date"])
dim = pd.read_csv(D / "dim_user.csv")
mon = pd.read_csv(D / "monthly_summary.csv")

check("fact_daily rows == Silver rows", len(f) == len(s), f"{len(f):,}")
check("fact_daily unique (user_id, date)", not f.duplicated(["user_id", "date"]).any())
check("dim_user rows == distinct users", len(dim) == s.user_id.nunique() == 437, len(dim))
for col in ["steps", "calories_burned", "active_minutes", "sedentary_minutes", "goal_achieved"]:
    check(f"sum({col}) identical to Silver", np.isclose(f[col].sum(), s[col].sum()), f"{f[col].sum():,.0f}")
check("no missing predictions / segments", f.predicted_calories.notna().all() and f.segment_label.notna().all())
check("monthly_summary total days == rows", int(mon.days.sum()) == len(s))
check("monthly_summary total steps == Silver", np.isclose(mon.total_steps.sum(), s.steps.sum()))
check("date range", f.date.min() == s.date.min() and f.date.max() == s.date.max(), f"{f.date.min().date()} .. {f.date.max().date()}")
check("no user names / account data in exports", not any(c in f.columns for c in ["username", "password"]))

t = f[f.model_split == "test"]
exp = [
    ("Total days (rows)", len(s)), ("Distinct users", s.user_id.nunique()),
    ("Total steps", s.steps.sum()), ("Average daily steps", s.steps.mean()),
    ("Average calories burned", s.calories_burned.mean()), ("Average active minutes", s.active_minutes.mean()),
    ("Average sedentary minutes", s.sedentary_minutes.mean()), ("Average sleep hours", (s.sleep_minutes / 60).mean()),
    ("Average sleep quality", s.sleep_quality_score.mean()), ("Personal step-goal achievement rate", s.goal_achieved.mean()),
    ("Test-set MAE (kcal)", (t.calorie_error).abs().mean()), ("Test-set days", len(t)),
]
for mth, g in s.assign(month=s.date.dt.strftime("%Y-%m")).groupby("month"):
    exp.append((f"Average daily steps in {mth}", g.steps.mean()))
for lab, g in f.groupby("segment_label"):
    exp.append((f"Users in segment '{lab}'", g.user_id.nunique()))
exp += [("Average distance (km)", s.distance_km.mean()), ("Average heart rate (bpm)", s.avg_heart_rate.mean()),
        ("Calorie-goal achievement rate", s.calorie_goal_achieved.mean()),
        ("Active share of waking time", s.active_minutes.sum() / (s.active_minutes.sum() + s.sedentary_minutes.sum())),
        ("Test-set mean error / bias (kcal)", t.calorie_error.mean()), ("Test-set RMSE (kcal)", float(np.sqrt((t.calorie_error ** 2).mean()))),
        ("Test-set R2", float(1 - (t.calorie_error ** 2).sum() / ((t.calories_burned - t.calories_burned.mean()) ** 2).sum())),
        ("Baseline (training mean) test MAE (kcal)", float((t.calories_burned - f[f.model_split == "train"].calories_burned.mean()).abs().mean()))]
for lab, g in f.groupby("segment_label"):
    exp += [(f"User-days in segment '{lab}'", len(g)), (f"Avg active minutes, segment '{lab}'", g.active_minutes.mean()),
            (f"Avg sedentary minutes, segment '{lab}'", g.sedentary_minutes.mean()), (f"Avg sleep hours, segment '{lab}'", g.sleep_hours.mean()),
            (f"Step-goal achievement, segment '{lab}'", g.goal_achieved.mean())]
for dow, g in f.groupby("day_of_week"):
    exp.append((f"Step-goal achievement on {dow}", g.goal_achieved.mean()))
pd.DataFrame(exp, columns=["measure", "expected_value"]).to_csv(Path(__file__).resolve().parent / "EXPECTED_VALUES.csv", index=False)
print(f"\nwrote EXPECTED_VALUES.csv ({len(exp)} rows)")

# ---------------- Page 3 / 4 / 5 tables ----------------
import json

me = pd.read_csv(D / "model_evaluation.csv")
cmx = pd.read_csv(D / "confusion_matrices.csv")
ks = pd.read_csv(D / "kmeans_k_selection.csv")
ex = pd.read_csv(D / "experiments.csv")
check("model_evaluation: no missing values / no duplicate rows", me.value.notna().all() and not me.duplicated(["experiment_id", "algorithm", "evaluation_set", "metric"]).any(), len(me))
check("model_evaluation: every experiment id is declared in experiments.csv", set(me.experiment_id) <= set(ex.experiment_id))
check("experiments are never merged: each row has target + granularity", me.target.notna().all() and me.data_granularity.notna().all())
e5 = me[(me.experiment_id == "E5") & (me.algorithm == "Linear Regression (Spark MLlib)") & (me.evaluation_set == "test")].set_index("metric").value
err = t.calorie_error
r2 = 1 - (err ** 2).sum() / ((t.calories_burned - t.calories_burned.mean()) ** 2).sum()
check("E5 test MAE == mean |error| over fact_daily test rows", abs(e5["MAE (kcal)"] - err.abs().mean()) < 0.05, f"{e5['MAE (kcal)']:.2f}")
check("E5 test RMSE == sqrt(mean error^2) over fact_daily test rows", abs(e5["RMSE (kcal)"] - np.sqrt((err ** 2).mean())) < 0.05, f"{e5['RMSE (kcal)']:.2f}")
check("E5 test R2 recomputed from fact_daily", abs(e5["R2"] - r2) < 0.001, f"{e5['R2']:.4f}")
check("E5 test row count == fact_daily test rows", len(t) == 14985)
check("fact_daily has the error_bin column for the histogram", "error_bin_kcal" in f.columns)
check("confusion matrix E1 sums to the E1 test set", int(cmx[cmx.experiment_id == "E1"]["count"].sum()) == 14796, int(cmx[cmx.experiment_id == "E1"]["count"].sum()))
check("confusion matrix E2 sums to the E2 test set", int(cmx[cmx.experiment_id == "E2"]["count"].sum()) == 9406, int(cmx[cmx.experiment_id == "E2"]["count"].sum()))
e1 = me[(me.experiment_id == "E1") & (me.evaluation_set == "test")].set_index("metric").value
c1 = cmx[cmx.experiment_id == "E1"].set_index(["actual", "predicted"])["count"]
tp, tn_, fp, fn = c1[("Achieved (1)", "Achieved (1)")], c1[("Not achieved (0)", "Not achieved (0)")], c1[("Not achieved (0)", "Achieved (1)")], c1[("Achieved (1)", "Not achieved (0)")]
check("E1 accuracy recomputed from its confusion matrix", abs(e1["Accuracy"] - (tp + tn_) / (tp + tn_ + fp + fn)) < 1e-6)
check("E1 recall/precision recomputed from its confusion matrix", abs(e1["Recall (positive class)"] - tp / (tp + fn)) < 1e-6 and abs(e1["Precision (positive class)"] - tp / (tp + fp)) < 1e-6)
e3 = me[(me.experiment_id == "E3") & (me.metric == "Users in cluster")].value.sum()
check("E3 users in clusters sum to 437 and equal dim_user", e3 == 437 == len(dim) and sorted(dim.segment_id.value_counts().tolist()) == sorted(me[(me.experiment_id == "E3") & (me.metric == "Users in cluster")].value.astype(int).tolist()))
check("E4 user-days in clusters sum to 100,122", me[(me.experiment_id == "E4") & (me.metric == "User-days in cluster")].value.sum() == 100122)
check("kmeans_k_selection covers K=2..10 (E3) and 2..6 (E4)", sorted(ks[ks.experiment_id == "E3"].K.unique()) == list(range(2, 11)) and sorted(ks[ks.experiment_id == "E4"].K.unique()) == list(range(2, 7)))

# column inventory for the .pbix checker (scripts/check_pbix.py)
schema = {p.stem: list(pd.read_csv(p, nrows=0).columns) for p in sorted(D.glob("*.csv"))}
(D / "_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
for p in sorted(D.glob("*.csv")):
    d_ = pd.read_csv(p)
    print(f"  {p.name:24s} rows={len(d_):>7,} missing_cells={int(d_.isna().sum().sum())} duplicate_rows={int(d_.duplicated().sum())}")
sys.exit(1 if bad else 0)
