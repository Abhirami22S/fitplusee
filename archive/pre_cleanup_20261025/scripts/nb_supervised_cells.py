"""
Cell definitions for the SUPERVISED version of FitPulse_Faculty_Demo.ipynb (sections 5-7, 9-10 and the patched cells).
Used by scripts/build_supervised_notebook.py. Markdown cells hold method text only; every NUMBER shown in the notebook is
printed by a code cell that READS exports/E<n>_results.csv or faculty_evidence/supervised/ (nothing is typed by hand).
"""

# --------------------------------------------------------------------------------------------------------- section 5
S5_MD = r"""## 5. Supervised learning protocol (all five experiments are supervised)

The faculty asked for **supervised** learning. The two K-Means experiments were therefore replaced (their code is in `archive/`),
and every experiment now predicts a *labelled target* from features:

| Id | Task | Label | Unit / rows | Evaluation (headline) | Models |
|---|---|---|---|---|---|
| **E1** | same-day goal classification | `GoalAchieved = 1 if steps >= 8000` | user-day, 100,122 | random 70/15/15 split, seed 42 (unchanged) | Random Forest (unchanged), Logistic Regression, Gradient-Boosted Trees |
| **E2** | next-day goal prediction (rebuilt) | `steps(t) >= 8000`, features from days before *t* only | user-day with history | **chronological** split by date | Random Forest, Gradient-Boosted Trees, Logistic Regression |
| **E3** | user-level classifier (replaces K-Means on 437 users) | `high_achiever = 1` if the user's goal rate is above the median user | user, 437 | stratified 5-fold cross-validation (every user tested once) | Random Forest, Logistic Regression |
| **E4** | user-day activity level (replaces K-Means on user-days) | `High` if `active_minutes` is above the median | user-day | **user-held-out** 70/15/15 (no user in two sets) | Random Forest, Gradient-Boosted Trees, Logistic Regression |
| **E5** | same-day calorie regression (kept) | `calories_burned` (kcal) | user-day | seeded hash split of (user, date) 70/15/15 + chronological check | Linear Regression (unchanged), Random Forest Regressor, GBT Regressor |

**Rules applied to every experiment**
1. **Seed 42** for every random operation (splits, trees, scikit-learn cross-checks).
2. **Tune on the validation set only.** The test set is scored once per final model.
3. **Leakage rules.** `steps`, `distance_km`, `user_id`, `date`, `smoking_status`, `health_condition` are never features of a goal model, and nothing derived from
   steps of the prediction day is either. Every experiment also runs once *with* a leaky feature; that score is stored with status **INVALID** and is never a result.
4. **Baseline comparison** (always predicting the majority class, or the training mean for regression) next to every score.
5. **Unseen-data evaluation**: unseen users, later dates, or cross-validation folds, never a plain random split alone for a headline number that could leak across neighbouring days.
6. **Independent scikit-learn cross-check** of the metrics (section 7.3).

**Data note: several columns are partly derived in this demonstration dataset** (`data/prepare_raw_dataset.py`).
`calories_burned = MET(activity_type, intensity) x weight_kg x duration / 60`; `active_minutes` is that session duration;
`sedentary_minutes = 1440 - sleep_minutes - active_minutes`; `distance_km = steps x stride(height, intensity)`;
`max_heart_rate` = average heart rate + an intensity margin + noise (capped at 220 - age); `sleep_quality_score` is a formula of sleep hours, stress and resting heart rate plus noise.
So *calories, distance, minutes, max heart rate and sleep quality are partly derived*: a model that scores well on them may only be recovering a formula, and several
leakage demonstrations below exist precisely because of that."""

S5_FACTS = r"""# Dataset facts that explain several results below (computed here from the Silver Parquet, not typed)
silver_pd = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "fitpulse_silver")
silver_pd["date"] = pd.to_datetime(silver_pd["date"])
silver_pd = silver_pd.drop_duplicates(["user_id", "date"])
silver_pd["month"] = silver_pd["date"].dt.month
print(f"{len(silver_pd):,} user-days, {silver_pd.user_id.nunique()} users, {silver_pd.date.min().date()} to {silver_pd.date.max().date()}")

w = silver_pd.weight_kg - silver_pd.groupby("user_id").weight_kg.transform("mean")
m = silver_pd.month - silver_pd.groupby("user_id").month.transform("mean")
rng = silver_pd.groupby("user_id").weight_kg.agg(lambda x: x.max() - x.min())
print(f"within-user correlation of weight_kg with calendar month = {np.corrcoef(w, m)[0, 1]:.3f}; median within-user weight range = {rng.median():.1f} kg")
print("   -> weight_kg behaves like a calendar clock in this synthetic data (a real person does not gain ~60 kg in a year).")
print("sedentary_minutes == max(0, 1440 - sleep_minutes - active_minutes) for",
      f"{(silver_pd.sedentary_minutes == (1440 - silver_pd.sleep_minutes - silver_pd.active_minutes).clip(lower=0)).mean():.1%} of rows")

by_month = silver_pd.groupby("month").agg(mean_steps=("steps", "mean"), goal_rate=("steps", lambda x: (x >= 8000).mean()), user_days=("steps", "size"))
display(by_month.round(3).T)
fig, ax = plt.subplots(figsize=(6.4, 2.8))
bars = ax.bar(by_month.index, by_month.goal_rate, color=BLUE, width=0.62)
for b, v in zip(bars, by_month.goal_rate):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8, color=INK)
ax.set_xticks(range(1, 13)); ax.set_ylim(0, 1); ax.set_xlabel("month of 2024"); ax.set_ylabel("share of days with steps >= 8,000")
ax.set_title("The goal rate follows the calendar (seasonal pattern of the data)"); ax.grid(axis="x", visible=False)
plt.tight_layout(); plt.show()"""

