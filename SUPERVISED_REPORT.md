# FitPulse - Supervised Experiments E1-E5: Results, Verification and Disclosures

Prepared 24 Oct 2026 from the files already in the project. **Nothing was re-run to write this report**: no Spark job and no cross-check was executed. Every result figure below (metrics, counts, differences, tolerances) was read from the CSV named beside it and inserted by a script, not typed by hand. What does not come from a CSV is marked as such: file modification times, line numbers, git state, and statements quoted from the notebook or READMEs. Design constants named in the scripts' documentation (the 70/15/15 split proportions, the 1e-6 display threshold in the comparison table, the 0.001 flag threshold) are stated as such, not as CSV values.

Updated 25 Oct 2026: after the dashboards were rebuilt, only the statements about the dashboards (section 1 item 6, section 6 item 8, Q1) and the wording about the earlier segmentation experiments were changed; no number in this report was changed.

Evidence tags: **[VERIFIED]** checked against the file named next to it | **[INTERPRETATION]** my reading of verified numbers | **[LIMITATION]** a stated weakness | **[UNCONFIRMED]** plausible but the project holds no evidence | **[UNKNOWN]** no evidence either way.

Paths are relative to the project folder `FitPulse/`. `exports/` holds the LOCAL run; `faculty_evidence/supervised/hdfs_rerun/` holds the HDFS rerun.

## 1. Summary

Five supervised experiments (E1-E5) were run in Spark MLlib on the Silver daily dataset (100,122 user-days). They replaced the two earlier user-segmentation experiments (old E3 and E4) because the faculty asked for supervised learning only; the old code is kept in `archive/` (`archive/README.md`). Results are in `exports/E<n>_results.csv`; evidence is in `faculty_evidence/supervised/`; the supervised sections of `FitPulse_Faculty_Demo.ipynb` (5-7, 9 and 10) read those files.

**Results at a glance** (headline evaluation of each experiment; ranges are across the models tried)

| Exp | Headline evaluation | Accuracy / R2 | ROC-AUC / MAE | Baseline | Reading [INTERPRETATION] |
|---|---|---|---|---|---|
| E1 same-day goal | test | 0.7352-0.7382 | 0.7396-0.7735 | accuracy 0.6144 | clearly above baseline |
| E2 next-day goal | chronological test | 0.5823-0.6835 | 0.6706-0.7004 | accuracy 0.5886 | weak; Random Forest accuracy is below baseline |
| E3 user high_achiever | 5-fold CV, out-of-fold | 0.5355-0.5378 | 0.5425-0.5486 | accuracy 0.5011 | no reliable skill |
| E4 activity level | user-held-out test | 0.5036-0.5056 | 0.4965-0.4999 | accuracy 0.5079 | no skill (accuracy below baseline) |
| E5 calories (regression) | test | R2 0.6296-0.6658 | MAE 183.28-199.71 kcal | training-mean MAE 334.51 kcal | beats baseline; formula recovery, see section 6 |

Sources: `faculty_evidence/supervised/final_metric_table_classification.csv` (E1-E4), `faculty_evidence/supervised/final_metric_table_regression.csv` (E5).

**Verification at a glance**

- Independent scikit-learn cross-check on the HDFS rerun: **103 checks, 103 pass** (E1 27, E2 25, E3 14, E4 24, E5 13); the original, defective copy was 102/103 with one failing value of 27102.0 (section 4.3).
- Local vs HDFS rerun: **485 rows compared, 0 flagged**, maximum absolute difference 6.7596e-05 (section 4.4).
- Leakage tests: 17 leakage runs are recorded in table 4.1, every one with status INVALID and none used as a result (section 4.1).

**Disclosures at a glance** (details in the sections named)

1. The first E2 no-future-information check was defective (failing value 27102.0); it was fixed, and a separate all-users check was added (section 4.3).
2. The full cross-check could not be run on the LOCAL outputs: they lack the E1 validation prediction files the current cross-check script reads (by code reading; I did not execute it). The evidence is from the HDFS rerun. What changed in the E1 script is **[UNCONFIRMED]**; no history exists to diff (section 5.1).
3. The HDFS-rerun cross-check is linked to the local results only through the local-vs-HDFS comparison table (section 5.2).
4. The local E5 outputs were regenerated at 19:27:07; the reason for that, and the 2 h 4 min 38 s gap after the tuning grid, are **[UNKNOWN]** (section 5.3).
5. Several columns are partly derived in this dataset, so some scores are formula recovery (section 6).
6. Power BI pages 4 and 5 were rebuilt to show only these results and the web page no longer shows a user grouping; the saved `.pbix` still has to be re-saved from the regenerated project in Power BI Desktop (section 6).

## 2. What each experiment predicts and how it is evaluated

