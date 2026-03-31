"""
chat_service.py — Phase 3 (v2): Hardened AI Intelligence Layer

Fixes applied:
  Fix 1 — Cleaner, tight system prompt (no disclaimer repetition, no over-control)
  Fix 2 — Structured JSON output: Gemini asked to reply in strict JSON, parsed here
  Fix 3 — Memory injection upgrade: clean ROLE: content context block
  Fix 4 — Repetition guard: prevents identical consecutive AI replies
  Fix 6 — Emergency context isolation: emergency exchanges excluded from memory
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from gemini_service import gemini_service
from severity_classifier import SeverityClassifier
from symptom_analyzer import SymptomAnalyzer

# ─────────────────────────────────────────────────────────────────────────────
# Fix 1 — Cleaner System Prompt
# No disclaimer repetition. No over-control. Medically logical structure.
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are MedicSense AI — an AI medical assistant. You support health awareness.

Rules:
- Never diagnose. Never say "You have [Disease]".
- Never recommend prescription drugs by name.
- Never invent statistics or dosages.
- Do not repeat previous responses unless the user asks.
- Be concise but medically logical.
- If life-threatening symptoms → say CALL 112 / 911 immediately.

Respond strictly in this JSON format:
{
  "assessment": "One empathetic sentence acknowledging what the user described.",
  "risk_level": "low | moderate | high | critical",
  "possible_causes": ["Cause 1", "Cause 2", "Cause 3"],
  "recommendations": ["Action 1", "Action 2", "Action 3"],
  "when_to_seek_care": "Specific escalation trigger(s).",
  "follow_up_question": "One clarifying question to help narrow assessment (optional)."
}

Do NOT add text outside the JSON. Do NOT wrap in markdown code blocks.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Fallback when JSON parse fails or Gemini returns nothing
# ─────────────────────────────────────────────────────────────────────────────
_SAFE_JSON_FALLBACK = {
    "assessment": "I understand you have some health concerns. Let me help you assess them.",
    "risk_level": "low",
    "possible_causes": ["Stress or fatigue", "Minor viral illness", "Environmental factors"],
    "recommendations": [
        "Rest and stay well-hydrated",
        "Monitor symptoms over the next 24-48 hours",
        "Consult a healthcare professional if symptoms persist or worsen",
    ],
    "when_to_seek_care": "Seek immediate care if you experience difficulty breathing, chest pain, or loss of consciousness.",
    "follow_up_question": "How long have you been experiencing these symptoms?",
}

# Risk → action mapping
_RISK_TO_SEVERITY = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
_SEVERITY_TO_RISK = {1: "low", 2: "moderate", 3: "high", 4: "critical"}
_ACTION_LABELS = {
    1: "rest_and_monitor",
    2: "see_doctor_soon",
    3: "seek_urgent_care",
    4: "call_emergency_services",
}

# Repetition guard state (per-process memory — fine for single-worker Flask)
_last_replies: dict[str, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# ChatResult — clean output contract
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ChatResult:
    reply: str           # formatted human-readable reply
    risk_level: str
    suggested_action: str
    severity: int
    symptoms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "reply": self.reply,
            "risk_level": self.risk_level,
            "suggested_action": self.suggested_action,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ChatService
# ─────────────────────────────────────────────────────────────────────────────
class ChatService:
    def __init__(self):
        self._analyzer = SymptomAnalyzer()
        self._classifier = SeverityClassifier()

    def process(self, message: str, history: List[Dict], user_id: str = "default") -> ChatResult:
        """
        Main entry point. All 6 fixes applied here.

        Args:
            message:  Validated user message.
            history:  List of {role, content, is_emergency?} dicts.
            user_id:  Used for repetition guard.
        """
        # 1. Classify severity from message
        try:
            symptoms = self._analyzer.extract_symptoms(message)
            severity = self._classifier.classify(message, symptoms)
        except Exception:
            symptoms = []
            severity = 1

        # 2. Fix 3 — Build clean context block (exclude emergency turns per Fix 6)
        context_block = self._build_context_block(history)

        # 3. Build full prompt
        sev_label = {1: "Mild", 2: "Moderate", 3: "Severe", 4: "Critical"}.get(severity, "Mild")
        prompt_parts = [
            SYSTEM_PROMPT,
            f"[Triage context: {sev_label} severity ({severity}/4)]",
        ]
        if context_block:
            prompt_parts.append(f"Conversation so far:\n{context_block}")
        prompt_parts.append(f"USER: {message}")
        full_prompt = "\n\n".join(prompt_parts)

        # 4. Call Gemini
        raw = gemini_service.chat_with_history(
            message=message,
            history=history,
            severity=severity,
            _override_prompt=full_prompt,  # pass our structured prompt
        )

        # 5. Fix 2 — Parse structured JSON
        parsed = self._parse_json_response(raw)

        # 6. Determine severity from AI risk_level (take max of classifier + AI)
        ai_severity = _RISK_TO_SEVERITY.get(parsed.get("risk_level", "low"), 1)
        final_severity = max(severity, ai_severity)

        # 7. Format human-readable reply
        reply = self._format_reply(parsed, final_severity)

        # 8. Fix 4 — Repetition guard
        reply = self._guard_repetition(reply, user_id)

        return ChatResult(
            reply=reply,
            risk_level=_SEVERITY_TO_RISK.get(final_severity, "low"),
            suggested_action=_ACTION_LABELS.get(final_severity, "rest_and_monitor"),
            severity=final_severity,
            symptoms=symptoms,
        )

    # ── Fix 3: Memory Injection Upgrade ──────────────────────────────────────

    def _build_context_block(self, history: List[Dict]) -> str:
        """
        Fix 3: Clean ROLE: content format, last 6 turns.
        Fix 6: Skip emergency exchanges to avoid contaminating future context.
        """
        if not history:
            return ""

        lines = []
        for turn in history[-6:]:
            # Fix 6 — skip emergency turns
            if turn.get("is_emergency"):
                continue
            role = turn.get("role", "user").upper()
            content = (turn.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")

        return "\n".join(lines)

    # ── Fix 2: JSON Response Parser ───────────────────────────────────────────

    def _parse_json_response(self, raw: str) -> dict:
        """
        Attempt to extract JSON from Gemini response.
        Falls back to safe defaults on any parse failure.
        """
        if not raw or len(raw.strip()) < 5:
            return _SAFE_JSON_FALLBACK.copy()

        text = raw.strip()

        # Strip markdown fences if present (```json ... ```)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if fence_match:
            text = fence_match.group(1).strip()

        # Find the outermost JSON object
        brace_match = re.search(r"\{[\s\S]+\}", text)
        if brace_match:
            text = brace_match.group(0)

        try:
            data = json.loads(text)
            # Validate required keys exist
            required = {"assessment", "risk_level", "recommendations"}
            if not required.issubset(data.keys()):
                raise ValueError("Missing required JSON fields")
            # Normalise risk_level
            rl = str(data.get("risk_level", "low")).lower()
            if rl not in _RISK_TO_SEVERITY:
                rl = "low"
            data["risk_level"] = rl
            return data
        except Exception as exc:
            print(f"[INFO] JSON parse failed ({type(exc).__name__}), using safe fallback")
            return _SAFE_JSON_FALLBACK.copy()

    # ── Format parsed JSON → readable reply ──────────────────────────────────

    def _format_reply(self, data: dict, severity: int) -> str:
        """Convert parsed JSON fields into a clean Markdown reply."""
        parts = []

        # Assessment
        assessment = data.get("assessment", "")
        if assessment:
            parts.append(assessment)

        # Triage badge
        badge = {1: "🟢 Mild", 2: "🟡 Moderate", 3: "🔴 Severe", 4: "🚨 Critical"}.get(severity, "🟢 Mild")
        parts.append(f"\n**Triage Level:** {badge}")

        # Possible causes
        causes = data.get("possible_causes", [])
        if causes:
            parts.append("\n**What This May Indicate:**")
            for c in causes[:3]:
                parts.append(f"• {c}")

        # Recommendations
        recs = data.get("recommendations", [])
        if recs:
            parts.append("\n**Recommendations:**")
            for r in recs[:5]:
                parts.append(f"• {r}")

        # When to seek care
        when = data.get("when_to_seek_care", "")
        if when:
            parts.append(f"\n**When to Seek Care:** {when}")

        # Emergency directive for high/critical
        if severity >= 3:
            parts.append(
                "\n🚨 **If symptoms are severe or rapidly worsening, "
                "call emergency services (112 / 911) immediately.**"
            )

        # Follow-up question
        fq = data.get("follow_up_question", "")
        if fq:
            parts.append(f"\n_{fq}_")

        return "\n".join(parts)

    # ── Fix 4: Repetition Guard ───────────────────────────────────────────────

    def _guard_repetition(self, reply: str, user_id: str) -> str:
        """
        Fix 4: If new reply matches the previous one for this user,
        append a perspective-shift note.
        """
        key = user_id
        last = _last_replies.get(key, "")
        if last and last.strip() == reply.strip():
            reply += (
                "\n\n_Let me add another perspective: if your symptoms "
                "haven't improved after 48 hours, a clinical evaluation "
                "would give a clearer picture than self-assessment alone._"
            )
        _last_replies[key] = reply
        return reply


# Singleton
chat_service = ChatService()
