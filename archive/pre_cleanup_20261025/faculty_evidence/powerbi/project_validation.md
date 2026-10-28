# Power BI project validation (automated; Power BI Desktop NOT used)
**70/70 checks passed.**

Not covered: DAX execution, Power Query data load, rendering, slicer behaviour - these need Power BI Desktop.

| Check | Result | Detail |
|---|---|---|
| A1 .pbip, .Report/definition.pbir and .SemanticModel/definition.pbism exist | PASS |  |
| A2 report binds to the semantic model by relative path | PASS | {'byPath': {'path': '../FitPulse_PowerBI_Dashboard.SemanticModel'}} |
| A3 DataFolder parameter points at an existing folder | PASS | D:\bigdata\fitpulsee\FitPulse\powerbi\data\ |
| A4 table confusion_matrices: CSV exists and TMDL columns == CSV header | PASS | confusion_matrices.csv 6 cols |
| A4 table dim_date: CSV exists and TMDL columns == CSV header | PASS | dim_date.csv 7 cols |
| A4 table dim_user: CSV exists and TMDL columns == CSV header | PASS | dim_user.csv 11 cols |
| A4 table experiments: CSV exists and TMDL columns == CSV header | PASS | experiments.csv 6 cols |
| A4 table fact_daily: CSV exists and TMDL columns == CSV header | PASS | fact_daily.csv 27 cols |
| A4 table kmeans_k_selection: CSV exists and TMDL columns == CSV header | PASS | kmeans_k_selection.csv 4 cols |
| A4 table model_evaluation: CSV exists and TMDL columns == CSV header | PASS | model_evaluation.csv 11 cols |
| A4 table segment_profile: CSV exists and TMDL columns == CSV header | PASS | segment_profile.csv 10 cols |
| A5 tables in model == tables in spec | PASS |  |
| A6 relationship fact_daily[date] -> dim_date[Date] uses existing columns | PASS |  |
| A7 relationship dim_date[Date] is unique (one side) and covers all fact_daily[date] values | PASS | 360 distinct -> 366 keys |
| A6 relationship fact_daily[user_id] -> dim_user[user_id] uses existing columns | PASS |  |
| A7 relationship dim_user[user_id] is unique (one side) and covers all fact_daily[user_id] values | PASS | 437 distinct -> 437 keys |
| A6 relationship dim_user[segment_id] -> segment_profile[cluster] uses existing columns | PASS |  |
| A7 relationship segment_profile[cluster] is unique (one side) and covers all dim_user[segment_id] values | PASS | 2 distinct -> 2 keys |
| A6 relationship model_evaluation[experiment_id] -> experiments[experiment_id] uses existing columns | PASS |  |
| A7 relationship experiments[experiment_id] is unique (one side) and covers all model_evaluation[experiment_id] values | PASS | 5 distinct -> 5 keys |
| A6 relationship confusion_matrices[experiment_id] -> experiments[experiment_id] uses existing columns | PASS |  |
| A7 relationship experiments[experiment_id] is unique (one side) and covers all confusion_matrices[experiment_id] values | PASS | 2 distinct -> 5 keys |
| A6 relationship kmeans_k_selection[experiment_id] -> experiments[experiment_id] uses existing columns | PASS |  |
| A7 relationship experiments[experiment_id] is unique (one side) and covers all kmeans_k_selection[experiment_id] values | PASS | 2 distinct -> 5 keys |
| B0 measure count in model == spec | PASS | 34 |
| B1 every table[column] and [measure] referenced in DAX exists | PASS | 34 measures checked |
| C1 the five requested pages exist with exact names | PASS | ['Calorie Prediction', 'Activity and Sleep', 'User Segmentation', 'Model Evaluation', 'Fitness Overview'] |
| C2 page order follows the requested sequence | PASS |  |
| C3 no visual references a nonexistent column or measure (and every spec field is present) | PASS | 70 visuals, 114 field references (spec expects 114) |
| C4 page 'Calorie Prediction': slicers >= 2 and data visuals >= 5 | PASS | 2 slicers, 10 data visuals |
| C4 page 'Activity and Sleep': slicers >= 2 and data visuals >= 5 | PASS | 5 slicers, 11 data visuals |
| C4 page 'User Segmentation': slicers >= 2 and data visuals >= 5 | PASS | 2 slicers, 8 data visuals |
| C4 page 'Model Evaluation': slicers >= 1 and data visuals >= 4 | PASS | 1 slicers, 4 data visuals |
| C4 page 'Fitness Overview': slicers >= 2 and data visuals >= 5 | PASS | 5 slicers, 10 data visuals |
| C5 every visual lies inside the 1280x720 page | PASS | 70 |
| C6 experiment ids E1-E5 preserved and distinct in experiments/model_evaluation/confusion/kmeans tables | PASS |  |
| C7 page 5 has a single-select experiment slicer with a default experiment (results are never mixed) | PASS |  |
| C8 page 4 states it is user-level (437 users) and not the user-day experiment | PASS |  |
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
| D2 Users in Segment 'Highest active-time' = 228 vs expected | PASS |  |
| D2 Users in Segment 'Lowest active-time' = 209 vs expected | PASS |  |
| D3 Segment Share % sums to 100% | PASS |  |
| D4 monthly average steps (page 1 trend) equals expected for all 12 months | PASS |  |
| E1 Microsoft PBIR validator (powerbi-report-author validate): 0 errors, 0 warnings | PASS | succeeded, 0 errors, 0 warnings |
| E2 Microsoft TMDL deserializer (TOM) parses the semantic model | PASS | TMDL parsed OK: 8 tables, 82 columns, 34 measures, 6 relationships, 1 expressions |
| F1 generated text files are UTF-8 without BOM | PASS | [] |
| F2 longest project path < 260 characters (Windows limit) | PASS | 158 |