"""
models/database.py — AURA Database Models
Handles SQLite database initialization, user management, and chat history.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

# ─── Database path ────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'aura.db')


def get_connection():
    """Get a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Users table ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            salt        TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── Chat history table ────────────────────────────────────────────────────
    cursor.execute("""
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

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


# ─── Password utilities ───────────────────────────────────────────────────────

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash password with salt using SHA-256. Returns (hashed, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against its hash."""
    check, _ = hash_password(password, salt)
    return check == hashed


# ─── User operations ──────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> dict:
    """Create a new user. Returns {'success': bool, 'message': str, 'user': dict|None}."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if email already exists
        existing = cursor.execute(
            "SELECT id FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()

        if existing:
            return {'success': False, 'message': 'Email already registered.'}

        hashed, salt = hash_password(password)
        cursor.execute(
            "INSERT INTO users (name, email, password, salt) VALUES (?, ?, ?, ?)",
            (name.strip(), email.lower().strip(), hashed, salt)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return {
            'success': True,
            'message': 'Account created successfully!',
            'user': {'id': user_id, 'name': name, 'email': email}
        }

    except Exception as e:
        return {'success': False, 'message': f'Registration error: {str(e)}'}


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user. Returns {'success': bool, 'user': dict|None}."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            "SELECT id, name, email, password, salt FROM users WHERE email = ?",
            (email.lower().strip(),)
        ).fetchone()
        conn.close()

        if not row:
            return {'success': False, 'message': 'Email not found.'}

        if not verify_password(password, row['password'], row['salt']):
            return {'success': False, 'message': 'Incorrect password.'}

        return {
            'success': True,
            'user': {'id': row['id'], 'name': row['name'], 'email': row['email']}
        }

    except Exception as e:
        return {'success': False, 'message': f'Login error: {str(e)}'}


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch user by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Chat history operations ──────────────────────────────────────────────────

def save_message(user_id: int, role: str, message: str,
                 intent: str = None, confidence: float = None):
    """Save a chat message to the database."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (user_id, role, message, intent, confidence) VALUES (?, ?, ?, ?, ?)",
        (user_id, role, message, intent, confidence)
    )
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, limit: int = 50) -> list[dict]:
    """Retrieve recent chat history for a user."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT role, message, intent, confidence, timestamp
           FROM chat_history
           WHERE user_id = ?
           ORDER BY timestamp DESC
           LIMIT ?""",
        (user_id, limit)
    ).fetchall()
    conn.close()
    # Return in chronological order
    return [dict(r) for r in reversed(rows)]


def clear_chat_history(user_id: int):
    """Clear all chat history for a user."""
    conn = get_connection()
    conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