| Exp | Task | Label (target) | Evaluation protocol | Rows / users | Feature columns | Models |
|---|---|---|---|---|---|---|
| E1 | Did the user reach the step goal today? | `label (steps >= 8000)` | seeded random 70/15/15 split of user-days; plus a user-held-out run (`test (user-held-out)` in exports/E1_results.csv) | train 70,383 / validation 14,943 / test 14,796 | 18 | Random Forest, Logistic Regression, Gradient-Boosted Trees |
| E2 | Will the user reach the goal tomorrow, from history only? | `label (steps(t) >= 8000)` | CHRONOLOGICAL: train to 2024-09-08, validation to 2024-11-02, test after | train 50,014 / validation 6,513 / test 7,647 | 20 | Random Forest, Logistic Regression, Gradient-Boosted Trees |
| E3 | Is a user a high achiever (goal rate above the median user)? | `high_achiever (goal rate > median user)` | stratified 5-fold cross-validation, out-of-fold predictions | 437 users, 218 high achievers | 9 | Random Forest, Logistic Regression |
| E4 | Is a user-day high or low activity (active minutes above the median)? | `label (active_minutes > median)` | USER-HELD-OUT: whole users are assigned to train / validation / test | users: train 312 / validation 72 / test 53 | 16 | Random Forest, Logistic Regression, Gradient-Boosted Trees |
| E5 | How many calories were burned today (regression)? | `calories_burned` | seeded random 70/15/15 split; plus a chronological test (`chronological test (>= 2024-10-15)` in exports/E5_results.csv) | train 70,085 / validation 15,052 / test 14,985 | 10 | Linear Regression, Random Forest Regressor, GBT Regressor (+ 2 baselines) |

Sources: `faculty_evidence/supervised/final_feature_set_E1_E5.csv` (labels, feature counts), `faculty_evidence/supervised/predictions/E1_splits.csv`, `faculty_evidence/supervised/E2_split_summary.csv`, `faculty_evidence/supervised/predictions/E3_user_table.csv`, `faculty_evidence/supervised/predictions/E4_splits.csv`, `faculty_evidence/supervised/predictions/E5_splits.csv`. Every random operation uses seed 42 (same in the local and HDFS runs).

## 3. Final metric tables

Values are from the LOCAL run (`exports/`), exactly the numbers the notebook prints. The HDFS rerun reproduces them within the differences shown in section 4.4.

### 3.1 E1 - same-day goal (label: steps >= 8,000)

**Random 70/15/15 split, test set** (source: `faculty_evidence/supervised/final_metric_table_classification.csv`)

| Model | Accuracy | F1 (weighted) | ROC-AUC |
|---|---|---|---|
| Random Forest | 0.7352 | 0.7346 | 0.7585 |
| Logistic Regression | 0.7356 | 0.7305 | 0.7396 |
| Gradient-Boosted Trees | 0.7382 | 0.7381 | 0.7735 |
| Baseline: always the majority class | 0.6144 | - | - |

**User-held-out run (users never seen in training)** (source: `exports/E1_results.csv`, split_type `test (user-held-out)`)

| Model | Accuracy | F1 (weighted) | ROC-AUC |
|---|---|---|---|
| Random Forest | 0.7232 | 0.7232 | 0.7498 |
| Logistic Regression | 0.7315 | 0.7275 | 0.7340 |
| Gradient-Boosted Trees | 0.7224 | 0.7223 | 0.7608 |
| Baseline: always the majority class | 0.6168 | - | - |

[INTERPRETATION] All three models beat the majority baseline: accuracy is 12.1-12.4 percentage points above it. On users never seen in training the ROC-AUC is slightly lower (0.7340-0.7608 vs 0.7396-0.7735), which is the more honest estimate for a new user. See section 6 for the `weight_kg` caveat.

### 3.2 E2 - next-day goal, chronological test

| Model | Accuracy | Precision (goal) | Recall (goal) | F1 (goal) | ROC-AUC |
|---|---|---|---|---|---|
| Random Forest | 0.5823 | 0.4954 | 0.8179 | 0.6170 | 0.6706 |
| Logistic Regression | 0.6835 | 0.6649 | 0.4654 | 0.5475 | 0.7004 |
| Gradient-Boosted Trees | 0.5991 | 0.5080 | 0.8039 | 0.6226 | 0.6970 |
| Baseline: always the test-majority class ('missed') | 0.5886 | - | - | - | - |
| Baseline: always the TRAINING-majority class ('goal met') | 0.4114 | - | - | - | - |

Source: `faculty_evidence/supervised/final_metric_table_classification.csv`; the training-majority baseline row is from `exports/E2_results.csv`.

**Why the chronological test is the headline, and the same models on a random split (REFERENCE, not a result)**

| Model | Accuracy, random split | ROC-AUC, random split | ROC-AUC, chronological test |
|---|---|---|---|
| Random Forest | 0.7732 | 0.8191 | 0.6706 |
| Logistic Regression | 0.7770 | 0.8295 | 0.7004 |
| Gradient-Boosted Trees | 0.7780 | 0.8301 | 0.6970 |

Source: `exports/E2_results.csv` (status REFERENCE) and `faculty_evidence/supervised/final_metric_table_classification.csv`.

