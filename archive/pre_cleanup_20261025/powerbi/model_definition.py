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
        "hidden": ["row_id", "user_id", "month", "segment_id", "segment_label", "daily_step_goal", "daily_calorie_goal"],
        "formats": {"date": "yyyy-mm-dd", "calories_burned": "#,0.0", "predicted_calories": "#,0.0", "calorie_error": "#,0.0",
                    "distance_km": "0.00", "sleep_hours": "0.00", "steps": "#,0"},
        "description": "One row per USER-DAY (100,122 rows). Source: Silver dataset + Linear Regression predictions.",
    },
    "dim_user": {
        "csv": "dim_user.csv", "hidden": ["segment_id"],
        "description": "One row per USER (437). Segment = user-level K-Means (experiment E3).",
    },
    "dim_date": {
        "csv": "dim_date.csv", "date_columns": ["Date"], "key_date": "Date",
        "sort_by": {"Month": "MonthNumber", "DayOfWeek": "DayOfWeekNumber"},
        "hidden": ["MonthNumber", "DayOfWeekNumber", "Year"],
        "description": "Calendar 2024-01-01..2024-12-31, marked as the date table.",
    },
    "segment_profile": {"csv": "segment_profile.csv", "description": "K-Means (E3) segment averages measured by Spark MLlib."},
    "experiments": {"csv": "experiments.csv", "description": "One row per evaluated experiment (E1-E5): target, granularity, split."},
    "model_evaluation": {"csv": "model_evaluation.csv", "hidden": ["experiment_name", "target", "data_granularity", "is_baseline", "source_file"],
                         "description": "Metrics per experiment/set; every row names its source file."},
    "confusion_matrices": {"csv": "confusion_matrices.csv", "description": "Test-set confusion matrices of the two Random Forest experiments (E1, E2)."},
    "kmeans_k_selection": {"csv": "kmeans_k_selection.csv", "description": "Silhouette / WCSS by K for the two K-Means experiments (E3, E4)."},
}

# many side -> one side
RELATIONSHIPS = [
    ("fact_daily", "date", "dim_date", "Date"),
    ("fact_daily", "user_id", "dim_user", "user_id"),
    ("dim_user", "segment_id", "segment_profile", "cluster"),
    ("model_evaluation", "experiment_id", "experiments", "experiment_id"),
    ("confusion_matrices", "experiment_id", "experiments", "experiment_id"),
    ("kmeans_k_selection", "experiment_id", "experiments", "experiment_id"),
]

INT, DEC, PCT, DEC4 = "#,0", "#,0.0", "0.0%", "0.0000"
E5 = ('model_evaluation[experiment_id] = "E5", model_evaluation[algorithm] = "Linear Regression (Spark MLlib)", '
      'model_evaluation[evaluation_set] = "test"')
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
    ("model_evaluation", "Verified Test MAE (kcal)", f'CALCULATE ( MAX ( model_evaluation[value] ), {E5}, model_evaluation[metric] = "MAE (kcal)" )', DEC, "3 Calorie Prediction"),
    ("model_evaluation", "Verified Test RMSE (kcal)", f'CALCULATE ( MAX ( model_evaluation[value] ), {E5}, model_evaluation[metric] = "RMSE (kcal)" )', DEC, "3 Calorie Prediction"),
    ("model_evaluation", "Verified Test R2", f'CALCULATE ( MAX ( model_evaluation[value] ), {E5}, model_evaluation[metric] = "R2" )', DEC4, "3 Calorie Prediction"),
    ("model_evaluation", "Baseline Test MAE (kcal)",
     'CALCULATE ( MAX ( model_evaluation[value] ), model_evaluation[experiment_id] = "E5", model_evaluation[algorithm] = "Training-mean baseline", '
     'model_evaluation[evaluation_set] = "test", model_evaluation[metric] = "MAE (kcal)" )', DEC, "3 Calorie Prediction"),
    # ---- Page 4: User Segmentation (E3: 437 USERS) ----
    ("dim_user", "Users in Segment", "COUNTROWS ( dim_user )", INT, "4 Segmentation"),
    ("dim_user", "Segment Share %", "DIVIDE ( COUNTROWS ( dim_user ), CALCULATE ( COUNTROWS ( dim_user ), ALL ( dim_user[segment_label] ) ) )", PCT, "4 Segmentation"),
    ("dim_user", "Segment Avg Steps", "AVERAGE ( dim_user[avg_steps] )", INT, "4 Segmentation"),
    ("dim_user", "Segment Avg Calories", "AVERAGE ( dim_user[avg_calories] )", DEC, "4 Segmentation"),
    # ---- Page 5: Model Evaluation ----
    ("model_evaluation", "Metric Value", "MAX ( model_evaluation[value] )", "0.0000", "5 Model Evaluation"),
    ("confusion_matrices", "Confusion Count", "SUM ( confusion_matrices[count] )", INT, "5 Model Evaluation"),
    ("confusion_matrices", "Confusion Share of Actual", "AVERAGE ( confusion_matrices[share_of_actual] )", PCT, "5 Model Evaluation"),
    ("kmeans_k_selection", "K Metric Value", "MAX ( kmeans_k_selection[value] )", "0.0000", "5 Model Evaluation"),
]
MEASURE_HOST = {m[1]: m[0] for m in MEASURES}

