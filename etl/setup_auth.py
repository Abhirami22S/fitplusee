"""
FitPulse - Set up authentication tables in the serving database
===================================================================
Adds two tables to dashboard/fitpulse.db (on top of what
etl/load_to_sqlite.py already wrote):

  - `users`: username/password (salted + hashed with hashlib.pbkdf2_hmac —
    fine for a course demo, NOT what a real product would use; a real
    product would use bcrypt/Argon2 behind a proper auth provider, and
    that tradeoff should be stated plainly if asked in the viva).
  - `user_daily_raw`: empty table where NEW (non-demo) users' manually
    logged days or uploaded CSV rows get appended. Demo users never write
    here — their full history already lives in `user_daily_metrics`
    (computed offline by Spark).

Seeds 3 demo accounts, each linked to a real user_id that already has a
full year of Spark-processed history in `user_daily_metrics`, so logging
in as a demo user shows the full dashboard immediately.

Run with:  python3 etl/setup_auth.py
"""

import hashlib
import os
import sqlite3

DB_PATH = "dashboard/fitpulse.db"
# Hand-picked for genuinely different personas (not just the first 3 sorted
# ids, which happened to look nearly identical): a young active male, an
# older female managing hypertension with lower sleep quality, and a young
# female with the best sleep/lowest stress in the cohort.
DEMO_ACCOUNTS = [
    ("demo1", "demo123", 1503),  # 20M, no condition, Walking
    ("demo2", "demo123", 2759),  # 56F, hypertension, lower sleep quality
    ("demo3", "demo123", 2373),  # 27F, Basketball, best sleep / lowest stress
]


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex(), digest.hex()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            age INTEGER, gender TEXT, height_cm REAL, weight_kg REAL,
            is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_daily_raw (
            user_id INTEGER, date TEXT, steps INTEGER, calories_burned REAL,
            distance_km REAL, active_minutes INTEGER, sedentary_minutes INTEGER,
            resting_heart_rate REAL, avg_heart_rate INTEGER, max_heart_rate INTEGER,
            sleep_minutes INTEGER, sleep_quality_score REAL, activity_type TEXT,
            intensity TEXT, stress_level INTEGER, hydration_level REAL,
            PRIMARY KEY (user_id, date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_user ON user_daily_raw(user_id)")

    # Re-seed demo accounts cleanly every run (avoids UNIQUE(username) clashes
    # if the underlying user_id assignment changes between runs).
    conn.execute("DELETE FROM users WHERE is_demo = 1")

    for username, password, uid in DEMO_ACCOUNTS:
        salt, pw_hash = hash_password(password)
        sample_row = conn.execute(
            "SELECT age, gender, height_cm, weight_kg FROM user_daily_metrics WHERE user_id = ? LIMIT 1", (uid,)
        ).fetchone()
        conn.execute(
            """INSERT OR REPLACE INTO users (user_id, username, salt, password_hash, age, gender, height_cm, weight_kg, is_demo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (uid, username, salt, pw_hash, *sample_row),
        )
        print(f"Demo account: username='{username}' password='{password}' -> user_id={uid}")

    conn.commit()
    conn.close()
    print("\nNew registrations will be assigned user_id 900001, 900002, ... (see dashboard/app.py's register_user()).")
    print("Auth tables ready in dashboard/fitpulse.db")


if __name__ == "__main__":
    main()