[VERIFIED] The goal rate differs strongly between the chronological blocks: 0.7378 in train, 0.2246 in validation, 0.4114 in test (`faculty_evidence/supervised/E2_split_summary.csv`).
[INTERPRETATION] Random Forest accuracy (0.5823) is below the test-majority baseline (0.5886); Gradient-Boosted Trees (0.5991) is only marginally above it; Logistic Regression (0.6835) is the only one clearly above. ROC-AUC (0.6706-0.7004) is the fairer summary. A random split would have shown ROC-AUC 0.8191-0.8301 and been misleading.

### 3.3 E3 - user-level `high_achiever` (replaces the earlier user-segmentation experiment)

| Model | Accuracy (out-of-fold) | F1 (weighted) | ROC-AUC (out-of-fold) | ROC-AUC mean +/- sd over folds |
|---|---|---|---|---|
| Random Forest | 0.5355 | 0.5318 | 0.5425 | 0.5446 +/- 0.0377 |
| Logistic Regression | 0.5378 | 0.5361 | 0.5486 | 0.5725 +/- 0.0332 |
| Baseline: always the majority class | 0.5011 | - | - | - |

Sources: `faculty_evidence/supervised/final_metric_table_classification.csv`; fold mean and sd from `exports/E3_results.csv`.

[INTERPRETATION] Both models are barely above chance and within the fold-to-fold spread; with only 437 users the standard error of an accuracy is about 2.4 percentage points (derived: sqrt(p(1-p)/n)). Read E3 as **no reliable skill**.
[VERIFIED] A one-feature model that only knows when the user's data were logged (`mean_logged_month`) scores out-of-fold ROC-AUC 0.6077 (Random Forest) and 0.6195 (Logistic Regression), higher than the nine-feature models above (`exports/E3_results.csv`). [INTERPRETATION] The E3 label is therefore partly tied to the calendar window in which a user happens to have data, not only to the profile features.

### 3.4 E4 - activity level, user-held-out (replaces the earlier user-day segmentation experiment)

| Model | Accuracy | F1 (macro) | ROC-AUC |
|---|---|---|---|
| Random Forest | 0.5056 | 0.4406 | 0.4965 |
| Logistic Regression | 0.5040 | 0.4442 | 0.4999 |
| Gradient-Boosted Trees | 0.5036 | 0.5002 | 0.4999 |
| Baseline: always the majority class | 0.5079 | - | - |

Source: `faculty_evidence/supervised/final_metric_table_classification.csv`.

[INTERPRETATION] ROC-AUC is 0.4965-0.4999 and every accuracy (0.5036-0.5056) is below the majority baseline (0.5079): **no skill** once the columns that encode the label are excluded (section 4.1 shows what happens when they are not).

### 3.5 E5 - same-day calories (regression)

**Test set (random hash split)** (source: `faculty_evidence/supervised/final_metric_table_regression.csv`)

| Model | MAE (kcal) | RMSE (kcal) | R2 |
|---|---|---|---|
| Linear Regression | 199.71 | 263.64 | 0.6296 |
| Random Forest Regressor | 188.61 | 258.68 | 0.6434 |
| GBT Regressor | 183.28 | 250.41 | 0.6658 |
| Baseline: Linear Regression on active_minutes only | 247.40 | 337.99 | 0.3912 |
| Baseline: training mean | 334.51 | 433.17 | -0.0000 |

**Chronological test (`chronological test (>= 2024-10-15)`)** (source: `exports/E5_results.csv`)

| Model | MAE (kcal) | RMSE (kcal) | R2 |
|---|---|---|---|
| Linear Regression | 247.20 | 329.29 | 0.5804 |
| Random Forest Regressor | 238.85 | 325.15 | 0.5909 |
| GBT Regressor | 235.86 | 317.99 | 0.6087 |
| Baseline: training mean | 395.21 | 548.22 | -0.1630 |

[INTERPRETATION] All three models are far better than predicting the training mean (MAE 334.51 kcal) and better than a one-feature model on `active_minutes` (MAE 247.40 kcal, R2 0.3912). The tree models beat Linear Regression because they can approximate a product of columns; this is formula recovery inside a dataset where calories are derived, not evidence that calories can be measured from steps (section 6). Reproduction check: the E5 Linear Regression equals the earlier stand-alone calorie regression (largest difference 0.0, `faculty_evidence/supervised/E5_reproduction_check.csv`).

## 4. Verification

### 4.1 Leakage tests - every leakage run is INVALID and excluded

Each experiment was also run once with a forbidden or label-encoding column added. Those rows carry status `INVALID`, are never quoted as results, and are excluded from the tables in section 3. The score jumps show what the forbidden column would have faked.

