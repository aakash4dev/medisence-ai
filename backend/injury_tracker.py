"""
injury_tracker.py — Comparative Healing Intelligence Tracker

Stores metadata from each image analysis session per user.
Images are NEVER stored — only analysis metadata.

v2 additions:
  - delta, delta_score, delta_explanation columns
  - record_analysis_with_delta()  → persist snapshot + comparison result
  - get_latest()                  → previous snapshot for comparison
  - build_comparison_context()    → rich context string injected into Gemini
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import List, Dict, Optional

_DB_PATH = "injury_progress.db"


def _init_db():
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS injury_progress (
                id                  TEXT PRIMARY KEY,
                user_id             TEXT NOT NULL,
                injury_type         TEXT,
                severity            TEXT,
                severity_score      INTEGER,
                infection_risk      TEXT,
                injury_note         TEXT,
                visual_description  TEXT,
                delta               TEXT,          -- improved | worsened | stable | baseline
                delta_score         REAL,          -- +ve = improvement, -ve = worsening
                delta_explanation   TEXT,
                timestamp           REAL,
                created_at          TEXT
            )
        """)
        # Add new columns to existing DB if upgrading
        for col, ctype in [
            ("visual_description", "TEXT"),
            ("delta",              "TEXT"),
            ("delta_score",        "REAL"),
            ("delta_explanation",  "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE injury_progress ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass   # column already exists
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_uid ON injury_progress(user_id, timestamp)"
        )
        conn.commit()


_init_db()


@contextmanager
def _conn():
    with sqlite3.connect(_DB_PATH) as c:
        c.row_factory = sqlite3.Row
        yield c


# ── Write ─────────────────────────────────────────────────────────────────────

def record_analysis(
    user_id: str,
    injury_type: str,
    severity: str,
    severity_score: int,
    infection_risk: str,
    injury_note: str = "",
    visual_description: str = "",
    delta: str = "baseline",
    delta_score: float = 0.0,
    delta_explanation: str = "",
) -> str:
    """
    Persist one injury analysis snapshot.
    Returns the generated analysis_id.
    """
    analysis_id = str(uuid.uuid4())[:12]
    ts = time.time()
    created = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts))

    with _conn() as c:
        c.execute(
            """INSERT INTO injury_progress
               (id, user_id, injury_type, severity, severity_score,
                infection_risk, injury_note, visual_description,
                delta, delta_score, delta_explanation,
                timestamp, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (analysis_id, user_id, injury_type, severity, severity_score,
             infection_risk, injury_note, visual_description,
             delta, delta_score, delta_explanation,
             ts, created),
        )
        c.commit()

    return analysis_id


# ── Read ──────────────────────────────────────────────────────────────────────

def get_progress(user_id: str, limit: int = 10) -> List[Dict]:
    """Return all snapshots for a user, newest first."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM injury_progress WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest(user_id: str) -> Optional[Dict]:
    """Return the most recent snapshot for a user."""
    rows = get_progress(user_id, limit=1)
    return rows[0] if rows else None


# ── Context builder for Gemini ────────────────────────────────────────────────

def build_comparison_context(user_id: str) -> Optional[Dict]:
    """
    Returns the previous snapshot as a dict that can be injected into
    the Gemini comparison prompt. Returns None if no prior history.
    """
    prev = get_latest(user_id)
    if not prev:
        return None
    return {
        "date": prev.get("created_at", "unknown"),
        "injury_type": prev.get("injury_type", "unknown"),
        "severity": prev.get("severity", "unknown"),
        "severity_score": prev.get("severity_score", 0),
        "infection_risk": prev.get("infection_risk", "unknown"),
        "visual_description": prev.get("visual_description", "Not recorded"),
        "session_number": len(get_progress(user_id, limit=100)),
    }


def build_progress_summary(user_id: str) -> str:
    """Human-readable healing progress summary for display."""
    snapshots = get_progress(user_id, limit=5)
    if not snapshots:
        return ""

    lines = [f"Injury progress ({len(snapshots)} sessions):"]
    for i, s in enumerate(reversed(snapshots)):
        day_label = f"Day {i + 1}"
        delta_str = ""
        if s.get("delta") and s["delta"] != "baseline":
            score = s.get("delta_score", 0)
            sign = "+" if score > 0 else ""
            delta_str = f" | Change: {s['delta']} ({sign}{score})"
        lines.append(
            f"  {day_label} ({s['created_at']}): {s['injury_type']} | "
            f"Severity: {s['severity']} ({s.get('severity_score', '?')}/10) | "
            f"Infection: {s.get('infection_risk', '?')}{delta_str}"
        )
    return "\n".join(lines)