S5_HELPERS = r"""# Helpers for sections 5-7. Every table and chart is READ from the files written by models/sup_e1_*.py ... sup_e5_*.py
# (exports/E<n>_results.csv, exports/E<n>_feature_importance.csv, faculty_evidence/supervised/).
import sys
from matplotlib.patches import Patch
sys.path.insert(0, str(PROJECT_ROOT / "models"))
EXPORTS = PROJECT_ROOT / "exports"
SUP = EVIDENCE / "supervised"
ACC, F1W, F1M, AUC = "Accuracy", "F1 (weighted)", "F1 (macro)", "ROC AUC"
P1, R1, F11 = "Precision (positive class)", "Recall (positive class)", "F1 (positive class)"
BASE = "Baseline accuracy (always majority class)"
MAE, RMSE, R2 = "MAE (kcal)", "RMSE (kcal)", "R2"

def results(exp):
    return pd.read_csv(EXPORTS / f"{exp}_results.csv")

def wide(res, split, metrics, status=("VALID",)):
    d = res[(res.split_type == split) & res.status.isin(status)]
    return d.pivot_table(index="model", columns="metric", values="value", aggfunc="first").reindex(columns=metrics)

def invalid_rows(res, metrics):
    d = res[res.status == "INVALID"].pivot_table(index="model", columns="metric", values="value", aggfunc="first")
    return d[[c for c in metrics if c in d.columns]]

def info(exp):
    return json.loads((SUP / f"{exp}_run_info.json").read_text(encoding="utf-8"))

def model_bars(tab, metric, baseline=None, title="", fmt="{:.3f}", ylim=None, baseline_label="majority-class baseline"):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    bars = ax.bar(tab.index, tab[metric], color=BLUE, width=0.5)
    for b, v in zip(bars, tab[metric]):
        ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v), ha="center", va="bottom", color=INK, fontsize=9)
    if baseline is not None:
        ax.axhline(baseline, color=MUTED, ls="--", lw=1.2, label=f"{baseline_label} {fmt.format(baseline)}")
        ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.set_title(title); ax.set_ylabel(metric); ax.grid(axis="x", visible=False)
    if ylim: ax.set_ylim(*ylim)
    long = max(len(str(n)) for n in tab.index) > 18
    plt.xticks(fontsize=8, rotation=20 if long else 0, ha="right" if long else "center"); plt.tight_layout(); plt.show()

def validity_chart(res, valid_split, metric, title):
    v = res[(res.split_type == valid_split) & (res.status == "VALID") & (res.metric == metric)][["model", "value"]].assign(kind="valid")
    i = res[(res.status == "INVALID") & (res.metric == metric)][["model", "value"]].assign(kind="INVALID (leakage)")
    d = pd.concat([v, i]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 0.36 * len(d) + 1.2))
    bars = ax.barh(range(len(d)), d.value, color=[BLUE if k == "valid" else ORANGE for k in d.kind], height=0.62)
    for b, k in zip(bars, d.kind):
        if k != "valid":
            b.set_hatch("///"); b.set_edgecolor("white")
    ax.set_yticks(range(len(d))); ax.set_yticklabels([n.replace(" (LEAKAGE)", "") for n in d.model], fontsize=7.5)
    ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    for y, val in enumerate(d.value):
        ax.text(val, y, f" {val:.3f}", va="center", fontsize=8, color=INK)
    ax.legend(handles=[Patch(color=BLUE, label="valid"), Patch(facecolor=ORANGE, hatch="///", edgecolor="white", label="INVALID (leakage)")],
              loc="lower right", frameon=False, fontsize=8)
    ax.set_xlabel(metric); ax.set_title(title); plt.tight_layout(); plt.show()

def importance_chart(exp, model, n=10):
    imp = pd.read_csv(EXPORTS / f"{exp}_feature_importance.csv")
    d = imp[imp.model == model].nlargest(n, "importance").iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 0.3 * len(d) + 1.1))
    ax.barh(d.feature, d.importance, color=BLUE, height=0.6)
    for y, val in enumerate(d.importance):
        ax.text(val, y, f" {val:.3f}", va="center", fontsize=8, color=INK)
    ax.set_title(f"{exp} {model}: top {len(d)} feature importances (impurity)"); ax.grid(axis="y", visible=False)
    plt.tight_layout(); plt.show()

def gains(tab, metric, base, label="baseline"):
    for name in tab.index:
        print(f"  {name:26s} {metric} {tab.loc[name, metric]:.4f} = {label} {base:.4f} {100 * (tab.loc[name, metric] - base):+.1f} points")

print("helpers ready; results are read from", EXPORTS, "and", SUP)"""

# --------------------------------------------------------------------------------------------------------- E1
E1_MD = r"""## 6. Goal prediction: E1, E2 and E3

### 6.1 E1 - same-day goal classification

**Question:** given a day's *other* measurements, was the 8,000-step goal reached that day? **Label:** `GoalAchieved = 1 if steps >= 8000`.
**E1 is unchanged:** the same Random Forest (18 features: 15 numeric including the engineered `active_ratio`, and 3 categorical), seed 42, the same
70/15/15 `randomSplit` and the same selected setting (`models/spark_report_classification.py`, imported not edited). Added on exactly the same rows and features:
**Logistic Regression** (one-hot + standardised, `regParam` tuned on validation) and **Gradient-Boosted Trees** (depth x iterations tuned on validation ROC-AUC).
**Never features:** `steps`, `distance_km`, `user_id`, `date`, `smoking_status`, `health_condition`."""

