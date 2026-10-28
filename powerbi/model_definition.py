"""
FitPulse Power BI - single source of truth for the semantic model (tables, relationships, measures) and the
five report pages.  build_powerbi.py turns this into a Power BI Project (PBIP: TMDL model + PBIR report);
validate_powerbi_project.py checks the GENERATED files against the CSV schemas.

Measure semantics (granularity) are documented next to each measure.  Hosts are the tables a measure lives in.
"""

NAME = "FitPulse_PowerBI_Dashboard"

# ---------------------------------------------------------------------------------------------------------------
# Tables: CSV file -> table name.  Column types come from the CSV at build time; only overrides are listed here.
# ---------------------------------------------------------------------------------------------------------------
TABLES = {
    "fact_daily": {
        "csv": "fact_daily.csv",
        "date_columns": ["date"],
        "hidden": ["row_id", "user_id", "month", "daily_step_goal", "daily_calorie_goal"],
        "formats": {"date": "yyyy-mm-dd", "calories_burned": "#,0.0", "predicted_calories": "#,0.0", "calorie_error": "#,0.0",
                    "distance_km": "0.00", "sleep_hours": "0.00", "steps": "#,0"},
        "description": "One row per USER-DAY (100,122 rows). Source: Silver dataset + Linear Regression predictions.",
    },
    "dim_user": {
        "csv": "dim_user.csv",
        "description": "One row per USER (437): age group, gender, days logged, average steps and calories.",
    },
    "dim_date": {
        "csv": "dim_date.csv", "date_columns": ["Date"], "key_date": "Date",
        "sort_by": {"Month": "MonthNumber", "DayOfWeek": "DayOfWeekNumber"},
        "hidden": ["MonthNumber", "DayOfWeekNumber", "Year"],
        "description": "Calendar 2024-01-01..2024-12-31, marked as the date table.",
    },
    "experiments": {"csv": "experiments.csv", "description": "One row per supervised experiment (E1-E5)."},
    "supervised_results": {"csv": "supervised_results.csv", "hidden": ["source_file"],
                           "description": "Every row of exports/E1_results.csv ... E5_results.csv: model, metric, value, evaluation split and status (VALID / BASELINE / REFERENCE / INVALID = leakage run)."},
    "crosscheck": {"csv": "crosscheck.csv", "hidden": ["source_file"],
                   "description": "The independent scikit-learn cross-check of the HDFS rerun: one row per check (passed = 1 or 0)."},
}

# many side -> one side
RELATIONSHIPS = [
    ("fact_daily", "date", "dim_date", "Date"),
    ("fact_daily", "user_id", "dim_user", "user_id"),
    ("supervised_results", "experiment_id", "experiments", "experiment_id"),
    ("crosscheck", "experiment_id", "experiments", "experiment_id"),
]

INT, DEC, PCT, DEC4 = "#,0", "#,0.0", "0.0%", "0.0000"
SR_LR = ('supervised_results[experiment_id] = "E5", supervised_results[model] = "Linear Regression", '
         'supervised_results[split_type] = "test", supervised_results[status] = "VALID"')
SR_BASE = ('supervised_results[experiment_id] = "E5", supervised_results[model] = "Baseline: training mean", '
           'supervised_results[split_type] = "test", supervised_results[status] = "BASELINE"')