| Exp | Leaky run (INVALID) | Metric | Leaky score | Same model without the leak | Inflation |
|---|---|---|---|---|---|
| E1 | Random Forest + steps & distance_km | ROC-AUC | 0.9996 | 0.7585 | 0.2411 |
| E1 | Logistic Regression + steps & distance_km | ROC-AUC | 1.0000 | 0.7396 | 0.2604 |
| E1 | Gradient-Boosted Trees + steps & distance_km | ROC-AUC | 0.9996 | 0.7735 | 0.2261 |
| E2 | Random Forest + rolling mean INCLUDING the prediction day | ROC-AUC | 0.7518 | 0.6706 | 0.0811 |
| E2 | Gradient-Boosted Trees + rolling mean INCLUDING the prediction day | ROC-AUC | 0.8257 | 0.6970 | 0.1287 |
| E2 | Logistic Regression + rolling mean INCLUDING the prediction day | ROC-AUC | 0.8787 | 0.7004 | 0.1783 |
| E3 | Random Forest + average steps | ROC-AUC | 0.7978 | 0.5425 | 0.2553 |
| E3 | Logistic Regression + average steps | ROC-AUC | 0.8242 | 0.5486 | 0.2756 |
| E4 | Random Forest + calories_burned | ROC-AUC | 0.8905 | 0.4965 | 0.3941 |
| E4 | Gradient-Boosted Trees + calories_burned | ROC-AUC | 0.9673 | 0.4999 | 0.4674 |
| E4 | Logistic Regression + calories_burned | ROC-AUC | 0.9512 | 0.4999 | 0.4512 |
| E4 | Random Forest + sedentary_minutes | ROC-AUC | 0.9027 | 0.4965 | 0.4062 |
| E4 | Gradient-Boosted Trees + sedentary_minutes | ROC-AUC | 0.9976 | 0.4999 | 0.4978 |
| E4 | Logistic Regression + sedentary_minutes | ROC-AUC | 0.9966 | 0.4999 | 0.4967 |
| E5 | Linear Regression + calories_roll7_avg incl. the day itself | R2 | 0.7032 | 0.6296 | 0.0736 |
| E5 | Random Forest Regressor + calories_roll7_avg incl. the day itself | R2 | 0.7237 | 0.6434 | 0.0804 |
| E5 | GBT Regressor + calories_roll7_avg incl. the day itself | R2 | 0.7450 | 0.6658 | 0.0791 |

Sources: `exports/E1_results.csv`, `exports/E2_results.csv`, `exports/E3_results.csv`, `exports/E4_results.csv`, `exports/E5_results.csv` (rows with status `INVALID`, and the matching `VALID` row of the base model).

### 4.2 Independent scikit-learn cross-check (HDFS rerun)

`scripts/sup_sklearn_crosscheck.py` uses no Spark. (a) It recomputes every metric with scikit-learn from the predictions Spark saved and compares with the Spark numbers; (b) it refits models independently (exact agreement is expected for the convex models, only approximate agreement for tree models, with stated tolerances); (c) it checks labels, feature rows and split/leakage rules. It is run here on the HDFS-rerun outputs.

| Experiment | Checks | Passed |
|---|---|---|
| E1 | 27 | 27 |
| E2 | 25 | 25 |
| E3 | 14 | 14 |
| E4 | 24 | 24 |
| E5 | 13 | 13 |
| **Total** | 103 | 103 |

Source: `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv`.

| Kind of check | Checks | Passed | Tolerance range | Largest difference seen |
|---|---|---|---|---|
| features | 3 | 3 | 0e+00 to 2e-05 | 5.00e-07 |
| label | 2 | 2 | 0e+00 to 1e-09 | 0.00e+00 |
| leakage | 1 | 1 | 3e-02 to 3e-02 | 8.16e-05 |
| leakage rule | 1 | 1 | 0e+00 to 0e+00 | 0.00e+00 |
| no-future-info | 1 | 1 | 1e-09 to 1e-09 | 0.00e+00 |
| recompute | 78 | 78 | 0e+00 to 2e-03 | 8.16e-06 |
| refit | 8 | 8 | 2e-03 to 5e-01 | 7.34e-04 |
| refit (approx.) | 7 | 7 | 3e-02 to 5e-02 | 2.35e-02 |
| split | 1 | 1 | 0e+00 to 0e+00 | 0.00e+00 |
| status | 1 | 1 | 0e+00 to 0e+00 | 0.00e+00 |

[VERIFIED] The largest difference in the whole suite is 0.0235 (E2: Random Forest: independent sklearn refit (approximate), chronological test ROC-AUC), against a tolerance of 0.05. [LIMITATION] The refit checks have deliberately wide tolerances; they show two implementations agree approximately, not exactly. The metric recomputations are tight (tolerance 1e-9, or 2e-3 for ROC-AUC).

### 4.3 The defective E2 no-future-information check (two separate facts)

The check changes the user's rows from a cut day onward, rebuilds the E2 window features with the independent pandas implementation, and asks whether the features of days up to the cut day moved. The first version of the check reported `abs_diff` 27102.0 (tolerance 1e-09) and **failed**; the corrected version reports 0.0 and passes. The tolerance is the same in both files. The failing copy is kept for audit as `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck_original_with_defect.csv`.

