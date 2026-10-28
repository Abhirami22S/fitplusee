**[PREVIOUS] Is 71.87% accuracy good?**
Always predicting "missed" would already score 63.16%. The model beats that, and its ROC-AUC of 82.47% shows real
ranking ability. Under the stricter chronological split, accuracy is 86.08% but that is misleading: only 11.8% of
those test days are positives, and F1 drops to 34.44%. The scikit-learn RF in `models/metrics_report.md` (F1 0.344,
AUC 0.718) agrees with that.