# (host table, name, DAX, format, display folder)
MEASURES = [
    # ---- Page 1: Fitness Overview  (fact_daily = user-days; DISTINCTCOUNT for users) ----
    ("fact_daily", "Total Users", "DISTINCTCOUNT ( fact_daily[user_id] )", INT, "1 Overview"),
    ("fact_daily", "User-Days", "COUNTROWS ( fact_daily )", INT, "1 Overview"),
    ("fact_daily", "Total Steps", "SUM ( fact_daily[steps] )", INT, "1 Overview"),
    ("fact_daily", "Avg Daily Steps", "AVERAGE ( fact_daily[steps] )", INT, "1 Overview"),
    ("fact_daily", "Avg Calories Burned", "AVERAGE ( fact_daily[calories_burned] )", DEC, "1 Overview"),
    ("fact_daily", "Avg Active Minutes", "AVERAGE ( fact_daily[active_minutes] )", DEC, "1 Overview"),
    ("fact_daily", "Step-Goal Achievement %", "DIVIDE ( SUM ( fact_daily[goal_achieved] ), COUNTROWS ( fact_daily ) )", PCT, "1 Overview"),
    ("fact_daily", "Calorie-Goal Achievement %", "DIVIDE ( SUM ( fact_daily[calorie_goal_achieved] ), COUNTROWS ( fact_daily ) )", PCT, "1 Overview"),
    ("fact_daily", "Avg Steps Prev Month", "CALCULATE ( [Avg Daily Steps], DATEADD ( dim_date[Date], -1, MONTH ) )", INT, "1 Overview"),
    ("fact_daily", "Steps MoM %", "DIVIDE ( [Avg Daily Steps] - [Avg Steps Prev Month], [Avg Steps Prev Month] )", PCT, "1 Overview"),
    # ---- Page 2: Activity and Sleep ----
    ("fact_daily", "Avg Distance (km)", "AVERAGE ( fact_daily[distance_km] )", "0.00", "2 Activity and Sleep"),
    ("fact_daily", "Avg Sedentary Minutes", "AVERAGE ( fact_daily[sedentary_minutes] )", DEC, "2 Activity and Sleep"),
    ("fact_daily", "Avg Sleep Hours", "AVERAGE ( fact_daily[sleep_hours] )", "0.00", "2 Activity and Sleep"),
    ("fact_daily", "Avg Sleep Quality", "AVERAGE ( fact_daily[sleep_quality_score] )", DEC, "2 Activity and Sleep"),
    ("fact_daily", "Avg Heart Rate", "AVERAGE ( fact_daily[avg_heart_rate] )", DEC, "2 Activity and Sleep"),
    ("fact_daily", "Active Share of Waking Time %", "DIVIDE ( SUM ( fact_daily[active_minutes] ), SUM ( fact_daily[active_minutes] ) + SUM ( fact_daily[sedentary_minutes] ) )", PCT, "2 Activity and Sleep"),
    # ---- Page 3: Calorie Prediction (experiment E5; TEST rows only for accuracy) ----
    ("fact_daily", "Avg Predicted Calories", "AVERAGE ( fact_daily[predicted_calories] )", DEC, "3 Calorie Prediction"),
    ("fact_daily", "Test Days", 'CALCULATE ( COUNTROWS ( fact_daily ), fact_daily[model_split] = "test" )', INT, "3 Calorie Prediction"),
    ("fact_daily", "Avg Prediction Error (bias, kcal)", 'CALCULATE ( AVERAGE ( fact_daily[calorie_error] ), fact_daily[model_split] = "test" )', DEC, "3 Calorie Prediction"),
    ("fact_daily", "Test MAE (recomputed, kcal)", 'CALCULATE ( AVERAGEX ( fact_daily, ABS ( fact_daily[calorie_error] ) ), fact_daily[model_split] = "test" )', DEC, "3 Calorie Prediction"),
    ("fact_daily", "Test RMSE (recomputed, kcal)", 'CALCULATE ( SQRT ( AVERAGEX ( fact_daily, fact_daily[calorie_error] ^ 2 ) ), fact_daily[model_split] = "test" )', DEC, "3 Calorie Prediction"),
    ("fact_daily", "Test R2 (recomputed)",
     'VAR T = CALCULATETABLE ( fact_daily, fact_daily[model_split] = "test" )\n'
     'VAR MeanActual = AVERAGEX ( T, fact_daily[calories_burned] )\n'
     'VAR SSE = SUMX ( T, fact_daily[calorie_error] ^ 2 )\n'
     'VAR SST = SUMX ( T, ( fact_daily[calories_burned] - MeanActual ) ^ 2 )\n'
     'RETURN 1 - DIVIDE ( SSE, SST )', DEC4, "3 Calorie Prediction"),
    ("supervised_results", "Verified Test MAE (kcal)", f'CALCULATE ( MAX ( supervised_results[value] ), {SR_LR}, supervised_results[metric] = "MAE (kcal)" )', DEC, "3 Calorie Prediction"),
    ("supervised_results", "Verified Test RMSE (kcal)", f'CALCULATE ( MAX ( supervised_results[value] ), {SR_LR}, supervised_results[metric] = "RMSE (kcal)" )', DEC, "3 Calorie Prediction"),
    ("supervised_results", "Verified Test R2", f'CALCULATE ( MAX ( supervised_results[value] ), {SR_LR}, supervised_results[metric] = "R2" )', DEC4, "3 Calorie Prediction"),
    ("supervised_results", "Baseline Test MAE (kcal)", f'CALCULATE ( MAX ( supervised_results[value] ), {SR_BASE}, supervised_results[metric] = "MAE (kcal)" )', DEC, "3 Calorie Prediction"),
    # ---- Pages 4 and 5: supervised results (every row names its experiment, evaluation split and status) ----
    ("supervised_results", "Result Value", "MAX ( supervised_results[value] )", "0.0000", "5 Model Evaluation"),
    ("crosscheck", "Cross-check Checks", "COUNTROWS ( crosscheck )", INT, "5 Model Evaluation"),
    ("crosscheck", "Cross-check Passed", "SUM ( crosscheck[passed] )", INT, "5 Model Evaluation"),
]
MEASURE_HOST = {m[1]: m[0] for m in MEASURES}

