# Automated build of the FitPulse Power BI project

**What this produces:** a Power BI Project (`powerbi/project/FitPulse_PowerBI_Dashboard.pbip`) with a TMDL semantic model and a 5-page PBIR report.
**What it does not produce:** a `.pbix` by itself - only Power BI Desktop can save that (open the `.pbip`, then *File > Save as*).
Status: validated offline (below). The `FitPulse_PowerBI_Dashboard.pbix` in this folder was saved from an EARLIER version of this project (opened in Power BI Desktop 2.158 on 2026-10-13); the project was regenerated on 2026-10-25 and the `.pbix` must be re-saved from it (section 7).

## 1. Prerequisites (one time)
* Project venv with pandas / pyarrow (already present: `..\.venv`).
* Node.js, then `npm install --prefix powerbi/_tools @microsoft/powerbi-report-authoring-cli` (Microsoft; provides `scaffold`, `validate`, and the Desktop Bridge CLI).
* Optional, for the TMDL parser check: Microsoft's NuGet `Microsoft.AnalysisServices.retail.amd64` 19.84.1 unpacked to `..\tools\nuget\as_pkg` (instructions in `validate_tmdl.ps1`).

## 2. Build
```powershell
cd D:\bigdata\fitpulsee\FitPulse
.\powerbi\build_powerbi.ps1            # exports -> validates data -> generates project -> validates project   (-SkipExport reuses the CSVs)
```
Steps it runs: `export_powerbi_data.py`, `export_model_evaluation.py`, `validate_exports.py`, `build_powerbi.py`, `validate_powerbi_project.py`.
Re-running regenerates `powerbi/project/` (only if the folder carries the marker file written by the generator; it refuses to overwrite anything else).
The model and report are defined in `powerbi/model_definition.py` (6 tables, 4 relationships, 29 measures, 5 pages / 68 visuals); `measures.dax` is regenerated from it.

## 3. Automated validation results (2026-10-25, after the supervised rebuild)
`python powerbi/validate_powerbi_project.py` -> **65/65 checks passed** (`faculty_evidence/powerbi/project_validation.md`):
* data sources exist; TMDL columns equal CSV headers; relationship keys exist, are unique on the one side and cover all many-side values;
* every DAX reference exists; every visual field (149 references in 68 visuals) exists as a column/measure on the right table;
* five exact page names in the requested order; slicers present where required; all visuals inside the page; every visual on pages 4 and 5 that shows a result names its experiment (column shown or pinned by a filter),
  and page 4 is pinned to E3 and E4, so experiments are never mixed; experiment ids E1-E5 preserved;
* every headline measure emulated in pandas matches `EXPECTED_VALUES.csv` (logic check, not DAX execution);
* **Microsoft PBIR validator** (`powerbi-report-author validate`): succeeded, 0 errors, 0 warnings;
* **Microsoft TMDL deserializer** (TOM 19.84.1): parsed - 6 tables, 55 columns, 29 measures, 4 relationships, 1 expression.
Two real defects were found and fixed by these Microsoft tools during development (undefined query group in `expressions.tmdl`; theme/slicer/textbox sizing rules).

## 4. What was done in Power BI Desktop (2026-10-13, EARLIER version of the project)
Desktop was installed with permission (Store id `9NTXR16HNW1T`). The `.pbip` opened, data was loaded with Desktop's own Refresh/Apply buttons, all five pages were rendered and screenshotted
(`faculty_evidence/powerbi/screenshots/`), rendering defects were fixed in the generator and rebuilt, and the project was saved as `powerbi/FitPulse_PowerBI_Dashboard.pbix`. The `.pbix` was then reopened
(data cached), card values were compared with expected values, and the Activity type slicer was clicked (Cycling) with matching results. Details and gaps: that record is archived (see `archive/README.md`).
Note: the Desktop Bridge cannot refresh or save; those steps were done through Desktop's own buttons/dialog (Windows UI Automation) and are not exposed as a supported API.

## 5. Refresh procedure
Pipeline rerun -> `.\powerbi\build_powerbi.ps1` -> in Desktop: reload the project (or reopen) -> Home > Refresh. If the project folder moved, regenerate (the generator writes the
current absolute `powerbi\data\` path into the `DataFolder` parameter) or edit it in Desktop: Transform data > Edit parameters.

## 6. Known limitations
* Per-page slicers are independent (I did not find how to author cross-page sync in the schemas I inspected; it can be added in Desktop via View > Sync slicers).
* Data is imported from CSV exports of the local Silver data; Power BI does not connect to HDFS (single-node, replication 1).
* Rendering, DAX results, Power Query load and exact visual formatting are unverified until opened in Desktop.
* `Steps MoM %` relies on the marked date table; the first month shows blank by design.

## 7. Re-saving the `.pbix` after the supervised rebuild (2026-10-25)
Pages 4 (`Supervised Results E3 and E4`) and 5 (`Model Evaluation`) read only `exports/E<n>_results.csv` (via `powerbi/data/supervised_results.csv`) plus the cross-check counts from `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv`.
Pages 1 and 2 no longer have a user-grouping slicer, and the page 3 'Verified' cards read the same results table. The `.pbix` is not updated by any script:
1. open `powerbi\project\FitPulse_PowerBI_Dashboard.pbip` in Power BI Desktop; 2. Home > Refresh and compare the cards with `powerbi\EXPECTED_VALUES.csv`; 3. File > Save as `powerbi\FitPulse_PowerBI_Dashboard.pbix`; 4. run `powerbi\check_pbix.py`; 5. recapture screenshots with `capture_powerbi_screenshots.ps1` if they are needed.