E1_CODE = r"""import spark_report_classification as e1_old          # the unchanged E1 Random Forest code
r1, i1 = results("E1"), info("E1")
print(f"E1 features ({len(e1_old.NUM) + len(e1_old.CAT)}): numeric {e1_old.NUM} + categorical {e1_old.CAT}")
print(f"records {i1['records']:,}; split {i1['split_sizes']}; same split as the existing E1 run: {i1['same_split_as_existing_E1']}")
print(f"settings: Random Forest {i1['rf_setting']} | Logistic Regression {i1['logreg_setting']} | GBT {i1['gbt_setting']}")
print(f"the unchanged Random Forest is reproduced: max |difference| to the existing E1 metrics = {i1['reproduction_max_abs_diff']:.1e}\n")

cols = [ACC, F1W, AUC, BASE]
t1 = wide(r1, "test", cols)
print("E1 comparison table - TEST set (random 70/15/15, seed 42):")
display(t1.round(4))
base1 = t1[BASE].iloc[0]
model_bars(t1, ACC, base1, "E1 test accuracy")
model_bars(t1, AUC, 0.5, "E1 test ROC-AUC", baseline_label="chance level")
print("VALIDATION set (used for tuning):"); display(wide(r1, "validation", cols).round(4))
print("USER-HELD-OUT check (15% of users never seen in training):"); display(wide(r1, "test (user-held-out)", cols).round(4))
print("LEAKAGE test - the same models with steps and distance_km added (status INVALID, never a result):")
display(invalid_rows(r1, [ACC, F1W, AUC]).round(4).assign(status="INVALID"))
validity_chart(r1, "test", AUC, "E1 ROC-AUC: valid models vs leakage runs")
importance_chart("E1", "Random Forest"); importance_chart("E1", "Gradient-Boosted Trees")

print("\nInterpretation (computed from the tables above)")
gains(t1, ACC, base1, "majority baseline")
uh = wide(r1, "test (user-held-out)", cols)
print("  user-held-out accuracy:", {m: round(float(uh.loc[m, ACC]), 4) for m in uh.index}, "against baseline", round(float(uh[BASE].iloc[0]), 4))
lk = invalid_rows(r1, [ACC, AUC])
print(f"  with steps/distance_km the score becomes accuracy {lk[ACC].min():.3f}-{lk[ACC].max():.3f}: the label is a threshold on steps, so the run is INVALID.")"""

E1_NOTE = r"""**Reading E1.** All three models beat the 61.4% majority baseline by a similar margin, and the margin survives when whole users are held out, so the models are not memorising individual users.
The most important feature of both tree models is `weight_kg`. Section 5 showed that, inside each user, `weight_kg` follows the calendar almost linearly in this synthetic data,
so it can act as a **clock** for the seasonal pattern in the goal rate. E1 is deliberately unchanged, so this is stated as a limitation rather than removed (no ablation was run for E1).
The leakage run (`steps`, `distance_km` added) is near-perfect and is **INVALID**: it measures a threshold, not learning."""

# --------------------------------------------------------------------------------------------------------- E2
E2_MD = r"""### 6.2 E2 - next-day goal prediction (rebuilt)

**Question:** using only what was recorded *before* day *t*, will the user reach 8,000 steps on day *t*? **Label:** `steps(t) >= 8000`.
The previous version reused Silver's rolling columns, whose window **includes** the current row (`steps_roll7_avg` uses `rowsBetween(-6, 0)`), and headlined a random split.
Rebuilt:
* every history feature is a Spark window function `Window.partitionBy("user_id").orderBy("date")` with the frame **ending at -1** (`rowsBetween(-7, -1)`, `rowsBetween(-3, -1)`) or a `lag()`, so day *t* never sees itself or later days;
* only rows whose previous logged row is exactly the previous calendar day, with at least 3 earlier rows, are used;
* features = history windows + calendar of day *t* (day of week, month sin/cos) + static profile (age, gender, BMI, height, **baseline weight** = BMI x height squared; raw `weight_kg` is replaced because it works as a calendar clock);
* **chronological split**: earliest 70% of the date span for training, the next 15% for validation, the latest 15% for the test block. The random split is shown only as a labelled contrast;
* Random Forest, Gradient-Boosted Trees and Logistic Regression, tuned on the validation block only."""

E2_CODE = r"""r2, i2 = results("E2"), info("E2")
sp2 = pd.read_csv(SUP / "E2_split_summary.csv")
print(f"usable rows {i2['usable_rows']:,}; split cut dates {i2['split_cuts']}; settings {i2['settings']}")
display(sp2.round(4))
f2 = pd.read_csv(SUP / "predictions" / "E2_features.csv", usecols=["date", "split", "label"], parse_dates=["date"])
mm = f2.assign(month=f2.date.dt.month).groupby("month").label.mean()
fig, ax = plt.subplots(figsize=(6.6, 2.9))
ax.bar(mm.index, mm.values, color=BLUE, width=0.62)
frac = lambda d: pd.Timestamp(d).month - 0.5 + (pd.Timestamp(d).day - 1) / pd.Timestamp(d).days_in_month   # month m is centred on x = m
c1, c2 = (frac(x) for x in i2["split_cuts"])
for x, lab in ((c1, "validation starts"), (c2, "test starts")):
    ax.axvline(x, color=INK, ls=":", lw=1); ax.text(x + 0.05, 0.97, lab, fontsize=8, va="top", color=INK)
ax.set_xticks(range(1, 13)); ax.set_ylim(0, 1); ax.set_xlabel("month of 2024"); ax.set_ylabel("share of days >= 8,000 steps")
ax.set_title("E2: the goal rate drifts across the chronological blocks"); ax.grid(axis="x", visible=False)
plt.tight_layout(); plt.show()

BASE_TR = "Baseline accuracy (always TRAINING-majority class)"
cols2 = [ACC, P1, R1, F11, AUC, BASE]
t2 = wide(r2, "chronological test", cols2)
t2[BASE_TR] = r2[(r2.split_type == "chronological test") & (r2.metric == BASE_TR)].value.iloc[0]
print("E2 comparison table - CHRONOLOGICAL TEST block (headline):"); display(t2.round(4))
model_bars(t2, ACC, t2[BASE].iloc[0], "E2 chronological test accuracy", baseline_label="always-'missed' baseline")
model_bars(t2, AUC, 0.5, "E2 chronological test ROC-AUC", baseline_label="chance level")
print("VALIDATION block:"); display(wide(r2, "validation", cols2).round(4))
print("LEAKAGE test - Silver's steps_roll7_avg (window includes the prediction day) added (INVALID):")
display(invalid_rows(r2, [ACC, F11, AUC]).round(4).assign(status="INVALID"))
validity_chart(r2, "chronological test", AUC, "E2 ROC-AUC: valid models vs leakage runs")
print("CONTRAST ONLY - a RANDOM split of the same rows (not the headline; neighbouring days leak across it):")
display(wide(r2, "random split (NOT headline)", [ACC, F11, AUC, BASE], status=("REFERENCE",)).round(4))
importance_chart("E2", "Random Forest"); importance_chart("E2", "Gradient-Boosted Trees")

print("\nInterpretation (computed from the tables above)")
pos = sp2.set_index("split").positive_share
print(f"  share of days meeting the goal: train {pos['train']:.3f}, validation {pos['validation']:.3f}, test {pos['test']:.3f}")
print(f"  test-majority baseline (always 'missed') {t2[BASE].iloc[0]:.4f}; training-majority baseline (always 'achieved') {t2[BASE_TR].iloc[0]:.4f}")
gains(t2, ACC, t2[BASE].iloc[0], "always-'missed' baseline")
rnd = wide(r2, "random split (NOT headline)", [ACC, AUC], status=("REFERENCE",))
print(f"  the random split gives accuracy {rnd[ACC].min():.3f}-{rnd[ACC].max():.3f}, the chronological block {t2[ACC].min():.3f}-{t2[ACC].max():.3f}: the random split is optimistic.")"""

