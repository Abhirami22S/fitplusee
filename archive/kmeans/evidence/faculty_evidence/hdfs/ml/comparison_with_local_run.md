# ML re-validation: Silver from HDFS vs earlier local-Parquet run
Silver source: hdfs://localhost:9000/fitpulse/silver (100,122 rows). Elapsed 289s.

- classification_results.csv: max |numeric diff| = 1.19e-06; non-numeric identical = True
- confusion_matrix.csv: max |numeric diff| = 0; non-numeric identical = True
- rf_validation_tuning.csv: max |diff| excluding wall-clock 'Train time (s)' = 0
- split_summary.csv: max |numeric diff| = 0; non-numeric identical = True
- rf_feature_importance.csv: max |numeric diff| = 0; non-numeric identical = True
- classification_split_comparison.csv: max |numeric diff| = 8.47e-06; non-numeric identical = True
- silhouette_scores.csv: max |numeric diff| = 0; non-numeric identical = True
- cluster_summary.csv: max |numeric diff| = 0; non-numeric identical = True

RESULT: DIFFERENCES FOUND - investigate

## Analysis of the differences (added by hand after reading the numbers above)
* Every label-based metric is **identical**: accuracy 0.7186902, precision 0.5849409, recall 0.8138528, F1 0.6806662, the confusion matrix, the 70/15/15 split sizes, the validation tuning table (best maxDepth), feature importances, K-Means silhouettes (K=2..6) and cluster summary.
* Only **ROC-AUC** differs, in the 6th-7th decimal: random split 0.82474168 (local) vs 0.82474287 (HDFS), diff 1.19e-06; chronological split 0.72618661 vs 0.72617814, diff 8.47e-06. Both still round to 82.47% / 72.62%.
* Likely cause (not proven by a separate experiment): ROC-AUC is computed from the forest's floating-point probabilities, and Spark reading the Parquet from HDFS yields a different row/partition order than reading the local files, which changes floating-point accumulation order. No feature, target, split, seed or hyper-parameter was changed.
* Conclusion: models and conclusions are reproduced from HDFS; the AUC wobble is numerical noise, not a data difference (the HDFS and local Silver tables are row-for-row identical, see verification_summary.json).
