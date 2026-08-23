"""
FitPulse Dashboard — Online Inference Layer
==============================================
Loads pre-trained models (models/artifacts/*.joblib) and queries SQLite for
one user's rows at a time (never the full training dataset) to render
personalized fitness insights. See README.md for the offline/online split.
"""

import sqlite3
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.recommendation_engine import recommend
from auth import register_user, authenticate
from theme import SERIES, STATUS, ordinal
import reports as report_builder

DB_PATH = "dashboard/fitpulse.db"
ARTIFACTS = "models/artifacts"

st.set_page_config(page_title="FitPulse", page_icon=":material/directions_run:", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 2.2rem; max-width: 1100px; }
    .fp-card {
        background: #FFFFFF; border-radius: 10px; padding: 20px 22px;
        border: 1px solid #E4E2DC; margin-bottom: 10px;
    }
    .fp-card h3 { margin: 0 0 6px 0; font-size: 0.8rem; color: #6B6A66; font-weight: 500; letter-spacing: 0.01em; }
    .fp-card .fp-value { font-size: 1.9rem; font-weight: 650; margin: 0; color: #1C1C1A; }
    .fp-card .fp-sub { font-size: 0.82rem; color: #8A8880; margin-top: 2px; }
    .fp-badge {
        display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 8px;
        font-weight: 600; font-size: 0.95rem; color: white; margin-bottom: 6px;
    }
    .fp-insight {
        font-size: 0.88rem; color: #5B5A55; border-left: 3px solid #E4E2DC;
        padding: 4px 0 4px 12px; margin: 6px 0 18px 0;
    }
    .rec-card {
        background: #FFFFFF; border: 1px solid #E4E2DC; border-radius: 10px;
        padding: 22px 24px; margin-bottom: 16px;
    }
    .rec-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .rec-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
    .rec-topic { font-size: 1.05rem; font-weight: 650; color: #1C1C1A; }
    .rec-metric { margin-left: auto; font-size: 0.85rem; color: #8A8880; }
    .rec-what { font-size: 0.98rem; color: #1C1C1A; margin: 2px 0 14px 0; font-weight: 500; }
    .rec-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #8A8880; margin: 10px 0 2px 0; }
    .rec-text { font-size: 0.88rem; color: #4A4944; line-height: 1.5; margin: 0; }
    .fp-alert { border-radius: 10px; padding: 16px 20px; margin-bottom: 14px; font-size: 0.92rem; border: 1px solid; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_user_data(user_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM user_daily_metrics WHERE user_id = ? ORDER BY date", conn, params=(int(user_id),)
    )
    df["date"] = pd.to_datetime(df["date"])
    month_num = df["date"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * month_num / 12)
    df["month_cos"] = np.cos(2 * np.pi * month_num / 12)
    return df


def load_user_percentile(user_id: int):
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM population_percentiles WHERE user_id = ?", conn, params=(int(user_id),))
    return df.iloc[0] if len(df) else None


def load_user_profile(user_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT age, gender, height_cm, weight_kg FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return {"age": row[0], "gender": row[1], "height_cm": row[2], "weight_kg": row[3]}


def load_user_raw(user_id: int) -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql(
        "SELECT * FROM user_daily_raw WHERE user_id = ? ORDER BY date", conn, params=(int(user_id),)
    )


def upsert_raw_rows(rows_df: pd.DataFrame):
    conn = get_conn()
    cols = ["user_id", "date", "steps", "calories_burned", "distance_km", "active_minutes",
            "sedentary_minutes", "resting_heart_rate", "avg_heart_rate", "max_heart_rate",
            "sleep_minutes", "sleep_quality_score", "activity_type", "intensity",
            "stress_level", "hydration_level"]
    rows_df = rows_df.copy()
    rows_df["date"] = pd.to_datetime(rows_df["date"]).dt.strftime("%Y-%m-%d")
    for col in cols:
        if col not in rows_df.columns:
            rows_df[col] = None
    conn.executemany(
        f"INSERT OR REPLACE INTO user_daily_raw ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        rows_df[cols].itertuples(index=False, name=None),
    )
    conn.commit()


def load_population_percentiles_for_cohort(age_group: str, gender: str) -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql(
        "SELECT * FROM population_percentiles WHERE age_group = ? AND gender = ?",
        conn, params=(age_group, gender),
    )


@st.cache_resource(show_spinner=False)
def load_models():
    # Note: anomaly_models_per_user.joblib (one Isolation Forest per training
    # user, ~900MB combined) is intentionally NOT loaded here. Fitting a
    # fresh Isolation Forest on one user's ~230 rows takes milliseconds, so
    # for the deployed app every user gets one fit on the fly (see the
    # Health Alerts tab) instead of shipping a near-gigabyte artifact that
    # would blow past GitHub's 100MB file limit and free-hosting resource
    # limits for no real benefit. The offline training/evaluation of that
    # artifact (models/train_anomaly_detection.py, metrics_report.md) is
    # still the source of truth for Model 4's reported accuracy.
    return {
        "goal_model": joblib.load(f"{ARTIFACTS}/goal_achievement_model.joblib"),
        "goal_features": joblib.load(f"{ARTIFACTS}/goal_achievement_features.joblib"),
        "forecast_model": joblib.load(f"{ARTIFACTS}/forecast_model.joblib"),
        "sleep_model": joblib.load(f"{ARTIFACTS}/sleep_quality_model.joblib"),
        "sleep_features": joblib.load(f"{ARTIFACTS}/sleep_quality_features.joblib"),
    }


def engineer_features_pandas(df: pd.DataFrame, profile: dict) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["age"] = profile["age"]
    df["gender"] = profile["gender"]
    df["height_cm"] = profile["height_cm"]
    df["weight_kg"] = profile["weight_kg"]
    df["bmi"] = profile["weight_kg"] / (profile["height_cm"] / 100) ** 2
    df["day_of_week"] = df["date"].dt.day_name()
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["month_sin"] = np.sin(2 * np.pi * df["date"].dt.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["date"].dt.month / 12)
    df["is_rest_day"] = (df["active_minutes"] < 15).astype(int)

    df["steps_lag1"] = df["steps"].shift(1)
    df["steps_lag2"] = df["steps"].shift(2)
    df["steps_lag7"] = df["steps"].shift(7)
    df["calories_lag1"] = df["calories_burned"].shift(1)
    df["steps_roll7_avg"] = df["steps"].rolling(7, min_periods=1).mean()
    df["calories_roll7_avg"] = df["calories_burned"].rolling(7, min_periods=1).mean()
    df["active_minutes_roll7_avg"] = df["active_minutes"].rolling(7, min_periods=1).mean()
    df["resting_hr_roll7_avg"] = df["resting_heart_rate"].rolling(7, min_periods=1).mean()

    df["daily_step_goal"] = round(df["steps"].mean() * 1.10, -2)
    df["daily_calorie_goal"] = round(df["calories_burned"].mean() * 1.10, -1)
    df["goal_achieved"] = (df["steps"] >= df["daily_step_goal"]).astype(int)
    return df


def status_color(pct_to_goal: float) -> str:
    if pct_to_goal >= 1.0:
        return STATUS["good"]
    if pct_to_goal >= 0.7:
        return STATUS["warning"]
    return STATUS["critical"]


def stat_card(col, label, value, sub, color=None):
    color_style = f"border-left: 3px solid {color};" if color else ""
    col.markdown(
        f"""<div class="fp-card" style="{color_style}">
                <h3>{label}</h3>
                <p class="fp-value">{value}</p>
                <p class="fp-sub">{sub}</p>
            </div>""",
        unsafe_allow_html=True,
    )


def insight(text: str):
    st.markdown(f'<p class="fp-insight">{text}</p>', unsafe_allow_html=True)


def base_layout(fig, y_title=""):
    fig.update_layout(
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", font_color="#1C1C1A",
        margin=dict(l=10, r=10, t=10, b=10), hoverlabel=dict(bgcolor="#1C1C1A", font_color="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E4E2DC")
    fig.update_yaxes(showgrid=True, gridcolor="#F0EFEA", title=y_title, zeroline=False)
    return fig


def recursive_forecast_steps(model, history: pd.DataFrame, horizon: int = 7) -> list:
    hist = history.copy().reset_index(drop=True)
    preds = []
    for _ in range(horizon):
        last = hist.iloc[-1]
        next_date = pd.to_datetime(last["date"]) + pd.Timedelta(days=1)
        row = {
            "steps_lag1": last["steps"],
            "steps_lag2": hist.iloc[-2]["steps"] if len(hist) >= 2 else last["steps"],
            "steps_lag7": hist.iloc[-7]["steps"] if len(hist) >= 7 else last["steps"],
            "steps_roll7_avg": hist["steps"].tail(7).mean(),
            "active_minutes_roll7_avg": hist["active_minutes"].tail(7).mean(),
            "resting_hr_roll7_avg": hist["resting_heart_rate"].tail(7).mean(),
            "month_sin": np.sin(2 * np.pi * next_date.month / 12),
            "month_cos": np.cos(2 * np.pi * next_date.month / 12),
        }
        pred = float(model.predict(pd.DataFrame([row]))[0])
        preds.append((next_date, pred))
        new_row = last.copy()
        new_row["date"], new_row["steps"] = next_date, pred
        hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)
    return preds


ACTIVITY_TYPES = ["Walking", "Running", "Cycling", "Swimming", "Yoga",
                   "Weight Training", "HIIT", "Dancing", "Basketball", "Tennis"]


def manual_day_form(key_prefix: str, profile: dict, user_id: int):
    with st.form(f"{key_prefix}_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            date = st.date_input("Date", key=f"{key_prefix}_date")
            steps = st.number_input("Steps", 0, 60000, 6000, key=f"{key_prefix}_steps")
            activity = st.selectbox("Activity", ACTIVITY_TYPES, key=f"{key_prefix}_activity")
        with c2:
            active_min = st.number_input("Active minutes", 0, 300, 30, key=f"{key_prefix}_active")
            intensity = st.selectbox("Intensity", ["Low", "Medium", "High"], key=f"{key_prefix}_intensity")
            calories = st.number_input("Calories burned", 0.0, 3000.0, 250.0, key=f"{key_prefix}_cal")
        with c3:
            avg_hr = st.number_input("Avg heart rate", 50, 220, 110, key=f"{key_prefix}_avghr")
            resting_hr = st.number_input("Resting heart rate", 40, 120, 68, key=f"{key_prefix}_resthr")
            sleep_h = st.number_input("Hours slept", 0.0, 14.0, 7.0, key=f"{key_prefix}_sleep")
        stress = st.slider("Stress level", 1, 10, 5, key=f"{key_prefix}_stress")
        hydration = st.number_input("Water intake (L)", 0.0, 6.0, 2.0, key=f"{key_prefix}_hydration")
        submitted = st.form_submit_button("Save")

    if submitted:
        stride_m = profile["height_cm"] / 100 * 0.45
        sleep_quality = max(0, min(100, 100 - abs(sleep_h - 8) * 9 - stress * 3.2 - max(0, resting_hr - 60) * 0.6))
        row = pd.DataFrame([{
            "user_id": user_id, "date": date, "steps": steps, "calories_burned": calories,
            "distance_km": round(steps * stride_m / 1000, 2), "active_minutes": active_min,
            "sedentary_minutes": max(0, 1440 - int(sleep_h * 60) - active_min),
            "resting_heart_rate": resting_hr, "avg_heart_rate": avg_hr,
            "max_heart_rate": min(220 - profile["age"], avg_hr + 15),
            "sleep_minutes": int(sleep_h * 60), "sleep_quality_score": round(sleep_quality, 1),
            "activity_type": activity, "intensity": intensity,
            "stress_level": stress, "hydration_level": hydration,
        }])
        upsert_raw_rows(row)
        st.rerun()


# ---------------------------------------------------------------------------
# Pre-warm the trained models BEFORE rendering anything else. These are
# cached process-wide (st.cache_resource), so this only actually does work
# once per server process — the very first page load after a restart — and
# is instant on every login/rerun after that. Doing it here (ahead of the
# login form) means a user never sees a loading state appear *between*
# clicking "Log in" and reaching the dashboard.
# ---------------------------------------------------------------------------
with st.spinner("Starting FitPulse…"):
    models = load_models()

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None:
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown("## FitPulse")
        st.caption("Track your activity, sleep, and progress.")
        tab_login, tab_register = st.tabs(["Log in", "Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", width="stretch")
            if submitted:
                user, error = authenticate(get_conn(), username, password)
                if error:
                    st.error(error)
                else:
                    st.session_state.auth_user = user
                    st.rerun()

        with tab_register:
            with st.form("register_form"):
                r_username = st.text_input("Username")
                r_password = st.text_input("Password", type="password")
                c1, c2 = st.columns(2)
                r_age = c1.number_input("Age", 13, 100, 30)
                r_gender = c2.selectbox("Gender", ["F", "M", "Other"])
                c3, c4 = st.columns(2)
                r_height = c3.number_input("Height (cm)", 120.0, 220.0, 170.0)
                r_weight = c4.number_input("Weight (kg)", 30.0, 200.0, 70.0)
                r_submitted = st.form_submit_button("Create account", width="stretch")
            if r_submitted:
                new_id, error = register_user(get_conn(), r_username, r_password, r_age, r_gender, r_height, r_weight)
                if error:
                    st.error(error)
                else:
                    st.success("Account created — log in on the other tab.")
    st.stop()

auth = st.session_state.auth_user
user_id, is_demo = auth["user_id"], auth["is_demo"]

header_left, header_right = st.columns([6, 1])
with header_left:
    st.markdown(f"## FitPulse")
with header_right:
    st.write("")
    if st.button("Log out", width="stretch"):
        st.session_state.auth_user = None
        st.rerun()

# ---------------------------------------------------------------------------
# Load this user's data
# ---------------------------------------------------------------------------
if is_demo:
    user_df = load_user_data(user_id)
    percentile_row = load_user_percentile(user_id)
else:
    profile = load_user_profile(user_id)
    raw_df = load_user_raw(user_id)

    if len(raw_df) == 0:
        st.info("No activity data yet — upload a file or log your first day to get started.")
        onboard_upload, onboard_manual = st.tabs(["Upload a file", "Log a day"])
        with onboard_upload:
            st.caption(
                "CSV columns: date, steps, calories_burned, distance_km, active_minutes, "
                "sedentary_minutes, resting_heart_rate, avg_heart_rate, max_heart_rate, "
                "sleep_minutes, sleep_quality_score, activity_type, intensity, stress_level, hydration_level."
            )
            up = st.file_uploader("Choose a file", type="csv", label_visibility="collapsed")
            if up is not None:
                new_rows = pd.read_csv(up)
                new_rows["user_id"] = user_id
                upsert_raw_rows(new_rows)
                st.rerun()
        with onboard_manual:
            manual_day_form("onboard", profile, user_id)
        st.stop()

    user_df = engineer_features_pandas(raw_df, profile)
    percentile_row = None

    with st.expander("Add another day"):
        add_upload, add_manual = st.tabs(["Upload a file", "Log a day"])
        with add_upload:
            up2 = st.file_uploader("Choose a file", type="csv", key="add_upload", label_visibility="collapsed")
            if up2 is not None:
                new_rows = pd.read_csv(up2)
                new_rows["user_id"] = user_id
                upsert_raw_rows(new_rows)
                st.rerun()
        with add_manual:
            manual_day_form("add", profile, user_id)

if len(user_df) < 8:
    st.info(f"{len(user_df)} day(s) logged — add a few more to unlock your insights.")
    st.stop()

today = user_df.iloc[-1]
history = user_df.iloc[:-1]

st.caption(f"{today['date'].strftime('%B %-d, %Y') if hasattr(today['date'],'strftime') else today['date']} · {len(user_df)} days on file")

tab_today, tab_trends, tab_sleep, tab_alerts, tab_reco, tab_bench, tab_reports = st.tabs([
    ":material/today: Today", ":material/show_chart: Trends & Forecast", ":material/bedtime: Sleep",
    ":material/monitor_heart: Health Alerts", ":material/checklist: Recommendations", ":material/leaderboard: Benchmarks",
    ":material/picture_as_pdf: Reports",
])

# ---------------------------------------------------------------------------
# TODAY
# ---------------------------------------------------------------------------
with tab_today:
    step_pct = today["steps"] / today["daily_step_goal"] if today["daily_step_goal"] else 0
    cal_pct = today["calories_burned"] / today["daily_calorie_goal"] if today["daily_calorie_goal"] else 0

    c1, c2, c3, c4 = st.columns(4)
    stat_card(c1, "Steps", f"{int(today['steps']):,}", f"Goal {int(today['daily_step_goal']):,}", status_color(step_pct))
    stat_card(c2, "Calories", f"{today['calories_burned']:.0f}", f"Goal {today['daily_calorie_goal']:.0f} kcal", status_color(cal_pct))
    stat_card(c3, "Heart Rate", f"{int(today['avg_heart_rate'])} bpm", f"Resting {today['resting_heart_rate']:.0f} bpm")
    stat_card(c4, "Sleep", f"{today['sleep_minutes']/60:.1f} hrs", f"Quality {today['sleep_quality_score']:.0f}/100")

    st.write("")
    feat_cols = models["goal_features"]
    row_df = pd.DataFrame([{k: today.get(k) for k in feat_cols}])
    if row_df.isnull().any(axis=1).iloc[0]:
        st.info("Add a bit more history to unlock tomorrow's outlook.")
    else:
        # This is a forward-looking prediction — it never looks at today's own
        # step count (that would be circular), only the rolling pattern
        # leading up to today. It can disagree with today's actual result
        # shown above; that's expected, not a bug (e.g. one strong day
        # doesn't guarantee the next one will match it).
        proba = models["goal_model"].predict_proba(row_df)[0][1]
        if proba >= 0.5:
            st.markdown(
                f'<span class="fp-badge" style="background:{STATUS["good"]}">'
                f"{proba*100:.0f}% likely to hit tomorrow's step goal</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<span class="fp-badge" style="background:{STATUS["critical"]}">'
                f"Only {proba*100:.0f}% likely to hit tomorrow's step goal</span>",
                unsafe_allow_html=True,
            )
        insight("Based on your activity and recovery pattern through today — not on today's step count itself.")

    gap = today["daily_step_goal"] - today["steps"]
    if gap > 0:
        insight(f"Today: {int(gap):,} steps short of the goal — see Recommendations for a concrete plan.")
    else:
        insight("Today: goal already met.")

# ---------------------------------------------------------------------------
# TRENDS & FORECAST
# ---------------------------------------------------------------------------
with tab_trends:
    st.markdown("#### Steps — last 14 days and next 7-day forecast")
    recent = user_df.tail(14)
    forecast = recursive_forecast_steps(models["forecast_model"], user_df, horizon=7)
    fc_dates = [d for d, _ in forecast]
    fc_values = [v for _, v in forecast]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=recent["date"], y=recent["steps"], mode="lines+markers", name="Actual steps",
        line=dict(color=SERIES["primary"], width=2),
        hovertemplate="%{x|%b %d}<br>%{y:,.0f} steps<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[recent["date"].iloc[-1]] + fc_dates, y=[recent["steps"].iloc[-1]] + fc_values,
        mode="lines+markers", name="Forecasted steps",
        line=dict(color=SERIES["amber"], width=2, dash="dash"),
        hovertemplate="%{x|%b %d}<br>Forecast: %{y:,.0f} steps<extra></extra>",
    ))
    fig.add_hline(y=today["daily_step_goal"], line_dash="dot", line_color="#B0AEA6",
                  annotation_text="Daily goal", annotation_font_color="#8A8880")
    fig = base_layout(fig, "Steps")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig, width="stretch")

    recent_avg, forecast_avg = recent["steps"].tail(7).mean(), np.mean(fc_values)
    direction = "higher" if forecast_avg > recent_avg * 1.05 else "lower" if forecast_avg < recent_avg * 0.95 else "similar"
    insight(f"Your forecasted pace for next week is {direction} than your last 7 days "
            f"({forecast_avg:,.0f} vs {recent_avg:,.0f} steps/day on average).")

# ---------------------------------------------------------------------------
# SLEEP
# ---------------------------------------------------------------------------
with tab_sleep:
    sleep_feat_cols = models["sleep_features"]
    row_df = pd.DataFrame([{k: today.get(k) for k in sleep_feat_cols}])
    predicted_quality = models["sleep_model"].predict(row_df)[0]

    c1, c2 = st.columns(2)
    c1.metric("Tonight's predicted quality", f"{predicted_quality:.0f}/100")
    c2.metric("7-day average", f"{user_df['sleep_quality_score'].tail(7).mean():.0f}/100")

    st.write("")
    st.markdown("#### Stress vs. sleep quality")
    fig = go.Figure(go.Scatter(
        x=user_df["stress_level"], y=user_df["sleep_quality_score"], mode="markers",
        marker=dict(color=SERIES["teal"], size=8, opacity=0.7),
        hovertemplate="Stress: %{x}/10<br>Sleep quality: %{y:.0f}/100<extra></extra>",
    ))
    fig = base_layout(fig, "Sleep quality (0-100)")
    fig.update_xaxes(title="Stress level (1-10)")
    st.plotly_chart(fig, width="stretch")
    corr1 = user_df["stress_level"].corr(user_df["sleep_quality_score"])
    insight(f"Your higher-stress days tend to have {'noticeably' if abs(corr1) > 0.4 else 'somewhat'} lower "
            f"sleep quality (correlation {corr1:.2f}).")

    st.markdown("#### Sitting time vs. sleep quality")
    fig2 = go.Figure(go.Scatter(
        x=user_df["sedentary_minutes"], y=user_df["sleep_quality_score"], mode="markers",
        marker=dict(color=SERIES["rose"], size=8, opacity=0.7),
        hovertemplate="Sedentary: %{x:.0f} min<br>Sleep quality: %{y:.0f}/100<extra></extra>",
    ))
    fig2 = base_layout(fig2, "Sleep quality (0-100)")
    fig2.update_xaxes(title="Sedentary minutes")
    st.plotly_chart(fig2, width="stretch")
    corr2 = user_df["sedentary_minutes"].corr(user_df["sleep_quality_score"])
    insight(f"More sedentary time is associated with {'lower' if corr2 < 0 else 'higher'} sleep quality in your "
            f"data (correlation {corr2:.2f}) — across all users, stress and sitting time are the two strongest drivers.")

# ---------------------------------------------------------------------------
# HEALTH ALERTS
# ---------------------------------------------------------------------------
with tab_alerts:
    hr_cols = ["resting_heart_rate", "avg_heart_rate", "max_heart_rate"]

    # Fit an Isolation Forest on this user's own heart-rate history — same
    # algorithm/hyperparameters used offline in models/train_anomaly_detection.py,
    # just fit on demand (a few hundred rows fits in milliseconds).
    from sklearn.ensemble import IsolationForest
    iso_model = IsolationForest(contamination=0.03, random_state=42, n_estimators=150)
    iso_model.fit(user_df[hr_cols])

    today_flag = iso_model.predict(pd.DataFrame([today[hr_cols]]))[0]

    if today_flag == -1:
        st.markdown(
            f'<div class="fp-alert" style="background:{STATUS["warning"]}14; border-color:{STATUS["warning"]}55; color:#7A5010">'
            f'Worth a look: today\'s heart rate pattern (resting {today["resting_heart_rate"]:.0f}, '
            f'average {today["avg_heart_rate"]:.0f}, peak {today["max_heart_rate"]:.0f} bpm) is unusual for you. '
            f'This is not a medical diagnosis, just a statistical flag.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="fp-alert" style="background:{STATUS["good"]}14; border-color:{STATUS["good"]}55; color:#155C36">'
            f'Today\'s heart rate pattern is consistent with your normal baseline.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Heart rate — last 30 days")
    plot_df = user_df.tail(30)
    fig = go.Figure()
    labels = {"resting_heart_rate": "Resting", "avg_heart_rate": "Average", "max_heart_rate": "Peak"}
    colors = [SERIES["slate"], SERIES["primary"], SERIES["rose"]]
    for col, color in zip(hr_cols, colors):
        fig.add_trace(go.Scatter(
            x=plot_df["date"], y=plot_df[col], name=labels[col], line=dict(color=color, width=2),
            hovertemplate=f"%{{x|%b %d}}<br>{labels[col]}: %{{y:.0f}} bpm<extra></extra>",
        ))
    fig = base_layout(fig, "Heart rate (bpm)")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig, width="stretch")
    insight("Flags are based on how far a day's heart rate sits from your own recent baseline, "
            "not a fixed medical threshold.")

# ---------------------------------------------------------------------------
# RECOMMENDATIONS
# ---------------------------------------------------------------------------
with tab_reco:
    recent_sleep_avg = user_df["sleep_quality_score"].tail(7).mean()
    sections = recommend(today.to_dict(), history, recent_sleep_avg)

    for s in sections:
        dot_color = STATUS["good"] if s["status"] == "on_track" else STATUS["warning"]
        st.markdown(
            f"""<div class="rec-card">
                    <div class="rec-header">
                        <span class="rec-dot" style="background:{dot_color}"></span>
                        <span class="rec-topic">{s['topic']}</span>
                        <span class="rec-metric">{s['metric']}</span>
                    </div>
                    <p class="rec-what">{s['what']}</p>
                    <p class="rec-label">Why</p><p class="rec-text">{s['why']}</p>
                    <p class="rec-label">How</p><p class="rec-text">{s['how']}</p>
                </div>""",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# BENCHMARKS
# ---------------------------------------------------------------------------
with tab_bench:
    if percentile_row is not None:
        steps_pctl = percentile_row["steps_percentile"]
        cal_pctl = percentile_row["calories_percentile"]
        sleep_pctl = percentile_row["sleep_quality_percentile"]
        cohort_desc = f"people aged {percentile_row['age_group']}, gender {percentile_row['gender']}"
    else:
        age_group = "18-24" if today["age"] < 25 else "25-34" if today["age"] < 35 else "35-44" if today["age"] < 45 else "45-54" if today["age"] < 55 else "55-64"
        cohort = load_population_percentiles_for_cohort(age_group, today["gender"])
        steps_pctl = (cohort["avg_steps"] < user_df["steps"].mean()).mean() * 100 if len(cohort) else 50.0
        cal_pctl = (cohort["avg_calories_burned"] < user_df["calories_burned"].mean()).mean() * 100 if len(cohort) else 50.0
        sleep_pctl = (cohort["avg_sleep_quality"] < user_df["sleep_quality_score"].mean()).mean() * 100 if len(cohort) else 50.0
        cohort_desc = f"people aged {age_group}, gender {today['gender']}"

    c1, c2, c3 = st.columns(3)
    stat_card(c1, "Steps", f"{ordinal(steps_pctl)} percentile", f"vs. {cohort_desc}")
    stat_card(c2, "Calories", f"{ordinal(cal_pctl)} percentile", f"vs. {cohort_desc}")
    stat_card(c3, "Sleep Quality", f"{ordinal(sleep_pctl)} percentile", f"vs. {cohort_desc}")

    st.write("")
    fig = go.Figure(go.Bar(
        x=["Steps", "Calories", "Sleep Quality"], y=[steps_pctl, cal_pctl, sleep_pctl],
        marker_color=[SERIES["primary"], SERIES["amber"], SERIES["teal"]],
        hovertemplate="%{x}: %{y:.0f}th percentile<extra></extra>",
    ))
    fig = base_layout(fig, "Percentile")
    fig.update_yaxes(range=[0, 100])
    st.plotly_chart(fig, width="stretch")

    strongest = max([("steps", steps_pctl), ("calories burned", cal_pctl), ("sleep quality", sleep_pctl)], key=lambda x: x[1])
    insight(f"Your strongest relative area is {strongest[0]}, in the {ordinal(strongest[1])} percentile among {cohort_desc}.")

# ---------------------------------------------------------------------------
# REPORTS — downloadable PDF summaries
# ---------------------------------------------------------------------------
with tab_reports:
    st.caption("Generate a report from your data (last 30 days) to download or share.")

    report_options = {
        "Sleep Report": lambda: report_builder.build_sleep_report(user_df, auth["username"]),
        "Activity Report": lambda: report_builder.build_activity_report(user_df, auth["username"]),
        "Body Functions Report": lambda: report_builder.build_body_report(user_df, auth["username"]),
        "Overall Health Report": lambda: report_builder.build_overall_report(user_df, auth["username"], percentile_row),
    }
    choice = st.radio("Report type", list(report_options.keys()), label_visibility="collapsed")

    if st.button("Generate report", width="stretch"):
        with st.spinner("Building your report…"):
            st.session_state["report_bytes"] = report_options[choice]()
            st.session_state["report_choice"] = choice

    if st.session_state.get("report_choice") == choice and "report_bytes" in st.session_state:
        st.download_button(
            f"Download {choice}", data=st.session_state["report_bytes"],
            file_name=f"fitpulse_{choice.lower().replace(' ', '_')}.pdf",
            mime="application/pdf", width="stretch",
        )