# ---------------------------------------------------------------------------------------------------------------
# Report pages.  Visual = dict(type, x, y, w, h, title, fields={role: [("c"|"m", table, name)]}, ...)
# ---------------------------------------------------------------------------------------------------------------
C = lambda t, n: ("c", t, n)
M = lambda n: ("m", MEASURE_HOST[n], n)

W, H = 1280, 720
import os
RE1 = "Random Forest - REPORT experiment"
DEFAULT_EXPERIMENT = os.environ.get("FITPULSE_PBI_DEFAULT_EXPERIMENT", RE1)   # only changed to capture per-experiment screenshots


def card(x, y, w, h, measure, title):
    return dict(type="card", x=x, y=y, w=w, h=h, title=title, fields={"Values": [M(measure)]}, alt=f"KPI card: {title}")


def slicer(x, y, w, h, table, col, title, mode="Dropdown", single=False, default=None):
    return dict(type="slicer", x=x, y=y, w=w, h=max(h, 76), title=title, fields={"Values": [C(table, col)]}, mode=mode, single=single, default=default,
                alt=f"Slicer: {title}")


def text(x, y, w, h, body, size="10pt", bold=False, color=None):
    return dict(type="textbox", x=x, y=y, w=w, h=h, body=body, size=size, bold=bold, color=color)


