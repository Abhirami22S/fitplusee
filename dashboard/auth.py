"""
FitPulse - Simple authentication helpers
===========================================
Deliberately simple, SQLite-backed username/password auth using
hashlib.pbkdf2_hmac (salted, 100k iterations) — good enough to demo a real
login flow for a course project, but NOT what a production system would
use. A real product would use bcrypt/Argon2 (or delegate entirely to an
auth provider like Auth0/Firebase/Cognito) and TLS in transit; say this
plainly if asked in the viva.
"""

import hashlib
import os
import sqlite3

DB_PATH = "dashboard/fitpulse.db"
NEW_USER_ID_START = 900001


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


def register_user(conn: sqlite3.Connection, username: str, password: str,
                   age: int, gender: str, height_cm: float, weight_kg: float):
    existing = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return None, "That username is already taken."
    if len(password) < 6:
        return None, "Password must be at least 6 characters."

    max_id = conn.execute(
        "SELECT MAX(user_id) FROM users WHERE user_id >= ?", (NEW_USER_ID_START,)
    ).fetchone()[0]
    new_id = (max_id + 1) if max_id else NEW_USER_ID_START

    salt = os.urandom(16)
    pw_hash = _hash(password, salt)
    conn.execute(
        """INSERT INTO users (user_id, username, salt, password_hash, age, gender, height_cm, weight_kg, is_demo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (new_id, username, salt.hex(), pw_hash, age, gender, height_cm, weight_kg),
    )
    conn.commit()
    return new_id, None


def authenticate(conn: sqlite3.Connection, username: str, password: str):
    row = conn.execute(
        "SELECT user_id, salt, password_hash, is_demo FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return None, "No account with that username."
    user_id, salt_hex, stored_hash, is_demo = row
    if _hash(password, bytes.fromhex(salt_hex)) != stored_hash:
        return None, "Incorrect password."
    return {"user_id": user_id, "username": username, "is_demo": bool(is_demo)}, None