E2_NOTE = r"""**Reading E2.** The honest next-day signal is weak. The goal rate falls from the first months to the last, so the training days are mostly 'achieved' while the test block is mostly 'missed':
a model trained on the early months over-predicts 'achieved' later (high recall, low precision for the tree models). Compare accuracy with the **always-'missed' baseline of the test block**, not with
the random-split figure. ROC-AUC (about 0.67-0.70) is the fairer summary of ranking ability under this shift. The leakage run, which adds the rolling mean that includes the prediction day, scores higher and is **INVALID**."""

# --------------------------------------------------------------------------------------------------------- E3
E3_MD = r"""### 6.3 E3 - user-level classifier `high_achiever` (replaces K-Means on 437 users)

One row per **user** (437 rows). **Label:** `high_achiever = 1` if the user's goal-achievement rate over *all* their days (share of days with steps >= 8,000) is **above the median** across users.
**Features (9, none step- or distance-based):** age, BMI, height, baseline weight (BMI x height squared, see section 5), average heart rate, average sleep minutes, average active minutes, average stress, average hydration.
**Evaluation:** stratified 5-fold cross-validation (every user is in a test fold exactly once). Inside each training part the hyper-parameters are chosen on an inner validation part (nested), so no test user influences tuning.
Metrics are pooled over the out-of-fold predictions; fold mean and standard deviation are also stored. Models: Random Forest and Logistic Regression against the majority-class baseline.
Two *reference* runs (not claims of skill): the logging window alone, and the raw average `weight_kg`."""

E3_CODE = r"""r3, i3 = results("E3"), info("E3")
SPLIT3 = "stratified 5-fold CV (out-of-fold)"
print(f"users {i3['users']}; high achievers {i3['high_achievers']}; median goal rate {i3['median_rate']:.4f}; features {i3['features']}")
print("settings chosen inside each fold:", i3["chosen_settings_per_fold"])
ut = pd.read_csv(SUP / "predictions" / "E3_user_table.csv")
print("users and high achievers per fold:"); display(ut.groupby("fold").label.agg(users="count", high_achievers="sum").T)
assert not any(("step" in f) or ("distance" in f) for f in i3["features"]), "a step/distance-based feature is present"
print("leakage rule check: no step- or distance-based average among the features -> OK")

cols3 = [ACC, F1W, AUC, BASE]
t3 = wide(r3, SPLIT3, cols3)
print("\nE3 comparison table (pooled out-of-fold predictions):"); display(t3.round(4))
display(wide(r3, SPLIT3, ["Accuracy (mean over folds)", "Accuracy (sd over folds)", "ROC AUC (mean over folds)", "ROC AUC (sd over folds)"]).round(4))
model_bars(t3, ACC, t3[BASE].iloc[0], "E3 out-of-fold accuracy")
print("LEAKAGE test - the user's average steps added (INVALID):"); display(invalid_rows(r3, [ACC, AUC, BASE]).round(4).assign(status="INVALID"))
print("REFERENCE runs (not valid claims of skill):")
display(r3[(r3.status == "REFERENCE") & r3.metric.isin([ACC, AUC])].pivot_table(index="model", columns="metric", values="value").round(4))
validity_chart(r3, SPLIT3, AUC, "E3 ROC-AUC: valid models vs leakage runs")
importance_chart("E3", "Random Forest", n=9)

from scipy.stats import binomtest
n_users = int(i3["users"])
print("\nInterpretation (computed from the tables above)")
for m in t3.index:
    k = round(t3.loc[m, ACC] * n_users)
    p = binomtest(k, n_users, float(t3[BASE].iloc[0]), alternative="greater").pvalue
    print(f"  {m:20s} {k}/{n_users} users classified correctly; majority baseline {t3[BASE].iloc[0]:.4f}; one-sided binomial p = {p:.3f} (p > 0.05 means not distinguishable from the baseline)")"""

E3_NOTE = r"""**Reading E3.** Whether a user is a high achiever is **not predictable from their average profile** in this data: accuracy and ROC-AUC are close to the baseline and to chance, and the difference is not statistically significant.
The reference run that uses only *which months a user logged* scores higher than the real features, which shows that most of the little signal is the logging window (the goal rate is seasonal, section 5), not the person.
Adding the user's average steps raises the score, but that is the label's own ingredient, so it is **INVALID**. A negative result reported with its baseline is a valid supervised result."""

