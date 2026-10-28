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
check("no missing predictions", f.predicted_calories.notna().all())
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
exp += [("Average distance (km)", s.distance_km.mean()), ("Average heart rate (bpm)", s.avg_heart_rate.mean()),
        ("Calorie-goal achievement rate", s.calorie_goal_achieved.mean()),
        ("Active share of waking time", s.active_minutes.sum() / (s.active_minutes.sum() + s.sedentary_minutes.sum())),
        ("Test-set mean error / bias (kcal)", t.calorie_error.mean()), ("Test-set RMSE (kcal)", float(np.sqrt((t.calorie_error ** 2).mean()))),
        ("Test-set R2", float(1 - (t.calorie_error ** 2).sum() / ((t.calories_burned - t.calories_burned.mean()) ** 2).sum())),
        ("Baseline (training mean) test MAE (kcal)", float((t.calories_burned - f[f.model_split == "train"].calories_burned.mean()).abs().mean()))]
for dow, g in f.groupby("day_of_week"):
    exp.append((f"Step-goal achievement on {dow}", g.goal_achieved.mean()))
cc_src = pd.read_csv(ROOT / "faculty_evidence" / "supervised" / "hdfs_rerun" / "sklearn_crosscheck.csv")
exp += [("Cross-check checks", len(cc_src)), ("Cross-check checks passed", int(cc_src["pass"].sum()))]
pd.DataFrame(exp, columns=["measure", "expected_value"]).to_csv(Path(__file__).resolve().parent / "EXPECTED_VALUES.csv", index=False)
print(f"\nwrote EXPECTED_VALUES.csv ({len(exp)} rows)")

# ---------------- Pages 3 / 4 / 5 tables (supervised results) ----------------
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_definition as md  # noqa: E402

sr = pd.read_csv(D / "supervised_results.csv")
ex = pd.read_csv(D / "experiments.csv")
cc = pd.read_csv(D / "crosscheck.csv")
src = pd.concat([pd.read_csv(ROOT / "exports" / f"E{i}_results.csv") for i in range(1, 6)], ignore_index=True)   # read independently, straight from exports/
KEY = ["experiment_id", "model", "metric", "split_type", "status"]
mrg = sr.merge(src, on=KEY, how="outer", suffixes=("_pbi", "_exports"), indicator=True)
check("supervised_results has exactly the rows of exports/E1..E5_results.csv", len(sr) == len(src), f"{len(sr)} rows")
check("every row matches exports/E<n>_results.csv by key and value (no row added, dropped or changed)",
      (mrg["_merge"] == "both").all() and bool(np.allclose(mrg.value_pbi, mrg.value_exports, rtol=0, atol=1e-12)))
check("supervised_results: no duplicate (experiment, model, metric, split, status)", not sr.duplicated(KEY).any())
check("experiments.csv declares E1-E5 and every result row belongs to one of them",
      sorted(ex.experiment_id) == ["E1", "E2", "E3", "E4", "E5"] and set(sr.experiment_id) == set(ex.experiment_id))
check("every status is VALID / BASELINE / REFERENCE / INVALID", set(sr.status) <= {"VALID", "BASELINE", "REFERENCE", "INVALID"}, sorted(set(sr.status)))
check("every INVALID row belongs to a leakage run (model name says LEAKAGE)", sr[sr.status == "INVALID"].model.str.contains("LEAKAGE").all())
e5 = sr[(sr.experiment_id == "E5") & (sr.model == "Linear Regression") & (sr.split_type == "test") & (sr.status == "VALID")].set_index("metric").value
err = t.calorie_error
r2 = 1 - (err ** 2).sum() / ((t.calories_burned - t.calories_burned.mean()) ** 2).sum()
check("E5 test MAE == mean |error| over fact_daily test rows", abs(e5["MAE (kcal)"] - err.abs().mean()) < 0.05, f"{e5['MAE (kcal)']:.2f}")
check("E5 test RMSE == sqrt(mean error^2) over fact_daily test rows", abs(e5["RMSE (kcal)"] - np.sqrt((err ** 2).mean())) < 0.05, f"{e5['RMSE (kcal)']:.2f}")
check("E5 test R2 recomputed from fact_daily", abs(e5["R2"] - r2) < 0.001, f"{e5['R2']:.4f}")
base5 = sr[(sr.experiment_id == "E5") & (sr.model == "Baseline: training mean") & (sr.split_type == "test") & (sr.status == "BASELINE") & (sr.metric == "MAE (kcal)")].value.iloc[0]
check("E5 baseline MAE == mean |actual - training mean| over fact_daily test rows",
      abs(base5 - (t.calories_burned - f[f.model_split == "train"].calories_burned.mean()).abs().mean()) < 0.05, f"{base5:.2f}")
check("E5 test row count == fact_daily test rows", len(t) == 14985)
check("fact_daily has the error_bin column for the histogram", "error_bin_kcal" in f.columns)
leak = sr[(sr.status == "INVALID") & sr.metric.isin(["ROC AUC", "R2"])]
runs = sr[sr.status == "INVALID"][["experiment_id", "model"]].drop_duplicates()
check("leakage table (INVALID rows of ROC AUC / R2) has exactly one row per leakage run", len(leak) == len(runs) and not leak.duplicated(["experiment_id", "model"]).any(), f"{len(leak)} rows")
cmp_rows = sr[sr.status.isin(["VALID", "BASELINE"]) & sr.split_type.isin(md.HEADLINE_SPLITS) & sr.metric.isin(md.COMPARE_METRICS)]
check("model-comparison table: one value per (experiment, model, split, metric) - MAX hides nothing", not cmp_rows.duplicated(["experiment_id", "model", "split_type", "metric"]).any(), f"{len(cmp_rows)} rows")
auc_rows = sr[(sr.status == "VALID") & (sr.metric == "ROC AUC") & sr.split_type.isin(md.HEADLINE_SPLITS)]
check("ROC-AUC chart: one value per (experiment, split, model)", not auc_rows.duplicated(["experiment_id", "split_type", "model"]).any(), f"{len(auc_rows)} rows")
cc_src = pd.read_csv(ROOT / "faculty_evidence" / "supervised" / "hdfs_rerun" / "sklearn_crosscheck.csv")
per = {k: {"count": int(v["count"]), "sum": int(v["sum"])} for k, v in cc.groupby("experiment_id").passed.agg(["count", "sum"]).to_dict("index").items()}
per_src = {k: {"count": int(v["count"]), "sum": int(v["sum"])} for k, v in cc_src.assign(p=cc_src["pass"].astype(int)).groupby("experiment").p.agg(["count", "sum"]).to_dict("index").items()}
check("crosscheck.csv equals the HDFS-rerun cross-check file (rows and passes, per experiment)", len(cc) == len(cc_src) and per == per_src, f"{int(cc.passed.sum())}/{len(cc)} passed")

# column inventory for the .pbix checker (scripts/check_pbix.py)
schema = {p.stem: list(pd.read_csv(p, nrows=0).columns) for p in sorted(D.glob("*.csv"))}
(D / "_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
for p in sorted(D.glob("*.csv")):
    d_ = pd.read_csv(p)
    print(f"  {p.name:24s} rows={len(d_):>7,} missing_cells={int(d_.isna().sum().sum())} duplicate_rows={int(d_.duplicated().sum())}")
sys.exit(1 if bad else 0)
