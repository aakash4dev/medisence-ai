import sqlite3
import os
from typing import List, Dict, Optional, Tuple

class AppointmentRepository:
    def __init__(self, db_path: str = "appointments.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    doctor_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    reason TEXT,
                    type TEXT DEFAULT 'in-person',
                    status TEXT DEFAULT 'confirmed',
                    name TEXT,
                    phone TEXT,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(doctor_id, date, time)
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def create_appointment(self, data: Dict) -> Dict:
        # data includes id, user_id, doctor_id, date, time, reason, type, status, created_at, name, phone, email
        # Use a new connection for this transaction to ensure isolation if needed,
        # but here we rely on the _get_connection context manager.
        # SQLite 'BEGIN IMMEDIATE' prevents other writers from starting.
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            # Double check availability inside transaction for safety
            cursor.execute('''
                SELECT 1 FROM appointments
                WHERE doctor_id = ? AND date = ? AND time = ? AND status != 'cancelled'
            ''', (data['doctor_id'], data['date'], data['time']))

            if cursor.fetchone():
                conn.rollback()
                raise sqlite3.IntegrityError("Slot already booked")

            # Ensure optional fields are present
            data.setdefault('name', '')
            data.setdefault('phone', '')
            data.setdefault('email', '')

            print(f"DEBUG: Inserting appointment for doctor={data['doctor_id']} date={data['date']} time={data['time']}")

            cursor.execute('''
                INSERT INTO appointments (id, user_id, doctor_id, date, time, reason, type, status, name, phone, email, created_at)
                VALUES (:id, :user_id, :doctor_id, :date, :time, :reason, :type, :status, :name, :phone, :email, :created_at)
            ''', data)
            conn.commit()
            return data
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_appointments_by_user(self, user_id: str) -> List[Dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM appointments
                WHERE user_id = ?
                ORDER BY date DESC, time DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_appointments_by_doctor_date(self, doctor_id: str, date: str) -> List[Dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT time FROM appointments
                WHERE doctor_id = ? AND date = ? AND status != 'cancelled'
            ''', (doctor_id, date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def check_slot_availability(self, doctor_id: str, date: str, time: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM appointments
                WHERE doctor_id = ? AND date = ? AND time = ? AND status != 'cancelled'
            ''', (doctor_id, date, time))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def cancel_appointment(self, appointment_id: str, user_id: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND user_id = ?",
                (appointment_id, user_id)
            )
            count = cursor.rowcount
            conn.commit()
            return count > 0
        finally:
            conn.close()

    def reschedule_appointment(self, appointment_id: str, user_id: str, new_date: str, new_time: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE appointments SET date = ?, time = ?, status = 'rescheduled' WHERE id = ? AND user_id = ?",
                (new_date, new_time, appointment_id, user_id)
            )
            count = cursor.rowcount
            conn.commit()
            return count > 0
        finally:
            conn.close()
