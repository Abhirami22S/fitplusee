"""
Why does Spark's K-Means silhouette (0.3413 at K=2) differ from the REPORT's 0.2018?
Hypothesis: Spark's ClusteringEvaluator(distanceMeasure="squaredEuclidean") uses squared distances, whereas the REPORT's
scikit-learn numbers use plain Euclidean distance. This script recomputes BOTH definitions on the same 437 standardised
user vectors, and also re-runs scikit-learn K-Means for K = 2..10 to compare with the REPORT's Table 15.
Output: faculty_evidence/report_aligned/kmeans_silhouette_definition_check.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "faculty_evidence" / "report_aligned"
s = pd.read_parquet(ROOT / "data" / "processed" / "fitpulse_silver")
s["ir"] = s.active_minutes / (s.active_minutes + s.sedentary_minutes)
u = s.groupby("user_id").agg(AvgSteps=("steps", "mean"), AvgActiveMin=("active_minutes", "mean"), AvgSedentaryMin=("sedentary_minutes", "mean"),
                             AvgCalories=("calories_burned", "mean"), AvgHeartRate=("avg_heart_rate", "mean"), AvgSleep=("sleep_minutes", "mean"),
                             AvgIntensity=("ir", "mean"))
X = ((u - u.mean()) / u.std(ddof=1)).to_numpy()          # Spark StandardScaler uses the sample std (ddof=1)
rows = []
for k in range(2, 11):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    rows.append({"K": k, "sklearn_WCSS": km.inertia_, "sklearn_silhouette_euclidean": silhouette_score(X, km.labels_),
                 "sklearn_silhouette_squared_euclidean": silhouette_score(X ** 2 if False else X, km.labels_, metric="sqeuclidean")})
seg = pd.read_csv(EV / "kmeans_user_segments.csv").set_index("user_id").loc[u.index, "cluster"].to_numpy()
spark_labels_eu = silhouette_score(X, seg)
spark_labels_sq = silhouette_score(X, seg, metric="sqeuclidean")
df = pd.DataFrame(rows)
df.to_csv(EV / "kmeans_silhouette_definition_check.csv", index=False)
print(df.round(4).to_string(index=False))
print(f"\nSpark's K=2 labels scored by sklearn: euclidean {spark_labels_eu:.4f}, squared-euclidean {spark_labels_sq:.4f}")
(EV / "kmeans_silhouette_definition_check.txt").write_text(
    df.round(4).to_string(index=False) + f"\n\nSpark's selected K=2 assignment scored with scikit-learn: "
    f"euclidean silhouette {spark_labels_eu:.4f}, squared-euclidean silhouette {spark_labels_sq:.4f}\n", encoding="utf-8")
