"""
notifications_service.py — SQLite-backed notification system for MedicSense AI.

Schema used (from init_db.py):
    notifications(id INTEGER PK, user_id TEXT, title TEXT, message TEXT,
                  type TEXT, read INTEGER DEFAULT 0, created_at TIMESTAMP)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from init_db import get_connection

NotificationType = Literal["appointment", "medication", "health_tip", "system"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_load_json(path: str, default):
    import json, os
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


class NotificationsService:
    def __init__(self, data_dir: str = "data"):
        # data_dir kept for backward-compat signature; not used (SQLite now)
        pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _insert_row(
        self,
        *,
        user_id: str,
        title: str,
        message: str,
        ntype: str,
    ) -> int:
        """Insert one notification row and return its new id."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notifications (user_id, title, message, type) "
                "VALUES (?, ?, ?, ?)",
                (user_id, title, message, ntype),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def _exists_dedupe(self, user_id: str, title: str, message: str) -> bool:
        """Return True if an identical (user_id, title, message) already exists."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM notifications "
                "WHERE user_id = ? AND title = ? AND message = ? LIMIT 1",
                (user_id, title, message),
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch(
        self,
        *,
        user_id: str,
        filter_key: str = "all",
        limit: int = 50,
        cursor: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        """Return paginated notifications for a user, newest first."""
        limit = max(1, min(limit, 100))
        offset = cursor or 0

        where_clauses = ["user_id = ?"]
        params: list = [user_id]

        if filter_key == "unread":
            where_clauses.append("read = 0")
        elif filter_key == "appointments":
            where_clauses.append("type = 'appointment'")
        elif filter_key == "medications":
            where_clauses.append("type = 'medication'")
        elif filter_key == "health_tips":
            where_clauses.append("type = 'health_tip'")

        where_sql = " AND ".join(where_clauses)

        conn = get_connection()
        try:
            cur = conn.cursor()
            # Total for pagination
            cur.execute(
                f"SELECT COUNT(*) FROM notifications WHERE {where_sql}", params
            )
            total = cur.fetchone()[0]

            # Page
            params_page = params + [limit, offset]
            cur.execute(
                f"SELECT * FROM notifications WHERE {where_sql} "
                f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params_page,
            )
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

        # Map to frontend shape
        items = [self._to_frontend(r) for r in rows]
        next_cursor = offset + limit if (offset + limit) < total else None
        return items, next_cursor

    def summary(self, *, user_id: str) -> Dict[str, int]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ?", (user_id,)
            )
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read = 0",
                (user_id,),
            )
            unread = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND type = 'appointment'",
                (user_id,),
            )
            appointments = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND type = 'medication'",
                (user_id,),
            )
            medications = cur.fetchone()[0]
        finally:
            conn.close()

        return {
            "total": total,
            "unread": unread,
            "appointments": appointments,
            "medications": medications,
        }

    def mark_one_read(self, *, user_id: str, notification_id) -> bool:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?",
                (notification_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def mark_all_read(self, *, user_id: str) -> int:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    # ── Notification creation ─────────────────────────────────────────────────

    def create_appointment_notification(
        self,
        *,
        user_id: str,
        appointment_id: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create an immediate appointment notification (e.g., confirmation)."""
        if self._exists_dedupe(user_id, title, message):
            return False
        self._insert_row(user_id=user_id, title=title, message=message, ntype="appointment")
        return True

    def create_notification(
        self,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        dedupe_key: Optional[str] = None,
    ) -> bool:
        """Create a general notification."""
        if self._exists_dedupe(user_id, title, message):
            return False
        self._insert_row(user_id=user_id, title=title, message=message, ntype=notification_type)
        return True

    def refresh(self, *, user_id: str) -> Dict[str, int]:
        """Generate new notifications from data sources (appointment reminders, tips)."""
        created = 0
        created += self._generate_appointment_notifications(user_id=user_id)
        created += self._generate_health_tip_notifications(user_id=user_id)
        return {"created": created}

    # ── Generators ────────────────────────────────────────────────────────────

    def _generate_appointment_notifications(self, *, user_id: str) -> int:
        from repositories.appointment_repository import AppointmentRepository
        repo = AppointmentRepository()
        appts = repo.get_appointments_by_user(user_id)
        now = _utcnow()
        created = 0
        for a in appts:
            if (a.get("status") or "").lower() in ("cancelled", "canceled"):
                continue
            date_str = a.get("date")
            time_str = a.get("time")
            if not date_str or not time_str:
                continue
            try:
                base = datetime.strptime(date_str, "%Y-%m-%d")
                # try HH:MM first, then "HH:MM AM/PM"
                for fmt in ("%H:%M", "%I:%M %p"):
                    try:
                        t = datetime.strptime(time_str.strip(), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue
                appt_dt = base.replace(
                    hour=t.hour, minute=t.minute, second=0, microsecond=0,
                    tzinfo=timezone.utc
                )
            except Exception:
                continue

            delta = appt_dt - now
            aid = a.get("id")

            if timedelta(hours=23, minutes=50) <= delta <= timedelta(hours=24, minutes=10):
                title = "Appointment reminder"
                msg = f"You have an appointment tomorrow at {time_str}."
                if not self._exists_dedupe(user_id, title, msg):
                    self._insert_row(user_id=user_id, title=title, message=msg, ntype="appointment")
                    created += 1

            if timedelta(minutes=50) <= delta <= timedelta(hours=1, minutes=10):
                title = "Upcoming appointment"
                msg = f"Your appointment starts in about 1 hour ({time_str})."
                if not self._exists_dedupe(user_id, title, msg):
                    self._insert_row(user_id=user_id, title=title, message=msg, ntype="appointment")
                    created += 1

        return created

    def _generate_health_tip_notifications(self, *, user_id: str) -> int:
        now = _utcnow()
        day_key = now.date().isoformat()
        title = "Health tip"
        tip = self._pick_tip(seed=day_key)
        if not tip:
            return 0
        if self._exists_dedupe(user_id, title, tip):
            return 0
        self._insert_row(user_id=user_id, title=title, message=tip, ntype="health_tip")
        return 1

    def _pick_tip(self, seed: str) -> Optional[str]:
        kb = _safe_load_json("medical_kb.json", {})
        candidates: List[str] = []
        if isinstance(kb, dict):
            for v in kb.values():
                if isinstance(v, str) and 30 <= len(v) <= 140:
                    candidates.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and 30 <= len(item) <= 140:
                            candidates.append(item)
        if not candidates:
            return None
        return candidates[abs(hash(seed)) % len(candidates)]

    # ── Shape helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _to_frontend(row: Dict) -> Dict:
        return {
            "id": row["id"],
            "userId": row["user_id"],
            "title": row["title"],
            "message": row["message"],
            "type": row["type"],
            "read": bool(row.get("read", 0)),
            "timestamp": row.get("created_at", ""),
        }
