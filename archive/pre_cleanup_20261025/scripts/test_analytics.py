"""
FitPulse - independent checks of the new analytics (run after models/train_calorie_regression.py and
archive/kmeans/spark_report_kmeans.py, whose saved output files are still read).  Exit code 1 if any check fails.  Output: faculty_evidence/analytics_validation.json

 1. Serving-time formula (models/analytics.py, coefficients from JSON) reproduces the Spark MLlib predictions row by row.
 2. MAE / RMSE / R2 recomputed from regression_predictions.csv (pandas/numpy, test rows) equal the metrics Spark reported.
 3. Re-computing the mean baseline from the TRAIN rows gives the baseline numbers (no leakage in the reported comparison).
 4. K-Means: nearest-centroid assignment in analytics.py reproduces Spark's cluster for every one of the 437 users.
 5. Monthly summary / score / guidance sanity checks against the Silver data.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import analytics  # noqa: E402

EV = ROOT / "faculty_evidence"
res = []


def check(name, ok, detail=""):
    res.append({"check": name, "passed": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def main():
    silver = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
    silver["date"] = pd.to_datetime(silver["date"])
    cfg = analytics.load_calorie_config()
    pred = pd.read_csv(EV / "regression_predictions.csv", parse_dates=["date"])
    m = silver.merge(pred[["user_id", "date", "predicted_calories", "split", "actual_calories"]], on=["user_id", "date"], how="inner")
    check("prediction file covers every Silver row", len(m) == len(silver) == len(pred), f"{len(m):,} rows")
    mine = analytics.predict_calories(m, cfg)
    maxdiff = float((mine - m["predicted_calories"]).abs().max())
    check("serving formula == Spark MLlib predictions (max |diff| < 0.01 kcal; Spark file is rounded to 0.01)", maxdiff < 0.01, f"max diff {maxdiff:.5f}")
    check("actual_calories column equals Silver calories_burned", np.allclose(m["actual_calories"], m["calories_burned"]))

    t = m[m["split"] == "test"]
    err = t["calories_burned"] - mine[t.index]
    mae, rmse = float(err.abs().mean()), float(np.sqrt((err ** 2).mean()))
    r2 = float(1 - (err ** 2).sum() / ((t["calories_burned"] - t["calories_burned"].mean()) ** 2).sum())
    tm = cfg["test_metrics"]
    check("test MAE recomputed independently == Spark's", abs(mae - tm["MAE"]) < 0.05, f"{mae:.3f} vs {tm['MAE']:.3f}")
    check("test RMSE recomputed independently == Spark's", abs(rmse - tm["RMSE"]) < 0.05, f"{rmse:.3f} vs {tm['RMSE']:.3f}")
    check("test R2 recomputed independently == Spark's", abs(r2 - tm["R2"]) < 0.001, f"{r2:.4f} vs {tm['R2']:.4f}")
    tr_mean = m.loc[m["split"] == "train", "calories_burned"].mean()
    base_mae = float((t["calories_burned"] - tr_mean).abs().mean())
    check("baseline (train mean) MAE recomputed == reported", abs(base_mae - cfg["baseline_mean_test_metrics"]["MAE"]) < 0.05,
          f"{base_mae:.3f} vs {cfg['baseline_mean_test_metrics']['MAE']:.3f}")
    check("model beats the baseline on test MAE", mae < base_mae, f"{mae:.1f} < {base_mae:.1f}")
    check("no leakage columns among features", not set(cfg["numeric_features"]) & {"calories_lag1", "calories_roll7_avg", "daily_calorie_goal", "calories_burned"})

    # K-Means
    seg_path = ROOT / "models" / "artifacts" / "kmeans_user_segments_model.json"
    if seg_path.exists():
        sm = analytics.load_segment_model()
        spark_seg = pd.read_csv(EV / "report_aligned" / "kmeans_user_segments.csv").set_index("user_id")["cluster"]
        agree = 0
        for uid, g in silver.groupby("user_id"):
            agree += int(analytics.assign_segment(g, sm)["cluster"] == spark_seg.loc[uid])
        check("nearest-centroid assignment reproduces Spark cluster for every user", agree == len(spark_seg), f"{agree}/{len(spark_seg)}")
    else:
        check("K-Means segment model exists", False, f"{seg_path} missing")

    # misc
    u = silver[silver.user_id == 1503].sort_values("date")
    ms = analytics.monthly_summary(u)
    check("monthly summary day counts add up", int(ms["days"].sum()) == len(u), f"{int(ms['days'].sum())} == {len(u)}")
    check("monthly avg steps matches pandas groupby",
          np.allclose(ms["avg_steps"], u.groupby(u.date.dt.strftime("%Y-%m"))["steps"].mean().values))
    fs = analytics.fitness_score(u)
    check("fitness score within 0..100 and weights sum to 1", 0 <= fs["score"] <= 100 and abs(sum(fs["weights"].values()) - 1) < 1e-9, f"{fs['score']:.1f}")
    g = [analytics.goal_guidance(p)["band"].split()[0] for p in (0.9, 0.5, 0.1)]
    check("probability bands: high -> On track, mid -> Uncertain, low -> At risk", g == ["On", "Uncertain", "At"], g)

    passed = sum(r["passed"] for r in res)
    (EV / "analytics_validation.json").write_text(json.dumps({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "passed": passed,
                                                              "total": len(res), "checks": res}, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(res)} checks passed")
    sys.exit(0 if passed == len(res) else 1)


if __name__ == "__main__":
    main()
