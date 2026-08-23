"""
FitPulse - Model 4: Abnormal Heart Rate / Health Risk Flagging
=================================================================
Business question this answers: "Was there anything unusual about my heart
rate today, relative to MY OWN normal?" Framed deliberately as "worth a
look" — this is anomaly detection, not a medical diagnosis, and the
dashboard copy must never claim otherwise.

Algorithm: Isolation Forest (unsupervised anomaly detection), fit
PER-USER on that user's own heart-rate-related features (resting HR, avg
HR, max HR, plus how far each is from that user's own rolling baseline).
Isolation Forest was chosen over a global model because "abnormal" only
makes sense relative to an individual's own baseline — a resting heart
rate of 80 bpm might be completely normal for one person and a real
outlier for another whose baseline is 58 bpm.

A simple fallback is also computed and reported: a per-user z-score /
IQR threshold method, which is easier to explain in a viva ("more than 2
standard deviations from your own average") if asked to justify Isolation
Forest with something simpler.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

SILVER_PATH = "data/processed/fitpulse_silver"
FEATURES = ["resting_heart_rate", "avg_heart_rate", "max_heart_rate"]
CONTAMINATION = 0.03  # expect ~3% of any user's days to be flagged as unusual


def zscore_fallback(udf: pd.DataFrame) -> pd.Series:
    """Simple, easy-to-explain fallback: flag a day if any HR metric is >2.5 SD from that user's mean."""
    z = (udf[FEATURES] - udf[FEATURES].mean()) / udf[FEATURES].std(ddof=0).replace(0, 1)
    return (z.abs() > 2.5).any(axis=1).astype(int)


def main():
    df = pd.read_parquet(SILVER_PATH).sort_values(["user_id", "date"])

    iso_flags, zscore_flags = [], []
    models = {}
    for uid, udf in df.groupby("user_id"):
        if len(udf) < 20:
            continue
        model = IsolationForest(contamination=CONTAMINATION, random_state=42, n_estimators=150)
        pred = model.fit_predict(udf[FEATURES])  # -1 = anomaly, 1 = normal
        iso_flags.append(pd.Series((pred == -1).astype(int), index=udf.index))
        zscore_flags.append(zscore_fallback(udf))
        models[uid] = model

    iso_series = pd.concat(iso_flags)
    z_series = pd.concat(zscore_flags)

    print(f"Users modeled: {len(models)}")
    print(f"Isolation Forest flagged {iso_series.sum():,} / {len(iso_series):,} days "
          f"({iso_series.mean()*100:.1f}%) as anomalous")
    print(f"Z-score fallback flagged {z_series.sum():,} / {len(z_series):,} days "
          f"({z_series.mean()*100:.1f}%) as anomalous")
    agreement = (iso_series.reindex(z_series.index) == z_series).mean()
    print(f"Agreement between the two methods: {agreement*100:.1f}% of days")

    joblib.dump(models, "models/artifacts/anomaly_models_per_user.joblib")
    print("\nSaved per-user Isolation Forest models to models/artifacts/anomaly_models_per_user.joblib")

    return {
        "isolation_forest_flag_rate_pct": round(iso_series.mean() * 100, 2),
        "zscore_fallback_flag_rate_pct": round(z_series.mean() * 100, 2),
        "method_agreement_pct": round(agreement * 100, 1),
    }


if __name__ == "__main__":
    main()
