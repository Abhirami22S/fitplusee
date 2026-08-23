"""
FitPulse - PDF Report Generation
===================================
Builds professional, downloadable PDF reports (Sleep, Activity, Body
Functions, Overall Health) from a user's own data — charts via matplotlib,
layout/typography via ReportLab. All numbers are computed live from the
user's dataframe; nothing here is templated placeholder text.
"""

import io
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                  Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.recommendation_engine import recommend
from theme import BORDER, INK, INK_MUTED, SERIES, STATUS, ordinal

PAGE_W, PAGE_H = LETTER
MARGIN = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": BORDER, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK_MUTED, "ytick.color": INK_MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "grid.color": "#F0EFEA",
})

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("FPTitle", parent=_styles["Title"], fontName="Helvetica-Bold",
                     fontSize=22, textColor=rl_colors.HexColor(INK), alignment=TA_LEFT, spaceAfter=4)
SUB = ParagraphStyle("FPSub", parent=_styles["Normal"], fontName="Helvetica", fontSize=10.5,
                      textColor=rl_colors.HexColor(INK_MUTED), spaceAfter=18)
H2 = ParagraphStyle("FPH2", parent=_styles["Heading2"], fontName="Helvetica-Bold", fontSize=14,
                     textColor=rl_colors.HexColor(SERIES["primary"]), spaceBefore=16, spaceAfter=8)
H3 = ParagraphStyle("FPH3", parent=_styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5,
                     textColor=rl_colors.HexColor(INK), spaceBefore=10, spaceAfter=3)
BODY = ParagraphStyle("FPBody", parent=_styles["Normal"], fontName="Helvetica", fontSize=9.3,
                       textColor=rl_colors.HexColor(INK), leading=13.5, spaceAfter=7)
