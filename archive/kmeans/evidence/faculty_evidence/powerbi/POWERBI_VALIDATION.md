# Power BI dashboard - validation record (2026-10-13)

**Deliverable:** `powerbi/FitPulse_PowerBI_Dashboard.pbix` (4,508,752 bytes), saved by **Power BI Desktop 2.158.1304.0** (File > Save as > "Power BI file (*.pbix)").
Origin: the generated PBIP project (`powerbi/project/`, produced by `powerbi/build_powerbi.py`) opened in Desktop, data loaded, then saved. Nothing in the `.pbix` was hand-edited.

## What was actually done in Power BI Desktop
| Step | Result |
|---|---|
| Installed Desktop (Microsoft Store id 9NTXR16HNW1T, via winget) | Installed, version 2.158.1304.0 |
| Opened the generated `.pbip` (Desktop Bridge `open`) | Loaded; bridge `status` listed the 5 pages by name |
| Loaded the data (Desktop's own "Refresh now" / "Apply changes") | All 8 tables loaded from `powerbi/data/*.csv` |
| Rendered all 5 pages (Bridge `screenshot-all`, real PNGs) | `faculty_evidence/powerbi/screenshots/` |
| Fixed defects found only by rendering | card values clipped; two scatter plots needed the Values well removed / a row key; Page 5 table columns clipped and matrices cramped; grand totals meaningless. Generator and CSV export updated and rebuilt |
| Saved as `.pbix` | File created |
| Closed Desktop, **reopened the `.pbix` itself** | Opened with data already cached (no refresh); bridge `status` reported `currentFilePath` = the `.pbix`, no unsaved changes; window captures in `faculty_evidence/powerbi/pbix_screenshots/` |
| Slicer interaction test (Page 1, Activity type = Cycling, real mouse click) | Cards changed to values equal to an independent pandas computation (below) |

## Card values read from the opened `.pbix` vs independent expected values (`powerbi/EXPECTED_VALUES.csv`)
| Page / visual | Power BI shows | Expected | Match |
|---|---|---|---|
| P1 Total users / user-days | 437 / 1,00,122 | 437 / 100,122 | yes (Indian digit grouping) |
| P1 Avg daily steps / calories / active min / goal rate | 8,625 / 662.2 / 69.9 / 33.8% | 8,624.77 / 662.20 / 69.93 / 33.75% | yes |
| P1 Jan / Feb / Mar average steps (table) | 8,893 / 9,607 / 10,122 | 8,892.6 / 9,607.2 / 10,121.6 | yes |
| P2 distance / active / sedentary / sleep h / sleep quality / heart rate | 6.54 / 69.9 / 947.2 / 7.05 / 67.1 / 130.8 | 6.54 / 69.93 / 947.24 / 7.05 / 67.10 / 130.82 | yes |
| P3 Verified MAE / RMSE / R2 / baseline MAE / test days | 199.7 / 263.6 / 0.6296 / 334.5 / 14,985 | 199.71 / 263.64 / 0.6296 / 334.51 / 14,985 | yes |
| P3 recomputed MAE / RMSE (cross-check table) | 199.7 / 263.6 | same | yes |
| P4 users per segment | 228 / 209 (donut labels, 52.x% / 47.x%) | 228 / 209 | yes |
| P5 (E1) test accuracy / baseline / F1 / AUC | 0.7352 / 0.6144 / 0.7862 / 0.7585 | same (`rf_metrics.csv`) | yes |
| P5 (E1) confusion matrix | 7,202 / 1,888 / 2,030 / 3,676 | same | yes |
| P5 (E3) users clustered / silhouettes / WCSS | 437 / 0.2018 (Euclid.), 0.3413 (Spark) / 2335.22 | same | yes |
| Slicer Cycling: users / avg steps / calories / goal rate / user-days | 437 / 8,595 / 725.7 / 33.3% / 10,740 | 437 / 8,595.0 / 725.7 / 33.3% / 10,740 | yes |

## Automated checks (no Desktop)
* `python powerbi/validate_powerbi_project.py` - 70/70 (data sources, TMDL vs CSV schema, relationships, DAX references, 118 visual field references, pages, experiments separate, pandas emulation of measures, Microsoft PBIR validator 0 errors / 0 warnings, Microsoft TMDL parser).
* `python powerbi/check_pbix.py` - structure of the saved `.pbix` (zip with DataModel, PBIR report, 5 pages, 70 visuals, 15 slicers, all field references resolve): `pbix_structure_check.md`.
* `python powerbi/validate_exports.py` - 28/28 export checks.

## NOT verified / limitations (stated plainly)
* Slicers were exercised by mouse only for **Activity type on Page 1**. The date, age, gender, segment and Page 3-5 slicers were not clicked individually.
* Page 5 per-experiment screenshots (`page5_by_experiment/E1-E5.png`) were produced by rebuilding the project with each experiment as the slicer default (not by clicking), on an intermediate layout build; the final layout differs slightly in column widths.
* The visible Desktop "Optimize your report for mobile" tip overlays the lower-left of the screenshots; it is a Desktop UI hint, not part of the report.
* The `.pbix` imports CSV files from `D:\bigdata\fitpulsee\FitPulse\powerbi\data\` (the `DataFolder` parameter). Moving the project requires editing that parameter (Transform data > Edit parameters) and Refresh.
* Power BI imports CSV exports of the local Silver data; it does not connect to HDFS (single node, replication factor 1).
* Slicers are per page (no cross-page sync). Line-chart axes are auto-scaled.
* DAX behaviour was exercised through the visuals above; there was no separate DAX test suite inside Desktop.