# --------------------------------------------------------------------------------------------------------- E4 / E5
E4_MD = r"""## 7. Activity level and calories: E4 and E5

### 7.1 E4 - user-day activity level (replaces K-Means on user-days)

**Label:** `activity_level = High` if the day's `active_minutes` is **above the median** (the median is taken from the *training users only*), otherwise `Low`.
**Split:** user-held-out 70/15/15 by a hash of `user_id` (no user appears in two sets).
**Excluded because they encode the label:** `active_minutes` (the label), `sedentary_minutes` (= 1440 - sleep - active), `active_ratio`, `active_minutes_roll7_avg` (window includes the day), and `calories_burned`
(calories = MET x weight x duration and the duration *is* `active_minutes`, so calories + weight + activity type + intensity reconstruct the label).
**Features:** heart rates (average, maximum, resting), sleep minutes and quality, stress, hydration, steps, distance, age, BMI, height, baseline weight, and intensity, activity type, gender.
Metrics: accuracy, macro F1, ROC-AUC, confusion matrix and the majority baseline. Models: Random Forest, Gradient-Boosted Trees, Logistic Regression (tuned on the validation users only)."""

E4_CODE = r"""r4, i4 = results("E4"), info("E4")
SPLIT4 = "test (user-held-out)"
print(f"median active_minutes of the training users = {i4['median_active_minutes']}; rows {i4['rows']}; users {i4['users']}; High share {i4['high_share']}")
print("users present in BOTH train and test (must be 0):", i4["users_in_train_and_test"])
cols4 = [ACC, F1M, AUC, BASE]
t4 = wide(r4, SPLIT4, cols4)
print("\nE4 comparison table - TEST users never seen in training:"); display(t4.round(4))
model_bars(t4, ACC, t4[BASE].iloc[0], "E4 user-held-out accuracy")
model_bars(t4, AUC, 0.5, "E4 user-held-out ROC-AUC", baseline_label="chance level")
print("VALIDATION users:"); display(wide(r4, "validation (user-held-out)", cols4).round(4))

cm = pd.read_csv(SUP / "E4_confusion_matrices.csv").set_index("model")
fig, axes = plt.subplots(1, len(cm), figsize=(3.1 * len(cm), 2.9))
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("blues", ["#ffffff", BLUE])
for ax, (name, row) in zip(np.atleast_1d(axes), cm.iterrows()):
    mat = np.array([[row["TN (Low->Low)"], row["FP (Low->High)"]], [row["FN (High->Low)"], row["TP (High->High)"]]])
    ax.imshow(mat, cmap=cmap, vmin=0, vmax=mat.max())
    for (y, x), v in np.ndenumerate(mat):
        ax.text(x, y, f"{int(v):,}", ha="center", va="center", fontsize=9, color="white" if v > 0.6 * mat.max() else INK)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["pred Low", "pred High"], fontsize=8); ax.set_yticks([0, 1]); ax.set_yticklabels(["actual Low", "actual High"], fontsize=8)
    ax.set_title(name, fontsize=9); ax.grid(False)
plt.tight_layout(); plt.show()
display(cm)

print("LEAKAGE tests - calories_burned or sedentary_minutes added (INVALID, they encode the label):")
display(invalid_rows(r4, [ACC, F1M, AUC]).round(4).assign(status="INVALID"))
validity_chart(r4, SPLIT4, AUC, "E4 ROC-AUC: valid models vs leakage runs")
importance_chart("E4", "Random Forest"); importance_chart("E4", "Gradient-Boosted Trees")

print("\nInterpretation (computed from the tables above)")
gains(t4, ACC, t4[BASE].iloc[0], "majority baseline")
lk4 = invalid_rows(r4, [ACC, AUC])
print(f"  ROC-AUC of the valid models: {t4[AUC].min():.3f}-{t4[AUC].max():.3f} (0.5 = chance); with a label-encoding column the accuracy becomes {lk4[ACC].min():.3f}-{lk4[ACC].max():.3f}: INVALID.")"""

E4_NOTE = r"""**Reading E4.** Once the columns that encode the label are removed, the remaining physiological and profile features **do not predict whether a day is a high- or low-activity day** for unseen users:
accuracy is at the baseline and ROC-AUC is near 0.5. The leakage runs are almost perfect only because `sedentary_minutes` and `calories_burned` are *derived from* `active_minutes` in this dataset (section 5), so they are **INVALID**.
This is the honest consequence of the derived-data note: the 'excellent' score was always a formula, not learning."""

E5_MD = r"""### 7.2 E5 - same-day calorie regression (Linear Regression kept; Random Forest and GBT regressors added)

**E5 is kept:** the Linear Regression, its features (steps, distance, active minutes, average and resting heart rate, age, height, **weight_kg**, BMI, gender), its seeded hash split of (user, date) 70/15/15 and its validation-chosen `regParam`
(`models/train_calorie_regression.py`, imported not edited). Added on exactly the same rows and features: a **Random Forest Regressor** and a **GBT Regressor** (depth, iterations tuned on validation RMSE).
Baselines: always predicting the **training mean** (MAE about 334.5 kcal), and a one-feature Linear Regression on `active_minutes`. A chronological check (train before 2024-10-15) is repeated for all models.
`weight_kg` is kept here: it is the true body-weight term of the calorie formula, and the target is the same-day value, so a calendar clock cannot leak the label.
**Derived-data note:** `calories_burned = MET x weight_kg x duration/60` with `duration == active_minutes`, so the target is a *formula of columns that are in the data*; linear models cannot represent the product, tree models can approximate it."""