**Fact (a) - the 103-check suite tests only a sample.** The E2 no-future check inside the 103-check suite covers 25 sampled users (the check name says so). Of those 25 users, 5 were flagged by the old window.

**Fact (b) - the separate all-users check covers every user.** `scripts/e2_nofuture_allusers_check.py` repeats the test for all 437 users (one row per user in `faculty_evidence/supervised/E2_nofuture_allusers_check.csv`). With the corrected window **437 of 437 users pass**, maximum change 0.0 (tolerance 1e-9). The old window would have flagged **131 users**, and those are exactly the 131 users whose cut day is not a kept row (no flagged user among the other 306; the largest change the old window produced was 29274.0).

**Cause [VERIFIED from the header of `scripts/e2_nofuture_allusers_check.py` and the columns of the CSV].** The old window was the corrected window plus the first kept day on or after the cut day. When the cut day itself is not a kept row (a logging gap), that extra day lies after the cut and legitimately uses the altered days, so the check flagged a change that is correct behaviour. The defect was in the check, not in the E2 features.

**Cross-link [VERIFIED].** In the all-users CSV, the largest old-window change among the 25 sampled users is 27102.0 (user 2094, cut day 2024-06-05, cut day not a kept row), which is exactly the failing value in the defective copy (27102.0). The corrected-window maximum in the same sample is 0.0.

**What this does and does not establish [INTERPRETATION].** The all-users check perturbs the independent pandas feature builder, not the Spark pipeline. The Spark features are tied to it by two checks in the suite: both builders produce the same (user, day) rows (the check `feature rows: same (user, day) set in pandas and Spark` passes in `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv`) and the maximum difference is 5.0e-07 over the numeric E2 features (tolerance 2e-05). The no-future property of the Spark features is therefore shown indirectly.

The cross-check script was edited between the defective output and the corrected output (defective CSV written 21:33:53, script saved 23:11:02, corrected CSV written 23:11:41, all on 18 Oct; file modification times). `scripts/` is untracked in git, so there is no diff of that edit either; the account above rests on the header of the all-users script and on the two CSVs.

### 4.4 Local run vs HDFS rerun

The same experiment scripts were run once reading Silver from the local Parquet and once reading it from HDFS (single-node, replication 1); `scripts/compare_local_vs_hdfs.py` compared every metric and every feature importance.

| Exp | Metric rows | Importance rows | Max abs diff (metrics) | Metric rows differing > 1e-6 | Max abs diff (importances) | Flagged rows |
|---|---|---|---|---|---|---|
| E1 | 69 | 36 | 6.76e-05 | 10 | 0e+00 | 0 |
| E2 | 75 | 40 | 7.94e-06 | 1 | 0e+00 | 0 |
| E3 | 66 | 9 | 0.00e+00 | 0 | 0e+00 | 0 |
| E4 | 78 | 32 | 0.00e+00 | 0 | 0e+00 | 0 |
| E5 | 60 | 20 | 5.68e-14 | 0 | 0e+00 | 0 |
| **Total** | 348 | 137 | 6.7596e-05 | 11 | 0e+00 | 0 |

Source: `faculty_evidence/supervised/local_vs_hdfs_comparison.csv` (485 rows; the flags file `faculty_evidence/supervised/local_vs_hdfs_flags.csv` has 0 data rows). Flag threshold: absolute difference above 0.001 (`local_vs_hdfs_summary.md`).

[VERIFIED] The overall maximum, 6.7596e-05, occurs on an **INVALID leakage run** (E1: Logistic Regression + steps & distance_km (LEAKAGE), F1 (weighted), test). Among VALID and BASELINE rows only, the largest difference is 9.36e-06. 325 of the 348 metric rows are exactly equal. Seeds, model settings and split sizes are identical in both runs (`local_vs_hdfs_run_info.csv`).
[LIMITATION] Both runs use the same Spark code, so this comparison tests the storage path and run-to-run reproducibility, not the correctness of the algorithm; the independent check of the algorithm is the scikit-learn cross-check (4.2).

## 5. Disclosures that need exact wording

### 5.1 The full cross-check could not be run on the local outputs; what changed in the E1 script is UNCONFIRMED

**Established [VERIFIED]:**

