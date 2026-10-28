# Automated build of the FitPulse Power BI project

**What this produces:** a Power BI Project (`powerbi/project/FitPulse_PowerBI_Dashboard.pbip`) with a TMDL semantic model and a 5-page PBIR report.
**What it does not produce:** a `.pbix` by itself - only Power BI Desktop can save that (open the `.pbip`, then *File > Save as*).
Status: validated offline (below) **and opened in Power BI Desktop 2.158**; the delivered `FitPulse_PowerBI_Dashboard.pbix` was saved from this project. Record: `faculty_evidence/powerbi/POWERBI_VALIDATION.md`.

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
The model and report are defined in `powerbi/model_definition.py` (tables, relationships, 34 measures, 5 pages / 70 visuals); `measures.dax` is regenerated from it.

## 3. Automated validation results (2026-10-12)
`python powerbi/validate_powerbi_project.py` -> **70/70 checks passed** (`faculty_evidence/powerbi/project_validation.md`):
* data sources exist; TMDL columns equal CSV headers; relationship keys exist, are unique on the one side and cover all many-side values;
* every DAX reference exists; every visual field (118 references in 70 visuals) exists as a column/measure on the right table;
* five exact page names in the requested order; slicers present; all visuals inside the page; page 5 slicer is single-select with a default so experiments are never mixed;
  experiment ids E1-E5 preserved;
* every headline measure emulated in pandas matches `EXPECTED_VALUES.csv` (logic check, not DAX execution);
* **Microsoft PBIR validator** (`powerbi-report-author validate`): succeeded, 0 errors, 0 warnings;
* **Microsoft TMDL deserializer** (TOM 19.84.1): parsed - 8 tables, 80 columns, 34 measures, 6 relationships, 1 expression.
Two real defects were found and fixed by these Microsoft tools during development (undefined query group in `expressions.tmdl`; theme/slicer/textbox sizing rules).

## 4. What was done in Power BI Desktop (2026-10-13)
Desktop was installed with permission (Store id `9NTXR16HNW1T`). The `.pbip` opened, data was loaded with Desktop's own Refresh/Apply buttons, all five pages were rendered and screenshotted
(`faculty_evidence/powerbi/screenshots/`), rendering defects were fixed in the generator and rebuilt, and the project was saved as `powerbi/FitPulse_PowerBI_Dashboard.pbix`. The `.pbix` was then reopened
(data cached), card values were compared with expected values, and the Activity type slicer was clicked (Cycling) with matching results. Details and gaps: `POWERBI_VALIDATION.md`.
Note: the Desktop Bridge cannot refresh or save; those steps were done through Desktop's own buttons/dialog (Windows UI Automation) and are not exposed as a supported API.

## 5. Refresh procedure
Pipeline rerun -> `.\powerbi\build_powerbi.ps1` -> in Desktop: reload the project (or reopen) -> Home > Refresh. If the project folder moved, regenerate (the generator writes the
current absolute `powerbi\data\` path into the `DataFolder` parameter) or edit it in Desktop: Transform data > Edit parameters.

## 6. Known limitations
* Per-page slicers are independent (I did not find how to author cross-page sync in the schemas I inspected; it can be added in Desktop via View > Sync slicers).
* Data is imported from CSV exports of the local Silver data; Power BI does not connect to HDFS (single-node, replication 1).
* Rendering, DAX results, Power Query load and exact visual formatting are unverified until opened in Desktop.
* `Steps MoM %` relies on the marked date table; the first month shows blank by design.