E5_CODE = r"""r5, i5 = results("E5"), info("E5")
print(f"rows {i5['rows']}; same split as the existing E5 run: {i5['same_split_as_existing_E5']}; settings {i5['settings']}")
print(f"the existing Linear Regression is reproduced: max |difference| to its saved test metrics = {i5['reproduction_max_abs_diff']:.1e}; training mean = {i5['train_mean_kcal']:.2f} kcal")
cols5 = [MAE, RMSE, R2]
t5 = wide(r5, "test", cols5, status=("VALID", "BASELINE"))
print("\nE5 comparison table - TEST set (random hash split):"); display(t5.round(4))
v5 = t5.drop(index=[i for i in t5.index if i.startswith("Baseline")])
model_bars(t5.loc[list(v5.index) + [i for i in t5.index if i.startswith("Baseline")]], MAE, None, "E5 test MAE (kcal, lower is better)", fmt="{:.1f}")
print("Chronological check (train before the cutoff, test on/after it):")
chrono = [s for s in r5.split_type.unique() if s.startswith("chronological")][0]
display(wide(r5, chrono, cols5, status=("VALID", "BASELINE")).round(4))
print("LEAKAGE test - calories_roll7_avg (Silver window includes the day itself) added (INVALID):")
display(invalid_rows(r5, cols5).round(4).assign(status="INVALID"))
print("REFERENCE - activity_type and intensity added (they fix the MET value: formula recovery, not a skill claim):")
display(wide(r5, "test", cols5, status=("REFERENCE",)).round(4))
validity_chart(r5, "test", R2, "E5 R-squared: valid models vs leakage runs")
importance_chart("E5", "Random Forest Regressor"); importance_chart("E5", "GBT Regressor")

print("\nInterpretation (computed from the tables above)")
bm = float(t5.loc["Baseline: training mean", MAE])
for m in v5.index:
    print(f"  {m:26s} MAE {v5.loc[m, MAE]:.1f} kcal = {100 * (1 - v5.loc[m, MAE] / bm):.1f}% lower than the training-mean baseline ({bm:.1f} kcal); R2 {v5.loc[m, R2]:.3f}")"""

E5_NOTE = r"""**Reading E5.** All three models beat the mean-prediction baseline by a wide margin. The tree regressors can approximate the product MET x weight x minutes, which the linear model cannot, so they score better;
that is *formula recovery inside a dataset where calories are computed from other columns*, not evidence that calories can be measured from steps. Adding activity type and intensity (which fix the MET value) is shown only as a reference.
The leakage run adds a rolling mean that includes the day's own calories and is **INVALID**."""

# --------------------------------------------------------------------------------------------------------- 7.3 verification
V_MD = r"""### 7.3 Verification of every experiment

1. **Leakage test:** each experiment was run once with a forbidden / label-encoding feature; those rows are stored with status `INVALID` and are never cited as results.
2. **Baseline comparison:** every score is printed next to the majority-class (or training-mean) baseline.
3. **Unseen-data evaluation:** E1 also user-held-out, E2 chronological, E3 stratified cross-validation, E4 user-held-out, E5 also chronological.
4. **Independent scikit-learn cross-check** (`scripts/sup_sklearn_crosscheck.py`, no Spark): metrics recomputed from the saved predictions, labels and window features rebuilt in pandas, and independent refits.
5. **HDFS rerun:** the same scripts run against the Silver data read from HDFS (section 11.6)."""

V_CODE = r"""HEADLINE = {"E1": ("test", AUC), "E2": ("chronological test", AUC), "E3": ("stratified 5-fold CV (out-of-fold)", AUC),
            "E4": ("test (user-held-out)", AUC), "E5": ("test", R2)}
rows = []
for exp, (split, metric) in HEADLINE.items():
    res = results(exp)
    bad = res[(res.status == "INVALID") & (res.metric == metric)]
    for _, r in bad.iterrows():
        base_model = r.model.split(" + ")[0]
        ok = res[(res.model == base_model) & (res.split_type == split) & (res.metric == metric) & (res.status == "VALID")]
        rows.append({"experiment": exp, "leaky run (INVALID)": r.model.replace(" (LEAKAGE)", ""), "metric": metric,
                     "leaky score": r.value, "same model without the leak": float(ok.value.iloc[0]) if len(ok) else np.nan})
leak = pd.DataFrame(rows).assign(status="INVALID")
leak["inflation"] = leak["leaky score"] - leak["same model without the leak"]
print("Leakage tests: score with a forbidden feature vs the same model without it"); display(leak.round(4))
print("every leakage row has status INVALID:", bool((pd.concat([results(e) for e in HEADLINE]).query("model.str.contains('LEAKAGE')", engine='python').status == "INVALID").all()))

cc = pd.read_csv(SUP / "hdfs_rerun" / "sklearn_crosscheck.csv")
local_vs_hdfs_max = pd.read_csv(SUP / "local_vs_hdfs_comparison.csv")["abs_diff"].max()
print(f"\nCross-check run on the HDFS-rerun outputs ({len(cc)} checks); local results match the HDFS rerun within {local_vs_hdfs_max:.2e} (see local_vs_hdfs_summary.md).")
print(f"Independent scikit-learn cross-check: {int(cc['pass'].sum())}/{len(cc)} checks passed")
display(cc.groupby(["experiment", "kind"])["pass"].agg(checks="count", passed="sum"))
print("largest differences (metric recomputation, tolerance 1e-9 or 2e-3 for ROC-AUC; refits have wider, stated tolerances):")
display(cc.sort_values("abs_diff", ascending=False).head(6)[["experiment", "check", "spark_value", "sklearn_value", "abs_diff", "tolerance", "pass"]].round(6))
assert cc["pass"].all(), "a cross-check failed - see sklearn_crosscheck.csv"
"""

# --------------------------------------------------------------------------------------------------------- sections 9 / 10
FINAL_MD = r"""## 9. Final Results

The consolidated table below is generated from `exports/E1_results.csv` ... `E5_results.csv` (the same files Power BI can import: `experiment_id, model, metric, value, split_type, status`).
Only `VALID` and `BASELINE` rows appear; `INVALID` leakage runs and `REFERENCE` contrast runs are excluded on purpose."""

