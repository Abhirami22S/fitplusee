# Report and presentation change log

Corrected copies (originals untouched): `D:\bigdata\FitPulse_Report_Updated_v3.docx` and `D:\bigdata\actualfitpulseppt_v2.pptx`.
Every value below was read from files written by actual runs (see `faculty_evidence/report_aligned/`, `regression_results.csv`).
Power BI statements in the original files are unchanged because the Power BI dashboard now exists (powerbi/FitPulse_PowerBI_Dashboard.pbix); Table 2 gains one clarifying sentence (CSV import, no direct HDFS read).
Not changed: the embedded figures (Figures 1-5) and the `[Insert Implementation URL]` cells - the repository URL is not known.

## Report (docx)
| Where | Old | New | Matches |
|---|---|---|---|
| 1.1 HDFS wording | Hadoop HDFS for distributed storage, | Hadoop HDFS for distributed storage (a single-node deployment in this project), | 1 |
| 1.1 Linear Regression status | Linear Regression is described only to complete the picture of the overall project. | Linear Regression (calorie burn) is implemented and evaluated in the project repository (test MAE 199.7 kcal, RMSE 263.6 kcal, R2 0.630; the | 1 |
| 1.6 fault tolerance | so a node failure does not stop the job. | so a node failure does not stop the job (a property of a multi-node cluster; the single-node HDFS used in this project demonstrates the stor | 1 |
| Table 2 HDFS row | Distributed storage: files are split into blocks spread across nodes and replicated (default factor 3) for fau | Distributed storage: files are split into blocks spread across nodes and replicated (default factor 3 on a cluster; this project's single-no | 1 |
| Table 2 Power BI row (role) | Interactive visualization of goals, segments, and calorie trends for end users. | Interactive visualization of goals, segments, and calorie trends for end users. Implemented as FitPulse_PowerBI_Dashboard.pbix (five pages)  | 1 |
| 2.1 leakage demonstration | reached 100% accuracy on a held-out split | reached 98.95% accuracy on a held-out split | 1 |
| 2.2 hyper-parameters | The best combination was numTrees = 100 and maxDepth = 20 (validation AUC 0.759, against 0.720 at maxDepth = 5 | Two of the eight combinations (100 trees at depth 15 and at depth 20) could not be run because the Spark JVM ran out of memory on the 16 GB  | 1 |
| 2.3 how results were computed | Reported results were computed with an equivalent scikit-learn implementation using the same 70/15/15 proporti | Reported results were computed by running this Spark MLlib code (models/spark_report_classification.py in the project repository) on the Sil | 1 |
| Listing 3 hyper-parameters | numTrees=100, maxDepth=20, maxBins=32, seed=42) | numTrees=50, maxDepth=15, maxBins=32, seed=42) | 1 |
| Listings 1 and 5 data path | <HDFS_PATH>/fitpulse_raw.csv | hdfs://localhost:9000/fitpulse/bronze/fitpulse_raw.csv | 2 |
| Listing placeholder comments |    # [Insert dataset path] |  | 2 |
| 2.4 split and provenance | The split contains 70,084 training, 15,019 validation and 15,019 test records. The values below were obtained  | The split (Spark randomSplit, seed 42) contains 70,383 training, 14,943 validation and 14,796 test records. The values below were measured b | 1 |
| Table 8 Accuracy validation | 0.7305 | 0.7293 | 1 |
| Table 8 Accuracy test | 0.7303 | 0.7352 | 1 |
| Table 8 Precision (weighted) validation | 0.7294 | 0.7275 | 1 |
| Table 8 Precision (weighted) test | 0.7292 | 0.7341 | 1 |
| Table 8 Recall (weighted) validation | 0.7305 | 0.7293 | 1 |
| Table 8 Recall (weighted) test | 0.7303 | 0.7352 | 1 |
| Table 8 F1 (weighted) validation | 0.7299 | 0.7282 | 1 |
| Table 8 F1 (weighted) test | 0.7297 | 0.7346 | 1 |
| Table 8 Precision (goal-achieved class) validation | 0.7782 | 0.7708 | 1 |
| Table 8 Precision (goal-achieved class) test | 0.7751 | 0.7801 | 1 |
| Table 8 Recall (goal-achieved class) validation | 0.7890 | 0.7912 | 1 |
| Table 8 Recall (goal-achieved class) test | 0.7875 | 0.7923 | 1 |
| Table 8 F1 (goal-achieved class) validation | 0.7835 | 0.7809 | 1 |
| Table 8 F1 (goal-achieved class) test | 0.7812 | 0.7862 | 1 |
| Table 8 ROC AUC validation | 0.7587 | 0.7549 | 1 |
| Table 8 ROC AUC test | 0.7580 | 0.7585 | 1 |
| Table 8 Baseline accuracy (always majority class) validation | 0.6181 | 0.6096 | 1 |
| Table 8 Baseline accuracy (always majority class) test | 0.6114 | 0.6144 | 1 |
| Table 9 TN | 3,737 | 3,676 | 1 |
| Table 9 FP | 2,099 | 2,030 | 1 |
| Table 9 FN | 1,951 | 1,888 | 1 |
| Table 9 TP | 7,232 | 7,202 | 1 |
| Table 10 rank 1 feature | weight_kg | weight_kg | 1 |
| Table 10 rank 1 importance | 0.2446 | 0.2822 | 1 |
| Table 10 rank 2 feature | bmi | bmi | 1 |
| Table 10 rank 2 importance | 0.0828 | 0.0929 | 1 |
| Table 10 rank 3 feature | calories_burned | height_cm | 1 |
| Table 10 rank 3 importance | 0.0695 | 0.0601 | 1 |
| Table 10 rank 4 feature | height_cm | activity_type | 1 |
| Table 10 rank 4 importance | 0.0629 | 0.0586 | 1 |
| Table 10 rank 5 feature | sleep_quality_score | active_minutes | 1 |
| Table 10 rank 5 importance | 0.0566 | 0.0480 | 1 |
| 2.5 accuracy | accuracy of 73.0%, which is 11.9 percentage points above the 61.1% | accuracy of 73.5%, which is 12.1 percentage points above the 61.4% | 1 |
| 2.5 AUC | ROC AUC of 0.758 | ROC AUC of 0.759 | 1 |
| 2.5 precision/recall | it finds 78.8% (recall) with a precision of 77.5% | it finds 79.2% (recall) with a precision of 78.0% | 1 |
| 2.5 specificity | it identifies 64.0% of the days on which the goal is missed (3,737 of 5,836) | it identifies 64.4% of the days on which the goal is missed (3,676 of 5,706) | 1 |
| 2.5 importances | The most important feature is weight_kg (24.5%), followed by bmi (8.3%), calories_burned (6.9%) and height_cm  | The most important feature is weight_kg (28.2%), followed by bmi (9.3%), height_cm (6.0%) and activity_type (5.9%). | 1 |
| 2.5 user-held-out | (accuracy 72.5%, AUC 0.755) | (accuracy 72.3%, AUC 0.750) | 1 |
| 3.2 silhouette wording | The silhouette score, computed with Spark's ClusteringEvaluator, measures | The silhouette score measures | 1 |
| 3.2 silhouette definition | The silhouette score is highest at K = 2 (0.202) | The silhouette score (Euclidean distance, as computed by scikit-learn; Spark's ClusteringEvaluator with squaredEuclidean distance gives 0.34 | 1 |
| 3.3 provenance | Reported results were computed with an equivalent scikit-learn implementation (standardized features, seed 42) | Cluster sizes and profiles were measured with this Spark MLlib code (models/spark_report_kmeans.py) on the HDFS-stored Silver dataset; the K | 1 |
| 3.4 provenance | Values were computed on the 437 user-level records (standardized features) with an equivalent scikit-learn imp | Table 15 was computed on the 437 standardized user vectors with scikit-learn (Euclidean silhouette, 10 initialisations, seed 42). Table 16 w | 1 |
| Table 15 K=2 WCSS | 2,340.54 | 2,335.18 | 1 |
| Table 15 K=2 silhouette | 0.2018 | 0.2018 | 1 |
| Table 15 K=3 WCSS | 2,057.38 | 2,052.67 | 1 |
| Table 15 K=3 silhouette | 0.1609 | 0.1609 | 1 |
| Table 15 K=4 WCSS | 1,850.04 | 1,845.81 | 1 |
| Table 15 K=4 silhouette | 0.1554 | 0.1554 | 1 |
| Table 15 K=5 WCSS | 1,710.52 | 1,706.61 | 1 |
| Table 15 K=5 silhouette | 0.1515 | 0.1515 | 1 |
| Table 15 K=6 WCSS | 1,616.96 | 1,613.26 | 1 |
| Table 15 K=6 silhouette | 0.1429 | 0.1429 | 1 |
| Table 15 K=7 WCSS | 1,527.97 | 1,524.47 | 1 |
| Table 15 K=7 silhouette | 0.1485 | 0.1485 | 1 |
| Table 15 K=8 WCSS | 1,441.29 | 1,438.00 | 1 |
| Table 15 K=8 silhouette | 0.1456 | 0.1456 | 1 |
| Table 15 K=9 WCSS | 1,374.51 | 1,371.36 | 1 |
| Table 15 K=9 silhouette | 0.1498 | 0.1498 | 1 |
| Table 15 K=10 WCSS | 1,308.77 | 1,305.77 | 1 |
| Table 15 K=10 silhouette | 0.1546 | 0.1546 | 1 |
| Table 16 row 1 col 2 | 210 | 209 | 1 |
| Table 16 row 1 col 3 | 8,632 | 8,631 | 1 |
| Table 16 row 1 col 4 | 68.7 | 68.7 | 1 |
| Table 16 row 1 col 5 | 950.1 | 950.1 | 1 |
| Table 16 row 1 col 6 | 647.3 | 647.3 | 1 |
| Table 16 row 1 col 7 | 130.3 | 130.4 | 1 |
| Table 16 row 1 col 8 | 421.2 | 421.2 | 1 |
| Table 16 row 2 col 2 | 227 | 228 | 1 |
| Table 16 row 2 col 3 | 8,620 | 8,621 | 1 |
| Table 16 row 2 col 4 | 71.1 | 71.1 | 1 |
| Table 16 row 2 col 5 | 944.6 | 944.6 | 1 |
| Table 16 row 2 col 6 | 675.1 | 675.0 | 1 |
| Table 16 row 2 col 7 | 131.3 | 131.3 | 1 |
| Table 16 row 2 col 8 | 424.3 | 424.3 | 1 |
| 3.4 cluster sizes | Cluster 0 (lower active-time, 210 users) and Cluster 1 (higher active-time, 227 users) | Cluster 0 (lower active-time, 209 users) and Cluster 1 (higher active-time, 228 users) | 1 |
| 3.4 overall quality | silhouette score 0.2018 and WCSS 2,340.54 for K = 2 | Euclidean silhouette score 0.2018 and WCSS 2,335.18 for K = 2 | 1 |
| 3.5 average steps | (8,632 and 8,620) | (8,631 and 8,621) | 1 |
| 3.5 interpretation | splits the 437 users into 210 and 227 users (silhouette 0.202, WCSS 2,340.5) | splits the 437 users into 209 and 228 users (Euclidean silhouette 0.202, WCSS 2,335.2) | 1 |
| Tables 12/18 platform | [Insert Platform: GitHub / Google Colab / Jupyter] | Jupyter Notebook and Python scripts, run locally (Windows, PySpark 4.0.1, Hadoop HDFS 3.4.1 single node) | 2 |
| Tables 12/18 repository name | [Insert Notebook or Repository Name] | FitPulse (FitPulse_Faculty_Demo.ipynb; models/spark_report_classification.py) | 1 |
| Tables 12/18 repository name | [Insert Notebook or Repository Name] | FitPulse (FitPulse_Faculty_Demo.ipynb; models/spark_report_kmeans.py) | 1 |

## Presentation (pptx)
| Where | Old | New | Matches |
|---|---|---|---|
| slide 3 dataset source | Publicly available Fitbit / Kaggle wearable fitness dataset | Publicly available Kaggle wearable fitness dataset | 1 |
| slide 4 HDFS | Distributed file system for fault-tolerant, large-scale data storage across commodity hardware clusters. | Distributed file system for large-scale data storage. Deployed here as a single node (replication 1); fault tolerance needs a multi-node clu | 1 |
| slide 6 results heading | Model performance is evaluated using standard task-appropriate metrics pending training completion. | Measured test-set results (Spark MLlib, Silver data on HDFS). | 1 |
| slide 6 results note | Numerical results to be populated upon model completion and validation testing. | Random Forest (same-day goal, steps >= 8,000): accuracy 0.735, ROC-AUC 0.759. Linear Regression (calories): MAE 199.7 kcal, RMSE 263.6 kcal, | 1 |
| slide 6 metric label Accuracy | Accuracy | Accuracy 0.735 | 1 |
| slide 6 metric label Precision | Precision | Precision 0.780 | 1 |
| slide 6 metric label Recall | Recall | Recall 0.792 | 1 |
| slide 6 metric label F1-Score | F1-Score | F1-Score 0.786 | 1 |
| slide 6 metric label RMSE | RMSE | RMSE 263.6 kcal | 1 |
| slide 6 metric label MAE | MAE | MAE 199.7 kcal | 1 |
| slide 6 metric label R² Score | R² Score | R² 0.630 | 1 |