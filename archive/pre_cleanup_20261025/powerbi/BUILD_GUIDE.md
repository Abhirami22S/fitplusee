# Building FitPulse_PowerBI_Dashboard.pbix in Power BI Desktop - exact steps

> **Update:** a generated, offline-validated Power BI *project* now exists - see `AUTOMATED_BUILD.md`. Prefer it: open `project\FitPulse_PowerBI_Dashboard.pbip` in Desktop and Save as `.pbix`. Use this manual guide only if the project fails to open. Note: this guide lists `monthly_summary`/`model_metrics` as not needed and uses a DAX-calculated `dim_date`; the generated project instead imports `dim_date.csv`.

**Status:** the `.pbix` does NOT exist yet. Power BI Desktop was not installed on this machine when this guide was written, and a `.pbix` can
only be authored in Desktop's GUI. Everything else is prepared and validated (data, DAX, theme, expected values, a checker for the finished file).
Estimated GUI time: 60-90 minutes.

## 0. Install Power BI Desktop (one time)
* Microsoft Store -> search "Power BI Desktop" -> Install; or PowerShell: `winget install 9NTXR16HNW1T --source msstore`.
* Sign-in is not required to build and save a local report. Free disk needed: about 1-2 GB (C: has ~100 GB free).
* Launch it once. Tell me when it is installed - I can then confirm the path and help with errors, but the clicking below is done by you.

## 1. Refresh the data files (already done once; repeat after any pipeline rerun)
```powershell
cd D:\bigdata\fitpulsee\FitPulse
..\.venv\Scripts\python.exe powerbi\export_powerbi_data.py
..\.venv\Scripts\python.exe powerbi\export_model_evaluation.py
..\.venv\Scripts\python.exe powerbi\validate_exports.py      # must print only [PASS]; also rewrites EXPECTED_VALUES.csv
```
Source of the data: the **local Silver Parquet** (proven row-for-row identical to the HDFS Silver by `scripts/verify_hdfs.py`) plus saved model-evaluation files.
Power BI imports CSV files; it does **not** connect to HDFS.

