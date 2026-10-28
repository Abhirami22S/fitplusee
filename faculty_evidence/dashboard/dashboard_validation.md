# Dashboard validation (streamlit AppTest)
Run: 2026-10-26 22:07:51 - **15/15 passed**
Data source: local SQLite dashboard/fitpulse.db + local joblib models (not HDFS)

| Check | Result | Detail |
|---|---|---|
| SQLite connectivity + tables | PASS | {'user_daily_metrics': 100122, 'population_percentiles': 437, 'users': 4, 'user_daily_raw': 46} |
| model loads: goal_achievement_model | PASS |  |
| model loads: forecast_model | PASS |  |
| model loads: sleep_quality_model | PASS |  |
| App starts (login screen, no exception) | PASS | [] |
| Wrong password gives an error message, no crash | PASS | ['Incorrect password.'] |
| demo1: dashboard renders without exception | PASS | 8 tabs, 2 metrics, 3.1s, [] |
| demo1: key sections present | PASS | [':material/today: Today', ':material/show_chart: Trends & Forecast', ':material/bedtime: Sleep', ':material/monitor_heart: Heart Rate', ':material/checklist: R |
| demo1: Calories & Trends tab present | PASS | [':material/today: Today', ':material/show_chart: Trends & Forecast', ':material/bedtime: Sleep', ':material/monitor_heart: Heart Rate', ':material/checklist: R |
| demo1: fitness score and monthly sections rendered | PASS |  |
| demo1: calorie model section rendered or reports a clear message | PASS |  |
| demo1: authenticated as the demo user id | PASS | {'user_id': 1503, 'username': 'demo1', 'is_demo': True} |
| demo2: dashboard renders without exception | PASS | 8 tabs, 2 metrics, 0.2s, [] |
| demo3: dashboard renders without exception | PASS | 8 tabs, 2 metrics, 0.2s, [] |
| Missing database: friendly st.error and no uncaught exception | PASS | ["FitPulse cannot start because required files are missing:\n\n- `C:\\Users\\Abhirami S\\AppData\\Local\\Temp\\fp_nodb_ezb8jx6y\\dashboard\\fitpulse.db`\n- `C:\ |