# ---------------------------------------------------------------------------------------------------------------
# Report pages.  Visual = dict(type, x, y, w, h, title, fields={role: [("c"|"m", table, name)]}, ...)
# ---------------------------------------------------------------------------------------------------------------
C = lambda t, n: ("c", t, n)
M = lambda n: ("m", MEASURE_HOST[n], n)

SR = "supervised_results"
E3_CV = "stratified 5-fold CV (out-of-fold)"
E4_HO = "test (user-held-out)"
ACC_VS_BASE = ["Accuracy", "Baseline accuracy (always majority class)"]
# the headline evaluation of each experiment (E1/E5 test, E2 chronological, E3 cross-validation, E4 user-held-out)
HEADLINE_SPLITS = ["test", "test (user-held-out)", "chronological test", "chronological test (>= 2024-10-15)", "stratified 5-fold CV (out-of-fold)"]
COMPARE_METRICS = ["Accuracy", "ROC AUC", "Baseline accuracy (always majority class)", "MAE (kcal)", "R2"]

def exp_filters(eid, split, metrics, status=("VALID",)):
    """Visual filters that pin a chart to ONE experiment, ONE evaluation split, the given metrics and status."""
    return [(SR, "experiment_id", [eid]), (SR, "split_type", [split]), (SR, "metric", list(metrics)), (SR, "status", list(status))]

W, H = 1280, 720


def card(x, y, w, h, measure, title, show_title=False):
    return dict(type="card", x=x, y=y, w=w, h=h, title=title, fields={"Values": [M(measure)]}, alt=f"KPI card: {title}", show_title=show_title)


def slicer(x, y, w, h, table, col, title, mode="Dropdown", single=False, default=None):
    return dict(type="slicer", x=x, y=y, w=w, h=max(h, 76), title=title, fields={"Values": [C(table, col)]}, mode=mode, single=single, default=default,
                alt=f"Slicer: {title}")


def text(x, y, w, h, body, size="10pt", bold=False, color=None):
    return dict(type="textbox", x=x, y=y, w=w, h=h, body=body, size=size, bold=bold, color=color)


def std_slicers(y=52):
    return [slicer(20, y, 250, 52, "dim_date", "Date", "Date range", mode="Between"),
            slicer(280, y, 200, 52, "fact_daily", "activity_type", "Activity type"),
            slicer(490, y, 190, 52, "dim_user", "age_group", "Age group"),
            slicer(690, y, 160, 52, "dim_user", "gender", "Gender")]


