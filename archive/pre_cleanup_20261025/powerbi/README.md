# powerbi/ - FitPulse Power BI assets

**Status: `FitPulse_PowerBI_Dashboard.pbix` exists** (saved by Power BI Desktop 2.158 on 2026-10-13, 4.5 MB). It was opened again from the `.pbix` file with data cached, the card values were
compared with independent values, and one slicer was tested by clicking - see `../faculty_evidence/powerbi/POWERBI_VALIDATION.md` for exactly what was and was not verified.
The `.pbix` was produced from the generated Power BI Project in `project/` (not hand-edited).

| File / folder | Purpose |
|---|---|
| `FitPulse_PowerBI_Dashboard.pbix` | **The deliverable** - open in Power BI Desktop; data is cached; after a pipeline rerun run `build_powerbi.ps1` and Refresh |
| `project/` | **Generated** Power BI Project: `FitPulse_PowerBI_Dashboard.pbip`, `.SemanticModel` (TMDL), `.Report` (PBIR, 5 pages). Do not edit by hand - change `model_definition.py` and rebuild |
| `model_definition.py` | Single source of truth: tables, relationships, 34 DAX measures, 5 pages / 70 visuals |
| `build_powerbi.ps1` / `build_powerbi.py` | One-command pipeline / the generator |
| `validate_powerbi_project.py`, `validate_tmdl.ps1` | Offline validation (70 checks; Microsoft PBIR validator and TMDL parser) |
| `export_powerbi_data.py`, `export_model_evaluation.py`, `validate_exports.py` | Build and validate `data/*.csv` from the Silver data and saved model results; write `EXPECTED_VALUES.csv` |
| `data/` | CSV tables imported by Power BI (`fact_daily` 100,122 user-days, `dim_user` 437 users, `dim_date`, `segment_profile`, `experiments`, `model_evaluation`, `confusion_matrices`, `kmeans_k_selection`); `monthly_summary.csv` and `model_metrics.csv` are legacy and unused |
| `measures.dax` | Human-readable copy of the measures (generated) |
| `FitPulse_theme.json` | Report theme (registered in the generated report) |
| `EXPECTED_VALUES.csv` | Independent expected values (pandas) for checking cards in Desktop |
| `capture_powerbi_screenshots.ps1`, `desktop_cycle.ps1` | Open the project and capture real page screenshots through the Desktop Bridge (used; `desktop_cycle.ps1` is an experimental helper) |
| `check_pbix.py` | Structural check of the saved `.pbix` (run on the delivered file: passes) |
| `AUTOMATION_OPTIONS.md` | Verified comparison of automation routes and their limits |
| `BUILD_GUIDE.md` | Original manual build steps (fallback only; the generated project opened without problems) |
| `_tools/`, `schemas/` | Local npm tooling (Microsoft authoring CLI) and cached JSON schemas; safe to delete and reinstall |

Data granularity: `fact_daily` = one row per **user-day**; `dim_user` = one row per **user**. Step goal = 1.10 x the user's own average steps (not a fixed 8,000).
Experiments are separate: E1 Random Forest (report, same-day 8,000 steps), E2 Random Forest (notebook, next-day personalised goal), E3 K-Means (report, 437 users),
E4 K-Means (notebook, user-days), E5 Linear Regression (calories).
Power BI imports CSV exports; it does not connect to HDFS. HDFS here is single-node with replication factor 1.