CAPTION = ParagraphStyle("FPCaption", parent=_styles["Normal"], fontName="Helvetica-Oblique",
                          fontSize=8.3, textColor=rl_colors.HexColor(INK_MUTED), spaceAfter=14)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def _header_footer(report_title):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(rl_colors.HexColor(SERIES["primary"]))
        canvas.drawString(MARGIN, PAGE_H - 0.55 * inch, "FitPulse")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(rl_colors.HexColor(INK_MUTED))
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.55 * inch, report_title)
        canvas.setStrokeColor(rl_colors.HexColor(BORDER))
        canvas.setLineWidth(0.75)
        canvas.line(MARGIN, PAGE_H - 0.68 * inch, PAGE_W - MARGIN, PAGE_H - 0.68 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(MARGIN, 0.5 * inch, datetime.now().strftime("Generated %B %d, %Y"))
        canvas.drawRightString(PAGE_W - MARGIN, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def _build_pdf(story, report_title) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.95 * inch, bottomMargin=0.75 * inch, title=f"FitPulse - {report_title}",
    )
    cb = _header_footer(report_title)
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()


def _fig_to_flowable(fig, target_width=CONTENT_W):
    fw, fh = fig.get_size_inches()
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=170, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    ratio = fh / fw
    return Image(buf, width=target_width, height=target_width * ratio)


def _stat_table(rows, col_widths=None):
    data = [[Paragraph(f"<b>{label}</b>", BODY), Paragraph(str(value), BODY)] for label, value in rows]
    col_widths = col_widths or [CONTENT_W * 0.45, CONTENT_W * 0.55]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor(BORDER)),
        ("BACKGROUND", (0, 0), (0, -1), rl_colors.HexColor("#F7F6F3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _suggestions_flowables(sections):
    flow = [Paragraph("Suggestions &amp; Areas for Improvement", H2)]
    for s in sections:
        label = "On track" if s["status"] == "on_track" else "Needs attention"
        color = STATUS["good"] if s["status"] == "on_track" else STATUS["warning"]
        flow.append(Paragraph(
            f'<font color="{color}">●</font> <b>{s["topic"]}</b> '
            f'&nbsp;&nbsp;{s["metric"]}&nbsp;&nbsp;<i>({label})</i>', H3,
        ))
        flow.append(Paragraph(f'<b>What:</b> {s["what"]}', BODY))
        flow.append(Paragraph(f'<b>Why:</b> {s["why"]}', BODY))
        flow.append(Paragraph(f'<b>How:</b> {s["how"]}', BODY))
        flow.append(Spacer(1, 4))
    return flow


def _trend_word(series: pd.Series) -> str:
    if len(series) < 4:
        return "stable"
    x = np.arange(len(series))
    slope = np.polyfit(x, series.values, 1)[0]
    rel = slope * len(series) / (series.mean() + 1e-9)
    if rel > 0.06:
        return "improving"
    if rel < -0.06:
        return "declining"
    return "stable"


def _current_bmi(row) -> float:
    """Recomputed from the latest height/weight rather than the dataset's stored
    `bmi` column, which was found to be frozen at a user's starting weight and
    never recalculated as weight_kg drifts over the year (a real data-quality
    issue in the source dataset — see viva.md)."""
    return row["weight_kg"] / (row["height_cm"] / 100) ** 2


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _period_df(user_df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    return user_df.tail(min(days, len(user_df))).reset_index(drop=True)


def _title_block(title, username, df):
    start, end = df["date"].iloc[0].strftime("%b %d, %Y"), df["date"].iloc[-1].strftime("%b %d, %Y")
    return [
        Paragraph(title, H1),
        Paragraph(f"{username} &nbsp;&middot;&nbsp; {start} &ndash; {end} ({len(df)} days)", SUB),
    ]


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------
def _fig_line(df, ycol, ylabel, color, goal_value=None, goal_label="Goal"):
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    ax.plot(df["date"], df[ycol], color=color, linewidth=1.6)
    if goal_value is not None:
        ax.axhline(goal_value, color=INK_MUTED, linestyle=":", linewidth=1, label=goal_label)
        ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_ylabel(ylabel)
    fig.autofmt_xdate()
    return fig


def _fig_scatter(x, y, xlabel, ylabel, color):
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    ax.scatter(x, y, color=color, alpha=0.6, s=16)
    if len(x) > 1 and x.nunique() > 1:
        z = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, np.poly1d(z)(xs), color=INK_MUTED, linewidth=1.2, linestyle="--")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig


def _fig_hist(values, xlabel, color):
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    ax.hist(values, bins=min(15, max(5, len(values) // 3)), color=color, edgecolor="white")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Days")
    return fig


def _fig_activity_breakdown(df):
    counts = df["activity_type"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(6.5, 2.7))
    ax.barh(counts.index, counts.values, color=SERIES["primary"])
    ax.set_xlabel("Sessions logged")
    return fig


def _fig_weekly_goal_rate(df):
    weekly = df.set_index("date")["goal_achieved"].resample("W").mean() * 100
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    ax.bar(weekly.index, weekly.values, color=SERIES["amber"], width=5)
    ax.set_ylabel("Goal achievement (%)")
    ax.set_ylim(0, 100)
    fig.autofmt_xdate()
    return fig


def _fig_heart_rate_trend(df):
    fig, ax = plt.subplots(figsize=(6.5, 2.7))
    ax.plot(df["date"], df["resting_heart_rate"], color=SERIES["slate"], label="Resting", linewidth=1.4)
    ax.plot(df["date"], df["avg_heart_rate"], color=SERIES["primary"], label="Average", linewidth=1.4)
    ax.plot(df["date"], df["max_heart_rate"], color=SERIES["rose"], label="Peak", linewidth=1.4)
    ax.set_ylabel("Heart rate (bpm)")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    fig.autofmt_xdate()
    return fig


def _fig_bmi_position(bmi):
    categories = [("Underweight", 12, 18.5), ("Normal", 18.5, 25), ("Overweight", 25, 30), ("Obese", 30, 48)]
    colors_map = [SERIES["teal"], SERIES["primary"], SERIES["amber"], SERIES["rose"]]
    fig, ax = plt.subplots(figsize=(6.5, 1.4))
    for (name, lo, hi), c in zip(categories, colors_map):
        ax.barh(0, hi - lo, left=lo, color=c, height=0.45)
        ax.text((lo + hi) / 2, -0.5, name, ha="center", fontsize=7.5, color=INK_MUTED)
    bmi_clamped = min(max(bmi, 12), 48)
    ax.plot([bmi_clamped, bmi_clamped], [-0.28, 0.28], color=INK, linewidth=2.2)
    ax.text(bmi_clamped, 0.38, f"You: {bmi:.1f}", ha="center", fontsize=8.5, fontweight="bold", color=INK)
    ax.set_xlim(12, 48)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    return fig




def _fig_blood_pressure(df):
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    ax.plot(df["date"], df["blood_pressure_systolic"], color=SERIES["rose"], label="Systolic", linewidth=1.4)
    ax.plot(df["date"], df["blood_pressure_diastolic"], color=SERIES["teal"], label="Diastolic", linewidth=1.4)
    ax.set_ylabel("mmHg")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.autofmt_xdate()
    return fig


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------
def build_sleep_report(user_df: pd.DataFrame, username: str) -> bytes:
    df = _period_df(user_df, 30)
    story = _title_block("Sleep Report", username, df)

    avg_q, avg_hours = df["sleep_quality_score"].mean(), (df["sleep_minutes"] / 60).mean()
    best, worst = df["sleep_quality_score"].max(), df["sleep_quality_score"].min()
    below60 = int((df["sleep_quality_score"] < 60).sum())
    trend = _trend_word(df["sleep_quality_score"])

    story.append(_stat_table([
        ("Average sleep duration", f"{avg_hours:.1f} hours"),
        ("Average sleep quality", f"{avg_q:.0f} / 100"),
        ("Best night", f"{best:.0f} / 100"),
        ("Lowest night", f"{worst:.0f} / 100"),
        ("Nights below 60/100", f"{below60} of {len(df)}"),
        ("Average stress level", f"{df['stress_level'].mean():.1f} / 10"),
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Sleep Quality Over Time", H2))
    story.append(_fig_to_flowable(_fig_line(df, "sleep_quality_score", "Sleep quality (0-100)", SERIES["primary"], 60, "Attention threshold")))
    story.append(Paragraph(
        f"Sleep quality has been {trend} over this period, averaging {avg_q:.0f}/100. "
        f"{'This is above the level we flag for attention.' if avg_q >= 60 else 'This sits below the level we flag for attention — see suggestions below.'}",
        CAPTION,
    ))

    story.append(Paragraph("Sleep Duration Distribution", H2))
    story.append(_fig_to_flowable(_fig_hist(df["sleep_minutes"] / 60, "Hours slept", SERIES["teal"])))
    story.append(Paragraph(f"Most nights fall between {(df['sleep_minutes']/60).quantile(0.25):.1f} and "
                            f"{(df['sleep_minutes']/60).quantile(0.75):.1f} hours.", CAPTION))

    story.append(Paragraph("Stress vs. Sleep Quality", H2))
    story.append(_fig_to_flowable(_fig_scatter(df["stress_level"], df["sleep_quality_score"], "Stress level (1-10)", "Sleep quality (0-100)", SERIES["rose"])))
    corr = df["stress_level"].corr(df["sleep_quality_score"])
    story.append(Paragraph(f"Correlation between stress and sleep quality: {corr:.2f}. "
                            f"{'Higher-stress days line up with lower sleep quality in your data.' if corr < -0.2 else 'No strong relationship shows up in this period.'}", CAPTION))

    story.append(PageBreak())
    recent_sleep_avg = df["sleep_quality_score"].tail(7).mean()
    today_row = user_df.iloc[-1].to_dict()
    history = user_df.iloc[:-1]
    sleep_section = [s for s in recommend(today_row, history, recent_sleep_avg) if s["topic"] == "Sleep"]
    story += _suggestions_flowables(sleep_section)

    return _build_pdf(story, "Sleep Report")


def build_activity_report(user_df: pd.DataFrame, username: str) -> bytes:
    df = _period_df(user_df, 30)
    story = _title_block("Activity Report", username, df)

    avg_steps, avg_cal = df["steps"].mean(), df["calories_burned"].mean()
    avg_active = df["active_minutes"].mean()
    goal_rate = df["goal_achieved"].mean() * 100
    fav_activity = df["activity_type"].mode()[0]
    total_dist = df["distance_km"].sum()

    story.append(_stat_table([
        ("Average daily steps", f"{avg_steps:,.0f}"),
        ("Average calories burned", f"{avg_cal:.0f} kcal"),
        ("Average active minutes", f"{avg_active:.0f} min/day"),
        ("Goal achievement rate", f"{goal_rate:.0f}%"),
        ("Most frequent activity", fav_activity),
        ("Total distance covered", f"{total_dist:.1f} km"),
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Steps Over Time", H2))
    story.append(_fig_to_flowable(_fig_line(df, "steps", "Steps", SERIES["primary"], df["daily_step_goal"].iloc[-1], "Daily goal")))
    trend = _trend_word(df["steps"])
    story.append(Paragraph(f"Your step count has been {trend} over this period, averaging {avg_steps:,.0f} steps/day "
                            f"against a goal of {df['daily_step_goal'].iloc[-1]:,.0f}.", CAPTION))

    story.append(Paragraph("Calories Burned Over Time", H2))
    story.append(_fig_to_flowable(_fig_line(df, "calories_burned", "Calories (kcal)", SERIES["amber"], df["daily_calorie_goal"].iloc[-1], "Daily goal")))
    story.append(Paragraph(f"Average calories burned was {avg_cal:.0f} kcal/day against a goal of "
                            f"{df['daily_calorie_goal'].iloc[-1]:.0f} kcal.", CAPTION))

    story.append(Paragraph("Activity Breakdown", H2))
    story.append(_fig_to_flowable(_fig_activity_breakdown(df)))
    story.append(Paragraph(f"{fav_activity} was your most frequent activity in this period.", CAPTION))

    story.append(Paragraph("Weekly Goal Achievement", H2))
    story.append(_fig_to_flowable(_fig_weekly_goal_rate(df)))
    story.append(Paragraph(f"You hit your daily step goal on {goal_rate:.0f}% of days this period.", CAPTION))

    story.append(PageBreak())
    recent_sleep_avg = user_df["sleep_quality_score"].tail(7).mean()
    today_row = user_df.iloc[-1].to_dict()
    history = user_df.iloc[:-1]
    sections = [s for s in recommend(today_row, history, recent_sleep_avg) if s["topic"] in ("Steps", "Calories")]
    story += _suggestions_flowables(sections)

    return _build_pdf(story, "Activity Report")


def build_body_report(user_df: pd.DataFrame, username: str) -> bytes:
    df = _period_df(user_df, 30)
    latest = user_df.iloc[-1]
    bmi = _current_bmi(latest)

    story = _title_block("Body Functions Report", username, df)

    profile_rows = [
        ("Age", f"{int(latest['age'])}"),
        ("Gender", latest["gender"]),
        ("Height", f"{latest['height_cm']:.0f} cm"),
        ("Weight", f"{latest['weight_kg']:.1f} kg"),
        ("BMI", f"{bmi:.1f} ({_bmi_category(bmi)})"),
        ("Average resting heart rate", f"{df['resting_heart_rate'].mean():.0f} bpm"),
        ("Average heart rate (active)", f"{df['avg_heart_rate'].mean():.0f} bpm"),
        ("Average peak heart rate", f"{df['max_heart_rate'].mean():.0f} bpm"),
    ]
    if "blood_pressure_systolic" in df.columns and df["blood_pressure_systolic"].notna().any():
        profile_rows.append(("Average blood pressure",
                              f"{df['blood_pressure_systolic'].mean():.0f}/{df['blood_pressure_diastolic'].mean():.0f} mmHg"))
    if "health_condition" in df.columns and pd.notna(latest.get("health_condition")):
        profile_rows.append(("Reported health condition", latest["health_condition"]))
    if "smoking_status" in df.columns and pd.notna(latest.get("smoking_status")):
        profile_rows.append(("Smoking status", latest["smoking_status"]))

    story.append(_stat_table(profile_rows))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Heart Rate Trends", H2))
    story.append(_fig_to_flowable(_fig_heart_rate_trend(df)))
    story.append(Paragraph(f"Your average heart rate stayed within a "
                            f"{df['avg_heart_rate'].min():.0f}–{df['avg_heart_rate'].max():.0f} bpm range this period.", CAPTION))

    if "blood_pressure_systolic" in df.columns and df["blood_pressure_systolic"].notna().any():
        story.append(Paragraph("Blood Pressure Trends", H2))
        story.append(_fig_to_flowable(_fig_blood_pressure(df)))
        story.append(Paragraph("Shown for context alongside your activity data — not a diagnostic reading.", CAPTION))

    story.append(Paragraph("BMI Position", H2))
    story.append(_fig_to_flowable(_fig_bmi_position(bmi), target_width=CONTENT_W * 0.9))
    story.append(Paragraph(f"Your BMI of {bmi:.1f} falls in the {_bmi_category(bmi)} range.", CAPTION))

    z = (df[["resting_heart_rate", "avg_heart_rate", "max_heart_rate"]]
         - df[["resting_heart_rate", "avg_heart_rate", "max_heart_rate"]].mean()) / \
        df[["resting_heart_rate", "avg_heart_rate", "max_heart_rate"]].std(ddof=0).replace(0, 1)
    flagged = int((z.abs() > 2.5).any(axis=1).sum())

    story.append(Paragraph("Heart Rate Pattern Check", H2))
    story.append(Paragraph(
        f"{flagged} day(s) in this period showed a heart rate pattern more than 2.5 standard deviations from "
        f"your own average — {'worth keeping an eye on' if flagged > 0 else 'none flagged this period'}. "
        f"This is a statistical comparison against your own baseline, not a medical diagnosis.", BODY,
    ))

    return _build_pdf(story, "Body Functions Report")


def build_overall_report(user_df: pd.DataFrame, username: str, percentile_row=None) -> bytes:
    df = _period_df(user_df, 30)
    latest = user_df.iloc[-1]
    bmi = _current_bmi(latest)

    story = _title_block("Overall Health Report", username, df)

    avg_steps, goal_rate = df["steps"].mean(), df["goal_achieved"].mean() * 100
    avg_sleep_q = df["sleep_quality_score"].mean()
    avg_hr = df["resting_heart_rate"].mean()

    story.append(Paragraph("Summary", H2))
    story.append(_stat_table([
        ("Average daily steps", f"{avg_steps:,.0f} ({goal_rate:.0f}% of days at goal)"),
        ("Average sleep quality", f"{avg_sleep_q:.0f} / 100"),
        ("Average resting heart rate", f"{avg_hr:.0f} bpm"),
        ("BMI", f"{bmi:.1f} ({_bmi_category(bmi)})"),
    ]))
    story.append(Spacer(1, 10))

    if percentile_row is not None:
        story.append(Paragraph("How You Compare", H2))
        story.append(_stat_table([
            ("Steps percentile", ordinal(percentile_row['steps_percentile'])),
            ("Calories percentile", ordinal(percentile_row['calories_percentile'])),
            ("Sleep quality percentile", ordinal(percentile_row['sleep_quality_percentile'])),
        ]))
        story.append(Paragraph(f"Compared against people aged {percentile_row['age_group']}, "
                                f"gender {percentile_row['gender']}.", CAPTION))
        story.append(Spacer(1, 6))

    story.append(Paragraph("Activity", H2))
    story.append(_fig_to_flowable(_fig_line(df, "steps", "Steps", SERIES["primary"], df["daily_step_goal"].iloc[-1], "Daily goal")))
    story.append(Paragraph(f"{_trend_word(df['steps']).capitalize()} trend, averaging {avg_steps:,.0f} steps/day.", CAPTION))

    story.append(Paragraph("Sleep", H2))
    story.append(_fig_to_flowable(_fig_line(df, "sleep_quality_score", "Sleep quality (0-100)", SERIES["teal"], 60, "Attention threshold")))
    story.append(Paragraph(f"{_trend_word(df['sleep_quality_score']).capitalize()} trend, averaging {avg_sleep_q:.0f}/100.", CAPTION))

    story.append(Paragraph("Body", H2))
    story.append(_fig_to_flowable(_fig_heart_rate_trend(df)))
    story.append(Paragraph(f"Resting heart rate averaged {avg_hr:.0f} bpm this period.", CAPTION))

    story.append(PageBreak())
    recent_sleep_avg = df["sleep_quality_score"].tail(7).mean()
    today_row = user_df.iloc[-1].to_dict()
    history = user_df.iloc[:-1]
    story += _suggestions_flowables(recommend(today_row, history, recent_sleep_avg))

    return _build_pdf(story, "Overall Health Report")