PAGES = [
    dict(name="Fitness Overview", description="Population KPIs, monthly trend, steps vs calories per user, step-goal achievement by weekday.",
         visuals=[
             text(20, 2, 1100, 48, "FitPulse - Fitness Overview", "20pt", True, "#20493A"),
             *std_slicers(),
             card(20, 132, 200, 88, "Total Users", "Total users"),
             card(228, 132, 200, 88, "User-Days", "User-days (records)"),
             card(436, 132, 200, 88, "Avg Daily Steps", "Average daily steps"),
             card(644, 132, 200, 88, "Avg Calories Burned", "Average calories burned (kcal)"),
             card(852, 132, 200, 88, "Avg Active Minutes", "Average active minutes"),
             card(1060, 132, 200, 88, "Step-Goal Achievement %", "Step-goal achievement"),
             dict(type="lineClusteredColumnComboChart", x=20, y=222, w=620, h=234, title="Monthly trend: average calories (columns) and steps (line)",
                  fields={"Category": [C("dim_date", "YearMonth")], "Y": [M("Avg Calories Burned")], "Y2": [M("Avg Daily Steps")]},
                  alt="Combo chart of monthly average calories and average daily steps"),
             dict(type="scatterChart", x=650, y=222, w=610, h=234, title="Steps vs calories - one point per user (437 users)",
                  fields={"Category": [C("dim_user", "user_id")], "X": [M("Avg Daily Steps")], "Y": [M("Avg Calories Burned")]},
                  alt="Scatter of each user's average steps against average calories"),
             dict(type="clusteredColumnChart", x=20, y=462, w=620, h=206, title="Step-goal achievement % by weekday",
                  fields={"Category": [C("dim_date", "DayOfWeek")], "Y": [M("Step-Goal Achievement %")]}, alt="Column chart of goal achievement by weekday"),
             dict(type="tableEx", x=650, y=462, w=610, h=206, title="Monthly summary",
                  fields={"Values": [C("dim_date", "YearMonth"), M("Avg Daily Steps"), M("Steps MoM %"), M("Step-Goal Achievement %"), M("User-Days")]},
                  alt="Table of monthly steps, month-over-month change, goal rate and user-days"),
             text(20, 672, 1240, 44, "Source: Silver dataset (local Parquet) exported to CSV; fact_daily = one row per user-day (100,122), 437 users. "
                  "Step goal = 1.10 x the user's own average daily steps (set by etl/spark_etl.py), not a fixed 8,000. Power BI imports CSV; it does not read HDFS.", "9pt"),
         ]),
    dict(name="Activity and Sleep", description="Distance, active/sedentary minutes, sleep duration and quality, intensity and activity type comparisons.",
         visuals=[
             text(20, 2, 1100, 48, "FitPulse - Activity and Sleep", "20pt", True, "#20493A"),
             *std_slicers(),
             card(20, 132, 200, 88, "Avg Distance (km)", "Average distance (km)"),
             card(228, 132, 200, 88, "Avg Active Minutes", "Average active minutes"),
             card(436, 132, 200, 88, "Avg Sedentary Minutes", "Average sedentary minutes"),
             card(644, 132, 200, 88, "Avg Sleep Hours", "Average sleep (hours)"),
             card(852, 132, 200, 88, "Avg Sleep Quality", "Average sleep quality (0-100)"),
             card(1060, 132, 200, 88, "Avg Heart Rate", "Average heart rate (bpm)"),
             dict(type="lineChart", x=20, y=222, w=620, h=234, title="Monthly sleep duration and quality",
                  fields={"Category": [C("dim_date", "YearMonth")], "Y": [M("Avg Sleep Hours")], "Y2": [M("Avg Sleep Quality")]}, alt="Line chart of monthly sleep hours and sleep quality"),
             dict(type="lineChart", x=650, y=222, w=610, h=234, title="Monthly active vs sedentary minutes",
                  fields={"Category": [C("dim_date", "YearMonth")], "Y": [M("Avg Active Minutes")], "Y2": [M("Avg Sedentary Minutes")]}, alt="Line chart of monthly active and sedentary minutes"),
             dict(type="clusteredColumnChart", x=20, y=462, w=410, h=206, title="Average steps by activity intensity",
                  fields={"Category": [C("fact_daily", "intensity")], "Y": [M("Avg Daily Steps")]}, alt="Average steps by intensity level"),
             dict(type="clusteredColumnChart", x=440, y=462, w=410, h=206, title="Average active minutes by activity type",
                  fields={"Category": [C("fact_daily", "activity_type")], "Y": [M("Avg Active Minutes")]}, alt="Average active minutes by activity type"),
             dict(type="scatterChart", x=860, y=462, w=400, h=206, title="Sedentary minutes vs sleep quality - per user",
                  fields={"Category": [C("dim_user", "user_id")], "X": [M("Avg Sedentary Minutes")], "Y": [M("Avg Sleep Quality")]}, alt="Scatter of sedentary minutes against sleep quality per user"),
             text(20, 672, 1240, 44, "Derived: sleep_hours = sleep_minutes / 60. Active + sedentary + sleep minutes = 1,440 per day in every record. "
                  "Intensity (Low/Medium/High) and activity type are the dataset's own categorical fields. Line-chart axes are auto-scaled, so small monthly differences look larger than they are.", "9pt"),
         ]),
    dict(name="Calorie Prediction", description="Linear Regression (experiment E5): actual vs predicted calories, error distribution, MAE / RMSE / R2 on test days.",
         visuals=[
             text(20, 2, 1240, 48, "FitPulse - Calorie Prediction (Linear Regression, target: same-day calories burned)", "18pt", True, "#20493A"),
             slicer(20, 52, 250, 76, "dim_date", "Date", "Date range", mode="Between"),
             slicer(280, 52, 220, 76, "fact_daily", "activity_type", "Activity type"),
             card(20, 132, 230, 88, "Verified Test MAE (kcal)", "MAE (kcal) - verified, test"),
             card(258, 132, 230, 88, "Verified Test RMSE (kcal)", "RMSE (kcal) - verified, test"),
             card(496, 132, 230, 88, "Verified Test R2", "R-squared - verified, test"),
             card(734, 132, 230, 88, "Baseline Test MAE (kcal)", "Baseline MAE (training mean)"),
             card(972, 132, 288, 88, "Test Days", "Test days (held out)"),
             dict(type="scatterChart", x=20, y=222, w=470, h=290, title="Actual vs predicted calories (test days)",
                  fields={"Category": [C("fact_daily", "row_id")], "X": [("a", "fact_daily", "calories_burned")], "Y": [("a", "fact_daily", "predicted_calories")]},
                  filters=[("fact_daily", "model_split", ["test"])], alt="Scatter of actual against predicted calories on test days"),
             dict(type="clusteredColumnChart", x=500, y=222, w=380, h=290, title="Prediction error distribution (50-kcal bins, test days)",
                  fields={"Category": [C("fact_daily", "error_bin_kcal")], "Y": [M("Test Days")]}, alt="Histogram of prediction errors"),
             dict(type="lineChart", x=890, y=222, w=370, h=290, title="Monthly average: actual vs predicted calories",
                  fields={"Category": [C("dim_date", "YearMonth")], "Y": [M("Avg Calories Burned"), M("Avg Predicted Calories")]}, alt="Line chart of monthly actual and predicted calories"),
             dict(type="tableEx", x=20, y=518, w=620, h=150, title="Test accuracy by activity type (recomputed from test rows)",
                  fields={"Values": [C("fact_daily", "activity_type"), M("Test MAE (recomputed, kcal)"), M("Test RMSE (recomputed, kcal)"), M("Test Days")]},
                  alt="Table of test MAE and RMSE by activity type"),
             dict(type="tableEx", x=650, y=518, w=610, h=150, title="Cross-check: recomputed from exported predictions vs verified evaluation",
                  fields={"Values": [M("Test MAE (recomputed, kcal)"), M("Verified Test MAE (kcal)"), M("Test RMSE (recomputed, kcal)"), M("Verified Test RMSE (kcal)"),
                                     M("Test R2 (recomputed)"), M("Verified Test R2"), M("Avg Prediction Error (bias, kcal)")]},
                  alt="Recomputed versus verified regression metrics"),
             text(20, 672, 1240, 44, "Experiment E5 - target: same-day calories_burned; granularity: user-day; seeded 70/15/15 split of (user_id, date); accuracy shown on TEST days only (14,985). "
                  "Features exclude calorie-derived columns (no target leakage). Training rows are in the data but excluded from every accuracy figure. Scatter shows a sample of points.", "9pt"),
         ]),
    dict(name="Supervised Results E3 and E4",
         description="Supervised results of E3 (user-level high_achiever) and E4 (activity level): ROC-AUC, accuracy against the majority baseline, fold spread and leakage runs, read from exports/E3_results.csv and exports/E4_results.csv.",
         visuals=[
             text(20, 2, 1240, 48, "FitPulse - Supervised Results E3 and E4 (source: exports/E3_results.csv and exports/E4_results.csv)", "18pt", True, "#20493A"),
             text(20, 50, 1240, 34, "E3: user-level classifier high_achiever, stratified 5-fold cross-validation, out-of-fold predictions. E4: user-day activity level, user-held-out test users. "
                  "Every chart shows ONE experiment: E3 and E4 are never combined.", "10pt", True, "#B5495B"),
             dict(type="clusteredColumnChart", x=20, y=90, w=400, h=200, title="E3 - ROC-AUC by model (5-fold CV, out-of-fold)",
                  fields={"Category": [C(SR, "model")], "Y": [M("Result Value")]}, filters=exp_filters("E3", E3_CV, ["ROC AUC"]), alt="E3 ROC-AUC by model"),
             dict(type="clusteredColumnChart", x=430, y=90, w=400, h=200, title="E3 - accuracy against the majority baseline",
                  fields={"Category": [C(SR, "model")], "Series": [C(SR, "metric")], "Y": [M("Result Value")]}, filters=exp_filters("E3", E3_CV, ACC_VS_BASE), alt="E3 accuracy and majority baseline by model"),
             dict(type="tableEx", x=840, y=90, w=420, h=200, title="E3 - ROC-AUC mean and sd over the 5 folds", no_total=True,
                  fields={"Values": [C(SR, "model"), C(SR, "metric"), M("Result Value")]},
                  filters=exp_filters("E3", E3_CV, ["ROC AUC (mean over folds)", "ROC AUC (sd over folds)"]), alt="E3 fold-to-fold spread of ROC-AUC"),
             dict(type="clusteredColumnChart", x=20, y=296, w=400, h=200, title="E4 - ROC-AUC by model (user-held-out test)",
                  fields={"Category": [C(SR, "model")], "Y": [M("Result Value")]}, filters=exp_filters("E4", E4_HO, ["ROC AUC"]), alt="E4 ROC-AUC by model"),
             dict(type="clusteredColumnChart", x=430, y=296, w=400, h=200, title="E4 - accuracy against the majority baseline",
                  fields={"Category": [C(SR, "model")], "Series": [C(SR, "metric")], "Y": [M("Result Value")]}, filters=exp_filters("E4", E4_HO, ACC_VS_BASE), alt="E4 accuracy and majority baseline by model"),
             dict(type="tableEx", x=840, y=296, w=420, h=200, title="E4 - accuracy, macro F1 and ROC-AUC (user-held-out test)", no_total=True,
                  fields={"Values": [C(SR, "model"), C(SR, "metric"), M("Result Value")]},
                  filters=exp_filters("E4", E4_HO, ["Accuracy", "F1 (macro)", "ROC AUC"]), alt="E4 accuracy, macro F1 and ROC-AUC by model"),
             dict(type="tableEx", x=20, y=502, w=1240, h=164, title="Leakage runs of E3 and E4 (status INVALID - never results)", no_total=True,
                  fields={"Values": [C(SR, "experiment_id"), C(SR, "model"), C(SR, "metric"), C(SR, "status"), M("Result Value")]},
                  filters=[(SR, "experiment_id", ["E3", "E4"]), (SR, "status", ["INVALID"]), (SR, "metric", ["ROC AUC"])],
                  alt="Leakage runs of E3 and E4 with status INVALID"),
             text(20, 672, 1240, 44, "Sources: exports/E3_results.csv and exports/E4_results.csv (rows with status VALID). INVALID rows are runs with a forbidden column added to show the leakage; "
                  "they are listed only to be rejected. Read every score against its majority baseline.", "9pt"),
         ]),
    dict(name="Model Evaluation",
         description="All five supervised experiments E1-E5: model comparison against the baseline, leakage runs (INVALID) and the independent cross-check, read from exports/E<n>_results.csv.",
         visuals=[
             text(20, 2, 1240, 48, "FitPulse - Model Evaluation: supervised experiments E1-E5 (source: exports/E<n>_results.csv)", "18pt", True, "#20493A"),
             slicer(20, 56, 320, 76, "experiments", "experiment_name", "Experiment (leave empty to show all five)", mode="Dropdown"),
             card(350, 56, 270, 84, "Cross-check Checks", "Checks - source: hdfs_rerun/sklearn_crosscheck.csv", show_title=True),
             card(630, 56, 270, 84, "Cross-check Passed", "Passed - source: hdfs_rerun/sklearn_crosscheck.csv", show_title=True),
             text(910, 56, 350, 84, "The cross-check is the independent scikit-learn recomputation of the HDFS rerun (faculty_evidence/supervised/hdfs_rerun/sklearn_crosscheck.csv). "
                  "It is the only source on this page besides exports/E<n>_results.csv.", "9pt"),
             dict(type="tableEx", x=20, y=142, w=740, h=296, title="Model comparison with the baseline - headline evaluation of each experiment", no_total=True,
                  fields={"Values": [C(SR, "experiment_id"), C(SR, "model"), C(SR, "split_type"), C(SR, "metric"), M("Result Value")]},
                  filters=[(SR, "status", ["VALID", "BASELINE"]), (SR, "split_type", HEADLINE_SPLITS), (SR, "metric", COMPARE_METRICS)],
                  alt="Model comparison with baselines for every experiment, one row per experiment, model, split and metric"),
             dict(type="clusteredColumnChart", x=770, y=142, w=490, h=296, title="ROC-AUC by experiment, evaluation split and model",
                  fields={"Category": [C(SR, "experiment_id"), C(SR, "split_type")], "Series": [C(SR, "model")], "Y": [M("Result Value")]},
                  filters=[(SR, "status", ["VALID"]), (SR, "split_type", HEADLINE_SPLITS), (SR, "metric", ["ROC AUC"])],
                  alt="ROC-AUC of every classifier by experiment and evaluation split"),
             dict(type="tableEx", x=20, y=444, w=620, h=222, title="Leakage runs (status INVALID - never results)", no_total=True,
                  fields={"Values": [C(SR, "experiment_id"), C(SR, "model"), C(SR, "metric"), C(SR, "status"), M("Result Value")]},
                  filters=[(SR, "status", ["INVALID"]), (SR, "metric", ["ROC AUC", "R2"])],
                  alt="Leakage runs with status INVALID and their inflated scores"),
             dict(type="tableEx", x=650, y=444, w=610, h=140, title="Cross-check by experiment (source: hdfs_rerun/sklearn_crosscheck.csv)",
                  fields={"Values": [C("experiments", "experiment_name"), M("Cross-check Checks"), M("Cross-check Passed")]},
                  alt="Number of cross-check checks and checks passed per experiment"),
             text(650, 588, 610, 80, "How to read this page\n"
                  "E1-E5 are different tasks: compare models inside one experiment, never across experiments. Every row names its experiment and evaluation split. "
                  "The baseline is the always-majority class (E5: the training mean). INVALID rows are leakage demonstrations.", "9pt"),
             text(20, 672, 1240, 44, "Sources: exports/E1_results.csv ... exports/E5_results.csv (copied row for row into powerbi/data/supervised_results.csv) and the cross-check file named above. "
                  "ROC-AUC is not defined for the regression experiment E5; its MAE and R2 are in the comparison table.", "9pt"),
         ]),
]
