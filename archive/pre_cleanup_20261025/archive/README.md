# archive/ - superseded experiments (moved, not deleted)

The faculty asked for SUPERVISED learning in every experiment, so the two K-Means experiments were replaced
(E3 K-Means on 437 users -> supervised user-level classifier `high_achiever`; E4 K-Means on user-days -> supervised
`activity_level` classifier). The old code and evidence are kept here for the record.

| Item | What it was | Notes |
|---|---|---|
| `kmeans/spark_report_kmeans.py` | Spark MLlib K-Means on 437 users (old E3) | needs `models/` on the path: `set PYTHONPATH=models` (PowerShell: `$env:PYTHONPATH="models"`). Its OUTPUT files (`faculty_evidence/report_aligned/kmeans_*`, `models/artifacts/kmeans_user_segments_model.json`) stay in place because the Power BI project, the web page and the legacy Streamlit app still read them until they are rewired. |
| `kmeans/check_kmeans_silhouette_definition.py` | Spark vs scikit-learn silhouette check | evidence stays in `faculty_evidence/report_aligned/` |
| `kmeans/hdfs_ml_validation.py` | re-executed notebook cells 41-99 (old random-split RF + K-Means) from HDFS | depends on the cell numbers of the ORIGINAL notebook, see below; replaced by `run_supervised.ps1 -Storage hdfs` |
| `FitPulse_Faculty_Demo_pre_supervised.ipynb` | the notebook exactly as it was before the supervised conversion | cell indices match `kmeans/hdfs_ml_validation.py` |
| `notebook_removed_cells.json` | notebook cells removed in the new version (old section 5-7, 12, 13 and K-Means text), with their saved outputs | |

Replacement: `models/sup_e1_*.py` ... `sup_e5_*.py`, `run_supervised.ps1`, results in `exports/`, evidence in `faculty_evidence/supervised/`.
