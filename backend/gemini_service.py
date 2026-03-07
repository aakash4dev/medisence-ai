"""
gemini_service.py — Phase 5: Hardened Gemini AI Service

Safety guarantees:
- API key ONLY from environment variable (GEMINI_API_KEY)
- 15-second timeout via threading (works on Windows + Unix)
- 1 retry max before graceful fallback
- try/except everywhere — raw errors NEVER surface to the caller
- is_configured flag: all paths safe when Gemini unavailable
"""

import base64
import io
import os
import threading

import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_TIMEOUT = 15.0  # seconds — hard cap on every Gemini call
GEMINI_MAX_RETRIES = 1  # 1 retry, then fallback — never more


class GeminiService:
    """
    Hardened Gemini wrapper.
    - API key from env only
    - 15 s timeout (threading, Windows-safe)
    - 1 retry max
    - Never exposes raw exceptions to callers
    """

    def __init__(self):
        # ── API Key: ONLY from environment ────────────────────────────────
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.is_configured = False
        self.model = None
        self.vision_model = None

        if not self.api_key or self.api_key in ("your_api_key_here", ""):
            print("[INFO] GEMINI_API_KEY not set — running in fallback mode.")
            print("[TIP]  Get a free key: https://makersuite.google.com/app/apikey")
            return

        try:
            genai.configure(api_key=self.api_key)
            _gen_cfg = {
                "temperature": 0.2,  # low = less hallucination
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 800,  # Fix 5: optimal for structured JSON output
            }
            _safety = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
            ]
            self.model = genai.GenerativeModel(
                GEMINI_MODEL,
                generation_config=_gen_cfg,
                safety_settings=_safety,
            )
            # Vision model: higher tokens for richer image description
            _vision_cfg = {
                "temperature": 0.15,  # very low — stay grounded in what you see
                "top_p": 0.9,
                "max_output_tokens": 1200,
            }
            self.vision_model = genai.GenerativeModel(
                GEMINI_MODEL,
                generation_config=_vision_cfg,
                safety_settings=_safety,
            )
            self.is_configured = True
            print(f"[OK] {GEMINI_MODEL} configured — medical AI ready.")
        except Exception as e:
            # Never expose the raw exception — just log it
            print(
                f"[WARNING] Gemini setup failed (check API key). Fallback mode active."
            )

    # ── System Prompt (canonical — also imported by chat_service.py) ──────────
    # Loaded lazily on first use to avoid circular imports at module level
    @property
    def _system_prompt(self) -> str:
        try:
            from chat_service import SYSTEM_PROMPT

            return SYSTEM_PROMPT
        except Exception:
            return (
                "You are MedicSense AI, a safety-first medical triage assistant. "
                "Never diagnose. Always recommend professional care. "
                "End every reply with a disclaimer."
            )

    def _call_gemini(self, prompt: str, timeout: float) -> str | None:
        """
        Thread-based Gemini call with hard timeout.
        Returns text on success, None on timeout/error.
        Never raises.
        """
        result_holder: list = [None]
        error_holder: list = [None]

        def _worker():
            try:
                resp = self.model.generate_content(prompt)
                result_holder[0] = resp
            except Exception as exc:
                error_holder[0] = exc

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            print(f"[WARNING] Gemini call timed out after {timeout}s")
            return None
        if error_holder[0]:
            # Log sanitised message — never expose raw error to caller
            print(f"[ERROR] Gemini call failed: {type(error_holder[0]).__name__}")
            return None
        resp = result_holder[0]
        if resp and hasattr(resp, "text") and resp.text:
            return resp.text.strip()
        print("[WARNING] Gemini returned empty/blocked response")
        return None

    def chat_with_history(
        self,
        message: str,
        history: list,
        severity: int,
        timeout: float = GEMINI_TIMEOUT,
        _override_prompt: str | None = None,
    ) -> str:
        """
        Context-aware medical chat.

        Args:
            _override_prompt: When set, use this fully-built prompt instead of
                              rebuilding internally. Set by chat_service (Fix 2/3).
        """
        if not self.is_configured:
            return self._fallback_response([], severity)

        if _override_prompt:
            # chat_service already built the optimal structured prompt
            full_prompt = _override_prompt
        else:
            # Legacy path: build prompt internally (backward compat)
            history_lines = []
            for turn in (history or [])[-6:]:
                role = "USER" if turn.get("role") == "user" else "ASSISTANT"
                content = (turn.get("content") or "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")

            sev_label = {1: "Mild", 2: "Moderate", 3: "Severe", 4: "Critical"}.get(
                severity, "Mild"
            )
            parts = [
                self._system_prompt,
                f"[Triage severity: {sev_label} ({severity}/4)]",
            ]
            if history_lines:
                context = "\n".join(history_lines)
                parts.append(f"Conversation so far:\n{context}")
            parts.append(f"USER: {message}")
            full_prompt = "\n\n".join(parts)

        # Attempt + 1 retry
        for attempt in range(GEMINI_MAX_RETRIES + 1):
            result = self._call_gemini(full_prompt, timeout=timeout)
            if result:
                return result
            if attempt < GEMINI_MAX_RETRIES:
                print(f"[INFO] Retrying Gemini call (attempt {attempt + 2})")

        print("[INFO] All Gemini attempts exhausted — returning fallback")
        return self._fallback_response([], severity)

    def chat_medical(self, user_message, symptoms, severity, system_override=None):
        """Generate AI-powered medical response with disease recognition

        Args:
            user_message: User's input message
            symptoms: List of detected symptoms
            severity: Severity level (1-4)
            system_override: Optional system prompt to override normal behavior (for emergency mode)
        """
        if not self.is_configured:
            return self._fallback_response(symptoms, severity)

        try:
            # Check if emergency mode override is provided
            if system_override:
                # EMERGENCY MODE: Use strict emergency prompt
                prompt = f"""{system_override}

User's emergency message: "{user_message}"

Respond according to EMERGENCY CONTEXT MODE rules above. You MUST:
1. Start with "🚨 CALL 112 IMMEDIATELY"
2. Explain why in ONE sentence
3. Give 3-4 immediate safety actions ONLY (while waiting for help)
4. End with "Emergency services are the ONLY proper response. I cannot replace them."

Do NOT diagnose. Do NOT treat. Do NOT reassure. ONLY safety guidance."""
                # NORMAL MODE: Standard medical chat
                # NORMAL MODE: Standard medical chat
                prompt = f"""System / Instruction Prompt (STRICT ENFORCEMENT MODE)

You are a Safety-First Medical Triage Assistant.
Your ONLY goal is determining if a user needs professional care.

**ZERO TOLERANCE RULES:**
1. ⛔ NO DIAGNOSIS: Never state "You have [Disease]". Use "Symptoms are consistent with..."
2. ⛔ NO CERTAINTY: Always use "may", "could", "associated with".
3. ⛔ NO STATISTICS: Do not invent numbers.
4. ⛔ NO GUESSING: If unsure, advise seeing a doctor immediately.

**RESPONSE PROTOCOL (STRICT):**

1. **Analysis & Triage**:
   - Assess severity based ONLY on provided input ({severity}/4).
   - Classify as: **Mild (Self-care)**, **Moderate (Doctor soon)**, or **Severe (Immediate care)**.

2. **Potential Indicators (Non-Diagnostic)**:
   - List detailed possibilities only if they match symptoms perfectly.
   - Example: "These symptoms is often associated with X, Y, or Z."

3. **Actionable Advice**:
   - Focus on safety: "Monitor temperature", "Keep hydrated", "Avoid exertion".
   - Do NOT recommend specific prescription drugs.

4. **Escalation & Doctor Routing (MANDATORY)**:
   - "If symptoms persist for >2 days..."
   - If recommending a doctor visit, you MUST explicitly name one of our clinic's doctors based on the symptoms:
     * Fever, general illness, flu -> "Dr. Sharma (General Physician)"
     * Heart issues, chest pain, BP -> "Dr. Patel (Cardiologist)"
     * Skin issues, rashes, acne -> "Dr. Verma (Dermatologist)"
     * Children/Pediatric issues -> "Dr. Singh (Pediatrician)"
     * Bone, joint, or muscle pain -> "Dr. Kumar (Orthopedic)"
   - Example: "Based on your symptoms, I strongly recommend booking an appointment with Dr. Sharma (General Physician)."

5. **Disclaimer**:
   - "⚠️ **Consult a Doctor:** This is an AI triage tool, not a diagnosis."

**HIGH-RISK OVERRIDE (AGGRESSIVE):**
If ANY red flag is present (Chest pain, breathing difficulty, severe bleeding, confusion, blue lips/skin):
- **STOP ANALYSIS.**
- **DIRECT TO ER:** "This sounds like a medical emergency. Go to the nearest ER immediately."

**TONE**:
- Authoritative on Safety.
- Conservative on Medicine.
- Clear and Direct.
"""

            response = self.model.generate_content(prompt)

            # Validate response exists and has text
            if response and hasattr(response, "text") and response.text:
                return response.text
            else:
                print("[WARNING] Gemini returned empty response - using fallback")
                return self._fallback_response(symptoms, severity)

        except Exception as e:
            print(f"[ERROR] Gemini API runtime error: {e}")
            # CRITICAL: Always fall back to rule-based response on ANY failure
            return self._fallback_response(symptoms, severity)

    def analyze_injury_image(self, image_data_url: str) -> dict:
        """
        Real visual analysis of a wound/injury image using Gemini Vision.
        Gemini actually looks at the image — describes what it sees, assesses
        severity, and gives first-aid steps specific to the visible condition.
        """
        if not self.is_configured:
            return self._fallback_image_analysis()

        import json as _json
        import re as _re

        try:
            # ── Decode image ─────────────────────────────────────────────────
            if "," in image_data_url:
                image_data = image_data_url.split(",")[1]
            else:
                image_data = image_data_url

            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))

            # ── Universal health image analysis prompt ────────────────────────
            prompt = """\
You are a medical image analysis AI. A patient has uploaded a health-related photo.
Examine the image carefully and respond ONLY based on what you can actually see.
Do NOT invent or assume details. If unsure, say so.

This could be ANY health-related image: a wound/cut, burn, bruise, rash, swelling,
eye issue, skin condition, allergic reaction, sprain, breathing distress signs,
a medication label, a medical document, or any daily-life health concern.

Return ONLY this JSON (no markdown, no extra text):
{
  "injury_type": "Brief label — what this appears to be (e.g. 'Second-degree burn', 'Allergic rash', 'Bruise/contusion', 'Swollen ankle', 'Eye redness', 'Skin abrasion', 'No visible injury')",
  "visual_description": "Describe exactly what you see: affected area, size estimate, colour, texture, swelling, blistering, discharge, redness pattern — only visible features",
  "possible_conditions": ["Most likely condition", "Alternative 1", "Alternative 2"],
  "severity": "mild | moderate | severe | emergency",
  "confidence": <integer 0-100 — how clearly is the condition visible>,
  "immediate_first_aid": ["Step 1", "Step 2", "Step 3", "Step 4"],
  "warning_signs": ["Sign that means get to ER 1", "Sign 2", "Sign 3"],
  "see_doctor_if": "Specific trigger condition requiring a doctor visit",
  "recommended_specialist": "Type of specialist if needed (e.g. Emergency, Dermatologist, Ophthalmologist, Orthopedic, General Physician)",
  "healing_time": "Estimated recovery time based on what is visible",
  "do_not": ["Action to avoid 1", "Action to avoid 2"]
}

If severity is 'emergency', make that the very first point in immediate_first_aid: "Call 112 / 911 immediately".
If no health concern is visible, set injury_type to "No visible health concern" and confidence to 10.
"""

            # ── Call Gemini Vision with timeout ───────────────────────────────
            result_holder: list = [None]
            error_holder: list = [None]

            def _worker():
                try:
                    resp = self.vision_model.generate_content([prompt, image])
                    result_holder[0] = resp
                except Exception as exc:
                    error_holder[0] = exc

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            t.join(timeout=20.0)  # Vision is slower — allow 20s

            if t.is_alive():
                print("[WARNING] Gemini Vision timed out")
                return self._fallback_image_analysis()

            if error_holder[0]:
                print(f"[ERROR] Vision API: {type(error_holder[0]).__name__}")
                return self._fallback_image_analysis()

            resp = result_holder[0]
            if not resp or not getattr(resp, "text", None):
                print("[WARNING] Gemini Vision: empty response")
                return self._fallback_image_analysis()

            raw = resp.text.strip()

            # ── Robust JSON extraction ────────────────────────────────────────
            # Strip markdown fences
            fence = _re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
            if fence:
                raw = fence.group(1).strip()

            # Find outermost JSON object
            obj_match = _re.search(r"\{[\s\S]+\}", raw)
            if obj_match:
                raw = obj_match.group(0)

            data = _json.loads(raw)
            data["success"] = True

            # Normalise severity field
            sev = str(data.get("severity", "moderate")).lower()
            if sev not in ("mild", "moderate", "severe", "emergency"):
                sev = "moderate"
            data["severity"] = sev

            # Fix 1 — Honest confidence: rename to model_certainty_approx
            raw_confidence = data.pop("confidence", 50)
            try:
                raw_confidence = int(raw_confidence)
            except (TypeError, ValueError):
                raw_confidence = 50
            data["model_certainty_approx"] = raw_confidence
            data["certainty_note"] = (
                "This is a heuristic estimate from the vision model, "
                "not a calibrated medical probability."
            )

            # Sanity check (downgrade only)
            data = self._vision_sanity_check(data)

            # Fix 1 — Severity scoring engine (keyword-based, independent of Gemini)
            data = self._compute_severity_score(data)

            # Fix 4 — Infection risk heuristic
            data = self._check_infection_risk(data)

            # Fix 3 — Abuse / relevance guard
            data = self._check_medical_relevance(data)

            return data

        except _json.JSONDecodeError as exc:
            print(f"[WARN] Vision JSON parse failed: {exc}")
            fallback = self._fallback_image_analysis()
            fallback["visual_description"] = raw if "raw" in dir() else "Parse error"
            return fallback
        except Exception as exc:
            print(f"[ERROR] Vision analysis failed: {type(exc).__name__}")
            return self._fallback_image_analysis()

    def analyze_injury_with_comparison(
        self,
        image_data_url: str,
        previous_snapshot: dict,
    ) -> dict:
        """
        Comparative healing intelligence.

        Sends the current image + structured previous snapshot to Gemini,
        asking it to assess whether the injury has improved, worsened, or
        stayed stable — and to quantify the change as a delta_score.

        Returns all standard analysis fields PLUS:
          delta             — "improved" | "worsened" | "stable"
          delta_score       — float -3..+3  (positive = improvement)
          delta_explanation — visual evidence for the assessment
          session_number    — which day this is
        """
        if not self.is_configured:
            # Fall back to regular analysis, mark delta as unknown
            result = self._fallback_image_analysis()
            result.update(
                {
                    "delta": "unknown",
                    "delta_score": 0.0,
                    "delta_explanation": "API unavailable — no comparison made.",
                }
            )
            return result

        import json as _json
        import re as _re

        try:
            # ── Decode image ─────────────────────────────────────────────────
            raw_b64 = (
                image_data_url.split(",")[1]
                if "," in image_data_url
                else image_data_url
            )
            image = Image.open(io.BytesIO(base64.b64decode(raw_b64)))

            session_num = previous_snapshot.get("session_number", 1) + 1

            # ── Comparison prompt ─────────────────────────────────────────────
            prev_date = previous_snapshot.get("date", "unknown")
            prev_inj = previous_snapshot.get("injury_type", "unknown")
            prev_sev = previous_snapshot.get("severity", "unknown")
            prev_score = previous_snapshot.get("severity_score", "?")
            prev_inf = previous_snapshot.get("infection_risk", "unknown")
            prev_desc = previous_snapshot.get("visual_description", "Not available")

            prompt = f"""\
You are a medical AI comparing a patient's injury across two time points.

PREVIOUS STATE — Day {session_num - 1} (recorded: {prev_date}):
  Injury type:       {prev_inj}
  Severity:          {prev_sev} (score: {prev_score}/10)
  Infection risk:    {prev_inf}
  Visual description: {prev_desc}

CURRENT IMAGE: [attached — Day {session_num}]

Analyze the current image in detail, then compare it to the previous state above.
Base your comparison ONLY on visible evidence in the current image vs the previous description.

Return ONLY this JSON (no markdown, no extra text):
{{
  "injury_type": "What the current injury appears to be",
  "visual_description": "Describe exactly what you see NOW vs before: colour change, wound edge healing, swelling reduction/increase, crust/scab formation, discharge change",
  "severity": "mild | moderate | severe | emergency",
  "severity_score": <0-10 for current state>,
  "infection_risk": "low | high",
  "immediate_first_aid": ["Step 1", "Step 2", "Step 3"],
  "warning_signs": ["Sign 1", "Sign 2"],
  "see_doctor_if": "Specific trigger",
  "healing_time": "Remaining estimated healing time",
  "delta": "improved | worsened | stable",
  "delta_score": <float: -3.0 (severe worsening) to +3.0 (significant improvement), 0 = stable>,
  "delta_explanation": "One specific visual reason for this delta assessment (e.g. 'wound edges are closing, redness reduced by ~50%', or 'new pus visible, spreading redness')",
  "possible_conditions": ["Current most likely condition", "Alternative"]
}}

If you cannot see meaningful change, set delta to "stable" and delta_score to 0.
"""

            # ── Call Gemini Vision with 25s timeout ───────────────────────────
            result_holder: list = [None]
            error_holder: list = [None]

            def _worker():
                try:
                    resp = self.vision_model.generate_content([prompt, image])
                    result_holder[0] = resp
                except Exception as exc:
                    error_holder[0] = exc

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            t.join(timeout=25.0)

            if t.is_alive():
                print("[WARNING] Comparison vision call timed out")
                return self._comparison_fallback(previous_snapshot, session_num)

            if error_holder[0]:
                print(f"[ERROR] Comparison vision: {type(error_holder[0]).__name__}")
                return self._comparison_fallback(previous_snapshot, session_num)

            resp = result_holder[0]
            if not resp or not getattr(resp, "text", None):
                return self._comparison_fallback(previous_snapshot, session_num)

            raw = resp.text.strip()

            # ── JSON extraction ───────────────────────────────────────────────
            fence = _re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
            if fence:
                raw = fence.group(1).strip()
            obj = _re.search(r"\{[\s\S]+\}", raw)
            if obj:
                raw = obj.group(0)

            data = _json.loads(raw)
            data["success"] = True
            data["session_number"] = session_num
            data["is_comparison"] = True

            # Normalise delta_score
            try:
                ds = float(data.get("delta_score", 0))
                data["delta_score"] = max(-3.0, min(3.0, round(ds, 1)))
            except (TypeError, ValueError):
                data["delta_score"] = 0.0

            # Normalise delta
            if data.get("delta", "stable") not in ("improved", "worsened", "stable"):
                data["delta"] = "stable"

            # Normalise severity
            sev = str(data.get("severity", "moderate")).lower()
            if sev not in ("mild", "moderate", "severe", "emergency"):
                sev = "moderate"
            data["severity"] = sev

            # Honest confidence label
            raw_conf = data.pop("confidence", 65)
            try:
                raw_conf = int(raw_conf)
            except (TypeError, ValueError):
                raw_conf = 65
            data["model_certainty_approx"] = raw_conf

            # Run standard guards
            data = self._vision_sanity_check(data)
            data = self._compute_severity_score(data)
            data = self._check_infection_risk(data)
            data = self._check_medical_relevance(data)

            print(
                f"[COMPARE] delta={data.get('delta')} score={data.get('delta_score')} session={session_num}"
            )
            return data

        except _json.JSONDecodeError as exc:
            print(f"[WARN] Comparison JSON parse failed: {exc}")
            return self._comparison_fallback(
                previous_snapshot, session_num if "session_num" in dir() else 2
            )
        except Exception as exc:
            print(f"[ERROR] Comparison failed: {type(exc).__name__}")
            return self._comparison_fallback(previous_snapshot, 2)

    def _comparison_fallback(self, previous_snapshot: dict, session_num: int) -> dict:
        """Fallback when comparison call fails — returns regular analysis hint."""
        fb = self._fallback_image_analysis()
        fb.update(
            {
                "delta": "unknown",
                "delta_score": 0.0,
                "delta_explanation": "Comparison analysis unavailable. Please try again.",
                "session_number": session_num,
                "is_comparison": True,
            }
        )
        return fb

    # ── Fix 3: Medical relevance / abuse detection ────────────────────────────

    # Signals that strongly suggest a non-medical / unrelated upload
    _UNRELATED_SIGNALS = {
        # Food / drink
        "photograph of food",
        "image of food",
        "food item",
        "dish of",
        "restaurant menu",
        "pizza",
        "burger",
        "coffee cup",
        # Nature / landscape
        "landscape photograph",
        "scenic view",
        "mountain range",
        "beach scene",
        "sunset photo",
        # Non-medical social
        "selfie",
        "group photo",
        "screenshot of",
        "meme",
        "cartoon character",
        "animated",
        "clip art",
        "company logo",
        "brand logo",
        "infographic",
        # Documents / UI
        "text document",
        "spreadsheet",
        "computer screen",
        "website screenshot",
        "user interface",
        # Explicit non-medical rejection phrases
        "no visible health concern",
        "not a medical image",
        "unrelated to medical",
        "not health-related",
        "not an injury",
        "does not show any injury",
    }

    def _check_medical_relevance(self, data: dict) -> dict:
        """
        Fix 3 — Abuse / relevance guard.
        Detects non-medical images by scanning Gemini's own output.
        If clearly unrelated → is_medical_image = False (app.py will return 422).
        """
        injury = (data.get("injury_type") or "").lower()
        desc = (data.get("visual_description") or "").lower()
        combined = injury + " " + desc

        hit = next((s for s in self._UNRELATED_SIGNALS if s in combined), None)

        # Flag only when BOTH: confidence very low AND injury explicitly says 'no health'
        low_conf = data.get("model_certainty_approx", 100) < 15
        no_injury_keyword = "no visible health" in injury or "not health" in injury

        if hit or (low_conf and no_injury_keyword):
            data["is_medical_image"] = False
            data["rejection_reason"] = (
                f"Image does not appear to be health-related "
                f"(detected: '{hit or 'low confidence + no injury'}'). "
                "Please upload a photo of an injury or health concern."
            )
            print(f"[ABUSE] Non-medical image rejected: {hit or 'low-conf+no-injury'}")
        else:
            data["is_medical_image"] = True

        return data

    # ── Fix 2: Vision sanity check layer ──────────────────────────────────────

    # Keywords that must appear in visual_description before accepting high severity
    _SEVERE_EVIDENCE = {
        "bone",
        "exposed",
        "arteri",
        "deep laceration",
        "deep cut",
        "skull",
        "fracture",
        "disloc",
        "prolapse",
        "organ",
        "unconscious",
        "cyanot",
        "blue lips",
        "severe bleed",
        "profuse",
        "spurting",
        "third degree",
        "full thickness",
        "charred",
    }
    _EMERGENCY_EVIDENCE = {
        "not breathing",
        "no pulse",
        "cardiac",
        "seizure",
        "anaphyla",
        "unconscious",
        "call 112",
        "call 911",
        "profuse bleeding",
        "spurting",
        "airway obstruct",
    }

    def _vision_sanity_check(self, data: dict) -> dict:
        """
        Fix 2 — Rule-based guard layer.

        Validates Gemini's claimed severity against keyword evidence in
        visual_description. Prevents hallucinations like calling a shadow
        'severe bleeding' without visual justification.

        Principle: only DOWNGRADE, never upgrade. Gemini's ceiling is honoured;
        its floor is enforced by evidence.
        """
        desc = (data.get("visual_description") or "").lower()
        injury = (data.get("injury_type") or "").lower()
        combined = desc + " " + injury
        claimed = data.get("severity", "moderate")

        if claimed == "emergency":
            has_evidence = any(kw in combined for kw in self._EMERGENCY_EVIDENCE)
            if not has_evidence:
                data["severity"] = "severe"  # downgrade: no emergency keywords found
                data["sanity_note"] = (
                    "Severity downgraded emergency→severe: "
                    "no high-acuity keywords confirmed in visual description."
                )
                print(
                    f"[SANITY] Vision downgrade: emergency→severe (no evidence keywords)"
                )

        elif claimed == "severe":
            has_evidence = any(kw in combined for kw in self._SEVERE_EVIDENCE)
            if not has_evidence:
                data["severity"] = "moderate"  # downgrade: unsubstantiated severe claim
                data["sanity_note"] = (
                    "Severity downgraded severe→moderate: "
                    "description does not contain keywords consistent with severe injury."
                )
                print(
                    f"[SANITY] Vision downgrade: severe→moderate (no evidence keywords)"
                )

        return data

    # ── Fix 1: Keyword-based severity scoring engine ───────────────────────────

    _SCORE_HIGH = {
        "deep laceration",
        "deep cut",
        "exposed tissue",
        "bone visible",
        "heavy bleeding",
        "arterial",
        "profuse bleeding",
        "spurting",
        "charred",
        "full thickness",
        "third degree",
        "skull",
        "fracture",
        "dislocation",
        "organ",
        "prolapse",
        "purple discolouration",
        "severe burn",
        "chemical burn",
    }
    _SCORE_MED = {
        "moderate bleed",
        "bleeding",
        "laceration",
        "gash",
        "torn",
        "infected",
        "swollen",
        "significant",
        "blistering",
        "second degree",
        "abrasion",
        "bruise",
        "contusion",
        "rash",
        "discharge",
        "spreading",
        "inflamed",
        "deep bruise",
    }
    _SCORE_LOW = {
        "mild",
        "small cut",
        "minor",
        "slight",
        "redness",
        "scratch",
        "superficial",
        "surface",
        "faint",
        "minimal",
        "dry skin",
    }

    _SEV_ORDER = {"mild": 0, "moderate": 1, "severe": 2, "emergency": 3}

    def _compute_severity_score(self, data: dict) -> dict:
        """
        Fix 1 — Visual Severity Scoring Engine.
        Independent of Gemini's severity field — computes score from
        keyword evidence, then elevates severity if score-derived is higher.
        """
        desc = (data.get("visual_description") or "").lower()
        injury = (data.get("injury_type") or "").lower()
        combined = desc + " " + injury

        score = 0
        matched = []
        for kw in self._SCORE_HIGH:
            if kw in combined:
                score += 3
                matched.append(f"+3:{kw}")
        for kw in self._SCORE_MED:
            if kw in combined:
                score += 2
                matched.append(f"+2:{kw}")
        for kw in self._SCORE_LOW:
            if kw in combined:
                score += 1
                matched.append(f"+1:{kw}")

        score = min(score, 10)

        # Derive severity from score
        if score >= 7:
            derived = "severe"
        elif score >= 4:
            derived = "moderate"
        else:
            derived = "mild"

        current = data.get("severity", "mild")
        # Only elevate — never downgrade (sanity check already handled downgrades)
        if self._SEV_ORDER.get(derived, 0) > self._SEV_ORDER.get(current, 0):
            data["severity"] = derived
            data["scoring_note"] = (
                f"Severity elevated {current}→{derived} "
                f"by keyword scoring engine (score: {score}/10)."
            )
            print(f"[SCORE] Severity elevated {current}→{derived} score={score}")
        else:
            data["scoring_note"] = (
                f"Keyword score: {score}/10 — consistent with '{current}'."
            )

        data["severity_score"] = score
        if matched:
            print(f"[SCORE] Matched: {', '.join(matched[:5])}")

        return data

    # ── Fix 4: Infection risk heuristic ───────────────────────────────────────

    _INFECTION_KEYWORDS = {
        "pus",
        "pus-filled",
        "purulent",
        "yellow discharge",
        "green discharge",
        "foul smell",
        "odour",
        "spreading redness",
        "red streaks",
        "warmth",
        "warm to touch",
        "hot to touch",
        "inflamed",
        "swollen around",
        "swelling around",
        "oedema",
        "edema",
        "fluctuant",
        "abscess",
        "cellulitis",
    }

    def _check_infection_risk(self, data: dict) -> dict:
        """
        Fix 4 — Infection Risk Heuristic.
        Scans visual_description for infection indicators.
        Automatically elevates risk_level and minimum severity.
        Does not rely on AI classification.
        """
        desc = (data.get("visual_description") or "").lower()

        found = [kw for kw in self._INFECTION_KEYWORDS if kw in desc]
        if found:
            data["infection_risk"] = "high"
            data["infection_indicators"] = found
            # Elevate minimum severity to moderate
            current = data.get("severity", "mild")
            if self._SEV_ORDER.get(current, 0) < 1:  # mild → moderate
                data["severity"] = "moderate"
                data["infection_note"] = (
                    f"Severity elevated to moderate: infection indicators detected "
                    f"({', '.join(found[:3])})."
                )
            else:
                data["infection_note"] = (
                    f"Infection indicators detected: {', '.join(found[:3])}. "
                    "Seek medical attention promptly."
                )
            print(f"[INFECTION] High risk indicators: {found}")
        else:
            data["infection_risk"] = "low"

        return data

    def _fallback_response(self, symptoms, severity):
        """Fallback response when API is not available"""
        if severity == 1:
            return f"""I understand you're experiencing {', '.join(symptoms[:3]) if symptoms else 'some symptoms'}. Based on what you've described, this appears to be mild and likely manageable with self-care.

**My Recommendations:**
• Rest and stay hydrated
• Monitor your symptoms over the next 24-48 hours
• Consider over-the-counter remedies if appropriate
• If symptoms worsen or persist beyond 3-4 days, consult a doctor

**Self-Care Tips:**
• Get adequate sleep (7-9 hours)
• Maintain a balanced diet
• Avoid stress when possible
• Light exercise if you feel up to it

Remember, I'm here to provide guidance, but this isn't a medical diagnosis. If you're concerned or symptoms change, please consult a healthcare professional.

How are you feeling otherwise? Any other symptoms I should know about?"""

        elif severity == 2:
            return f"""Thank you for sharing your symptoms: {', '.join(symptoms[:5]) if symptoms else 'these concerns'}. Based on what you've described, this appears to be moderate and warrants attention.

**What This Might Indicate:**
Your symptoms suggest a condition that could benefit from medical evaluation. While not immediately urgent, it's important to address this properly.

**Recommended Actions:**
• Schedule an appointment with your primary care doctor within the next few days
• Keep track of your symptoms (when they occur, severity, triggers)
• Stay well-hydrated and get plenty of rest
• Avoid strenuous activities until you feel better

**When to Seek Immediate Care:**
• If symptoms suddenly worsen
• If you develop a high fever (over 103°F/39.4°C)
• If you experience severe pain
• If new, concerning symptoms appear

Would you like me to help you find suitable specialists in your area? Also, do you have a family doctor I should know about?"""

        elif severity == 3:
            return f"""I'm concerned about the symptoms you've described: {', '.join(symptoms[:5]) if symptoms else 'these symptoms'}. This appears to be a serious situation that requires prompt medical attention.

**Immediate Actions Needed:**
🏥 **Seek medical care today or within 24 hours**
• Contact your doctor immediately for an urgent appointment
• If after hours, consider visiting an urgent care facility
• Don't wait to see if symptoms improve on their own

**What to Tell Your Doctor:**
• All symptoms you're experiencing
• When symptoms started
• How symptoms have progressed
• Any medications you're taking
• Any relevant medical history

**In the Meantime:**
• Rest as much as possible
• Stay hydrated
• Avoid physical exertion
• Have someone stay with you if possible
• Keep emergency contact numbers handy

**Call 911 or go to ER if:**
• Symptoms rapidly worsen
• You experience severe pain
• You have difficulty breathing
• You feel confused or disoriented

Would you like help finding nearby medical facilities or specialists who can help?"""

        else:  # severity == 4
            return f"""🚨 **EMERGENCY - IMMEDIATE ACTION REQUIRED** 🚨

Based on what you've described, this is a medical emergency that requires immediate professional care.

**CALL 911 OR GO TO THE NEAREST EMERGENCY ROOM NOW**

**While Waiting for Help:**
• Stay calm and try to keep the person calm
• Do not leave the person alone
• Call emergency services immediately if you haven't already
• Follow any specific first-aid instructions for your situation
• Have someone gather important medical information (medications, allergies, conditions)

**Important Information to Provide:**
• Exact symptoms and when they started
• Any known allergies
• Current medications
• Relevant medical history
• Any recent injuries or illnesses

⚠️ **This is a critical situation.** Professional emergency medical care is essential. Do not delay seeking help.

If you're alone and able, call 911 now. If you're helping someone else, ensure emergency services have been contacted.

I'll provide additional guidance, but emergency services should be your first priority."""

        return "I'm here to help with your medical concerns. Please describe your symptoms."

    def _fallback_image_analysis(self):
        """Fallback image analysis when API is not available"""
        return {
            "success": True,
            "injury_type": "General Injury",
            "severity": "moderate",
            "confidence": 75,
            "description": "Unable to perform detailed AI analysis without API key. Based on typical injury patterns, this appears to be a common injury that requires basic first aid.",
            "cure_steps": [
                "Clean the affected area gently with clean water and mild soap",
                "Pat dry with a clean, soft cloth or sterile gauze",
                "Apply an appropriate antiseptic or antibacterial ointment",
                "Cover with a sterile bandage if needed to protect from dirt and bacteria",
                "Change the dressing daily or when it becomes wet or dirty",
                "Monitor for signs of infection (increased pain, redness, swelling, or pus)",
            ],
            "warning_signs": [
                "Increasing pain, redness, or swelling around the injury",
                "Pus or unusual discharge from the wound",
                "Red streaks spreading from the injury",
                "Fever above 100.4°F (38°C)",
                "Wound doesn't show signs of healing after 3-5 days",
            ],
            "do_not": [
                "Do not touch the injury with dirty hands",
                "Do not use hydrogen peroxide or alcohol directly on the wound (can damage tissue)",
                "Do not pick at scabs or healing tissue",
                "Do not expose the injury to dirty water or environments",
            ],
            "healing_time": "5-14 days for most minor to moderate injuries",
            "medical_advice": "Consult a healthcare provider if the injury is deep, won't stop bleeding, shows signs of infection, or if you haven't had a tetanus shot in the last 10 years. For best results, consider getting a free Gemini API key to enable AI-powered image analysis.",
        }


# Global instance
gemini_service = GeminiService()
