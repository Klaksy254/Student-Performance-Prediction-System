"""SQLite-backed user accounts (register / verify)."""
from __future__ import annotations

import secrets
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")

UTC = timezone.utc


def ensure_schema(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                api_key TEXT,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(conn, "users", "is_admin", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "api_key", "TEXT")
        _ensure_column(conn, "users", "failed_attempts", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "locked_until", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column in cols:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _validate_username(username: str) -> tuple[bool, str]:
    u = (username or "").strip()
    if not u:
        return False, "Username is required."
    if not _USERNAME_RE.match(u):
        return False, "Username must be 3–32 characters (letters, numbers, underscore)."
    return True, u


def _validate_password(password: str) -> tuple[bool, str]:
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    # Basic strength signal (kept lightweight, no extra deps).
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    if sum([has_lower, has_upper, has_digit, has_symbol]) < 3:
        return False, "Password must include at least 3 of: lowercase, uppercase, number, symbol."
    return True, password  # echo normalized input (no trimming for passwords)


def register_user(
    db_path: str, username: str, password: str
) -> tuple[bool, str, int | None, str | None]:
    ok, msg = _validate_username(username)
    if not ok:
        return False, msg, None, None
    username = msg
    ok, pwd_ok = _validate_password(password)
    if not ok:
        return False, pwd_ok, None, None
    password = pwd_ok
    pwd_hash = generate_password_hash(password)
    api_key = secrets.token_urlsafe(32)
    try:
        with sqlite3.connect(db_path) as conn:
            existing_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            is_admin = 1 if int(existing_users or 0) == 0 else 0
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, api_key, is_admin) VALUES (?, ?, ?, ?)",
                (username, pwd_hash, api_key, is_admin),
            )
            conn.commit()
            return True, "Registered.", cur.lastrowid, username
    except sqlite3.IntegrityError:
        return False, "That username is already taken.", None, None


def verify_user(db_path: str, username: str, password: str) -> tuple[int, str, bool] | None:
    ok, msg = _validate_username(username)
    if not ok:
        return None
    username = msg
    if not password:
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, is_admin, failed_attempts, locked_until FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None
    user_id, canonical_name, pwd_hash, is_admin, failed_attempts, locked_until = row

    now = datetime.now(UTC)
    if locked_until:
        try:
            until = datetime.fromisoformat(locked_until)
            if until.tzinfo is None:
                until = until.replace(tzinfo=UTC)
        except ValueError:
            until = None
        if until and until > now:
            return None

    if check_password_hash(pwd_hash, password):
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()
        return user_id, canonical_name, bool(is_admin)

    # Failed attempt: increment & maybe lock.
    failed_attempts = int(failed_attempts or 0) + 1
    lock_until = None
    if failed_attempts >= 5:
        lock_until = (now + timedelta(minutes=10)).isoformat()
    conn.execute(
        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
        (failed_attempts, lock_until, user_id),
    )
    conn.commit()
    return None


def get_user_by_id(db_path: str, user_id: int) -> tuple[int, str, bool] | None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, username, is_admin FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
    if not row:
        return None
    uid, uname, is_admin = row
    return int(uid), str(uname), bool(is_admin)
