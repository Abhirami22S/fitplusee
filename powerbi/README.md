# powerbi/ - FitPulse Power BI assets

**Status (2026-10-25):** the generated Power BI Project in `project/` was rebuilt: pages 4 and 5 now show only the supervised results E1-E5 (they read `exports/E<n>_results.csv`, copied row for row into `data/supervised_results.csv`,
plus the cross-check counts from the HDFS rerun) and the model no longer contains any user grouping. `validate_powerbi_project.py` passes on the project.
**The `FitPulse_PowerBI_Dashboard.pbix` in this folder is still the PREVIOUS version** until you re-save it:

1. Open `project\FitPulse_PowerBI_Dashboard.pbip` in Power BI Desktop (the `DataFolder` parameter already points at `powerbi\data\`).
2. Home > **Refresh**. Check the cards against `EXPECTED_VALUES.csv`, and on page 5 that the two cross-check cards read 103 and 103.
3. File > **Save as** `powerbi\FitPulse_PowerBI_Dashboard.pbix` (replace the old file).
4. Run `..\.venv\Scripts\python.exe powerbi\check_pbix.py` (structure check of the saved file; rewrites `faculty_evidence\powerbi\pbix_structure_check.md`) and, for new screenshots, `capture_powerbi_screenshots.ps1`.

The earlier Desktop verification of the previous `.pbix` is archived under `archive/` (see `archive/README.md`).

| File / folder | Purpose |
|---|---|
| `FitPulse_PowerBI_Dashboard.pbix` | **The deliverable** - open in Power BI Desktop; data is cached; after a pipeline rerun run `build_powerbi.ps1` and Refresh |
| `project/` | **Generated** Power BI Project: `FitPulse_PowerBI_Dashboard.pbip`, `.SemanticModel` (TMDL), `.Report` (PBIR, 5 pages). Do not edit by hand - change `model_definition.py` and rebuild |
| `model_definition.py` | Single source of truth: tables, relationships, 34 DAX measures, 5 pages / 70 visuals |
| `build_powerbi.ps1` / `build_powerbi.py` | One-command pipeline / the generator |
| `validate_powerbi_project.py`, `validate_tmdl.ps1` | Offline validation (70 checks; Microsoft PBIR validator and TMDL parser) |
| `export_powerbi_data.py`, `export_model_evaluation.py`, `validate_exports.py` | Build and validate `data/*.csv` from the Silver data, `exports/E<n>_results.csv` and the HDFS-rerun cross-check; write `EXPECTED_VALUES.csv` |
| `data/` | CSV tables imported by Power BI (`fact_daily` 100,122 user-days, `dim_user` 437 users, `dim_date`, `experiments`, `supervised_results` 348 rows, `crosscheck` 103 rows); `monthly_summary.csv` and `model_metrics.csv` are legacy and unused |
| `measures.dax` | Human-readable copy of the measures (generated) |
| `FitPulse_theme.json` | Report theme (registered in the generated report) |
| `EXPECTED_VALUES.csv` | Independent expected values (pandas) for checking cards in Desktop |
| `capture_powerbi_screenshots.ps1`, `desktop_cycle.ps1` | Open the project and capture real page screenshots through the Desktop Bridge (used; `desktop_cycle.ps1` is an experimental helper) |
| `check_pbix.py` | Structural check of the saved `.pbix` (run on the delivered file: passes) |
| `AUTOMATION_OPTIONS.md` | Verified comparison of automation routes and their limits |
| `BUILD_GUIDE.md` | Original manual build steps (fallback only; the generated project opened without problems) |
| `_tools/`, `schemas/` | Local npm tooling (Microsoft authoring CLI) and cached JSON schemas; safe to delete and reinstall |

Data granularity: `fact_daily` = one row per **user-day**; `dim_user` = one row per **user**. Step goal = 1.10 x the user's own average steps (not a fixed 8,000).
Experiments are separate (supervised E1-E5, see `../SUPERVISED_REPORT.md`): E1 same-day goal, E2 next-day goal (chronological), E3 user-level high_achiever, E4 activity level (user-held-out),
E5 calories; every result row names its experiment, evaluation split and status.
Power BI imports CSV exports; it does not connect to HDFS. HDFS here is single-node with replication factor 1.
