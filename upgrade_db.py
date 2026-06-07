"""
upgrade_db.py - Initialize or migrate the AURA SQLite database.

Run this locally with:
    python upgrade_db.py

On Render, the application also runs the same initialization automatically
when Gunicorn imports app.py.
"""

from models.database import DB_PATH, init_db


def upgrade() -> None:
    init_db()
    print(f"Database upgrade complete: {DB_PATH}")


if __name__ == "__main__":
    upgrade()
