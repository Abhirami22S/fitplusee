# archive/ - superseded experiments (moved, not deleted)

The faculty asked for SUPERVISED learning in every experiment, so the two K-Means experiments were replaced
(E3 K-Means on 437 users -> supervised user-level classifier `high_achiever`; E4 K-Means on user-days -> supervised
`activity_level` classifier). The old code and evidence are kept here for the record.

| Item | What it was | Notes |
|---|---|---|
| `kmeans/spark_report_kmeans.py` | Spark MLlib K-Means on 437 users (old E3) | needs `models/` on the path: `set PYTHONPATH=models` (PowerShell: `$env:PYTHONPATH="models"`). Its OUTPUT files were moved here on 2026-10-25 (`kmeans/evidence/faculty_evidence/...` and `kmeans/artifacts/kmeans_user_segments_model.json`) because nothing live reads them any more (Power BI, the web page and the Streamlit app no longer use them). |
| `kmeans/check_kmeans_silhouette_definition.py` | Spark vs scikit-learn silhouette check | evidence stays in `faculty_evidence/report_aligned/` |
| `kmeans/hdfs_ml_validation.py` | re-executed notebook cells 41-99 (old random-split RF + K-Means) from HDFS | depends on the cell numbers of the ORIGINAL notebook, see below; replaced by `run_supervised.ps1 -Storage hdfs` |
| `FitPulse_Faculty_Demo_pre_supervised.ipynb` | the notebook exactly as it was before the supervised conversion | cell indices match `kmeans/hdfs_ml_validation.py` |
| `notebook_removed_cells.json` | notebook cells removed in the new version (old section 5-7, 12, 13 and K-Means text), with their saved outputs | |
| `pre_supervised_generators/build_notebook.py`, `update_section14.py` | scripts that generated sections of the pre-supervised notebook (moved here on 2026-10-25; they read files that are archived too, so they are not meant to be re-run) | |
| `anomaly/train_anomaly_detection.py` | per-user heart-rate anomaly flagging (Model 4), removed from the live project on 2026-10-25 | the Streamlit Heart Rate tab and the docs no longer use it |
| `kmeans/evidence/`, `kmeans/artifacts/` | the old K-Means result files, the pre-supervised notebook evidence that mentioned them, the old Power BI Desktop verification record and screenshots | same relative paths as in `faculty_evidence/` and `models/` |
| `pre_cleanup_20261025/` | byte-exact copies (same relative paths) of every file edited in place on 2026-10-25, so removed text and the previous versions can be recovered; `moved/` holds the previous generated Power BI project and the Power BI CSV tables that were replaced | nothing was deleted |

Replacement: `models/sup_e1_*.py` ... `sup_e5_*.py`, `run_supervised.ps1`, results in `exports/`, evidence in `faculty_evidence/supervised/`.
