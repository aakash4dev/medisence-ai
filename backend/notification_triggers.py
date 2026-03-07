"""
notification_triggers.py — Phase 6: Automatic notification event bus.

ALL notifications must fire automatically from backend events, never from frontend.

Trigger points:
  A. Appointment booked       → called by appointment_service
  B. Appointment cancelled    → called by appointment_service
  C. Emergency detected       → called by /api/chat emergency path
  D. Chat contains intent     → "book" / "appointment" keywords in message
  E. High severity symptoms   → severity >= 2 in chat response

Usage:
    from notification_triggers import notification_triggers
    notification_triggers.on_appointment_booked(user_id, appointment)
    notification_triggers.on_appointment_cancelled(user_id, appointment_id)
    notification_triggers.on_emergency_detected(user_id, message)
    notification_triggers.on_booking_intent_detected(user_id, message)
    notification_triggers.on_high_severity(user_id, severity, symptoms)
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# ── Booking-intent keyword detection ─────────────────────────────────────────
_BOOKING_PATTERNS = [
    r"\bbook\b", r"\bappointment\b", r"\bschedule\b", r"\bsee a doctor\b",
    r"\bsee the doctor\b", r"\bvisit a doctor\b", r"\bclinic\b",
    r"\bconsult\b", r"\breservation\b", r"\bbook a slot\b", r"\bget an appointment\b",
]
_BOOKING_RE = re.compile("|".join(_BOOKING_PATTERNS), re.IGNORECASE)


def has_booking_intent(message: str) -> bool:
    """Return True if message contains appointment booking intent keywords."""
    return bool(_BOOKING_RE.search(message))


# ── NotificationTriggers service ─────────────────────────────────────────────

class NotificationTriggers:
    """
    Thin wrapper that translates backend events into notification records.
    Injected with the NotificationsService at app startup — keeps triggers
    decoupled from the notification storage layer.
    """

    def __init__(self):
        self._svc = None  # set by inject()

    def inject(self, notifications_service) -> None:
        """Called once at app startup to wire in the notifications service."""
        self._svc = notifications_service

    def _fire(self, *, user_id: str, notification_type: str, title: str, message: str) -> bool:
        """Safe wrapper — logs but never raises on failure."""
        if not self._svc:
            print("[WARN] notification_triggers.inject() not called yet")
            return False
        try:
            return self._svc.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
            )
        except Exception as exc:
            print(f"[WARN] Notification trigger failed: {exc}")
            return False

    # ── Trigger A: Appointment booked ─────────────────────────────────────────
    def on_appointment_booked(
        self,
        *,
        user_id: str,
        appointment: Dict[str, Any],
    ) -> bool:
        """Fire automatically when an appointment is successfully created."""
        doctor_id = appointment.get("doctor_id", "your doctor")
        date = appointment.get("date", "")
        time_ = appointment.get("time", "")
        appt_id = appointment.get("id", "")
        return self._fire(
            user_id=user_id,
            notification_type="appointment",
            title="✅ Appointment Confirmed",
            message=(
                f"Your appointment with Dr. {doctor_id} on {date} at {time_} "
                f"has been confirmed (ID: {appt_id}). We'll remind you closer to the time."
            ),
        )

    # ── Trigger B: Appointment cancelled ─────────────────────────────────────
    def on_appointment_cancelled(
        self,
        *,
        user_id: str,
        appointment_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Fire automatically when an appointment is cancelled."""
        msg = f"Appointment #{appointment_id} has been cancelled."
        if reason:
            msg += f" Reason: {reason}"
        msg += " You can book a new appointment any time."
        return self._fire(
            user_id=user_id,
            notification_type="appointment",
            title="❌ Appointment Cancelled",
            message=msg,
        )

    # ── Trigger C: Emergency detected ────────────────────────────────────────
    def on_emergency_detected(
        self,
        *,
        user_id: str,
        message: str,
    ) -> bool:
        """Fire automatically when emergency keywords are detected in chat."""
        return self._fire(
            user_id=user_id,
            notification_type="system",
            title="🚨 Emergency Situation Detected",
            message=(
                "MedicSense detected potential emergency keywords in your message. "
                "Please call emergency services (112 / 911) immediately. "
                "Your message has been flagged for review."
            ),
        )

    # ── Trigger D: Booking intent in chat ────────────────────────────────────
    def on_booking_intent_detected(
        self,
        *,
        user_id: str,
        message: str,
    ) -> bool:
        """
        Fire automatically when the chat message contains booking-related keywords.
        Suggests the user visit the appointments page.
        """
        return self._fire(
            user_id=user_id,
            notification_type="appointment",
            title="📅 Want to Book an Appointment?",
            message=(
                "It looks like you might want to book a doctor's appointment. "
                "Head to the Appointments section to find a doctor and book a slot."
            ),
        )

    # ── Trigger E: High severity symptoms in chat ─────────────────────────────
    def on_high_severity(
        self,
        *,
        user_id: str,
        severity: int,
        symptoms: list,
    ) -> bool:
        """Fire automatically when chat classifier detects moderate/high severity."""
        sev_label = {2: "Moderate", 3: "Severe", 4: "Critical"}.get(severity, "High")
        symp_str = ", ".join(symptoms[:3]) if symptoms else "reported symptoms"
        return self._fire(
            user_id=user_id,
            notification_type="appointment",
            title=f"⚕️ {sev_label} Symptoms — See a Doctor",
            message=(
                f"Based on your {symp_str}, MedicSense recommends seeing a "
                f"healthcare professional soon. Book an appointment from the "
                f"Appointments section."
            ),
        )


# ── Singleton ─────────────────────────────────────────────────────────────────
notification_triggers = NotificationTriggers()
