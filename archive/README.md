# archive/ - superseded experiments (moved, not deleted)

The faculty asked for SUPERVISED learning in every experiment, so the two K-Means experiments were replaced
(E3 K-Means on 437 users -> supervised user-level classifier `high_achiever`; E4 K-Means on user-days -> supervised
`activity_level` classifier). The old code and evidence are kept here for the record. Nothing was deleted: everything was
moved, and byte-exact copies of every file that was edited in place are in `pre_cleanup_20261025/`.

Replacement: `models/sup_e1_*.py` ... `sup_e5_*.py`, `run_supervised.ps1`, results in `exports/`, evidence in `faculty_evidence/supervised/`.

## Two files that must stay

`FitPulse_Faculty_Demo_pre_supervised.ipynb` and `notebook_removed_cells.json` (both in the root of this folder) must stay where they are,
because `scripts/build_supervised_notebook.py` uses them:

- `FitPulse_Faculty_Demo_pre_supervised.ipynb` is the notebook exactly as it was before the supervised conversion. The script READS it:
  every run rebuilds `FitPulse_Faculty_Demo.ipynb` from this original (that is what makes the script repeatable). Without it the script cannot run.
- `notebook_removed_cells.json` lists the 73 cells that were removed, with their saved outputs. The script WRITES it (regenerates it
  from the original) on every run; it is kept as the record of what was removed.

They are the only files in `archive/` that a live script uses. Checked again on 2026-10-26: no test, dashboard, `run_*.ps1` or other script reads or
imports anything else in this folder; the live documents and the notebook text only mention `archive/` in sentences.

## For a faculty submission copy

Everything else in `archive/` can be left out of a faculty submission copy: nothing live reads it. If the copy does not include
`scripts/build_supervised_notebook.py`, the two files above can be left out as well.

## What is in each folder (file counts and sizes as of 2026-10-26)

| Folder | What it holds | Why it is kept |
|---|---|---|
| root (5 files) | the two files above; `FitPulse_Faculty_Demo_before_rebuild2.ipynb` and `notebook_removed_cells_before_rebuild2.json` (copies taken just before the second run of the build script); this README | the first two are required (see above); the `before_rebuild2` copies are safety copies, nothing reads them |
| `anomaly/` (1 file, 3.3 KB) | `train_anomaly_detection.py`: per-user heart-rate anomaly flagging with an Isolation Forest (Model 4), removed from the live project on 2026-10-25 | it is unsupervised and not one of E1-E5; kept for the record |
| `kmeans/` (39 files, 2.0 MB) | the three scripts of the old K-Means work: `spark_report_kmeans.py` (Spark MLlib K-Means on 437 users, old E3), `check_kmeans_silhouette_definition.py` (Spark vs scikit-learn silhouette check), `hdfs_ml_validation.py` (re-executed cells 41-99 of the ORIGINAL notebook from HDFS); `artifacts/` (1 file: `kmeans_user_segments_model.json`); `evidence/` (35 files: the old K-Means result files, the pre-supervised notebook evidence that mentioned them, the old Power BI Desktop verification record and its screenshots, under the same relative paths as in `faculty_evidence/`) | the record of the replaced experiments. Not meant to be re-run: the scripts need `models/` on the path (`$env:PYTHONPATH="models"`), `spark_report_kmeans.py` wrote its outputs into live folders (`faculty_evidence/report_aligned/`, `models/artifacts/`), and `hdfs_ml_validation.py` depends on the cell numbers of the original notebook (replaced by `run_supervised.ps1 -Storage hdfs`) |
| `pre_supervised_generators/` (4 files, 104.2 KB) | `build_notebook.py`, `update_section14.py` (moved 2026-10-25) and `add_sections_12_14.py`, `add_hdfs_section.py` (moved 2026-10-26): scripts that generated sections of the pre-supervised notebook | the record of how the old notebook was built; they read files that are archived too, so they are not meant to be re-run |
| `pre_cleanup_20261025/` (269 files, 20.2 MB) | everything touched by the clean-up that started on 2026-10-25 (the folder name keeps that date; later additions are also here): see the list below | lets any removed text or previous version be recovered; nothing was deleted |

Inside `pre_cleanup_20261025/`:

- `README.md`, `SUPERVISED_REPORT.md`, `faculty_demo_notes.md`, `viva.md`, and the folders `dashboard/`, `faculty_evidence/`, `models/`, `powerbi/`, `scripts/`, `webapp/`:
  byte-exact copies, with the same relative paths, of the files as they were before they were edited in place. `powerbi/` also holds
  `export_model_evaluation_with_BOM_before_strip.py` (the file as it was before its UTF-8 BOM was removed on 2026-10-26).
- `archive/`: earlier versions of this README (`README.md` = before the 2026-10-25 edit, `README_before_26Oct_update.md` = before the 2026-10-26 rewrite).
- `removed_passages/` (1 file): text cut out of a document, saved before it was removed (the old 34.44 Random Forest passage of `faculty_demo_notes.md`).
- `moved/` (211 files): files moved out of live folders, under their old relative paths:
  - `moved/powerbi/` (196 files): the two previously generated Power BI projects (`project/` with the user-segmentation pages, and `project_before_card_labels/`) and the four Power BI CSV tables that were replaced (`kmeans_k_selection.csv`, `segment_profile.csv`, `model_evaluation.csv`, `confusion_matrices.csv`).
  - `moved/faculty_evidence/` (15 files): the five old Power BI page screenshots (they show the previous `.pbix`, including the "User Segmentation" page) and the ten Jupyter checkpoint files.

## Not in archive/ (as of 2026-10-26)

- `faculty_evidence/FINAL_ACCEPTANCE_TABLE.md`, `PROJECT_IMPLEMENTATION_AUDIT.md` and `REPORT_AND_PPT_CHANGE_LOG.md` are historical records that still
  quote the old K-Means numbers; they stay in `faculty_evidence/` for now.
- `powerbi/FitPulse_PowerBI_Dashboard.pbix` is still the previous version until it is re-saved from `powerbi/project/` in Power BI Desktop.
