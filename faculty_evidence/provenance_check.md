# Provenance check (independent, read-only)

**16/16 checks passed.** Script: `scripts/provenance_check.py`.

| Check | Result | Detail |
|---|---|---|
| Kaggle source file: 687,701 rows, 3,000 participants | PASS | 687,701 rows, 3000 participants |
| the 437 users are exactly a seeded random sample (seed 42) of the 3,000 | PASS |  |
| Bronze row count equals the Kaggle rows of those 437 users (full yearly series kept, nothing dropped) | PASS | 100,122 vs 100,122 |
| source fields in Bronze (steps, age, height, weight, activity, intensity, heart rates, stress, bmi) equal the Kaggle values row by row | PASS |  |
| calories_burned = MET x weight x minutes/60 within rounding to 0.1 kcal (recomputed independently, all rows) | PASS |  |
| distance_km = steps x height-based stride (recomputed) | PASS |  |
| sleep_minutes = hours_sleep x 60 and active + sedentary + sleep = 1,440 (recomputed) | PASS |  |
| Silver has the same 100,122 rows and users as Bronze | PASS |  |
| Silver source columns equal Bronze (steps, calories, sleep quality) | PASS |  |
| steps_lag1 / steps_lag7 recomputed in pandas equal Spark's | PASS |  |
| steps_roll7_avg (7 logged rows) recomputed equals Spark's | PASS |  |
| personal step goal = 1.10 x user's mean steps rounded to 100 (recomputed) | PASS | 100.0000% identical |
| goal_achieved = steps >= goal (recomputed from Silver goal) | PASS |  |
| saved goal model (LogisticRegression) re-measured on the held-out period: ROC-AUC 0.755 (reported 0.755), accuracy 0.870 (0.870), F1 0.224 (0.224) | PASS | 9,760 test rows |
| web page: all 437 'tomorrow' probabilities equal the saved model's output on each user's final Silver row | PASS |  |
| calorie model re-trained independently (scikit-learn OLS on train rows): test MAE 199.7 / RMSE 263.6 / R2 0.630 vs Spark 199.7 / 263.6 / 0.630 | PASS |  |