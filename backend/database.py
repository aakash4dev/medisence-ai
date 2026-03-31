"""
Database Module for MedicSense AI — SQLite backend
Handles users, conversations, and messages tables.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from init_db import get_connection


class Database:
    """SQLite-backed database for users, conversations, and messages."""

    # ── Users ──────────────────────────────────────────────────────────────────
    def create_user(self, user_id: str, user_data: Dict) -> Dict:
        """
        Insert or replace a user record.
        Expected keys in user_data: email, name, phone, auth_method,
        google_id, google_email, password_hash, last_active.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO users (
                    id, name, email, phone, auth_method,
                    google_id, google_email, password_hash, last_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_data.get("name", ""),
                    user_data.get("email", "").lower().strip(),
                    user_data.get("phone", ""),
                    user_data.get("auth_method", "email_password"),
                    user_data.get("google_id"),
                    user_data.get("google_email"),
                    user_data.get("password_hash"),
                    user_data.get("last_active"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return self.get_user(user_id)

    def get_user(self, user_id: str) -> Optional[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_google_id(self, google_id: str) -> Optional[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM users WHERE google_id = ?", (google_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update any allowed field for a user."""
        allowed = {
            "name", "email", "phone", "auth_method",
            "google_id", "google_email", "password_hash", "last_active"
        }
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE users SET {set_clause} WHERE id = ?", values
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def delete_user(self, user_id: str) -> bool:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ── Conversations ──────────────────────────────────────────────────────────
    def create_conversation(self, user_id: str) -> int:
        """Create a new conversation and return its id."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO conversations (user_id) VALUES (?)", (user_id,)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_conversations(self, user_id: str, limit: int = 20) -> List[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM conversations WHERE user_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Messages ───────────────────────────────────────────────────────────────
    def add_message(
        self, conversation_id: int, role: str, content: str
    ) -> Dict:
        """role must be 'user' or 'assistant'."""
        assert role in ("user", "assistant"), f"Invalid role: {role}"
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content) "
                "VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )
            conn.commit()
            new_id = cur.lastrowid
            cur.execute("SELECT * FROM messages WHERE id = ?", (new_id,))
            return dict(cur.fetchone())
        finally:
            conn.close()

    def get_messages(
        self, conversation_id: int, limit: int = 50
    ) -> List[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at ASC LIMIT ?",
                (conversation_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Legacy shim: save_conversation (used by old app.py calls) ─────────────
    def save_conversation(
        self, user_id: str, message: str, response: str, severity: int = 0
    ):
        """Backward-compat shim — creates a conversation + two messages."""
        conv_id = self.create_conversation(user_id)
        self.add_message(conv_id, "user", message)
        self.add_message(conv_id, "assistant", response)


# Singleton
db = Database()
