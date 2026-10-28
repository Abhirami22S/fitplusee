"""
FitPulse - E2 "no future information" check over ALL users (not only the 25 sampled by scripts/sup_sklearn_crosscheck.py)
==========================================================================================================================
For every user: alter the user's rows from the middle row's date (the "cut day") onward (steps, calories, active minutes, sleep,
resting heart rate, stress -> value*3 + 1000), rebuild the E2 window features with the independent pandas implementation
(`e2_features` in sup_sklearn_crosscheck.py) and compare.

  corrected window : days up to and INCLUDING the cut day -> their features must not change (tolerance 1e-9, as in the cross-check)
  defective window : the earlier cross-check window = the corrected window PLUS the first kept day on or after the cut day. When the
                     cut day itself is not a kept row (logging gap), that day lies AFTER the cut and legitimately uses altered days.

Writes faculty_evidence/supervised/E2_nofuture_allusers_check.csv (one row per user). Refuses to overwrite an existing file.
    python scripts/e2_nofuture_allusers_check.py
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import sup_sklearn_crosscheck as x

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "faculty_evidence" / "supervised" / "E2_nofuture_allusers_check.csv"
TOL = 1e-9
ALTERED = ("steps", "calories_burned", "active_minutes", "sleep_quality_score", "sleep_minutes", "resting_heart_rate", "stress_level")


def main():
    if OUT.exists():
        sys.exit(f"{OUT} already exists - not overwriting")
    s = x.silver()
    cols = x.E2_NUM[:12]                                    # the history-derived features, as in the cross-check
    sample = set(np.random.default_rng(x.SEED).choice(s.user_id.unique(), 25, replace=False).tolist())   # same draw as the cross-check
    rows = []
    for u, su in s.groupby("user_id"):
        su = su.sort_values("date")
        cut = su.date.iloc[len(su) // 2]
        pert = su.copy()
        msk = pert.date >= cut
        for c in ALTERED:
            pert.loc[msk, c] = pert.loc[msk, c] * 3 + 1000
        a = x.e2_features(su).set_index("date")
        b = x.e2_features(pert).set_index("date")
        first = a.index[a.index >= cut][0] if (a.index >= cut).any() else None
        before = a.index[a.index <= cut]
        new_idx = [i for i in before if i in b.index]
        old_idx = [i for i in (list(before) + ([first] if first is not None and first not in before else [])) if i in b.index]
        diff = lambda idx: float((a.loc[idx, cols] - b.loc[idx, cols]).abs().max().max()) if len(idx) else float("nan")
        rows.append({"user_id": int(u), "n_rows": len(su), "cut_day": cut.date().isoformat(), "cut_is_kept_row": bool(cut in a.index),
                     "in_original_25_sample": int(u) in sample, "days_compared_corrected": len(new_idx),
                     "max_change_corrected_window": diff(new_idx), "max_change_defective_window": diff(old_idx)})
    r = pd.DataFrame(rows)
    r["pass_corrected_window"] = r.max_change_corrected_window <= TOL
    r["flagged_by_defective_window"] = r.max_change_defective_window > TOL
    r.to_csv(OUT, index=False)
    print(f"{len(r)} users | corrected window: {int(r.pass_corrected_window.sum())} pass, max change {r.max_change_corrected_window.max():.3g} | "
          f"defective window flagged {int(r.flagged_by_defective_window.sum())} users | cut day not a kept row: {int((~r.cut_is_kept_row).sum())}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
