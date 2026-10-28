"""
FitPulse - ML re-validation on the Silver dataset READ FROM HDFS.

Re-executes the notebook's *own* code cells (feature set, 70/15/15 split, Random Forest, K-Means) unchanged,
but with `silver = spark.read.parquet(hdfs://.../fitpulse/silver)` and all evidence files redirected to
faculty_evidence/hdfs/ml/ so the previously executed notebook evidence is never overwritten.
It then compares each result file with the one from the earlier local-Parquet run and reports every difference.

    python scripts/hdfs_ml_validation.py --hdfs-uri hdfs://localhost:9000
Exit code: 0 = ran and all compared metrics identical, 1 = ran but something differs, 2 = could not run.
"""
import argparse
import contextlib
import io
import json
import os
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "etl"))
import storage  # noqa: E402

OUT = ROOT / "faculty_evidence" / "hdfs" / "ml"
CELLS_SETUP = [3, 4, 9]                   # env/imports, helpers, Spark session
CELLS_ML = list(range(41, 100))           # feature set .. K-Means user mix (code cells only)
COMPARE = ["classification_results.csv", "confusion_matrix.csv", "rf_validation_tuning.csv", "split_summary.csv",
           "rf_feature_importance.csv", "classification_split_comparison.csv", "silhouette_scores.csv",
           "cluster_summary.csv"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hdfs-uri", required=True)
    ap.add_argument("--silver", default="/fitpulse/silver")
    a = ap.parse_args()
    try:
        cfg = storage.resolve("hdfs", a.hdfs_uri, output_path=a.silver)
        storage.require_hdfs(cfg)
    except storage.HdfsUnavailable as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(2)
    OUT.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    nb = json.loads((ROOT / "FitPulse_Faculty_Demo.ipynb").read_text(encoding="utf-8"))
    code = {i: "".join(c["source"]) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code"}
    ns = {"__name__": "__hdfs_ml__"}
    log = io.StringIO()
    t0 = time.time()

    def run(i):
        with contextlib.redirect_stdout(log):
            exec(compile(code[i], f"<notebook cell {i}>", "exec"), ns)

    try:
        for i in CELLS_SETUP:
            run(i)
        ns["EVIDENCE"] = OUT                                    # redirect every to_csv / savefig
        spark = ns["spark"]
        silver = spark.read.parquet(cfg.output_path)            # <-- the HDFS read
        ns["silver"] = silver
        n = silver.count()
        header = (f"STORAGE MODE: {cfg.label()}\nSilver read from: {cfg.output_path}\n"
                  f"rows={n:,} columns={len(silver.columns)}\n\n")
        print(header)
        log.write(header)
        for i in CELLS_ML:
            if i in code:
                run(i)
        ns["spark"].stop()
    except Exception:
        (OUT / "ml_validation_log.txt").write_text(log.getvalue() + "\n" + traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        sys.exit(2)
    (OUT / "ml_validation_log.txt").write_text(log.getvalue(), encoding="utf-8")

    # ---- compare with the earlier (local Parquet) run ----
    lines = [f"# ML re-validation: Silver from HDFS vs earlier local-Parquet run",
             f"Silver source: {cfg.output_path} ({n:,} rows). Elapsed {time.time()-t0:.0f}s.\n"]
    all_same = True
    for f in COMPARE:
        old_p, new_p = ROOT / "faculty_evidence" / f, OUT / f
        if not old_p.exists() or not new_p.exists():
            lines.append(f"- {f}: MISSING ({'old' if not old_p.exists() else 'new'})")
            all_same = False
            continue
        old, new = pd.read_csv(old_p), pd.read_csv(new_p)
        if old.shape != new.shape or list(old.columns) != list(new.columns):
            lines.append(f"- {f}: SHAPE/COLUMNS DIFFER old={old.shape} new={new.shape}")
            all_same = False
            continue
        num = old.select_dtypes("number").columns
        maxdiff = float((old[num] - new[num]).abs().max().max()) if len(num) else 0.0
        nonnum_same = old.drop(columns=num).equals(new.drop(columns=num))
        same = maxdiff == 0.0 and nonnum_same
        # Training-time columns legitimately differ run to run
        if "Train time (s)" in num and maxdiff > 0:
            n2 = [c for c in num if c != "Train time (s)"]
            md2 = float((old[n2] - new[n2]).abs().max().max())
            lines.append(f"- {f}: max |diff| excluding wall-clock 'Train time (s)' = {md2:.3g}")
            same = md2 == 0.0 and nonnum_same
        else:
            lines.append(f"- {f}: max |numeric diff| = {maxdiff:.3g}; non-numeric identical = {nonnum_same}")
        all_same &= same
    lines.append("\nRESULT: " + ("all compared files IDENTICAL" if all_same else "DIFFERENCES FOUND - investigate"))
    (OUT / "comparison_with_local_run.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if all_same else 1)


if __name__ == "__main__":
    main()