## 2. Load the data (Home -> Get data -> Text/CSV)
Folder: `D:\bigdata\fitpulsee\FitPulse\powerbi\data\`. Import these 7 files (click **Transform Data**, not Load, for the first one to set the parameter):
`fact_daily.csv`, `dim_user.csv`, `segment_profile.csv`, `experiments.csv`, `model_evaluation.csv`, `confusion_matrices.csv`, `kmeans_k_selection.csv`.
(Do not import `monthly_summary.csv` or `model_metrics.csv`; they are superseded.)

**Relative/refreshable path (recommended):** Home -> Manage parameters -> New: Name `DataFolder`, Type Text, Current value `D:\bigdata\fitpulsee\FitPulse\powerbi\data\`.
For each query: Home -> Advanced Editor and change the path argument: `File.Contents(DataFolder & "fact_daily.csv")` (same pattern for each file).
Moving the project only requires changing this one parameter.

**Column types (Power Query):**
| Table | Set type |
|---|---|
| fact_daily | `date` = **Date**; `user_id`, `steps`, `active_minutes`, `sedentary_minutes`, `avg_heart_rate`, `goal_achieved`, `calorie_goal_achieved`, `segment_id`, `error_bin_kcal` = Whole number; the other numeric columns = Decimal number; text columns Text |
| dim_user | `user_id`, `age`, `days`, `segment_id` = Whole number; `PC1`, `PC2`, `avg_*` = Decimal |
| segment_profile | `cluster`, `Users` = Whole number; rest Decimal |
| experiments / model_evaluation / confusion_matrices / kmeans_k_selection | `value`, `count`, `share_of_actual` = Decimal; `K`, `is_baseline` = Whole number; rest Text |
Close & Apply. Check: `fact_daily` 100,122 rows; `dim_user` 437 rows (Table view / Model view).

## 3. Model (Model view)
1. Create `dim_date` and the measures: copy the blocks from `powerbi/measures.dax` (Modeling -> New table for `dim_date`; Home -> Enter data, name `_Measures`, then Modeling -> New measure for each).
   Select `dim_date` -> Table tools -> **Mark as date table** -> Date column. Set sort: `dim_date[Month]` by `MonthNumber`, `dim_date[DayOfWeek]` by `DayOfWeekNumber`.
2. Relationships (drag, or Manage relationships), all single direction, many-to-one:
   | From (many) | To (one) |
   |---|---|
   | fact_daily[date] | dim_date[Date] |
   | fact_daily[user_id] | dim_user[user_id] |
   | dim_user[segment_id] | segment_profile[cluster] |
   | model_evaluation[experiment_id] | experiments[experiment_id] |
   | confusion_matrices[experiment_id] | experiments[experiment_id] |
   | kmeans_k_selection[experiment_id] | experiments[experiment_id] |
3. Hide from Report view: `fact_daily[segment_id]`, `fact_daily[segment_label]` (use `dim_user[...]`), all `*_id` key columns on the many side, and `fact_daily[month]`.
4. Format measures (Measure tools): `%` measures -> Percentage, 1 decimal; steps/users/user-days -> whole number with thousands separator; kcal measures -> 1 decimal; `Test R2`, `Verified Test R2` -> 4 decimals.
5. Data category: `dim_user[user_id]` none. Make sure `fact_daily[calories_burned]`, `predicted_calories`, `calorie_error` are **Don't summarize**.

## 4. Theme and page setup
View -> Themes -> Browse for themes -> `powerbi\FitPulse_theme.json`. Page size 16:9. Create 5 pages named EXACTLY (the checker looks for these):
`Fitness Overview`, `Activity and Sleep`, `Calorie Prediction`, `User Segmentation`, `Model Evaluation`.
Add to every page: a title text box, and a footnote text box (data source, granularity).

## 5. Pages - visuals, field wells, expected values
Validate every card against `powerbi/EXPECTED_VALUES.csv` (no filters applied).

### Page 1 - Fitness Overview
Footnote: "Source: Silver dataset (local Parquet) exported to CSV. fact_daily = one row per user-day (100,122). Step goal = 1.10 x the user's own average daily steps (not a fixed 8,000)."
| Visual | Fields | Expected (unfiltered) |
|---|---|---|
| Card | Total Users | 437 |
| Card | User-Days | 100,122 |
| Card | Avg Daily Steps | 8,624.77 |
| Card | Avg Calories Burned | 662.20 |
| Card | Avg Active Minutes | 69.93 |
| Card | Step-Goal Achievement % | 33.75% |
| Line + clustered column | X `dim_date[YearMonth]`; columns `Avg Calories Burned`; line `Avg Daily Steps` | Jan 8,892.6 ... Sep 6,851.6 (see "Average daily steps in YYYY-MM") |
| Scatter | Details `dim_user[user_id]`; X `Avg Daily Steps`; Y `Avg Calories Burned` (437 points = one per user) | - |
| Column | X `dim_date[DayOfWeek]`; Y `Step-Goal Achievement %` | Sat 56.9%, Sun 56.3%, Mon 24.4% ... |
| Slicers | `dim_date[Date]` (Between), `fact_daily[activity_type]` (dropdown), `dim_user[age_group]`, `dim_user[gender]`, `dim_user[segment_label]` | - |

### Page 2 - Activity and Sleep
Footnote: "Derived: sleep_hours = sleep_minutes / 60. Active + sedentary + sleep minutes = 1,440 per day."
| Visual | Fields | Expected |
|---|---|---|
| Cards | Avg Distance (km) / Avg Active Minutes / Avg Sedentary Minutes / Avg Sleep Hours / Avg Sleep Quality | 6.54 / 69.93 / 947.24 / 7.05 / 67.10 |
| Line | X `dim_date[YearMonth]`; Y `Avg Sleep Hours`, secondary `Avg Sleep Quality` | - |
| Clustered column | X `fact_daily[intensity]`; Y `Avg Daily Steps`, `Avg Calories Burned` | - |
| Clustered column | X `fact_daily[activity_type]`; Y `Avg Active Minutes` | - |
| Scatter | Details `dim_user[user_id]`; X `Avg Sedentary Minutes`; Y `Avg Sleep Quality` | - |
| Line | X `dim_date[YearMonth]`; Y `Avg Active Minutes`, `Avg Sedentary Minutes` | - |
| Slicers | synced from page 1: Date, activity_type, age_group, gender | - |

### Page 3 - Calorie Prediction (experiment E5, Linear Regression, target: same-day calories_burned)
Footnote: "Accuracy figures use TEST days only (14,985). Seeded 70/15/15 split; features exclude calorie-derived columns."
| Visual | Fields | Expected |
|---|---|---|
| Cards | Verified Test MAE (kcal) / Verified Test RMSE (kcal) / Verified Test R2 / Baseline Test MAE (kcal) / Test Days | 199.71 / 263.64 / 0.6296 / 334.51 / 14,985 |
| Small cards (cross-check) | Test MAE (recomputed, kcal) / Test RMSE (recomputed, kcal) / Test R2 (recomputed) / Avg Prediction Error (bias, kcal) | 199.71 / 263.64 / 0.6296 / -3.63 |
| Scatter | X `fact_daily[calories_burned]`, Y `fact_daily[predicted_calories]` (Don't summarize); **visual filter** `model_split = test`; Analytics pane -> Symmetry shading ON | points hug the diagonal; R2 0.63 means visible spread |
| Column (histogram) | X `fact_daily[error_bin_kcal]`; Y Count of `fact_daily[calorie_error]`; visual filter `model_split = test` | roughly symmetric around 0 |
| Line | X `dim_date[YearMonth]`; Y `Avg Calories Burned`, `Avg Predicted Calories` | the two lines track each other |
| Table | `fact_daily[activity_type]`, `Test MAE (recomputed, kcal)`, `Test Days` | - |
Note on the page: "Training rows are in the file but excluded from every accuracy visual."

### Page 4 - User Segmentation (experiment E3: K-Means on 437 USERS, K = 2)
Banner: "User-level clusters (437 users). Not the faculty notebook's K-Means, which clusters 100,122 user-days."
| Visual | Fields | Expected |
|---|---|---|
| Cards | Users in Segment (by segment, use a multi-row card or table) | Highest active-time 228, Lowest active-time 209 |
| Donut | Legend `dim_user[segment_label]`; Values `Users in Segment` | 52.2% / 47.8% |
| Table | `segment_profile` (all columns) | profile from Spark run |
| Clustered column x3 | X `dim_user[segment_label]`; Y `Avg Active Minutes`; second: `Avg Sedentary Minutes`; third: `Avg Sleep Hours` | active 71.09 vs 68.67; sedentary 944.60 vs 950.11; sleep 7.07 vs 7.02 |
| Scatter | Details `dim_user[user_id]`; X `dim_user[PC1]`; Y `dim_user[PC2]` (Don't summarize); Legend `segment_label` | PCA of the 7 standardised features |
| Text box | "The two segments differ by only about 2.4 active minutes, 5.5 sedentary minutes and 28 kcal; average steps are the same (8,631 vs 8,621). Euclidean silhouette 0.20 = weak separation." | measured |
Slicers: age_group, gender.

### Page 5 - Model Evaluation (each experiment shown separately; never combined)
| Visual | Fields | Notes |
|---|---|---|
| Slicer (single select, required) | `experiments[experiment_name]` | default E1 |
| Table | `experiments[target]`, `[data_granularity]`, `[split_method]` | follows the slicer |
| Matrix | Rows `model_evaluation[metric]`; Columns `model_evaluation[evaluation_set]`; Values `Metric Value`; add `model_evaluation[algorithm]` as a rows level | E1 test: accuracy 0.7352, ROC AUC 0.7585, precision 0.7801, recall 0.7923, F1 0.7862 |
| Matrix (confusion) | Rows `confusion_matrices[actual]`; Columns `[predicted]`; Values `Confusion Count`; conditional background | E1: 3,676 / 2,030 / 1,888 / 7,202; E2: 3,940 / 2,001 / 645 / 2,820. Only E1/E2 have rows; hide for others |
| Line | X `kmeans_k_selection[K]`; Y `K Metric Value`; Legend `metric`; visual filter metric contains "Silhouette" | E3: Euclidean K=2 0.2018; Spark K=2 0.3413. E4: K=2 0.3528 |
| Text box | "Spark's silhouette uses squared Euclidean distance; scikit-learn's uses Euclidean. The same K=2 grouping scores 0.341 vs 0.202." | measured (faculty_evidence/report_aligned/kmeans_silhouette_definition_check.txt) |
| Text box | "Dashboard Logistic Regression (ROC-AUC 0.755) is documented in models/metrics_report.md and is not part of this table (not re-run)." | honest scope |

## 6. Accessibility and finish
Add alt text to every visual; set tab order; View -> Page view -> Fit to page. Remove unused fields. **File -> Save as** `D:\bigdata\fitpulsee\FitPulse\powerbi\FitPulse_PowerBI_Dashboard.pbix`.

## 7. Refresh procedure (for the demo and later)
Run section 1, open the `.pbix`, Home -> **Refresh**. If Power BI cannot find the files, fix the `DataFolder` parameter (Home -> Transform data -> Edit parameters).

## 8. Validation (what I need you to do, and what I will check)
1. For every card: compare to the Expected column above / `EXPECTED_VALUES.csv`. Note any mismatch.
2. Slicer tests: set `activity_type = Yoga` and confirm User-Days drops and Total Users stays <= 437; set Date to Jun-Aug and confirm Avg Daily Steps matches the "Average daily steps in YYYY-MM" values combined; clear filters.
3. Open each page and confirm no visual shows a warning triangle / "Can't display the visual".
4. Take one screenshot per page (Win+Shift+S) and save them in `faculty_evidence\powerbi\screenshots\` named `page1_overview.png` ... `page5_model_evaluation.png`. These must be real screenshots of your report.
5. Run `..\.venv\Scripts\python.exe powerbi\check_pbix.py` - checks the saved file's structure, that all field references exist, and writes `faculty_evidence\powerbi\pbix_structure_check.md`.
6. Tell me the result. Only then will I update the report, slides, README, viva and faculty notes to call Power BI the primary dashboard.
