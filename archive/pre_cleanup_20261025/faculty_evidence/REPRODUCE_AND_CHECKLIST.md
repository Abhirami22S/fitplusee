# Reproducibility commands and faculty-proof checklist

All commands: PowerShell, from `D:\bigdata\fitpulsee\FitPulse`. Venv Python: `..\.venv\Scripts\python.exe` (Streamlit and Plotly were added to it).
Spark scripts need JDK 17 + Hadoop settings: `. .\scripts\hdfs_env.ps1` sets them (JAVA_HOME, HADOOP_HOME, HADOOP_CONF_DIR, PYSPARK_PYTHON).

```powershell
# --- HDFS (one-time setup was already done; never re-format) ---
.\start_hdfs.ps1
.\run_fitpulse_hdfs.ps1                 # ingest + ETL in HDFS mode + 16 checks   (-SkipEtl = checks only)
.\scripts\test_hdfs_down.ps1            # fail-fast / local-fallback test (stops and restarts HDFS)
# --- SUPERVISED experiments E1-E5 (all experiments are supervised; K-Means is archived in archive\kmeans\) ---
.\run_supervised.ps1 -Experiment All                    # local Silver Parquet -> exports\E<n>_results.csv, faculty_evidence\supervised\, then the scikit-learn cross-check
.\run_fitpulse_hdfs.ps1 -SkipEtl                        # HDFS + Silver verification (16 checks)
.\run_supervised.ps1 -Experiment All -Storage hdfs      # same experiments reading Silver from HDFS -> faculty_evidence\supervised\hdfs_rerun\ (never falls back to local)
& $Py scripts\build_supervised_notebook.py              # rebuild the notebook sections 5-7, 9-10 from those results
& $Py scripts\build_supervised_report.py                # faculty_evidence\supervised\SUPERVISED_REPORT.md
# (the earlier report-aligned RF / K-Means scripts are kept in archive\kmeans\ and archive\README.md says how to run them)
# --- validation ---
& $Py scripts\test_analytics.py
& $Py scripts\test_dashboard.py
& $Py powerbi\export_powerbi_data.py; & $Py powerbi\validate_exports.py
& $Py scripts\build_model_metrics.py
& $Py scripts\update_report_files.py    # corrected copies of the report and slides
# --- demo ---
# Power BI (primary dashboard): open powerbi\FitPulse_PowerBI_Dashboard.pbix in Power BI Desktop (data is cached; Home > Refresh after a rebuild)
& $Py powerbi\export_model_evaluation.py
.\powerbi\build_powerbi.ps1               # regenerates powerbi\project and validates it (70 checks); then open it in Desktop and File > Save as .pbix
& $Py powerbi\check_pbix.py               # structure check of the saved .pbix
# legacy / optional Streamlit (not required for the demo): & $Py -m streamlit run dashboard\app.py   (demo1/demo2/demo3, password demo123)
.\run_faculty_demo.ps1                    # notebook (saved outputs, sections 1-14)
.\stop_hdfs.ps1
```

## Faculty-proof checklist (tick only what the evidence file shows)
| Claim you may make | Evidence file |
|---|---|
| Data is in a real HDFS (single node) and Spark reads/writes it | `faculty_evidence/hdfs/verification_summary.json` (16/16), notebook s.11 |
| HDFS mode fails clearly when HDFS is down; local mode is separate | `faculty_evidence/hdfs/failure_mode_test.txt` |
| Supervised experiments E1-E5: metrics, baselines, leakage runs (INVALID), splits | `exports/E<n>_results.csv`, `faculty_evidence/supervised/SUPERVISED_REPORT.md`, `faculty_evidence/supervised/E<n>_run.log` |
| Independent scikit-learn cross-check of E1-E5 | `faculty_evidence/supervised/sklearn_crosscheck.csv` |
| E1-E5 re-run from HDFS and compared with the local run | `faculty_evidence/supervised/hdfs_rerun/`, notebook s.11.6 |
| (previous experiment) Random Forest, report-aligned metrics | `faculty_evidence/report_aligned/rf_metrics.csv`, `rf_confusion_matrix.csv`, `rf_tuning_grid.csv` |
| (archived, unsupervised) K-Means user segments, K=2..10 | `report_aligned/kmeans_evaluation.csv`, `kmeans_silhouette_definition_check.txt`, `kmeans_cluster_summary.csv`; code in `archive/kmeans/` |
| Linear Regression calorie model | `regression_results.csv`, `regression_coefficients.csv`, `regression_actual_vs_predicted.png`, `analytics_validation.json` |
| Power BI dashboard exists and renders the real data | `powerbi/FitPulse_PowerBI_Dashboard.pbix`, `faculty_evidence/powerbi/POWERBI_VALIDATION.md`, `pbix_screenshots/`, `pbix_structure_check.md`, `project_validation.md` |
| (legacy) Streamlit app works | `faculty_evidence/dashboard/dashboard_validation.md` (15/15) |
| Notebook shows all of the above with executed outputs | `FitPulse_Faculty_Demo.ipynb` sections 5-7 (E1-E5), 11 (HDFS), 12 |
| Every model number with its source | `exports/E<n>_results.csv` (supervised); `model_metrics.csv`, `kmeans_evaluation.csv` hold the PREVIOUS experiments |
| Report/PPT corrections | `REPORT_AND_PPT_CHANGE_LOG.md`, corrected copies in `D:\bigdata\` |
| **Do NOT claim** | that Power BI reads HDFS (it imports CSV); that every slicer was individually tested; multi-node HDFS or fault tolerance; the report's "100 trees, depth 20" result; a re-measured dashboard Logistic Regression score |
