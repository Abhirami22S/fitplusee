"""
FitPulse - Model 5: Personalized Recommendation Engine
=========================================================
Deliberately RULE-BASED, not a trained model — see README.md/viva.md for
why. Returns a list of sections (Steps, Calories, Sleep), each with a
status, the relevant numbers, and a What / Why / How breakdown so the
reasoning is fully inspectable rather than a black-box suggestion.
"""

import pandas as pd


def typical_pace(user_history: pd.DataFrame) -> float:
    active = user_history["active_minutes"].sum()
    steps = user_history["steps"].sum()
    return steps / active if active > 0 else 100.0


def calorie_rate(user_history: pd.DataFrame) -> float:
    active = user_history["active_minutes"].sum()
    cals = user_history["calories_burned"].sum()
    return cals / active if active > 0 else 6.0


def recommend(today_row: dict, user_history: pd.DataFrame, recent_sleep_quality_avg: float) -> list[dict]:
    pace = typical_pace(user_history)
    cal_rate = calorie_rate(user_history)
    step_gap = today_row["daily_step_goal"] - today_row["steps"]
    calorie_gap = today_row["daily_calorie_goal"] - today_row["calories_burned"]

    sections = []

    if step_gap > 0:
        extra_minutes = max(1, round(step_gap / pace))
        sections.append({
            "topic": "Steps",
            "status": "needs_focus",
            "metric": f"{int(today_row['steps']):,} / {int(today_row['daily_step_goal']):,}",
            "what": f"Add about {extra_minutes} more minutes of walking today.",
            "why": f"You're {int(step_gap):,} steps short of your personal goal, which is set 10% above "
                   f"your own yearly average — so it moves as your fitness does.",
            "how": f"At your typical pace of roughly {pace:.0f} steps per minute, {extra_minutes} minutes "
                   f"of brisk walking would close the gap — a short walk after a meal or a call taken "
                   f"standing up both work well.",
        })
    else:
        sections.append({
            "topic": "Steps", "status": "on_track",
            "metric": f"{int(today_row['steps']):,} / {int(today_row['daily_step_goal']):,}",
            "what": "You've already reached today's step goal.",
            "why": "Your step count today is at or above your personal target.",
            "how": "No action needed — keep your current routine going.",
        })

    if calorie_gap > 0:
        extra_minutes_cal = max(1, round(calorie_gap / cal_rate))
        sections.append({
            "topic": "Calories",
            "status": "needs_focus",
            "metric": f"{today_row['calories_burned']:.0f} / {today_row['daily_calorie_goal']:.0f} kcal",
            "what": f"About {extra_minutes_cal} more minutes of activity would close today's calorie gap.",
            "why": f"You're {calorie_gap:.0f} kcal short of today's goal, based on your own typical burn rate.",
            "how": f"At roughly {cal_rate:.1f} kcal burned per minute of activity for you, {extra_minutes_cal} "
                   f"extra minutes — of any activity type you enjoy — would get you there.",
        })
    else:
        sections.append({
            "topic": "Calories", "status": "on_track",
            "metric": f"{today_row['calories_burned']:.0f} / {today_row['daily_calorie_goal']:.0f} kcal",
            "what": "You've already reached today's calorie goal.",
            "why": "Calories burned today are at or above your personal target.",
            "how": "No action needed.",
        })

    if recent_sleep_quality_avg < 60:
        sections.append({
            "topic": "Sleep",
            "status": "needs_focus",
            "metric": f"{recent_sleep_quality_avg:.0f}/100 (7-night average)",
            "what": "Focus on lowering stress and breaking up sitting time today.",
            "why": "Across everyone in this dataset, stress level and sedentary time are the two strongest "
                   "drivers of sleep quality — well ahead of exercise intensity or heart rate.",
            "how": "A short walk every hour or two to break up sitting, plus a 10-minute wind-down before "
                   "bed instead of screen time, are the two changes most likely to help.",
        })
    else:
        sections.append({
            "topic": "Sleep", "status": "on_track",
            "metric": f"{recent_sleep_quality_avg:.0f}/100 (7-night average)",
            "what": "Your sleep quality has been solid this week.",
            "why": "Your average sleep score is above the range where we'd flag it for attention.",
            "how": "Keep your current stress and activity balance — it's working.",
        })

    return sections


if __name__ == "__main__":
    df = pd.read_parquet("data/processed/fitpulse_silver").sort_values(["user_id", "date"])
    uid = df.user_id.iloc[0]
    udf = df[df.user_id == uid]
    history, today = udf.iloc[:-1], udf.iloc[-1]
    recent_sleep = udf["sleep_quality_score"].tail(7).mean()

    for section in recommend(today.to_dict(), history, recent_sleep):
        print(f"\n[{section['status']}] {section['topic']} — {section['metric']}")
        print("What:", section["what"])
        print("Why: ", section["why"])
        print("How: ", section["how"])