- The local cross-check file `faculty_evidence/supervised/sklearn_crosscheck.csv` holds 15 rows, all E1, all passing. 12 of them name the test split, 0 name the validation split, and 3 are `majority baseline recomputed` checks that name no split. A byte-identical copy (15 rows) is kept as `faculty_evidence/supervised/sklearn_crosscheck_E1_only_before_full_check.csv`. No local cross-check exists for E2-E5.
- The HDFS-rerun cross-check has 27 E1 checks, of which 12 are validation-split checks.
- The local folder `faculty_evidence/supervised/predictions/` holds the E1 test-prediction files and `E1_splits.csv` but **no** `E1_<model>_validation.csv`; the HDFS-rerun folder holds all three validation files (directory listing).
- The current cross-check script reads both `E1_<model>_validation.csv` and `E1_<model>_test.csv` (`scripts/sup_sklearn_crosscheck.py`, lines 69-70), and the current E1 script writes both (`models/sup_e1_goal_same_day.py`, lines 89-93).
- File modification times (all 18 Oct): last local E1 output `E1_run.log` 16:19:47; local E1-only cross-check CSV 16:23:17; `models/sup_e1_goal_same_day.py` **16:23:33**, i.e. 3 min 46 s after the last local E1 output.
- By reading the code, `read_pred` opens prediction files with `pd.read_csv` and no existence check (lines 51-55) and the script writes `sklearn_crosscheck.csv` only at the end (line 339), so a run against the local outputs would stop at the first missing E1 validation file before writing any CSV **[INTERPRETATION]; I did not execute it, because it would overwrite the local CSV**.

**UNCONFIRMED: what changed in `models/sup_e1_goal_same_day.py` at the time above.** The file is untracked in git, so no commit contains it; there is no backup copy and no compiled `.pyc` of it, so **no diff can be produced**. It is true by file times that the local E1 outputs predate the current E1 script. It is the natural reading, but **not confirmed**, that the script edit added the saving of validation predictions. The local E1 numbers in section 3 were produced by the file as it stood before that last save (which may or may not differ in content); the HDFS rerun, and therefore the cross-check, used the current file. What ties the two together is the comparison table: for E1, 60 VALID and BASELINE metric rows agree within 9.36e-06 (section 4.4). [INTERPRETATION] That is evidence the edit did not change the reported E1 results; it is not a diff and does not say what the edit was.

### 5.2 The cross-check evidence is from the HDFS rerun and is linked to the local results by the comparison table

The 103 passing checks verify the HDFS-rerun outputs (`faculty_evidence/supervised/hdfs_rerun/`). The local results in `exports/` (the numbers in section 3 and in the notebook) were not cross-checked directly. They are connected to the verified numbers by the comparison table in section 4.4: 485 rows, 0 flagged, maximum difference 6.7596e-05. This is **indirect** evidence for the local numbers. The notebook (section 7.3) says the same: it reads `hdfs_rerun/sklearn_crosscheck.csv` and states that local results match the HDFS rerun within 6.76e-05.

### 5.3 E5 regeneration: what is known and what is UNKNOWN

**Known [VERIFIED from file modification times and the CSVs named]:**

- An earlier attempt is preserved as `faculty_evidence/supervised/E5_run_attempt1_rf_depth12_OOM.log` (modified 17:16:43 on 18 Oct). It contains repeated `java.lang.OutOfMemoryError: Java heap space` and ends in a `TypeError` at `models/sup_e5_calories.py` line 68 (the GBT tuning call). The `depth12` in the file name is the operator's label; I did not trace which grid point caused it.
- `models/sup_e5_calories.py` and `models/sup_common.py` were saved 17:16:45 and 17:16:44, right after that log.
- Local tuning grid `E5_tuning_grid.csv` written 17:22:29; reproduction check 17:22:34. The final grid tries Random Forest depths 5, 8, 10 and no depth 12.
- All other local E5 outputs (`E5_comparison_table.csv`, `exports/E5_results.csv`, predictions, `E5_run_info.json`, `E5_run.log`) were written at **19:27:07-19:27:09**, which is 2 h 4 min 38 s after the tuning grid.
- HDFS rerun for comparison: tuning grid written 21:20:59, final outputs 21:33:21, which is 12 min 22 s later. The grid CSVs record 325.6 s of tuning (local) and 593.6 s (HDFS) before the grid was written, so the whole HDFS run was longer than 12 minutes; the start time of either run is not recorded.
- The regenerated local E5 numbers are reproduced by the HDFS rerun: maximum difference over 60 E5 metric rows is 5.68e-14 (`faculty_evidence/supervised/local_vs_hdfs_comparison.csv`). This shows the numbers are stable; it does **not** explain the regeneration.

**UNKNOWN:**

- **Why the local E5 outputs were regenerated at 19:27:07.** No log, note or file in the project records the reason.
- **Why there is a gap of 2 h 4 min 38 s between the local tuning grid and the final local outputs**, when the same stage took 12 min 22 s in the HDFS rerun.
- **Whether earlier local E5 outputs existed and differed.** I found no copy of any E5 result written before the regeneration.

## 6. Limitations

1. **[LIMITATION] Derived data.** `calories_burned`, `distance_km`, `active_minutes`, `sedentary_minutes`, `max_heart_rate` and `sleep_quality_score` are partly derived in this public (Kaggle) demonstration dataset (notebook section 10, limitations; header of `models/sup_e4_activity_level.py`). Scores that depend on them can be formula recovery rather than learning. Evidence in the results files:
   - E4: adding `calories_burned` or `sedentary_minutes` lifts ROC-AUC to 0.8905-0.9976 from about 0.4999 (table 4.1).
   - E5: adding `activity_type` and `intensity` (which fix the MET value) gives R2 0.8720 / 0.9721 / 0.9948 (Linear / Random Forest / GBT), against 0.6296-0.6658 without them. This is shown only as a reference.
