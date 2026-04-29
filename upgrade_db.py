"""
upgrade_db.py — Run this ONCE to add new tables to your existing aura.db
It will NOT delete your existing users or chat_history tables.
Run: python upgrade_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'aura.db')

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Add role column to users table (if not exists) ────────────────────────
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
        print("[OK] Added 'role' column to users table")
    except Exception:
        print("[SKIP] 'role' column already exists in users table")

    # ── Create messages table for Faculty DM ─────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message     TEXT    NOT NULL,
            is_read     INTEGER DEFAULT 0,
            timestamp   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (sender_id)   REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)
    print("[OK] Created 'messages' table")

    # ── Create gpt_history table ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gpt_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            role      TEXT    NOT NULL,
            message   TEXT    NOT NULL,
            timestamp TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("[OK] Created 'gpt_history' table")

    conn.commit()
    conn.close()
    print("\n✅ Database upgrade complete!")

if __name__ == '__main__':
    upgrade()
