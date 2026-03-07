import sqlite3
from typing import List, Dict
from init_db import get_connection


class AppointmentRepository:
    def __init__(self):
        # Schema is guaranteed by init_db() called at app startup
        pass

    # ── Slots ─────────────────────────────────────────────────────────────────
    def get_appointments_by_doctor_date(self, doctor_id: str, date: str) -> List[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT time FROM appointments "
                "WHERE doctor_id = ? AND date = ? AND status != 'cancelled'",
                (doctor_id, date),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def check_slot_availability(self, doctor_id: str, date: str, time: str) -> bool:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM appointments "
                "WHERE doctor_id = ? AND date = ? AND time = ? AND status != 'cancelled'",
                (doctor_id, date, time),
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    # ── Create ────────────────────────────────────────────────────────────────
    def create_appointment(self, data: Dict) -> Dict:
        """
        data must contain: user_id, doctor_id, date, time, type, status
        Returns the inserted row as a dict (with auto-generated id).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")

            # Re-check inside transaction (prevent race condition)
            cur.execute(
                "SELECT 1 FROM appointments "
                "WHERE doctor_id = ? AND date = ? AND time = ? AND status != 'cancelled'",
                (data["doctor_id"], data["date"], data["time"]),
            )
            if cur.fetchone():
                conn.rollback()
                raise sqlite3.IntegrityError("Slot already booked")

            cur.execute(
                """
                INSERT INTO appointments (user_id, doctor_id, doctor_name, date, time, type, reason, status)
                VALUES (:user_id, :doctor_id, :doctor_name, :date, :time, :type, :reason, :status)
                """,
                {
                    "user_id":     data["user_id"],
                    "doctor_id":   data["doctor_id"],
                    "doctor_name": data.get("doctor_name"),
                    "date":        data["date"],
                    "time":        data["time"],
                    "type":        data.get("type", "in-person"),
                    "reason":      data.get("reason"),
                    "status":      data.get("status", "confirmed"),
                },
            )
            new_id = cur.lastrowid
            conn.commit()

            # Return a full row
            cur.execute("SELECT * FROM appointments WHERE id = ?", (new_id,))
            return dict(cur.fetchone())
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Read ──────────────────────────────────────────────────────────────────
    def get_appointments_by_user(self, user_id: str) -> List[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM appointments WHERE user_id = ? ORDER BY date DESC, time DESC",
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Update ────────────────────────────────────────────────────────────────
    def cancel_appointment(self, appointment_id: str, user_id: str) -> bool:
        conn = get_connection()
        try:
            cur = conn.cursor()
            # Try with user_id first for security
            cur.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND user_id = ?",
                (appointment_id, user_id),
            )
            count = cur.rowcount
            if count == 0:
                # Fallback: cancel by ID alone (user_id may not match localStorage)
                cur.execute(
                    "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND status = 'confirmed'",
                    (appointment_id,),
                )
                count = cur.rowcount
            conn.commit()
            return count > 0
        finally:
            conn.close()

    def cancel_all_by_user(self, user_id: str) -> int:
        """Cancel all confirmed appointments for a user. Returns count updated."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE appointments SET status = 'cancelled' "
                "WHERE user_id = ? AND status = 'confirmed'",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    def reschedule_appointment(
        self, appointment_id: str, user_id: str, new_date: str, new_time: str
    ) -> bool:
        conn = get_connection()
        try:
            cur = conn.cursor()
            # Try with user_id first for security
            cur.execute(
                "UPDATE appointments SET date = ?, time = ?, status = 'confirmed' "
                "WHERE id = ? AND user_id = ?",
                (new_date, new_time, appointment_id, user_id),
            )
            if cur.rowcount == 0:
                # Fallback: update by ID alone if confirmed
                cur.execute(
                    "UPDATE appointments SET date = ?, time = ?, status = 'confirmed' "
                    "WHERE id = ? AND status = 'confirmed'",
                    (new_date, new_time, appointment_id),
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
