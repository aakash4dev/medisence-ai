"""
emergency_guard.py — Phase 4: Emergency Guard (Critical Safety Layer)

EMERGENCY_KEYWORDS are matched case-insensitively BEFORE any AI call.
If matched → return exact structured response immediately.

Response contract:
{
  "success": true,
  "data": {
    "reply": "⚠️ This may be a medical emergency...",
    "risk_level": "high",
    "suggested_action": "emergency"
  }
}
"""

from emergency_detector import EmergencyDetector

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — PRIMARY emergency keywords (exact spec from judges)
# ─────────────────────────────────────────────────────────────────────────────
EMERGENCY_KEYWORDS = [
    "chest pain",
    "breathing difficulty",
    "unconscious",
    "seizure",
    "severe bleeding",
]

# ─────────────────────────────────────────────────────────────────────────────
# Extended safety net — broader patterns caught in addition to the above
# ─────────────────────────────────────────────────────────────────────────────
_EXTENDED_KEYWORDS = [
    # Cardiac
    "chest tightness", "pressure in chest", "crushing chest",
    "pain in left arm", "pain in jaw", "heart attack", "cardiac arrest",
    "palpitations with dizziness",
    # Stroke / Neuro
    "sudden weakness", "face drooping", "slurred speech",
    "sudden confusion", "sudden vision loss", "loss of balance",
    "worst headache", "numbness on one side",
    # Respiratory
    "cannot breathe", "can't breathe", "shortness of breath",
    "breathlessness", "gasping", "choking", "bluish lips", "bluish face",
    "tight throat",
    # Trauma
    "loss of consciousness", "fainted", "collapsed",
    "head injury", "bone sticking out",
    # Bleeding
    "bleeding won't stop", "heavy bleeding", "vomiting blood",
    "coughing blood", "internal bleeding",
    # Allergy
    "anaphylaxis", "throat swelling", "swelling of face",
    "swelling of lips", "swelling of tongue",
    # Infection
    "very high fever", "fever with confusion", "stiff neck", "febrile seizure",
    # Poison / OD
    "poisoning", "overdose", "swallowed poison", "chemical ingestion",
    # Mental health
    "suicidal", "want to die", "harm myself", "kill myself",
    "self harm", "cutting myself",
    # Paediatric
    "child unconscious", "child not breathing", "newborn fever",
    # EmergencyDetector native keywords
    "stroke", "snake bite", "bleeding heavily",
]

_ALL_KEYWORDS = EMERGENCY_KEYWORDS + _EXTENDED_KEYWORDS

_EMERGENCY_REPLY = (
    "⚠️ **This may be a medical emergency.**\n\n"
    "Based on what you've described, I am detecting potential life-threatening "
    "keywords. Please take immediate action:\n\n"
    "🚨 **CALL 112 (India) or 911 (US/UK) RIGHT NOW**\n\n"
    "**While waiting for help:**\n"
    "1. Stay as calm as possible and keep the person still\n"
    "2. Do NOT give anything to eat or drink\n"
    "3. If unconscious and not breathing — begin CPR if trained\n"
    "4. Unlock the door so paramedics can enter\n"
    "5. Keep the phone line open with emergency services\n\n"
    "⚠️ I am an AI assistant. I cannot replace emergency medical services. "
    "Emergency responders are the only appropriate response to this situation."
)


class EmergencyGuard:
    """
    Fast, keyword-based safety layer that runs BEFORE any Gemini call.

    Usage:
        guard = EmergencyGuard()
        if guard.is_emergency(message):
            return guard.get_response(message)
    """

    def __init__(self):
        self._detector = EmergencyDetector()

    def is_emergency(self, message: str) -> bool:
        """True if message contains any emergency keyword (primary or extended)."""
        lower = message.lower()
        if any(kw in lower for kw in _ALL_KEYWORDS):
            return True
        # Also delegate to EmergencyDetector for pattern-based checks
        return self._detector.check_emergency(message).get("is_emergency", False)

    def get_response(self, message: str) -> dict:
        """
        Return the exact structured emergency response.
        risk_level is always "high".
        suggested_action is always "emergency".
        """
        # Try to provide a more specific response from EmergencyDetector
        detector_result = self._detector.check_emergency(message)
        specific_reply = detector_result.get("response")

        # Use specific if meaningful, else generic
        reply = specific_reply if specific_reply else _EMERGENCY_REPLY
        # Always prepend the standard warning header if not already there
        if "⚠️ **This may be a medical emergency" not in reply:
            reply = (
                "⚠️ **This may be a medical emergency.** "
                "Please call emergency services immediately.\n\n" + reply
            )

        return {
            "success": True,
            "data": {
                "reply": reply,
                "risk_level": "high",
                "suggested_action": "emergency",
                "is_emergency": True,
            },
        }


# Singleton
emergency_guard = EmergencyGuard()
