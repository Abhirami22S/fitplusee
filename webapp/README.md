# FitPulse per-user web dashboard (`webapp/`)

**Goal:** pick a user and see that person's insights, produced by models trained on **all** users' data.
One static page (`public/index.html`) reads one JSON file (`public/data/insights.json`); there is no server code.

| Insight | Produced by |
|---|---|
| Tomorrow's step-goal probability | Logistic Regression trained on all users (`models/artifacts/goal_achievement_model.joblib`; chronological test ROC-AUC 0.755) |
| Calories actual vs estimate | Linear Regression (Spark MLlib, test MAE 199.7 kcal, R2 0.63) |
| Percentile vs other users | rank of the user's average among all 437 users |
| Recommendations, fitness score | transparent rules (`models/recommendation_engine.py`, `models/analytics.py`); not medical advice |

## Run (PowerShell, from `D:\bigdata\fitpulsee\FitPulse`)
```powershell
..\.venv\Scripts\python.exe webapp\export_insights.py      # builds public/data/insights.json (437 users, ~1.9 MB)
..\.venv\Scripts\python.exe webapp\validate_insights.py    # 10 checks against the Silver data and saved models
.\webapp\run_local.ps1                                     # http://127.0.0.1:8765/?user=1503
```

## Host on Vercel (one-time login needed)
```powershell
cd D:\bigdata\fitpulsee\FitPulse\webapp
npx vercel login          # opens the browser once
npx vercel --prod         # accept the defaults; Vercel serves ./public (vercel.json)
```
The deployed site contains the exported data of all 437 (anonymous numeric) users. The data is a public Kaggle dataset; do not put real personal data in a public deployment.

## Limits (say these honestly)
The page shows pre-computed results from the last export; it is not a live prediction service. The models were trained offline; the data is 100,122 rows
(single-node Spark/HDFS demonstration). Power BI (`powerbi/`) remains the population-level analytics dashboard.
