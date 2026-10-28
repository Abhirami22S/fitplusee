# Power BI project validation (automated; Power BI Desktop NOT used)
**65/65 checks passed.**

Not covered: DAX execution, Power Query data load, rendering, slicer behaviour - these need Power BI Desktop.

| Check | Result | Detail |
|---|---|---|
| A1 .pbip, .Report/definition.pbir and .SemanticModel/definition.pbism exist | PASS |  |
| A2 report binds to the semantic model by relative path | PASS | {'byPath': {'path': '../FitPulse_PowerBI_Dashboard.SemanticModel'}} |
| A3 DataFolder parameter points at an existing folder | PASS | D:\bigdata\fitpulsee\FitPulse\powerbi\data\ |
| A4 table crosscheck: CSV exists and TMDL columns == CSV header | PASS | crosscheck.csv 7 cols |
| A4 table dim_date: CSV exists and TMDL columns == CSV header | PASS | dim_date.csv 7 cols |
| A4 table dim_user: CSV exists and TMDL columns == CSV header | PASS | dim_user.csv 7 cols |
| A4 table experiments: CSV exists and TMDL columns == CSV header | PASS | experiments.csv 2 cols |
| A4 table fact_daily: CSV exists and TMDL columns == CSV header | PASS | fact_daily.csv 25 cols |
| A4 table supervised_results: CSV exists and TMDL columns == CSV header | PASS | supervised_results.csv 7 cols |
| A5 tables in model == tables in spec | PASS |  |
| A6 relationship fact_daily[date] -> dim_date[Date] uses existing columns | PASS |  |
| A7 relationship dim_date[Date] is unique (one side) and covers all fact_daily[date] values | PASS | 360 distinct -> 366 keys |
| A6 relationship fact_daily[user_id] -> dim_user[user_id] uses existing columns | PASS |  |
| A7 relationship dim_user[user_id] is unique (one side) and covers all fact_daily[user_id] values | PASS | 437 distinct -> 437 keys |
| A6 relationship supervised_results[experiment_id] -> experiments[experiment_id] uses existing columns | PASS |  |
| A7 relationship experiments[experiment_id] is unique (one side) and covers all supervised_results[experiment_id] values | PASS | 5 distinct -> 5 keys |
| A6 relationship crosscheck[experiment_id] -> experiments[experiment_id] uses existing columns | PASS |  |
| A7 relationship experiments[experiment_id] is unique (one side) and covers all crosscheck[experiment_id] values | PASS | 5 distinct -> 5 keys |
| B0 measure count in model == spec | PASS | 29 |
| B1 every table[column] and [measure] referenced in DAX exists | PASS | 29 measures checked |
| C1 the five requested pages exist with exact names | PASS | ['Supervised Results E3 and E4', 'Calorie Prediction', 'Activity and Sleep', 'Model Evaluation', 'Fitness Overview'] |
| C2 page order follows the requested sequence | PASS |  |
| C3 no visual references a nonexistent column or measure (and every spec field is present) | PASS | 68 visuals, 149 field references (spec expects 149) |
| C4 page 'Supervised Results E3 and E4': slicers >= 0 and data visuals >= 5 | PASS | 0 slicers, 7 data visuals |
| C4 page 'Calorie Prediction': slicers >= 2 and data visuals >= 5 | PASS | 2 slicers, 10 data visuals |
| C4 page 'Activity and Sleep': slicers >= 2 and data visuals >= 5 | PASS | 4 slicers, 11 data visuals |
| C4 page 'Model Evaluation': slicers >= 1 and data visuals >= 4 | PASS | 1 slicers, 6 data visuals |
| C4 page 'Fitness Overview': slicers >= 2 and data visuals >= 5 | PASS | 4 slicers, 10 data visuals |
| C5 every visual lies inside the 1280x720 page | PASS | 68 |
| C6 experiment ids E1-E5 preserved and distinct in experiments / supervised_results / crosscheck | PASS |  |
| C7 every visual showing Result Value names its experiment (column shown, or pinned to a single experiment by a filter) - results are never mixed | PASS | [] |
| C8 page 4 shows only E3 and E4: every Result Value visual is pinned by a filter to E3 and/or E4 | PASS | [] |
| C9 page 4 states that E3 and E4 are never combined | PASS |  |
| C10 page 5: both cross-check cards show a title that names hdfs_rerun/sklearn_crosscheck.csv as their source | PASS | [(True, "'Passed - source: hdfs_rerun/sklearn_crosscheck.csv'"), (True, "'Checks - source: hdfs_rerun/sklearn_crosscheck |
| D0 every headline measure has a pandas emulation | PASS | [] |
| D1 Total Users: emulated 437.0000 vs expected 'Distinct users' 437.0000 | PASS |  |
| D1 User-Days: emulated 100,122.0000 vs expected 'Total days (rows)' 100,122.0000 | PASS |  |
| D1 Total Steps: emulated 863,529,003.0000 vs expected 'Total steps' 863,529,003.0000 | PASS |  |
| D1 Avg Daily Steps: emulated 8,624.7678 vs expected 'Average daily steps' 8,624.7678 | PASS |  |
| D1 Avg Calories Burned: emulated 662.2013 vs expected 'Average calories burned' 662.2013 | PASS |  |
| D1 Avg Active Minutes: emulated 69.9294 vs expected 'Average active minutes' 69.9294 | PASS |  |
| D1 Step-Goal Achievement %: emulated 0.3375 vs expected 'Personal step-goal achievement rate' 0.3375 | PASS |  |
| D1 Calorie-Goal Achievement %: emulated 0.3533 vs expected 'Calorie-goal achievement rate' 0.3533 | PASS |  |
| D1 Avg Distance (km): emulated 6.5400 vs expected 'Average distance (km)' 6.5400 | PASS |  |
| D1 Avg Sedentary Minutes: emulated 947.2411 vs expected 'Average sedentary minutes' 947.2411 | PASS |  |
| D1 Avg Sleep Hours: emulated 7.0472 vs expected 'Average sleep hours' 7.0472 | PASS |  |
| D1 Avg Sleep Quality: emulated 67.0993 vs expected 'Average sleep quality' 67.0993 | PASS |  |
| D1 Avg Heart Rate: emulated 130.8156 vs expected 'Average heart rate (bpm)' 130.8156 | PASS |  |
| D1 Active Share of Waking Time %: emulated 0.0687 vs expected 'Active share of waking time' 0.0687 | PASS |  |
| D1 Test Days: emulated 14,985.0000 vs expected 'Test-set days' 14,985.0000 | PASS |  |
| D1 Test MAE (recomputed, kcal): emulated 199.7126 vs expected 'Test-set MAE (kcal)' 199.7126 | PASS |  |
| D1 Test RMSE (recomputed, kcal): emulated 263.6442 vs expected 'Test-set RMSE (kcal)' 263.6442 | PASS |  |
| D1 Test R2 (recomputed): emulated 0.6296 vs expected 'Test-set R2' 0.6296 | PASS |  |
| D1 Avg Prediction Error (bias, kcal): emulated -3.6304 vs expected 'Test-set mean error / bias (kcal)' -3.6304 | PASS |  |
| D1 Verified Test MAE (kcal): emulated 199.7126 vs expected 'Test-set MAE (kcal)' 199.7126 | PASS |  |
| D1 Verified Test RMSE (kcal): emulated 263.6442 vs expected 'Test-set RMSE (kcal)' 263.6442 | PASS |  |
| D1 Verified Test R2: emulated 0.6296 vs expected 'Test-set R2' 0.6296 | PASS |  |
| D1 Baseline Test MAE (kcal): emulated 334.5102 vs expected 'Baseline (training mean) test MAE (kcal)' 334.5102 | PASS |  |
| D1 Cross-check Checks: emulated 103.0000 vs expected 'Cross-check checks' 103.0000 | PASS |  |
| D1 Cross-check Passed: emulated 103.0000 vs expected 'Cross-check checks passed' 103.0000 | PASS |  |
| D3 monthly average steps (page 1 trend) equals expected for all 12 months | PASS |  |
| E1 Microsoft PBIR validator (powerbi-report-author validate): 0 errors, 0 warnings | PASS | succeeded, 0 errors, 0 warnings |
| E2 Microsoft TMDL deserializer (TOM) parses the semantic model | PASS | TMDL parsed OK: 6 tables, 55 columns, 29 measures, 4 relationships, 1 expressions |
| F1 generated text files are UTF-8 without BOM | PASS | [] |
| F2 longest project path < 260 characters (Windows limit) | PASS | 158 |