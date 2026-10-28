# FitPulse Power BI dashboard - specification and status

> **Superseded for building:** follow `BUILD_GUIDE.md` (exact steps, field wells, expected values) and `measures.dax` (version 2). This file is the original outline.

> **STATUS: NOT BUILT. This folder is PREPARATION only.** No `.pbix` exists, because Power BI Desktop is not installed on this
> machine and a `.pbix` can only be authored and validated inside Power BI Desktop (a GUI application). Nothing here should be
> described as "the Power BI dashboard" until someone has built it from this spec, opened it, and checked the measures against
> `EXPECTED_VALUES.csv`. The working dashboard today is the **Streamlit** app (`dashboard/app.py`), a separate tool.

## Data source and refresh
1. `python models/train_calorie_regression.py` (calorie predictions) and `.\run_supervised.ps1 -Experiment All` (writes `exports/E<n>_results.csv`);
   add `--storage hdfs --hdfs-uri hdfs://localhost:9000` to the first to read Silver from HDFS.
2. `python powerbi/export_powerbi_data.py` -> `powerbi/data/*.csv` (read from the LOCAL Silver, which `scripts/verify_hdfs.py` proves identical to the HDFS Silver).
3. `python powerbi/validate_exports.py` -> checks the CSVs against Silver and writes `EXPECTED_VALUES.csv`.
4. In Power BI Desktop: Get data -> Text/CSV for the files in `powerbi/data/`; paste `measures.dax`; relationship `fact_daily[user_id]` -> `dim_user[user_id]`.
   Refresh = repeat steps 1-3, then Home -> Refresh.

## Pages and visuals (all from real FitPulse data)
| Page | Visual | Fields | Source table |
|---|---|---|---|
| Overview | Cards: Users, Total Days, Avg Daily Steps, Avg Calories, Goal Achievement Rate | measures | fact_daily |
| Activity | Line: Avg Daily Steps by month; Column: Avg Active vs Avg Sedentary Minutes by month | month, measures | monthly_summary / fact_daily |
| Calories | Line: Avg Calories vs Avg Predicted Calories by month; Scatter: actual vs predicted (filter model_split = test, sample); Cards: Test MAE, Test RMSE | calories_burned, predicted_calories | fact_daily |
| Sleep | Line: Avg Sleep Hours and Avg Sleep Quality by month; Scatter: sedentary minutes vs sleep quality | sleep_* | fact_daily |
| Goals | Gauge/card: Goal Achievement Rate; Column: goal rate by day_of_week and by age_group | goal_achieved | fact_daily |
| Supervised results E3 and E4 | Column charts: ROC-AUC and accuracy against the baseline per model; table of leakage runs (INVALID) | Result Value | supervised_results |

Slicers (synced across pages): **Date** (between), **Activity type** (activity_type), **Age group**, **Gender**, and **User** (numeric id,
optional; hide on the overview page). Use aggregated visuals by default; do not show per-user tables on the main pages.

## Validation checklist once built (compare with `EXPECTED_VALUES.csv`)
- Each card equals its expected value (tolerance 0.01 for averages).
- Month-by-month Avg Daily Steps equals the `Average daily steps in YYYY-MM` rows.
- Cross-check checks and checks passed equal the numbers in EXPECTED_VALUES (all experiments selected); Test Days = number in EXPECTED_VALUES.
- Filtering Activity type = Yoga changes totals consistently with `monthly_summary.csv`.

## Optional: installing Power BI Desktop
Available from the Microsoft Store (`winget install 9NTXR16HNW1T --source msstore`). It is a large install (several hundred MB
plus WebView2/.NET prerequisites). Not installed by this project's tooling; installing it and authoring/saving the `.pbix` is a step for the user.