2. **[LIMITATION] E2 chronological weakness.** The goal rate drifts across the blocks (train 0.7378, validation 0.2246, test 0.4114), Random Forest accuracy (0.5823) is below the test-majority baseline (0.5886), and ROC-AUC is only 0.6706-0.7004. Read E2 as a weak signal.
3. **[LIMITATION] E3 and E4 show no reliable skill** (E3 ROC-AUC 0.5425-0.5486, E4 ROC-AUC 0.4965-0.4999); E3 has only 437 users, and its label is partly tied to the logging window (section 3.3).
4. **[LIMITATION] E1 may partly be a calendar clock.** The notebook states that in this synthetic data `weight_kg` drifts almost linearly with the calendar inside each user and that E1 and E5 keep `weight_kg` as specified, so E1's top feature may act as a clock; **no ablation was run**. This statement is taken from the notebook's limitations cell (section 10), not from a CSV, and no number for it is given here.
5. **[LIMITATION] Refit tolerances are wide** (up to 0.5 for exact-type refits and 0.05 for tree refits, `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv`); the local-vs-HDFS comparison shares the Spark code (section 4.4).
6. **[LIMITATION] One seed.** Every run uses seed 42; only E3 reports a spread (over folds). There is no across-seed variance for E1, E2, E4 or E5.
7. **[LIMITATION] Local Spark and single-node HDFS.** Spark runs in local mode; HDFS is one node with replication 1 (notebook sections 10 and 11).
8. **[VERIFIED] Power BI pages 4 and 5 now show only the supervised results; the saved `.pbix` still has to be re-saved.** After the cleanup of 25 Oct 2026, Power BI page 4 (`Supervised Results E3 and E4`) and page 5 (`Model Evaluation`) read `exports/E<n>_results.csv` (copied row for row into `powerbi/data/supervised_results.csv`; `powerbi/validate_exports.py` checks the copy against the exports) plus the cross-check counts from `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv`. The generated project `powerbi/project/` passes `powerbi/validate_powerbi_project.py` (including Microsoft's PBIR and TMDL validators), but the saved `.pbix` file is still the previous version until it is re-opened, refreshed and re-saved in Power BI Desktop, and what Desktop renders from the regenerated file has not been checked. The web page (`webapp/`) no longer shows a user grouping; it reads one static JSON file and has no server code. The legacy Streamlit app no longer has a segment or an anomaly section; it loads saved scikit-learn `joblib` models and queries SQLite (`dashboard/app.py`).
9. **[LIMITATION] This report re-ran nothing.** It reads the existing evidence; the local cross-check (5.1) and the E1/E5 questions above remain open because no history exists to answer them.

## 7. Ten viva questions with answers

**Q1. Why are there no segmentation experiments now, and do the dashboards show the new models?**

The faculty asked for supervised learning only, so the two earlier user-segmentation experiments were replaced by supervised classifiers (E3 on users, E4 on user-days); the old code and outputs are kept in `archive/`. Power BI pages 4 and 5 now show only the supervised results (page 4: E3 and E4, page 5: E1-E5) and the web page no longer shows a user grouping; the saved `.pbix` still has to be re-saved from the regenerated project in Power BI Desktop. The legacy Streamlit app has no segment or anomaly section any more (section 6, item 8).

**Q2. What is the label and the split of each experiment, and why those splits?**

E1 same-day goal (steps >= 8,000), random seeded split plus a user-held-out run; E2 next-day goal from history only, chronological split (train to 2024-09-08, test after 2024-11-02); E3 user-level `high_achiever`, 5-fold CV on 437 users; E4 high/low activity, whole users held out (53 test users); E5 calories regression, random split plus a chronological test. Random splits would let neighbouring days of one user sit on both sides, so E2 is chronological and E1/E4 add or use a user-held-out evaluation; E3 uses cross-validation because there are few users (section 2).

**Q3. E1 reaches about 74% accuracy - is that good?**

It is clearly above the majority baseline: accuracy 0.7352-0.7382 against 0.6144, ROC-AUC 0.7396-0.7735. On users never seen in training the ROC-AUC is slightly lower (0.7340-0.7608). A caveat I must state: `weight_kg` may act as a calendar clock in this synthetic data and no ablation was run (section 6, item 4).

**Q4. Why is E2 weak, and why do you headline the chronological test?**

Predicting tomorrow from history is a real forecast, so the test must come after the training data. On that test the ROC-AUC is 0.6706-0.7004 and Random Forest accuracy (0.5823) is below the always-'missed' baseline (0.5886) because the goal rate drifts from 0.7378 in train to 0.4114 in test. A random split would show ROC-AUC 0.8191-0.8301 and look much better, which would be misleading.

**Q5. E3 and E4 are near chance. What do you conclude?**

That the profile averages (E3) and the physiological columns (E4) carry no reliable signal for these labels: E3 ROC-AUC 0.5425-0.5486 with fold spread about 0.0332, E4 ROC-AUC 0.4965-0.4999 and accuracy below the baseline 0.5079. I report them as negative results rather than tuning until they look good. For E3 a model that only knows the logging window scores higher (0.6077), so the label is partly a calendar effect.

**Q6. How do you know there is no leakage?**

Three ways. Forbidden columns were excluded by rule. Each experiment was also run with a forbidden column added, and those runs score far higher (for example E1 ROC-AUC 1.0000 with steps and distance versus 0.7396 without), are marked INVALID and are never cited (table 4.1). And the E2 features are checked to ignore the future: all users pass the corrected no-future check (section 4.3).

**Q7. E5 gets R2 about 0.63-0.67. Can calories be predicted from activity?**

Only partly, and the honest reading is formula recovery: calories are partly derived from other columns in this dataset. The trees beat Linear Regression (R2 0.6296-0.6658), and with `activity_type` and `intensity` added, R2 reaches 0.9948, which recovers the formula rather than showing skill. Separately, the local E5 outputs were regenerated at 19:27:07 for a reason I cannot document (section 5.3); the numbers are reproduced by the HDFS rerun within 5.68e-14.

**Q8. What does the 103/103 cross-check prove and what does it not?**

It proves that, on the HDFS-rerun outputs, the metrics Spark reported can be recomputed independently with scikit-learn (tolerance 1e-9, or 2e-3 for ROC-AUC) and that independently refitted models agree within stated tolerances (103 checks, 103 pass). It does not prove the data are real, that no bug exists anywhere, or that the local run was checked directly. The refit tolerances are wide for tree models (up to 0.05); the largest difference seen was 0.0235.

**Q9. What was wrong with the E2 check?**

The first version failed with a difference of 27102.0. The cause was the check's window, not the model: it included the first kept day after the cut day, and when the cut day itself was not a kept row that day legitimately uses altered data. Two separate facts: the 103-check suite tests 25 sampled users and now passes; the separate all-users check covers 437 users, 437 pass with maximum change 0.0, and the old window would have flagged 131 users whose cut day is not a kept row. The failing copy is kept for audit.

**Q10. Why does the cross-check come from the HDFS rerun, and how does it relate to your local numbers?**

The local cross-check only exists for E1 (15 checks, none on the validation split): the local E1 outputs have no validation prediction files, which the current cross-check script reads. The E1 script was last saved at 16:23:33, 3 min 46 s after the last local E1 output, but **what changed in it is unconfirmed**: the file is untracked in git and has no backup, so no diff exists. The full cross-check was therefore run on the HDFS rerun, and the local numbers are tied to it by the comparison table: 485 rows, 0 flagged, maximum difference 6.7596e-05 (on an INVALID leakage run; 9.36e-06 on valid rows). That is indirect evidence for the local numbers, and I say so.

## 8. Where the evidence is

| Item | Location |
|---|---|
| Final metric tables | `faculty_evidence/supervised/final_metric_table_classification.csv`, `faculty_evidence/supervised/final_metric_table_regression.csv` |
| Per-experiment results (all splits, all statuses) | `exports/E1_results.csv` ... `exports/E5_results.csv`; feature importances in `exports/E<n>_feature_importance.csv` |
| Local run evidence (tuning grids, predictions, logs, run info) | `faculty_evidence/supervised/` |
| HDFS rerun (same scripts, Silver read from HDFS) | `faculty_evidence/supervised/hdfs_rerun/` |
| Cross-check (HDFS rerun; corrected / defective copy) | `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv` / `faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck_original_with_defect.csv` |
| Cross-check (local; E1 only, and its backup) | `faculty_evidence/supervised/sklearn_crosscheck.csv` / `faculty_evidence/supervised/sklearn_crosscheck_E1_only_before_full_check.csv` |
| E2 all-users no-future check | `faculty_evidence/supervised/E2_nofuture_allusers_check.csv` (made by `scripts/e2_nofuture_allusers_check.py`) |
| Local vs HDFS comparison | `faculty_evidence/supervised/local_vs_hdfs_comparison.csv`, `local_vs_hdfs_summary.md`, `faculty_evidence/supervised/local_vs_hdfs_flags.csv` |
| Notebook before the supervised conversion (73 cells were removed, with their saved outputs, by the build script) | `archive/FitPulse_Faculty_Demo_pre_supervised.ipynb` (SHA-256 begins E2D47F60, ends C509A); `archive/notebook_removed_cells.json` |
| Scripts | `models/sup_e1_*.py` ... `sup_e5_*.py`, `run_supervised.ps1`, `scripts/sup_sklearn_crosscheck.py`, `scripts/compare_local_vs_hdfs.py` |

Git state: the supervised scripts, `scripts/`, `archive/` and `faculty_evidence/supervised/` are untracked; nothing was committed for this report.
