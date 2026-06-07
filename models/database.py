"""
models/database.py - AURA database helpers.

This module owns every SQLite connection and every schema migration so local
development and Render use the same database behavior.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RENDER_DB_PATH = Path("/var/data/aura.db")


def _database_path() -> Path:
    configured = os.environ.get("AURA_DB_PATH")
    if configured:
        return Path(configured)

    if os.environ.get("RENDER"):
        return DEFAULT_RENDER_DB_PATH

    return BASE_DIR / "aura.db"


DB_PATH = _database_path()


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with production-friendly pragmas enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db() -> None:
    """Create or migrate all tables needed by the application."""
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            salt        TEXT    NOT NULL DEFAULT '',
            role        TEXT    NOT NULL DEFAULT 'student',
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    _ensure_column(conn, "users", "role", "role TEXT NOT NULL DEFAULT 'student'")
    _ensure_column(conn, "users", "salt", "salt TEXT NOT NULL DEFAULT ''")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            role        TEXT    NOT NULL CHECK(role IN ('user', 'bot')),
            message     TEXT    NOT NULL,
            intent      TEXT,
            confidence  REAL,
            timestamp   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message     TEXT    NOT NULL,
            is_read     INTEGER DEFAULT 0,
            timestamp   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS gpt_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            role      TEXT    NOT NULL,
            message   TEXT    NOT NULL,
            timestamp TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_dashboard (
            user_id              INTEGER PRIMARY KEY,
            attendance_percent   INTEGER DEFAULT 86,
            attendance_note      TEXT    DEFAULT 'Above the 75% requirement',
            fee_status           TEXT    DEFAULT 'Due soon',
            fee_balance          TEXT    DEFAULT 'Rs.12,500',
            fee_note             TEXT    DEFAULT 'Balance due by 30 May',
            fee_paid             TEXT    DEFAULT 'Rs.87,500',
            fee_paid_percent     INTEGER DEFAULT 88,
            next_exam_title      TEXT    DEFAULT 'Business Analytics',
            next_exam_date       TEXT    DEFAULT '2026-05-24T09:30',
            exam_result          TEXT    DEFAULT 'Internal 1: 82%',
            gpa                  TEXT    DEFAULT '8.7',
            cgpa                 TEXT    DEFAULT '8.4',
            timetable            TEXT    DEFAULT 'Mon 09:30 - Business Analytics\nTue 11:00 - Python Lab\nWed 10:00 - Finance\nThu 02:00 - Marketing\nFri 09:30 - Mentoring',
            updated_at           TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gpt_history_user ON gpt_history(user_id)")

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with Werkzeug's adaptive password hasher."""
    return generate_password_hash(password), "werkzeug"


def _verify_legacy_password(password: str, hashed: str, salt: str) -> bool:
    legacy_hash = hashlib.sha256((password + (salt or "")).encode()).hexdigest()
    return secrets.compare_digest(legacy_hash, hashed)


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify both modern Werkzeug hashes and older SHA-256 hashes."""
    if hashed.startswith(("scrypt:", "pbkdf2:", "argon2:")):
        return check_password_hash(hashed, password)
    return _verify_legacy_password(password, hashed, salt)


def _upgrade_password_hash(user_id: int, password: str) -> None:
    hashed, salt = hash_password(password)
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password = ?, salt = ? WHERE id = ?",
        (hashed, salt, user_id),
    )
    conn.commit()
    conn.close()


def create_user(name: str, email: str, password: str, role: str = "student") -> dict:
    """Create a new user."""
    try:
        normalized_email = email.lower().strip()
        normalized_role = role if role in {"student", "faculty"} else "student"

        conn = get_connection()
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

        if existing:
            conn.close()
            return {"success": False, "message": "Email already registered."}

        hashed, salt = hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (name, email, password, salt, role) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), normalized_email, hashed, salt, normalized_role),
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return {
            "success": True,
            "message": "Account created successfully!",
            "user": {
                "id": user_id,
                "name": name.strip(),
                "email": normalized_email,
                "role": normalized_role,
            },
        }

    except Exception as exc:
        print(f"[DB] Registration error: {exc}")
        return {"success": False, "message": "Registration failed. Please try again."}


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user."""
    try:
        normalized_email = email.lower().strip()
        conn = get_connection()
        row = conn.execute(
            "SELECT id, name, email, password, salt, role FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
        conn.close()

        if not row:
            return {"success": False, "message": "Email not found."}

        if not verify_password(password, row["password"], row["salt"]):
            return {"success": False, "message": "Incorrect password."}

        if not row["password"].startswith(("scrypt:", "pbkdf2:", "argon2:")):
            _upgrade_password_hash(row["id"], password)

        return {
            "success": True,
            "user": {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"] or "student",
            },
        }

    except Exception as exc:
        print(f"[DB] Login error: {exc}")
        return {"success": False, "message": "Login failed. Please try again."}


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch user by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, email, role, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_message(
    user_id: int,
    role: str,
    message: str,
    intent: str | None = None,
    confidence: float | None = None,
) -> None:
    """Save a chat message."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (user_id, role, message, intent, confidence) VALUES (?, ?, ?, ?, ?)",
        (user_id, role, message, intent, confidence),
    )
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, limit: int = 50) -> list[dict]:
    """Retrieve recent chat history for a user in chronological order."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT role, message, intent, confidence, timestamp
           FROM chat_history
           WHERE user_id = ?
           ORDER BY timestamp DESC
           LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def clear_chat_history(user_id: int) -> None:
    """Clear all chat history for a user."""
    conn = get_connection()
    conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
