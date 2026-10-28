"""
FitPulse - Streamlit dashboard validation (headless, executes the real app with streamlit.testing.v1.AppTest).

    python scripts/test_dashboard.py          # exit code 1 if any check fails
Writes faculty_evidence/dashboard/dashboard_validation.json and .md (actual results only).

Data source of the dashboard (documented, not changed): LOCAL SQLite `dashboard/fitpulse.db`
(built by etl/load_to_sqlite.py from the LOCAL Silver Parquet) + local joblib models. It does not read HDFS.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from streamlit.testing.v1 import AppTest  # noqa: E402

EVID = ROOT / "faculty_evidence" / "dashboard"
EVID.mkdir(parents=True, exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "passed": bool(ok), "detail": str(detail)[:400]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def exceptions(at):
    return [str(e.value)[:300] for e in at.exception]


def login(at, user, pw):
    at.text_input[0].set_value(user)
    at.text_input[1].set_value(pw)
    submit = [b for b in at.button if "Log in" in str(b.label)]
    submit[0].click()
    at.run(timeout=120)


def main():
    # 1. database + artifacts
    con = sqlite3.connect(ROOT / "dashboard" / "fitpulse.db")
    counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0]
              for t in ["user_daily_metrics", "population_percentiles", "users", "user_daily_raw"]}
    check("SQLite connectivity + tables", counts["user_daily_metrics"] == 100122, counts)
    import joblib
    for f in ["goal_achievement_model", "forecast_model", "sleep_quality_model"]:
        try:
            joblib.load(ROOT / "models" / "artifacts" / f"{f}.joblib")
            check(f"model loads: {f}", True)
        except Exception as e:
            check(f"model loads: {f}", False, e)

    # 2. login screen
    at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=120).run()
    check("App starts (login screen, no exception)", not at.exception and len(at.text_input) >= 2, exceptions(at))

    # 3. wrong password -> understandable error
    login(at, "demo1", "wrong-password")
    check("Wrong password gives an error message, no crash", len(at.error) > 0 and not at.exception,
          [e.value for e in at.error])

    # 4. demo login, full dashboard
    for user in ["demo1", "demo2", "demo3"]:
        at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=120).run()
        t0 = time.time()
        login(at, user, "demo123")
        tabs = [t.label for t in at.tabs]
        check(f"{user}: dashboard renders without exception", not at.exception and len(at.tabs) >= 7,
              f"{len(at.tabs)} tabs, {len(at.metric)} metrics, {time.time()-t0:.1f}s, {exceptions(at)}")
        if user == "demo1":
            check("demo1: key sections present", any("Trends" in t for t in tabs) and any("Sleep" in t for t in tabs)
                  and any("Recommendations" in t for t in tabs), tabs)
            check("demo1: Calories & Segments tab present", any("Calories" in t for t in tabs), tabs)
            md_text = " ".join(m.value for m in at.markdown)
            check("demo1: fitness score, segment and monthly sections rendered",
                  "fitness score" in md_text and "Your activity segment" in md_text and "Monthly trends" in md_text)
            check("demo1: calorie model section rendered or reports a clear message",
                  "Actual vs predicted calories" in md_text and not at.exception)
            df = at.session_state["auth_user"]
            check("demo1: authenticated as the demo user id", df.get("user_id") == 1503, df)

    # 5. missing database -> understandable error, not a stack trace
    tmp = Path(tempfile.mkdtemp(prefix="fp_nodb_"))
    try:
        shutil.copytree(ROOT / "dashboard", tmp / "dashboard", ignore=shutil.ignore_patterns("fitpulse.db", "__pycache__"))
        shutil.copytree(ROOT / "models", tmp / "models", ignore=shutil.ignore_patterns("artifacts", "__pycache__", ".ipynb_checkpoints"))
        os.chdir(tmp)
        at = AppTest.from_file(str(tmp / "dashboard" / "app.py"), default_timeout=60).run()
        os.chdir(ROOT)
        check("Missing database: friendly st.error and no uncaught exception", len(at.error) > 0 and not at.exception,
              ([e.value for e in at.error] or exceptions(at)))
    finally:
        os.chdir(ROOT)
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(r["passed"] for r in results)
    summary = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "passed": passed, "total": len(results), "checks": results,
               "data_source": "local SQLite dashboard/fitpulse.db + local joblib models (not HDFS)"}
    (EVID / "dashboard_validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = ["# Dashboard validation (streamlit AppTest)", f"Run: {summary['timestamp']} - **{passed}/{len(results)} passed**",
          f"Data source: {summary['data_source']}", "", "| Check | Result | Detail |", "|---|---|---|"]
    md += [f"| {r['check']} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail'][:160].replace('|', '/')} |" for r in results]
    (EVID / "dashboard_validation.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
