"""
Canonical SQLite Database Initializer for MedicSense AI
Creates/migrates all 5 required tables with the exact specified schema.
Run this script directly OR import init_db() at app startup.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "appointments.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """
    Create all required tables if they do not exist.
    Existing data is preserved (IF NOT EXISTS).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # ── 1. users ──────────────────────────────────────────────────────────
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              TEXT PRIMARY KEY,
                name            TEXT,
                email           TEXT,
                phone           TEXT,
                auth_method     TEXT DEFAULT 'email_password',
                google_id       TEXT,
                google_email    TEXT,
                password_hash   TEXT,
                last_active     TIMESTAMP,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Migration: Ensure missing columns exist if table was created with old schema
        cur.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in cur.fetchall()}

        required_cols = {
            "auth_method": "TEXT DEFAULT 'email_password'",
            "google_id": "TEXT",
            "google_email": "TEXT",
            "password_hash": "TEXT",
            "last_active": "TIMESTAMP",
        }

        for col, col_def in required_cols.items():
            if col not in existing_cols:
                print(f"Adding column {col} to users table...")
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")

        # ── 2. conversations ──────────────────────────────────────────────────
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # ── 3. messages ───────────────────────────────────────────────────────
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role            TEXT CHECK(role IN ('user','assistant')) NOT NULL,
                content         TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # ── 4. appointments ───────────────────────────────────────────────────
        # Drop and recreate only if the schema is wrong (id column type check).
        cur.execute("PRAGMA table_info(appointments)")
        cols = {row[1]: row[2] for row in cur.fetchall()}  # name -> type
        id_col_type = cols.get("id", "")

        if id_col_type.upper() != "INTEGER":
            # Migrate: rename old table, create correct one, copy compatible data
            cur.execute("ALTER TABLE appointments RENAME TO appointments_old")
            cur.execute(
                """
                CREATE TABLE appointments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    doctor_id   TEXT NOT NULL,
                    doctor_name TEXT,
                    date        TEXT NOT NULL,
                    time        TEXT NOT NULL,
                    type        TEXT NOT NULL,
                    reason      TEXT,
                    status      TEXT DEFAULT 'confirmed',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(doctor_id, date, time)
                )
            """
            )
            # Copy rows that have the required columns; ignore extras
            cur.execute(
                """
                INSERT OR IGNORE INTO appointments
                    (user_id, doctor_id, date, time, type, status, created_at)
                SELECT
                    user_id,
                    doctor_id,
                    date,
                    time,
                    COALESCE(type, 'in-person'),
                    COALESCE(status, 'confirmed'),
                    created_at
                FROM appointments_old
            """
            )
            cur.execute("DROP TABLE appointments_old")
        else:
            # Table exists with correct id type — ensure all required columns exist
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS appointments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    doctor_id   TEXT NOT NULL,
                    doctor_name TEXT,
                    date        TEXT NOT NULL,
                    time        TEXT NOT NULL,
                    type        TEXT NOT NULL,
                    reason      TEXT,
                    status      TEXT DEFAULT 'confirmed',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(doctor_id, date, time)
                )
            """
            )

            # Migration: Ensure doctor_name and reason columns exist
            cur.execute("PRAGMA table_info(appointments)")
            existing_apt_cols = {row[1] for row in cur.fetchall()}
            if "doctor_name" not in existing_apt_cols:
                print("Adding column doctor_name to appointments table...")
                cur.execute("ALTER TABLE appointments ADD COLUMN doctor_name TEXT")
            if "reason" not in existing_apt_cols:
                print("Adding column reason to appointments table...")
                cur.execute("ALTER TABLE appointments ADD COLUMN reason TEXT")

        # ── 5. notifications ──────────────────────────────────────────────────
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                title      TEXT NOT NULL,
                message    TEXT NOT NULL,
                type       TEXT NOT NULL,
                read       INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        print("[OK] Database schema initialised - all 5 tables OK.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    # Verification print
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables present: {tables}")
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        print(f"\n  {t}:")
        for col in cur.fetchall():
            print(f"    {col[1]:20s} {col[2]}")
    conn.close()
