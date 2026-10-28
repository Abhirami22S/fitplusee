"""
FitPulse - compare the LOCAL run of the supervised experiments (exports/E<n>_results.csv) with the HDFS re-run
(faculty_evidence/supervised/hdfs_rerun/exports/E<n>_results.csv) for EVERY metric of E1-E5.

* rows are matched on (experiment_id, model, metric, split_type); a row present on one side only is reported as MISSING
* a difference larger than the threshold (default 0.001, absolute) is flagged; nothing is adjusted or rounded to make the runs agree
* feature-importance values, the split sizes and the tuned settings stored in E<n>_run_info.json are compared as well

    python scripts/compare_local_vs_hdfs.py [--threshold 0.001]
Writes faculty_evidence/supervised/local_vs_hdfs_comparison.csv (all rows), local_vs_hdfs_flags.csv (flagged rows only) and
local_vs_hdfs_summary.md.  Exit code 1 if anything is flagged or missing, 0 otherwise.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LOCAL_EX = ROOT / "exports"
LOCAL_EV = ROOT / "faculty_evidence" / "supervised"
HDFS_EV = LOCAL_EV / "hdfs_rerun"
HDFS_EX = HDFS_EV / "exports"
EXPERIMENTS = ["E1", "E2", "E3", "E4", "E5"]
KEY = ["experiment_id", "model", "metric", "split_type"]


def compare_frames(loc, hdf, key, value, threshold, what):
    m = loc.merge(hdf, on=key, how="outer", suffixes=("_local", "_hdfs"), indicator=True)
    m["abs_diff"] = (m[value + "_local"] - m[value + "_hdfs"]).abs()
    m["rel_diff"] = m["abs_diff"] / m[value + "_local"].abs().where(m[value + "_local"].abs() > 0)
    m["flag"] = ""
    m.loc[m["_merge"] != "both", "flag"] = "MISSING"
    m.loc[(m["_merge"] == "both") & (m["abs_diff"] > threshold), "flag"] = "DIFF>" + str(threshold)
    m.insert(0, "what", what)
    return m.drop(columns="_merge")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.001)
    a = ap.parse_args()
    th = a.threshold
    res_parts, fi_parts, info_rows = [], [], []
    for e in EXPERIMENTS:
        lp, hp = LOCAL_EX / f"{e}_results.csv", HDFS_EX / f"{e}_results.csv"
        if not (lp.exists() and hp.exists()):
            print(f"{e}: missing file ({lp.exists()=}, {hp.exists()=}) - cannot compare")
            info_rows.append({"experiment": e, "item": "results file present on both sides", "local": lp.exists(), "hdfs": hp.exists(), "flag": "MISSING"})
            continue
        loc, hdf = pd.read_csv(lp), pd.read_csv(hp)
        # status must match too (VALID / INVALID / BASELINE / REFERENCE)
        r = compare_frames(loc.drop(columns="status"), hdf.drop(columns="status"), KEY, "value", th, "metric")
        st = loc[KEY + ["status"]].merge(hdf[KEY + ["status"]], on=KEY, how="outer", suffixes=("_local", "_hdfs"))
        r = r.merge(st, on=KEY, how="left")
        r.loc[(r.status_local != r.status_hdfs) & (r.flag == ""), "flag"] = "STATUS"
        res_parts.append(r)
        fl, fh = pd.read_csv(LOCAL_EX / f"{e}_feature_importance.csv"), pd.read_csv(HDFS_EX / f"{e}_feature_importance.csv")
        fi_parts.append(compare_frames(fl[["experiment_id", "model", "feature", "importance"]], fh[["experiment_id", "model", "feature", "importance"]],
                                       ["experiment_id", "model", "feature"], "importance", th, "feature importance"))
        li = json.loads((LOCAL_EV / f"{e}_run_info.json").read_text())
        hi = json.loads((HDFS_EV / f"{e}_run_info.json").read_text())
        for item in ("rows", "settings", "seed"):
            if item in li or item in hi:
                same = li.get(item) == hi.get(item)
                info_rows.append({"experiment": e, "item": item, "local": json.dumps(li.get(item)), "hdfs": json.dumps(hi.get(item)), "flag": "" if same else "DIFF"})
        info_rows.append({"experiment": e, "item": "storage_mode", "local": li.get("storage_mode"), "hdfs": hi.get("storage_mode"),
                          "flag": "" if (li.get("storage_mode"), hi.get("storage_mode")) == ("local", "hdfs") else "UNEXPECTED"})
    res = pd.concat(res_parts, ignore_index=True)
    fi = pd.concat(fi_parts, ignore_index=True) if fi_parts else pd.DataFrame()
    info = pd.DataFrame(info_rows)
    allr = pd.concat([res, fi], ignore_index=True, sort=False)
    allr.to_csv(LOCAL_EV / "local_vs_hdfs_comparison.csv", index=False)
    flagged = allr[allr.flag != ""]
    flagged.to_csv(LOCAL_EV / "local_vs_hdfs_flags.csv", index=False)
    info.to_csv(LOCAL_EV / "local_vs_hdfs_run_info.csv", index=False)

    lines = [f"# Local vs HDFS comparison (threshold: absolute difference > {th})", "",
             "| experiment | metric rows compared | max abs diff (metrics) | metric rows differing > 1e-6 | flagged metric rows | feature-importance rows | max abs diff (importance) | flagged importance rows |",
             "|---|---|---|---|---|---|---|---|"]
    for e in EXPERIMENTS:
        m = res[res.experiment_id == e]
        f = fi[fi.experiment_id == e] if len(fi) else fi
        if m.empty:
            lines.append(f"| {e} | not compared | | | | | | |")
            continue
        lines.append(f"| {e} | {int((m.flag != 'MISSING').sum())} | {m.abs_diff.max():.3g} | {int((m.abs_diff > 1e-6).sum())} | {int((m.flag != '').sum())} | "
                     f"{len(f)} | {f.abs_diff.max():.3g} | {int((f.flag != '').sum())} |")
    lines += ["", f"Flagged rows in total: **{len(flagged)}** (see local_vs_hdfs_flags.csv).", ""]
    if len(info):
        lines += ["## Run settings and split sizes", "", "| experiment | item | local | HDFS | flag |", "|---|---|---|---|---|"]
        lines += [f"| {r.experiment} | {r.item} | {r.local} | {r.hdfs} | {r.flag} |" for r in info.itertuples()]
    (LOCAL_EV / "local_vs_hdfs_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    bad_info = info[info.flag != ""]
    if len(flagged) or len(bad_info):
        print("\nFLAGGED / MISSING:")
        cols = [c for c in KEY + ["feature", "value_local", "value_hdfs", "importance_local", "importance_hdfs", "abs_diff", "flag"] if c in flagged.columns]
        print(flagged[cols].to_string(index=False) if len(flagged) else "(no metric / importance rows)")
        if len(bad_info):
            print(bad_info.to_string(index=False))
        sys.exit(1)
    print("\nNo metric differs by more than the threshold.")


if __name__ == "__main__":
    main()