FINAL_CODE = r"""HEAD = {"E1": ("test", [ACC, F1W, AUC, BASE]), "E2": ("chronological test", [ACC, P1, R1, F11, AUC, BASE]),
        "E3": ("stratified 5-fold CV (out-of-fold)", [ACC, F1W, AUC, BASE]), "E4": ("test (user-held-out)", [ACC, F1M, AUC, BASE])}
frames = []
for exp, (split, cols) in HEAD.items():
    t = wide(results(exp), split, cols).reset_index().assign(experiment=exp, evaluation=split)
    frames.append(t)
final_cls = pd.concat(frames, ignore_index=True)
final_cls = final_cls[["experiment", "model", "evaluation"] + [c for c in final_cls.columns if c not in ("experiment", "model", "evaluation")]]
print("Classification experiments (headline evaluation of each):"); display(final_cls.round(4))
final_reg = wide(results("E5"), "test", [MAE, RMSE, R2], status=("VALID", "BASELINE")).reset_index().assign(experiment="E5", evaluation="test (random hash split)")
print("Regression experiment E5:"); display(final_reg.round(4))
SUP.mkdir(exist_ok=True)
final_cls.to_csv(SUP / "final_metric_table_classification.csv", index=False); final_reg.to_csv(SUP / "final_metric_table_regression.csv", index=False)
print("saved faculty_evidence/supervised/final_metric_table_classification.csv and final_metric_table_regression.csv")"""

INF_MD = r"""## 10. Final Inference"""

INF_CODE = r"""t1_ = wide(results("E1"), "test", [ACC, AUC, BASE]); t2_ = wide(results("E2"), "chronological test", [ACC, AUC, BASE])
t3_ = wide(results("E3"), "stratified 5-fold CV (out-of-fold)", [ACC, AUC, BASE]); t4_ = wide(results("E4"), "test (user-held-out)", [ACC, AUC, BASE])
t5_ = wide(results("E5"), "test", [MAE, R2], status=("VALID", "BASELINE"))
v5_ = t5_[~t5_.index.str.startswith("Baseline")]
rng = lambda s: f"{s.min():.3f}-{s.max():.3f}"
print(f'''1. DATA: {len(silver_pd):,} daily records from {silver_pd.user_id.nunique()} users, processed by Apache Spark (Bronze CSV -> Silver partitioned Parquet).
   Several columns (calories, distance, active/sedentary minutes, max heart rate, sleep quality) are partly derived in this demonstration dataset.

2. E1 same-day goal: accuracy {rng(t1_[ACC])} and ROC-AUC {rng(t1_[AUC])} for Random Forest, Logistic Regression and GBT, against a {t1_[BASE].iloc[0]:.3f} majority baseline.
3. E2 next-day goal (history only, chronological test): accuracy {rng(t2_[ACC])}, ROC-AUC {rng(t2_[AUC])}, against an always-'missed' baseline of {t2_[BASE].iloc[0]:.3f}.
   The signal is weak and the goal rate drifts over the year; a random split would have looked much better and would have been misleading.
4. E3 user-level high_achiever (437 users, 5-fold CV): accuracy {rng(t3_[ACC])}, ROC-AUC {rng(t3_[AUC])}, baseline {t3_[BASE].iloc[0]:.3f}: no reliable skill from profile averages.
5. E4 activity level (unseen users): accuracy {rng(t4_[ACC])}, ROC-AUC {rng(t4_[AUC])}, baseline {t4_[BASE].iloc[0]:.3f}: near chance once the label-encoding columns are removed.
6. E5 calories: MAE {v5_[MAE].min():.1f}-{v5_[MAE].max():.1f} kcal and R2 {rng(v5_[R2])} against MAE {t5_.loc['Baseline: training mean', MAE]:.1f} kcal for always predicting the training mean.

7. EVERY leakage run is marked INVALID, and the scikit-learn cross-check passed {int(cc['pass'].sum())}/{len(cc)} checks.''')"""

LIM_MD = r"""**Limitations (stated honestly):**
* The data is a public Kaggle dataset. `calories_burned`, `distance_km`, `active_minutes`, `sedentary_minutes`, `max_heart_rate` and `sleep_quality_score` are **partly derived** (section 5); scores on them can be formula recovery.
* In this synthetic data `weight_kg` drifts almost linearly with the calendar inside each user and the goal rate is seasonal. E1 and E5 keep `weight_kg` as specified; E2 and E3 use a baseline weight instead; E1's top feature may therefore be a calendar clock (no ablation was run).
* E2's chronological blocks differ strongly in goal rate (train / validation / test), so accuracy must be read against the test-block baseline and ROC-AUC is the fairer summary.
* E3 has only 437 users, so its accuracy has a standard error of about 2.4 percentage points; E3 and E4 are best read as 'no reliable skill', not as small positive results.
* Spark runs in local mode. HDFS is a single-node deployment (replication 1, section 11); the local run and the HDFS rerun are compared in 11.6.
* The legacy Streamlit dashboard still contains an unsupervised Isolation Forest (heart-rate anomaly flagging, `models/train_anomaly_detection.py`). It is not one of E1-E5 and was not changed.
* Power BI and the web page were built from the earlier experiments and have not been rewired to the supervised `exports/E<n>_results.csv` files."""

# --------------------------------------------------------------------------------------------------------- patched cells
C41_CODE = r"""# Feature sets of the SUPERVISED experiments E1-E5 (read from the experiment scripts themselves, so they cannot drift apart)
import sys, importlib
sys.path.insert(0, str(PROJECT_ROOT / "models"))
e1m = importlib.import_module("spark_report_classification")
e2m = importlib.import_module("sup_e2_goal_next_day")
e3m = importlib.import_module("sup_e3_user_high_achiever")
e4m = importlib.import_module("sup_e4_activity_level")
e5m = importlib.import_module("train_calorie_regression")

feature_set = pd.DataFrame(
    [("E1 same-day goal", f, "numeric") for f in e1m.NUM] + [("E1 same-day goal", f, "categorical") for f in e1m.CAT] + [("E1 same-day goal", "label (steps >= 8000)", "TARGET")]
    + [("E2 next-day goal", f, "numeric (history before day t / calendar / profile)") for f in e2m.NUM] + [("E2 next-day goal", f, "categorical") for f in e2m.CAT] + [("E2 next-day goal", "label (steps(t) >= 8000)", "TARGET")]
    + [("E3 high_achiever", f, "numeric (per-user average)") for f in e3m.FEATURES] + [("E3 high_achiever", "high_achiever (goal rate > median user)", "TARGET")]
    + [("E4 activity level", f, "numeric") for f in e4m.NUM] + [("E4 activity level", f, "categorical") for f in e4m.CAT] + [("E4 activity level", "label (active_minutes > median)", "TARGET")]
    + [("E5 calories", f, "numeric") for f in e5m.NUM] + [("E5 calories", f, "categorical") for f in e5m.CAT] + [("E5 calories", e5m.TARGET, "TARGET")],
    columns=["Experiment", "Column", "Role"])
(EVIDENCE / "supervised").mkdir(exist_ok=True)
feature_set.to_csv(EVIDENCE / "supervised" / "final_feature_set_E1_E5.csv", index=False)
display(feature_set.groupby("Experiment").Role.value_counts().unstack(fill_value=0))
display(feature_set)"""

