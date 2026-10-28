# FitPulse — Model Metrics Report

All numbers below are from actual runs against the Silver layer (`data/processed/fitpulse_silver`,
100,122 rows, 437 users), produced by `python3 models/train_*.py`. Nothing here is fabricated —
re-run any script to reproduce these numbers exactly (seeded with `random_state=42`).

---

## Model 1 — Next-Day Goal Achievement Prediction (`train_goal_achievement.py`)

**Task:** binary classification — given the user's pattern *through today*, will they hit
their personalized step goal *tomorrow*?
**Split:** chronological (train on dates before 2024-10-15, test on dates after — a genuine
out-of-time evaluation, not a random shuffle), restricted to consecutive-calendar-day pairs
(a logging gap between two rows doesn't count as a valid 1-day-ahead example).

| Model | Accuracy | F1 (Achieved class) | ROC-AUC |
|---|---|---|---|
| Logistic Regression (baseline) | 0.870 | 0.224 | **0.755** |
| Random Forest Classifier | 0.861 | 0.344 | 0.718 |

**Winner: Logistic Regression** (higher ROC-AUC) — saved to `models/artifacts/goal_achievement_model.joblib`.

**A design mistake we caught and fixed:** the first version of this model was trained to
predict a day's outcome from that *same* day's own rolling-average features (which are
computed inclusive of that day) — a same-day classifier, ROC-AUC 0.828. When the dashboard
started applying it to answer "will I hit *tomorrow's* goal," we checked whether that
repurposing actually held up, rather than assuming it did: evaluated against real next-day
outcomes, the same-day model only reached ROC-AUC 0.738 — a real drop, because it was never
trained for that question. We retrained directly against the actual next-day label instead
(the numbers above), which is both more honest and, in this case, slightly *better*
(0.755 vs. 0.738) than the repurposed original. The lesson worth stating plainly in a viva:
what a label is named matters less than what it was actually trained to predict — always
re-verify a model's evaluation matches its deployed use before trusting it.

**Note on class imbalance:** the test period (Oct–Dec) has a much lower goal-achievement rate
than the training period, because the dataset has a real seasonal swing in activity
(steps peak ~10,100/day in March, trough ~6,800/day in Sept/Oct — see `viva.md`). Accuracy
alone is misleading here; ROC-AUC is the metric to quote.

---

## Model 2 — 7-Day Activity Trend Forecast (`train_forecast.py`)

**Task:** regression — forecast the next 7 days of steps per user, recursively.
**Algorithm:** HistGradientBoostingRegressor (scikit-learn's built-in gradient boosting,
same family as XGBoost/LightGBM), trained on lag/rolling features.
**Evaluation:** genuine walk-forward validation — for each of the 437 users, the last 7 days
were held out and forecast recursively from real history before that point.

| Metric | Value |
|---|---|
| 7-day-ahead MAE | 1,435.9 steps |
| Dataset average daily steps | 8,625 steps |
| MAE as % of average | **16.6%** |

---

## Model 3 — Sleep Quality Prediction (`train_sleep_quality.py`)

**Task:** regression — predict `sleep_quality_score` (0–100) from daytime behavior/physiology.

| Model | MAE | R² |
|---|---|---|
| Linear Regression (baseline) | 4.10 | 0.812 |
| Random Forest Regressor (improved) | **3.49** | **0.876** |

**Winner: Random Forest** — saved to `models/artifacts/sleep_quality_model.joblib`.
**Top drivers (Random Forest feature importance):** `stress_level` (0.587), `sedentary_minutes`
(0.273), `resting_heart_rate` (0.071), `active_minutes` (0.065) — i.e. stress and sitting time
hurt sleep quality far more than any other measured factor, which is exactly the kind of
personalized insight the dashboard surfaces to users.

---

## Model 4 — removed

Heart-rate anomaly flagging was removed from the live project (it is not one of the supervised experiments E1-E5). The script is kept in `archive/anomaly/`; its numbers are not repeated here.

---

## Model 5 — Personalized Recommendation Engine (`recommendation_engine.py`)

**Not a trained model — rule-based logic**, by deliberate design (see the module docstring for
the reasoning). Takes a user's goal shortfall (from Model 1's inputs) and their own historical
pace/calorie-burn rate, and outputs a concrete suggested action (e.g. "14 more minutes of
walking at your usual pace would close today's step gap"). No accuracy metric applies — the
"metric" here is that every recommendation is directly traceable to a number the user can verify.

---

## Model 6 — Percentile Benchmarking (`etl/spark_benchmarks.py`)

**Not machine learning — a statistical computation** (`PERCENT_RANK()` in Spark SQL), computed
once as a batch job over all 437 users, partitioned by (age_group, gender) cohort. Produces each
user's percentile rank for steps, calories burned, and sleep quality within their cohort. No
train/test split applies — if asked in the viva "what's the accuracy of the percentile model?",
the correct answer is "there isn't one; it's not a model."

---

## Summary table

| # | Prediction | Type | Algorithm | Key metric |
|---|---|---|---|---|
| 1 | Next-day goal achievement | Classification | Logistic Regression | ROC-AUC 0.755 |
| 2 | 7-day forecast | Regression (time series) | HistGradientBoosting | MAE 16.6% of avg |
| 3 | Sleep quality | Regression | Random Forest | R² 0.876 |
| 4 | (removed) | - | archived in `archive/anomaly/` | - |
| 5 | Recommendations | Rule-based | — | N/A by design |
| 6 | Percentile benchmarking | Statistics | Spark SQL PERCENT_RANK | N/A — not ML |