def std_slicers(y=52):
    return [slicer(20, y, 250, 52, "dim_date", "Date", "Date range", mode="Between"),
            slicer(280, y, 200, 52, "fact_daily", "activity_type", "Activity type"),
            slicer(490, y, 190, 52, "dim_user", "age_group", "Age group"),
            slicer(690, y, 160, 52, "dim_user", "gender", "Gender"),
            slicer(860, y, 220, 52, "dim_user", "segment_label", "User segment (E3)")]


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
    dict(name="User Segmentation", description="User-level K-Means (experiment E3, 437 users, K=2): cluster sizes, profiles and measured differences.",
         visuals=[
             text(20, 2, 1240, 48, "FitPulse - User Activity Segmentation (K-Means on 437 users)", "18pt", True, "#20493A"),
             text(20, 50, 1240, 34, "User-level clusters (experiment E3). These are NOT the faculty notebook's K-Means, which clusters 100,122 user-days (experiment E4).", "11pt", True, "#B5495B"),
             slicer(20, 88, 200, 76, "dim_user", "age_group", "Age group"),
             slicer(230, 88, 160, 76, "dim_user", "gender", "Gender"),
             card(400, 88, 250, 80, "Users in Segment", "Users (current filter)"),
             dict(type="donutChart", x=20, y=170, w=300, h=244, title="Users per segment",
                  fields={"Category": [C("dim_user", "segment_label")], "Y": [M("Users in Segment")]}, alt="Donut chart of users per segment"),
             dict(type="tableEx", x=330, y=170, w=500, h=244, title="Segment profile (user averages, measured by Spark MLlib)",
                  fields={"Values": [C("segment_profile", "segment_label"), C("segment_profile", "Users"), C("segment_profile", "AvgSteps"), C("segment_profile", "AvgActiveMin"),
                                     C("segment_profile", "AvgSedentaryMin"), C("segment_profile", "AvgCalories"), C("segment_profile", "AvgHeartRate"), C("segment_profile", "AvgSleep")]},
                  alt="Table of segment profiles"),
             dict(type="scatterChart", x=840, y=170, w=420, h=244, title="Users in PCA space (7 standardised features)",
                  fields={"Series": [C("dim_user", "segment_label")], "X": [C("dim_user", "PC1")], "Y": [C("dim_user", "PC2")]},
                  alt="Scatter of users on the first two principal components, coloured by segment"),
             dict(type="clusteredColumnChart", x=20, y=420, w=300, h=244, title="Avg active minutes per day",
                  fields={"Category": [C("dim_user", "segment_label")], "Y": [M("Avg Active Minutes")]}, alt="Active minutes by segment"),
             dict(type="clusteredColumnChart", x=330, y=420, w=300, h=244, title="Avg sedentary minutes per day",
                  fields={"Category": [C("dim_user", "segment_label")], "Y": [M("Avg Sedentary Minutes")]}, alt="Sedentary minutes by segment"),
             dict(type="clusteredColumnChart", x=640, y=420, w=300, h=244, title="Avg sleep hours per day",
                  fields={"Category": [C("dim_user", "segment_label")], "Y": [M("Avg Sleep Hours")]}, alt="Sleep hours by segment"),
             dict(type="clusteredColumnChart", x=950, y=420, w=310, h=244, title="Step-goal achievement %",
                  fields={"Category": [C("dim_user", "segment_label")], "Y": [M("Step-Goal Achievement %")]}, alt="Goal achievement by segment"),
             text(20, 668, 1240, 48, "Interpretation (measured): the two segments differ by only about 2.4 active minutes, 5.5 sedentary minutes and 28 kcal per day; average steps are the same "
                  "(8,631 vs 8,621). Euclidean silhouette 0.20 = weak separation. Labels come from the measured average active minutes, not from an assumed Sedentary/Moderate/Active scheme.", "9pt"),
         ]),
    dict(name="Model Evaluation", description="Metrics of the five experiments, shown one experiment at a time: Random Forest x2, K-Means x2, Linear Regression.",
         visuals=[
             text(20, 2, 1240, 48, "FitPulse - Model Evaluation (one experiment at a time)", "18pt", True, "#20493A"),
             slicer(20, 56, 420, 76, "experiments", "experiment_name", "Experiment (select one)", mode="Dropdown", single=True, default=DEFAULT_EXPERIMENT),
             dict(type="tableEx", x=450, y=56, w=810, h=130, title="What was evaluated",
                  fields={"Values": [C("experiments", "target"), C("experiments", "data_granularity"), C("experiments", "split_method")]}, alt="Target, granularity and split of the selected experiment"),
             dict(type="tableEx", x=20, y=194, w=500, h=378, title="Metrics of the selected experiment (by evaluation set)", no_total=True,
                  fields={"Values": [C("model_evaluation", "metric_label"), C("model_evaluation", "evaluation_set"), M("Metric Value")]},
                  alt="Metrics for the selected experiment by evaluation set"),
             dict(type="tableEx", x=530, y=194, w=730, h=190, title="Confusion matrix on the test set (Random Forest experiments only)", no_total=True,
                  fields={"Values": [C("confusion_matrices", "actual"), C("confusion_matrices", "predicted"), M("Confusion Count"), M("Confusion Share of Actual")]},
                  alt="Confusion matrix counts and row percentages of the selected Random Forest experiment"),
             dict(type="lineChart", x=530, y=390, w=730, h=182, title="Silhouette by K (K-Means experiments only)",
                  fields={"Category": [C("kmeans_k_selection", "K")], "Y": [M("K Metric Value")], "Series": [C("kmeans_k_selection", "metric")]},
                  filters=[("kmeans_k_selection", "metric", ["Silhouette (Euclidean, scikit-learn)", "Silhouette (Spark squaredEuclidean)"])],
                  alt="Silhouette score against K for the selected K-Means experiment"),
             text(20, 578, 1240, 90, "How to read this page\n"
                  "E1 Random Forest (report): same-day goal steps >= 8,000, user-days. E2 Random Forest (notebook): next-day achievement of the personalised goal, user-days with lag features. "
                  "E3 K-Means (report): 437 USERS. E4 K-Means (notebook): 100,122 user-DAYS. E5 Linear Regression: same-day calories. Results of different experiments are never combined.\n"
                  "Silhouette: Spark's ClusteringEvaluator uses squared Euclidean distance; scikit-learn uses Euclidean. The same E3 grouping scores 0.341 (Spark) and 0.202 (Euclidean).\n"
                  "The old Streamlit dashboard's Logistic Regression (ROC-AUC 0.755) is documented in models/metrics_report.md and is not in this table (it was not re-run).", "9pt"),
             text(20, 672, 1240, 44, "Sources: faculty_evidence/report_aligned/*, faculty_evidence/classification_results.csv, confusion_matrix.csv, silhouette_scores.csv, cluster_summary.csv, regression_results.csv "
                  "(file names are recorded per row in model_evaluation.source_file).", "9pt"),
         ]),
]