C105_CODE = r"""# Spark MLlib stages of the supervised experiments (pipelines are built, not fitted, here)
import sys
sys.path.insert(0, str(PROJECT_ROOT / "models"))
import sup_common as S
from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
from pyspark.ml.regression import GBTRegressor, LinearRegression, RandomForestRegressor
examples = {
    "E1-E4 Random Forest classifier": S.make_pipeline(["x"], ["c"], RandomForestClassifier()),
    "E1-E4 Gradient-Boosted Trees classifier": S.make_pipeline(["x"], ["c"], GBTClassifier()),
    "E1-E4 Logistic Regression (one-hot + scaled)": S.make_pipeline(["x"], ["c"], LogisticRegression(), onehot=True, scale=True),
    "E5 Linear Regression (one-hot + scaled)": S.make_pipeline(["x"], ["c"], LinearRegression(), onehot=True, scale=True),
    "E5 Random Forest / GBT regressors": S.make_pipeline(["x"], ["c"], RandomForestRegressor()),
}
mllib_stages = pd.DataFrame([(name, type(s).__name__) for name, p in examples.items() for s in p.getStages()],
                            columns=["Supervised model pipeline", "Spark MLlib stage"])
print("Spark MLlib components used by the supervised experiments:")
display(mllib_stages)"""

C123_CODE = r"""# 11.6 The SUPERVISED experiments re-run on the Silver data READ FROM HDFS (run_supervised.ps1 -Storage hdfs; results saved separately)
hd = EVIDENCE / "supervised" / "hdfs_rerun"
if (hd / "exports" / "E1_results.csv").exists():
    rows = []
    for exp in ("E1", "E2", "E3", "E4", "E5"):
        a, b = pd.read_csv(EXPORTS / f"{exp}_results.csv"), pd.read_csv(hd / "exports" / f"{exp}_results.csv")
        j = a.merge(b, on=["experiment_id", "model", "metric", "split_type", "status"], suffixes=("_local", "_hdfs"), how="outer", indicator=True)
        both = j[j._merge == "both"]
        d = (both.value_local - both.value_hdfs).abs()
        rows.append({"experiment": exp, "rows compared": len(both), "only in one run": int((j._merge != "both").sum()),
                     "max |local - HDFS|": d.max(), "rows differing by more than 1e-6": int((d > 1e-6).sum())})
    cmp_ = pd.DataFrame(rows)
    display(cmp_)
    for exp in ("E1", "E2", "E3", "E4", "E5"):
        ri = json.loads((hd / f"{exp}_run_info.json").read_text(encoding="utf-8"))
        print(f"{exp}: storage mode used = {ri['storage_mode'].upper()}  |  Silver source = {ri['silver_source']}")
    cc_h = pd.read_csv(hd / "sklearn_crosscheck.csv") if (hd / "sklearn_crosscheck.csv").exists() else None
    if cc_h is not None:
        print(f"scikit-learn cross-check on the HDFS rerun: {int(cc_h['pass'].sum())}/{len(cc_h)} passed")
else:
    print("NOT VERIFIED - run .\\run_fitpulse_hdfs.ps1 -SkipEtl and then .\\run_supervised.ps1 -Experiment All -Storage hdfs first")"""

C125_PARA = ("**About the HDFS rerun in 11.6:** it re-executes E1-E5 with the Silver dataset read from HDFS (`run_supervised.ps1 -Storage hdfs`; it never falls back to local files) and compares every result row "
             "with the local run. Differences larger than floating-point noise would be listed in the table; ROC-AUC can differ in the last digits because Spark's reading order, and therefore its floating-point accumulation order, may differ "
             "(probable cause, not proven by a separate experiment). Also note: the scratch files written by this notebook's Spark session carry replication 3 (the kernel does not load `hadoop-conf`), whereas the ETL writes replication 1; the scratch directory was deleted.")

C137_CODE = r"""mm = pd.read_csv(EVIDENCE / "model_metrics.csv")
print("faculty_evidence/model_metrics.csv holds the PREVIOUS (pre-supervised) experiments; rows:", len(mm))
display(mm[mm.metric.isin(["Accuracy", "ROC AUC", "ROC-AUC", "F1 (goal-achieved class)", "MAE (kcal)", "RMSE (kcal)", "R2"])]
        .drop(columns=["source_file"]).round(4).reset_index(drop=True))
print("\nThe SUPERVISED results are exports/E1_results.csv ... E5_results.csv (sections 5-7). Known limits: Power BI and the web page have not been rewired to them; "
      "the legacy Streamlit app's classifier is Logistic Regression (ROC-AUC 0.755 from models/metrics_report.md, an earlier training run that was not repeated); HDFS is single node; Power BI imports CSV and does not read HDFS.")"""

C135_APPEND = ("\n\n**Status after the supervised conversion:** the Power BI file and the web page were built from the earlier experiments and still show the previous E3/E4 K-Means views, which read "
               "output files that were deliberately left in place (`faculty_evidence/report_aligned/kmeans_*`, `models/artifacts/kmeans_user_segments_model.json`; the scripts that made them are in `archive/kmeans/`). "
               "They have not been rewired to the supervised `exports/E<n>_results.csv` files, which already use the Power BI long format (experiment id, model, metric, value, split type, status).")
