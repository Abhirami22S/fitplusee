"""
FitPulse - REPORT-aligned K-Means (Spark MLlib): 437 USER-level segments
=========================================================================
Implements REPORT section 3 (Listings 5-9, Tables 13, 15, 16, Figures 4-5) which the repository did not contain
(report numbers came from scikit-learn). Different experiment from the faculty notebook, which clusters user-DAYS.

Per-user averages of: steps, active_minutes, sedentary_minutes, calories_burned, avg_heart_rate, sleep_minutes and
intensity_ratio = active / (active + sedentary).  StandardScaler(withMean, withStd) -> KMeans K = 2..10 (seed 42, maxIter 50).
K is chosen by the highest silhouette (ClusteringEvaluator, squaredEuclidean). Segment labels are derived from the
measured cluster averages (relative active time), never assumed.

Writes to faculty_evidence/report_aligned/: kmeans_evaluation.csv, kmeans_cluster_summary.csv, kmeans_user_segments.csv,
kmeans_user_range.csv, kmeans_pca.png, kmeans_elbow_silhouette.png
"""
import argparse

import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.feature import PCA, StandardScaler, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

import spark_common as sc

FEATURES = ["AvgSteps", "AvgActiveMin", "AvgSedentaryMin", "AvgCalories", "AvgHeartRate", "AvgSleep", "AvgIntensity"]


def main():
    ap = argparse.ArgumentParser()
    sc.add_storage_args(ap)
    args = ap.parse_args()
    out = sc.out_dir(args) / "report_aligned"
    out.mkdir(parents=True, exist_ok=True)
    spark, silver, cfg = sc.open_silver(args, "FitPulse-Report-KMeans")

    df = silver.withColumn("intensity_ratio", F.col("active_minutes") / (F.col("active_minutes") + F.col("sedentary_minutes")))
    user_df = (df.groupBy("user_id").agg(
        F.avg("steps").alias("AvgSteps"), F.avg("active_minutes").alias("AvgActiveMin"),
        F.avg("sedentary_minutes").alias("AvgSedentaryMin"), F.avg("calories_burned").alias("AvgCalories"),
        F.avg("avg_heart_rate").alias("AvgHeartRate"), F.avg("sleep_minutes").alias("AvgSleep"),
        F.avg("intensity_ratio").alias("AvgIntensity")).dropna())
    n_users = user_df.count()
    print("users:", n_users)
    rng = user_df.agg(*[F.min(c).alias(c + "_min") for c in FEATURES], *[F.max(c).alias(c + "_max") for c in FEATURES]).first().asDict()
    pd.DataFrame([{"feature": c, "min": rng[c + "_min"], "max": rng[c + "_max"]} for c in FEATURES]).to_csv(out / "kmeans_user_range.csv", index=False)

    vec = VectorAssembler(inputCols=FEATURES, outputCol="raw_features").transform(user_df)
    scaler_model = StandardScaler(inputCol="raw_features", outputCol="features", withMean=True, withStd=True).fit(vec)
    scaled = scaler_model.transform(vec).cache()
    ev = ClusteringEvaluator(featuresCol="features", predictionCol="cluster", metricName="silhouette", distanceMeasure="squaredEuclidean")

    rows, models = [], {}
    for k in range(2, 11):
        m = KMeans(featuresCol="features", predictionCol="cluster", k=k, seed=sc.SEED, maxIter=50).fit(scaled)
        p = m.transform(scaled)
        rows.append({"K": k, "WCSS": m.summary.trainingCost, "Silhouette": ev.evaluate(p)})
        models[k] = m
    kev = pd.DataFrame(rows)
    kev.to_csv(out / "kmeans_evaluation.csv", index=False)
    print(kev.round(4).to_string(index=False))
    best_k = int(kev.loc[kev.Silhouette.idxmax(), "K"])
    print("selected K (highest silhouette):", best_k)

    clustered = models[best_k].transform(scaled)
    prof = (clustered.groupBy("cluster").agg(F.count("*").alias("Users"), *[F.round(F.avg(c), 2).alias(c) for c in FEATURES])
            .orderBy("cluster").toPandas())
    # labels from measured relative active time
    order = prof["AvgActiveMin"].rank(method="first").astype(int)
    labels = {1: "Lowest active-time", len(prof): "Highest active-time"}
    prof["Segment label (from measured AvgActiveMin rank)"] = [labels.get(r, f"Active-time rank {r}") for r in order]
    prof.to_csv(out / "kmeans_cluster_summary.csv", index=False)
    print(prof.to_string(index=False))

    # model definition for the dashboard (assign any user to the nearest centroid; no Spark needed at serve time)
    import json
    seg_labels = dict(zip(prof["cluster"].astype(int), prof["Segment label (from measured AvgActiveMin rank)"]))
    model_json = {"features": FEATURES, "mean": list(map(float, scaler_model.mean)), "std": list(map(float, scaler_model.std)),
                  "centers_standardised": [list(map(float, c)) for c in models[best_k].clusterCenters()],
                  "labels": {str(k): v for k, v in seg_labels.items()}, "K": best_k, "users": n_users,
                  "silhouette": float(kev.loc[kev.K == best_k, "Silhouette"].iloc[0]),
                  "note": "user-level segments from per-user averages; centroid assignment in standardised space"}
    sc.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (sc.ARTIFACTS / "kmeans_user_segments_model.json").write_text(json.dumps(model_json, indent=2), encoding="utf-8")

    pca_df = PCA(k=2, inputCol="features", outputCol="pca").fit(clustered).transform(clustered)
    pdf = pca_df.select("user_id", "cluster", vector_to_array("pca").alias("pc")).toPandas()
    pdf["PC1"] = pdf.pc.str[0]
    pdf["PC2"] = pdf.pc.str[1]
    seg = pdf[["user_id", "cluster", "PC1", "PC2"]]
    seg.to_csv(out / "kmeans_user_segments.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    ax.scatter(pdf.PC1, pdf.PC2, c=pdf.cluster, s=12, cmap="coolwarm")
    ax.set(xlabel="Principal component 1", ylabel="Principal component 2", title=f"User segments, K={best_k} (PCA projection)")
    fig.tight_layout(); fig.savefig(out / "kmeans_pca.png", dpi=130)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ax[0].plot(kev.K, kev.WCSS, marker="o"); ax[0].set(xlabel="K", ylabel="WCSS", title="Elbow")
    ax[1].plot(kev.K, kev.Silhouette, marker="o", color="#eb6834"); ax[1].set(xlabel="K", ylabel="Silhouette", title="Silhouette")
    fig.tight_layout(); fig.savefig(out / "kmeans_elbow_silhouette.png", dpi=130)
    pd.Series({"storage_mode": cfg.mode, "silver_source": cfg.output_path, "users": n_users, "selected_K": best_k}).to_json(out / "kmeans_run_info.json", indent=2)
    print("Storage mode used:", cfg.mode.upper())
    spark.stop()


if __name__ == "__main__":
    main()
