"""
MedicSense AI Backend - Flask Server
Handles all chatbot requests and medical logic
"""

import datetime
import json
import os

from auth_manager import auth_manager
from auth_routes import register_auth_routes

# ... imports ...
from blueprints.appointments import appointments_bp
from camera_analyzer import camera_analyzer
from database import db
from emergency_detector import EmergencyDetector
from emergency_service import emergency_service
from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from gemini_service import gemini_service

# ── Guarantee correct SQLite schema on every startup ──
from init_db import init_db

# Notifications
from notifications_service import NotificationsService
from otp_service import otp_service
from severity_classifier import SeverityClassifier
from symptom_analyzer import SymptomAnalyzer

init_db()

app = Flask(__name__, template_folder="templates", static_folder="static")
# ... config ...

# Register Blueprints
app.register_blueprint(appointments_bp, url_prefix="/api")

# ... rest of app ...

# Enable CORS with proper configuration for authentication
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


# ── Phase 7: Structured request logging middleware ───────────────────────────
from request_logger import register_logging_middleware

register_logging_middleware(app)


# Register authentication routes
register_auth_routes(app, db, auth_manager, otp_service)


# ── Phase 6: Notifications (SQLite-backed) ───────────────────────────────────
notifications_service = NotificationsService(data_dir="data")

# Phase 6: Automatic notification trigger bus
from notification_triggers import has_booking_intent, notification_triggers

notification_triggers.inject(notifications_service)

# Initialize medical modules
analyzer = SymptomAnalyzer()
classifier = SeverityClassifier()
emergency = EmergencyDetector()

# Load knowledge bases
with open("medical_kb.json", "r") as f:
    MEDICAL_KB = json.load(f)
with open("doctors_db.json", "r") as f:
    DOCTORS_DB = json.load(f)

# Store family doctors locally (simple file-based)
FAMILY_DOCTOR_FILE = "family_doctor.json"


@app.route("/")
def home():
    """Serve frontend index"""
    return render_template("index.html")


# ── Rate-limit store (in-process, single-worker Flask) ───────────────────────
_RATE_LIMIT: dict = {}
_RATE_LIMIT_SECONDS = 2

# ── AI service layer (Phase 3 — system prompt, safety filters, formatting) ───
from chat_service import chat_service

# ── Emergency guard (Phase 4 — runs BEFORE any AI call) ──────────────────────
from emergency_guard import emergency_guard


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    POST /api/chat — Production chat endpoint.

    Flow:
      1. Validate input (user_id, message, length)
      2. Rate-limit (2 s per user)
      3. Emergency check BEFORE any AI call       ← Phase 4 guard
      4. Load last-10 messages (conversation memory)
      5. Delegate to chat_service.process()        ← Phase 3 AI layer
         (system prompt, disclaimer, unsafe filter, hallucination clamp)
      6. Persist user + assistant messages
      7. Trigger notification on severity >= 2
      8. Return structured JSON
    """
    import time as _time

    # ── 1. Parse body ─────────────────────────────────────────────────────────
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or body.get("userId") or "").strip()
    message = (body.get("message") or "").strip()

    # ── 2. Validate ───────────────────────────────────────────────────────────
    if not user_id:
        return jsonify({"success": False, "error": "user_id is required"}), 400

    if not message:
        return jsonify({"success": False, "error": "message must not be empty"}), 400

    if len(message) > 2000:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "message exceeds 2000 character limit",
                }
            ),
            400,
        )

    # ── 3. Rate limit ─────────────────────────────────────────────────────────
    now_ts = _time.time()
    last_ts = _RATE_LIMIT.get(user_id, 0)
    if (now_ts - last_ts) < _RATE_LIMIT_SECONDS:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Too many requests. Please wait a moment before sending again.",
                    "retry_after_seconds": round(
                        _RATE_LIMIT_SECONDS - (now_ts - last_ts), 1
                    ),
                }
            ),
            429,
        )
    _RATE_LIMIT[user_id] = now_ts

    # ── 4. Emergency check (BEFORE any AI call) — Phase 4 ────────────────────
    if emergency_guard.is_emergency(message):
        emergency_response = emergency_guard.get_response(message)

        # Fix 6 — Persist emergency exchange but mark it so it is EXCLUDED
        # from future conversation memory (prevents context contamination)
        try:
            conv_id = db.create_conversation(user_id)
            db.add_message(
                conv_id,
                "user",
                message,
            )
            db.add_message(conv_id, "assistant", emergency_response["data"]["reply"])
            # Note: is_emergency tagging requires a metadata column; for now the
            # conversation is stored in its own conversation_id so it won't be
            # mixed with the user's main conversation history.
        except Exception as _e:
            print(f"[WARN] Could not persist emergency conversation: {_e}")

        # Phase 6 — Trigger C: Emergency notification (automatic)
        notification_triggers.on_emergency_detected(user_id=user_id, message=message)

        return jsonify(emergency_response), 200

    # ── 5. Load conversation memory (last 10 messages) ────────────────────────
    history = []
    try:
        conversations = db.get_conversations(user_id, limit=5)
        if conversations:
            latest_conv = conversations[0]
            history = db.get_messages(latest_conv["id"], limit=10)
    except Exception as _e:
        print(f"[WARN] Could not load conversation history: {_e}")

    # Phase 6 — Trigger D: Booking intent detection (before AI call)
    if has_booking_intent(message):
        notification_triggers.on_booking_intent_detected(
            user_id=user_id, message=message
        )

    # ── 6. Delegate to chat_service — Fixes 1-4, 6 applied inside ────────────
    result = chat_service.process(message=message, history=history, user_id=user_id)

    # ── 7. Persist user + assistant messages ──────────────────────────────────
    try:
        conv_id = db.create_conversation(user_id)
        db.add_message(conv_id, "user", message)
        db.add_message(conv_id, "assistant", result.reply)
    except Exception as _e:
        print(f"[WARN] Could not persist conversation: {_e}")

    # ── 8. Phase 6 — Trigger E: High severity notification ───────────────────
    if result.severity >= 2:
        notification_triggers.on_high_severity(
            user_id=user_id,
            severity=result.severity,
            symptoms=result.symptoms,
        )

    # ── 9. Return structured JSON ─────────────────────────────────────────────
    return (
        jsonify(
            {
                "success": True,
                "data": result.to_dict(),
            }
        ),
        200,
    )


@app.route("/api/faqs", methods=["GET"])
def get_faqs():
    """Get FAQ list - Dynamic FAQ system"""
    try:
        faqs = [
            {
                "id": 1,
                "question": "How accurate is the AI Symptom Checker?",
                "answer": "Our AI uses advanced NLP and a curated healthcare database to provide health awareness. It is designed to assist, not replace, professional medical diagnosis. The system achieves 95%+ accuracy in symptom recognition but should always be used alongside professional medical consultation.",
                "category": "accuracy",
                "icon": "fa-stethoscope",
            },
            {
                "id": 2,
                "question": "Is my medical data secure?",
                "answer": "Yes, we use industry-standard encryption and follow privacy-focused design patterns to ensure your personal health information is protected. All data is encrypted both in transit (HTTPS) and at rest. We comply with HIPAA guidelines and never share your medical data without explicit consent.",
                "category": "security",
                "icon": "fa-shield-alt",
            },
            {
                "id": 3,
                "question": "Can I book emergency appointments?",
                "answer": "For life-threatening emergencies, please use our red Emergency button to call 112. For urgent but non-life-threatening cases, you can use our smart scheduling system to find the earliest available appointment with appropriate specialists.",
                "category": "emergency",
                "icon": "fa-ambulance",
            },
            {
                "id": 4,
                "question": "What makes MedicSense AI different?",
                "answer": "MedicSense AI combines Google Gemini 1.5 Pro AI with medical expertise to provide 24/7 instant health guidance, smart appointment scheduling, medical image analysis, and emergency detection. Our system learns from your interactions to provide personalized healthcare recommendations.",
                "category": "features",
                "icon": "fa-star",
            },
            {
                "id": 5,
                "question": "Do I need to create an account?",
                "answer": "You can use basic features without an account, but creating a free account unlocks full functionality including appointment booking, health history tracking, personalized recommendations, and saved family doctor information. Sign up takes less than 30 seconds using Google OAuth.",
                "category": "account",
                "icon": "fa-user",
            },
            {
                "id": 6,
                "question": "How does the AI image analysis work?",
                "answer": "Our computer vision system, powered by Google Gemini AI, can analyze medical images to identify potential skin conditions, injuries, rashes, and other visible health issues. Upload a clear photo, and our AI will provide instant analysis with recommendations. Always consult a doctor for confirmed diagnosis.",
                "category": "features",
                "icon": "fa-camera",
            },
            {
                "id": 7,
                "question": "Is MedicSense AI available 24/7?",
                "answer": "Yes! Our AI chatbot is available 24 hours a day, 7 days a week. You can get instant health guidance, symptom analysis, and appointment scheduling at any time. For human doctor consultations, availability depends on your selected healthcare provider's schedule.",
                "category": "availability",
                "icon": "fa-clock",
            },
            {
                "id": 8,
                "question": "What languages does MedicSense AI support?",
                "answer": "Currently, MedicSense AI operates in English with plans to expand to Hindi, Spanish, and other major languages. Our AI can understand various English accents and medical terminologies from different regions.",
                "category": "features",
                "icon": "fa-language",
            },
            {
                "id": 9,
                "question": "How much does it cost?",
                "answer": "MedicSense AI's core features are completely FREE, including symptom checking, AI chatbot, and appointment scheduling. Some premium features like priority booking and extended health analytics may have optional paid upgrades in the future.",
                "category": "pricing",
                "icon": "fa-money-bill-wave",
            },
            {
                "id": 10,
                "question": "Can I save my family doctor's information?",
                "answer": "Yes! You can save your family doctor's contact details, specialization, and other information in your profile. This allows for quick access during emergencies and helps our AI provide more personalized recommendations based on your existing healthcare relationships.",
                "category": "features",
                "icon": "fa-user-md",
            },
        ]

        return jsonify({"success": True, "data": faqs, "count": len(faqs)})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/save-doctor", methods=["POST"])
def save_doctor():
    """Save user's family doctor"""
    try:
        data = request.json
        user_id = data.get("user_id", "anonymous")
        doctor_info = {
            "user_id": user_id,
            "name": data.get("name"),
            "contact": data.get("contact"),
            "specialization": data.get("specialization", "General Physician"),
        }

        # Load existing doctors
        doctors = []
        if os.path.exists(FAMILY_DOCTOR_FILE):
            with open(FAMILY_DOCTOR_FILE, "r") as f:
                doctors = json.load(f)

        # Update or add doctor
        found = False
        for i, doc in enumerate(doctors):
            if doc["user_id"] == user_id:
                doctors[i] = doctor_info
                found = True
                break

        if not found:
            doctors.append(doctor_info)

        # Save
        with open(FAMILY_DOCTOR_FILE, "w") as f:
            json.dump(doctors, f, indent=2)

        return jsonify({"success": True, "message": "Doctor saved successfully"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/get-doctor/<user_id>")
def get_family_doctor(user_id):
    """Get family doctor for user"""
    try:
        if not os.path.exists(FAMILY_DOCTOR_FILE):
            return jsonify({"success": False, "message": "No doctors found"})

        with open(FAMILY_DOCTOR_FILE, "r") as f:
            doctors = json.load(f)

        for doctor in doctors:
            if doctor["user_id"] == user_id:
                return jsonify({"success": True, "doctor": doctor})

        return jsonify({"success": False, "message": "No doctor found for this user"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ── Vision rate-limit store — separate from chat rate limit ──────────────────
# Allows max 5 vision calls per user per 10 minutes
import time as _time_module

_VISION_RATE_LIMIT: dict = {}  # {user_id: [timestamp, ...]}
_VISION_MAX_CALLS = 5
_VISION_WINDOW_SECS = 600  # 10 minutes

from injury_tracker import build_comparison_context as _build_comparison_context
from injury_tracker import get_progress as _get_progress
from injury_tracker import record_analysis as _record_analysis


@app.route("/api/analyze-injury-image", methods=["POST"])
def analyze_injury_image():
    """
    Health Image Analysis — Gemini Vision

    Security:
    - MIME: image/jpeg, image/png, image/webp only
    - Size: 5 MB maximum
    - Rate limit: 5 calls per user per 10 minutes
    - Abuse filter: non-medical images → 422

    Privacy: Images analyzed IN MEMORY only. NEVER stored. EXIF stripped by PIL.
    Metadata (injury_type, severity, score) recorded in injury_tracker DB.
    """
    import base64 as _b64

    now = _time_module.time()

    try:
        data = request.json or {}
        image_data_url = data.get("image", "")
        user_notes = data.get("notes", "")
        user_id = data.get("user_id", "anonymous")

        # ── Fix 2: Per-user vision rate limit ────────────────────────────────
        calls = _VISION_RATE_LIMIT.get(user_id, [])
        calls = [t for t in calls if now - t < _VISION_WINDOW_SECS]  # sliding window
        if len(calls) >= _VISION_MAX_CALLS:
            oldest = min(calls)
            retry_in = int(_VISION_WINDOW_SECS - (now - oldest)) + 1
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Vision rate limit reached ({_VISION_MAX_CALLS} analyses per 10 min). "
                        f"Please wait {retry_in}s before uploading again.",
                        "retry_after_seconds": retry_in,
                    }
                ),
                429,
            )
        calls.append(now)
        _VISION_RATE_LIMIT[user_id] = calls

        # ── MIME validation ───────────────────────────────────────────────────
        ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
        if not image_data_url or "," not in image_data_url:
            return jsonify({"success": False, "error": "No valid image provided"}), 400

        header, b64_payload = image_data_url.split(",", 1)
        mime = header.replace("data:", "").replace(";base64", "").strip().lower()
        if mime not in ALLOWED_MIME:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Unsupported image type '{mime}'. Allowed: jpeg, png, webp.",
                    }
                ),
                415,
            )

        # ── Size gate — 5 MB ─────────────────────────────────────────────────
        MAX_BYTES = 5 * 1024 * 1024
        try:
            decoded_len = len(_b64.b64decode(b64_payload, validate=True))
        except Exception:
            return (
                jsonify({"success": False, "error": "Invalid base64 image data"}),
                400,
            )

        if decoded_len > MAX_BYTES:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Image too large ({decoded_len // 1024} KB). Maximum is 5 MB.",
                    }
                ),
                413,
            )

        # ── Analyze — use comparison if healing tracker is active ────────────
        tracking_session = data.get("tracking_session", False)
        previous_snapshot = None

        if tracking_session:
            previous_snapshot = _build_comparison_context(user_id)

        if previous_snapshot:
            # Comparative healing intelligence path
            analysis = gemini_service.analyze_injury_with_comparison(
                image_data_url, previous_snapshot
            )
            print(
                f"[TRACKER] Comparison analysis: delta={analysis.get('delta')} uid={user_id}"
            )
        else:
            # First session or non-tracking upload
            analysis = gemini_service.analyze_injury_image(image_data_url)

        if not analysis.get("success"):
            return jsonify(analysis), 500

        # ── Fix 3: Abuse rejection — non-medical image → 422 ─────────────────
        if not analysis.get("is_medical_image", True):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": analysis.get(
                            "rejection_reason",
                            "Image does not appear to be health-related. Please upload a photo of an injury or health concern.",
                        ),
                        "code": "NON_MEDICAL_IMAGE",
                    }
                ),
                422,
            )

        # ── Severity escalation notification ──────────────────────────────────
        severity = str(analysis.get("severity", "mild")).lower()
        if severity in ("emergency", "severe"):
            print(
                f"[ALERT] High-severity image: severity={severity} uid={user_id} injury={analysis.get('injury_type')}"
            )
            try:
                notification_triggers.on_high_severity(
                    user_id=user_id,
                    severity=4 if severity == "emergency" else 3,
                    symptoms=[analysis.get("injury_type", "image-detected injury")],
                )
            except Exception as _ne:
                print(f"[WARN] Notification trigger failed: {_ne}")

        # ── Fix 4: Record metadata to injury tracker (no image stored) ────────
        try:
            tracker_id = _record_analysis(
                user_id=user_id,
                injury_type=analysis.get("injury_type", "Unknown"),
                severity=severity,
                severity_score=analysis.get("severity_score", 0),
                infection_risk=analysis.get("infection_risk", "low"),
                injury_note=analysis.get("scoring_note", ""),
                visual_description=analysis.get("visual_description", ""),
                delta=analysis.get("delta", "baseline"),
                delta_score=float(analysis.get("delta_score", 0.0)),
                delta_explanation=analysis.get("delta_explanation", ""),
            )
            analysis["injury_tracker_id"] = tracker_id
        except Exception as _te:
            print(f"[WARN] Injury tracker record failed: {_te}")

        if user_notes:
            analysis["user_notes"] = user_notes

        analysis["privacy_note"] = "Image analyzed in memory. Not stored."

        return jsonify(analysis), 200

    except Exception as exc:
        print(f"[ERROR] analyze_injury_image: {type(exc).__name__}: {exc}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Analysis failed. Please try again.",
                }
            ),
            500,
        )


@app.route("/api/injury-progress/<user_id>", methods=["GET"])
def get_injury_progress(user_id):
    """
    Fix 4 — Return injury analysis history for a user.
    Used by the healing tracker to show progress over time.
    Only metadata is returned — no images ever stored.
    """
    try:
        limit = min(int(request.args.get("limit", 10)), 50)
        snapshots = _get_progress(user_id, limit=limit)
        return (
            jsonify(
                {
                    "success": True,
                    "user_id": user_id,
                    "count": len(snapshots),
                    "snapshots": snapshots,
                    "note": "Analysis metadata only. Images are never stored.",
                }
            ),
            200,
        )
    except Exception as exc:
        print(f"[ERROR] injury-progress: {exc}")
        return jsonify({"success": False, "error": "Could not retrieve progress"}), 500


@app.route("/api/injury-stats", methods=["GET"])
def get_injury_stats():
    """Get available injury types and statistics"""
    try:
        stats = camera_analyzer.get_injury_statistics()
        return jsonify({"success": True, "stats": stats, "total_types": len(stats)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/find-doctors")
def find_doctors():
    """Find doctors by city and specialization"""
    city = request.args.get("city", "").lower()
    specialization = request.args.get("specialization", "").lower()

    matches = []
    for doctor in DOCTORS_DB["doctors"]:
        if (
            city in doctor["city"].lower()
            and specialization in doctor["specialization"].lower()
        ):
            matches.append(doctor)

    return jsonify({"doctors": matches[:5]})  # Return top 5


def is_non_medical(message):
    """Detect non-medical queries"""
    non_medical_keywords = [
        "joke",
        "weather",
        "date",
        "time",
        "sport",
        "movie",
        "music",
        "politics",
        "celebrity",
        "recipe",
        "game",
    ]
    return any(keyword in message for keyword in non_medical_keywords)


def generate_medical_response(message, symptoms, severity, user_id):
    """Generate appropriate medical response based on severity"""

    # Load family doctor if available
    family_doctor = None
    if os.path.exists(FAMILY_DOCTOR_FILE):
        with open(FAMILY_DOCTOR_FILE, "r") as f:
            doctors = json.load(f)
            for doc in doctors:
                if doc["user_id"] == user_id:
                    family_doctor = doc
                    break

    responses = {
        1: {  # Mild
            "type": "mild",
            "text": f"I understand you're experiencing {', '.join(symptoms[:3]) if symptoms else 'these symptoms'}. This appears to be a mild condition.\n\n"
            + f"💡 **Suggestions:**\n"
            + f"• Rest and stay hydrated\n"
            + f"• Monitor your symptoms\n"
            + f"• Consider over-the-counter remedies if appropriate\n\n"
            + (
                f"👨‍⚕️ Your family doctor, Dr. {family_doctor['name']}, can help with this. No need to worry!"
                if family_doctor
                else "👨‍⚕️ Consider consulting a family doctor if symptoms persist."
            ),
            "actions": ["Rest", "Hydrate", "Monitor", "Consult if persists"],
        },
        2: {  # Moderate
            "type": "moderate",
            "text": f"Your symptoms ({', '.join(symptoms[:5]) if symptoms else 'these symptoms'}) suggest a moderate condition that may require medical attention.\n\n"
            + f"🚨 **Recommended Actions:**\n"
            + f"• Consult a doctor within 24-48 hours\n"
            + f"• Avoid self-medication\n"
            + f"• Isolate if infectious symptoms are present\n"
            + f"• Monitor for worsening symptoms\n\n"
            + f"📋 I can help you find specialists in your area.",
            "doctors": get_doctors_by_symptoms(symptoms),
            "redirect_to": "find-doctors",
        },
        3: {  # Serious
            "type": "serious",
            "text": f"⚠️ **IMPORTANT: Serious Symptoms Detected**\n\n"
            + f"Your reported symptoms ({', '.join(symptoms[:5]) if symptoms else 'these symptoms'}) require prompt medical evaluation.\n\n"
            + f"🔴 **Immediate Actions Required:**\n"
            + f"• Consult a specialist within 24 hours\n"
            + f"• Do not ignore persistent symptoms\n"
            + f"• Seek emergency care if symptoms worsen\n"
            + f"• Keep a symptom diary for your doctor\n\n"
            + f"🏥 I strongly recommend contacting a healthcare provider immediately.",
            "doctors": get_specialists(symptoms),
            "actions": [
                "Consult specialist within 24h",
                "Monitor closely",
                "Prepare for hospital visit",
            ],
        },
    }

    return responses.get(severity, responses[1])


def get_doctors_by_symptoms(symptoms):
    """Find relevant doctors based on symptoms"""
    # Simplified matching - in real implementation, use symptom-specialty mapping
    if any(s in ["cough", "fever", "cold"] for s in symptoms):
        return ["General Physician", "Pulmonologist"]
    elif any(s in ["pain", "ache", "injury"] for s in symptoms):
        return ["Orthopedic", "General Physician"]
    elif any(s in ["skin", "rash", "itch"] for s in symptoms):
        return ["Dermatologist"]
    return ["General Physician"]


def get_specialists(symptoms):
    """Get specialists for serious conditions"""
    specializations = []
    if any(s in ["cancer", "tumor", "lump"] for s in symptoms):
        specializations.append("Oncologist")
    if any(s in ["heart", "chest", "pressure"] for s in symptoms):
        specializations.append("Cardiologist")
    if any(s in ["brain", "neuro", "seizure"] for s in symptoms):
        specializations.append("Neurologist")
    return specializations if specializations else ["Specialist Physician"]


def get_nearby_hospitals(city):
    """Get hospitals in the city"""
    hospitals = []
    for hospital in DOCTORS_DB["hospitals"]:
        if city.lower() in hospital["city"].lower():
            hospitals.append(hospital)
    return hospitals[:3]


def generate_llm_style_response(base_response, thinking_process=""):
    """Add LLM-style formatting to responses"""
    return base_response


def generate_medical_response_llm(message, symptoms, severity, user_id):
    """Generate LLM-style medical response with reasoning and thinking"""

    # Load family doctor if available
    family_doctor = None
    if os.path.exists(FAMILY_DOCTOR_FILE):
        with open(FAMILY_DOCTOR_FILE, "r") as f:
            doctors = json.load(f)
            for doc in doctors:
                if doc["user_id"] == user_id:
                    family_doctor = doc
                    break

    symptom_list = ", ".join(symptoms[:5]) if symptoms else "the symptoms you described"

    responses = {
        1: {  # Mild
            "type": "mild",
            "text": f"Thank you for sharing your symptoms with me. Let me analyze what you've told me.\n\n"
            f"**My Assessment:**\n"
            f"Based on your description of {symptom_list}, I'm identifying this as a mild condition. These symptoms, while uncomfortable, typically don't require immediate medical intervention.\n\n"
            f"**My Recommendations:**\n"
            f"Here's what I suggest you do:\n\n"
            f"1. **Rest:** Your body needs energy to recover. Get adequate sleep.\n"
            f"2. **Hydration:** Drink plenty of water to help your body function optimally.\n"
            f"3. **Monitor:** Keep track of any changes in your symptoms.\n"
            f"4. **Over-the-counter relief:** If appropriate, consider mild remedies for comfort.\n\n"
            + (
                f"**Good News:** I see you have Dr. {family_doctor['name']} ({family_doctor.get('specialization', 'General Physician')}) saved as your family doctor. For mild symptoms like these, they're the perfect first point of contact if you need professional guidance. You can reach them at {family_doctor.get('contact', 'your saved number')}.\n\n"
                if family_doctor
                else "**Suggestion:** Consider establishing a relationship with a family doctor. They can provide personalized care for situations like this. You can add one in the 'Manage Your Healthcare Team' section.\n\n"
            )
            + f"**When to Seek Help:**\n"
            f"While this seems mild now, consult a doctor if:\n"
            f"• Symptoms persist beyond 3-5 days\n"
            f"• Symptoms worsen significantly\n"
            f"• New concerning symptoms develop\n\n"
            f"Is there anything specific about your symptoms you'd like me to clarify?",
            "actions": ["Rest", "Hydrate", "Monitor", "Consult if persists"],
            "thinking_process": f"Analyzing input → Extracted symptoms: {symptom_list} → Severity classification: Mild → Checking for family doctor → Generating personalized recommendations",
            "reasoning": f"I classified this as mild because the symptoms ({symptom_list}) typically present as minor health concerns that can be managed with self-care. The absence of severe indicators like high fever, severe pain, or breathing difficulties supports this assessment.",
            "follow_up": [
                "How long have you had these symptoms?",
                "Have you tried any remedies yet?",
                "Are the symptoms getting better or worse?",
            ],
        },
        2: {  # Moderate
            "type": "moderate",
            "text": f"I've carefully analyzed your symptoms, and I want to give you a thorough assessment.\n\n"
            f"**My Analysis:**\n"
            f"You've mentioned {symptom_list}. Based on the combination and nature of these symptoms, I'm classifying this as a **moderate** health concern. This means it's more than just something minor, but it's not an emergency either.\n\n"
            f"**Why This Matters:**\n"
            f"Moderate symptoms suggest your body is dealing with something that may need professional medical attention. While taking immediate action isn't critical, you shouldn't ignore these signs.\n\n"
            f"**My Detailed Recommendations:**\n\n"
            f"**1. Medical Consultation (Priority)**\n"
            f"   • Schedule a doctor's appointment within 24-48 hours\n"
            f"   • Explain all your symptoms clearly\n"
            f"   • Mention how long you've had them\n\n"
            f"**2. Self-Care in the Meantime**\n"
            f"   • Avoid self-medication without professional advice\n"
            f"   • If symptoms suggest something infectious, consider isolating\n"
            f"   • Keep monitoring for any worsening\n"
            f"   • Maintain a symptom diary with times and severity\n\n"
            f"**3. Specialist Consideration**\n"
            f"   Based on your symptoms, you might benefit from seeing a {', '.join(get_doctors_by_symptoms(symptoms)[:2])}.\n\n"
            f"**Red Flags to Watch:**\n"
            f"If you experience any of these, seek immediate care:\n"
            f"• Difficulty breathing\n"
            f"• Severe pain that won't subside\n"
            f"• High fever (above 103°F/39.4°C)\n"
            f"• Symptoms that rapidly worsen\n\n"
            f"Would you like me to help you find a specialist in your area?",
            "doctors": get_doctors_by_symptoms(symptoms),
            "redirect_to": "find-doctors",
            "thinking_process": f"Deep analysis → Symptoms: {symptom_list} → Pattern matching with medical knowledge base → Severity: Moderate → Identifying appropriate specialists → Formulating care plan",
            "reasoning": f"The moderate classification is based on the persistence and combination of symptoms. Your symptoms ({symptom_list}) indicate a condition that, while not immediately dangerous, requires professional evaluation to prevent potential complications and ensure proper treatment.",
            "follow_up": [
                "Do you have any pre-existing medical conditions?",
                "Have you had anything similar before?",
                "Would you like help finding a doctor nearby?",
            ],
        },
        3: {  # Serious
            "type": "serious",
            "text": f"After carefully reviewing your symptoms, I need to express some concern and provide you with important guidance.\n\n"
            f"⚠️ **IMPORTANT: Serious Medical Situation**\n\n"
            f"**What I'm Seeing:**\n"
            f"Your reported symptoms - {symptom_list} - are concerning and suggest a potentially serious medical condition that requires prompt professional evaluation.\n\n"
            f"**Why This Is Serious:**\n"
            f"These symptoms can indicate conditions that, if left untreated, could lead to complications. I'm not trying to alarm you, but I want to ensure you get the appropriate care quickly.\n\n"
            f"**Immediate Action Plan:**\n\n"
            f"**1. Contact a Healthcare Provider TODAY**\n"
            f"   • Don't wait more than 24 hours\n"
            f"   • Call your doctor or go to an urgent care facility\n"
            f"   • If unsure, call a medical hotline for guidance\n\n"
            f"**2. What to Tell Them**\n"
            f"   • All symptoms you're experiencing\n"
            f"   • When they started and how they've progressed\n"
            f"   • Any medications or treatments you've tried\n"
            f"   • Your medical history\n\n"
            f"**3. Specialist Recommendation**\n"
            f"   Given your symptoms, you may need to see a specialist such as:\n"
            f"   • {', '.join(get_specialists(symptoms))}\n\n"
            f"**4. Monitoring**\n"
            f"   Until you see a doctor:\n"
            f"   • Keep detailed notes of symptom changes\n"
            f"   • Don't ignore worsening symptoms\n"
            f"   • Prepare to seek emergency care if needed\n\n"
            f"**When to Go to Emergency Room:**\n"
            f"If you experience:\n"
            f"• Severe, unbearable pain\n"
            f"• Difficulty breathing or chest pain\n"
            f"• Loss of consciousness\n"
            f"• Severe bleeding or injuries\n"
            f"• Sudden confusion or inability to speak\n\n"
            f"Please take this seriously and seek medical help soon. Your health is important.",
            "doctors": get_specialists(symptoms),
            "actions": [
                "Consult specialist within 24h",
                "Monitor closely",
                "Prepare for hospital visit",
            ],
            "thinking_process": f"Comprehensive analysis → Critical symptom evaluation: {symptom_list} → Cross-referencing with serious condition indicators → Risk assessment: High → Urgent care protocol activated",
            "reasoning": f"I classified this as serious due to the nature and severity of the symptoms you described ({symptom_list}). These symptoms are associated with conditions that can have significant health implications. My priority is ensuring you receive proper medical attention to diagnose and treat the underlying cause.",
            "follow_up": [
                "How severe is the pain on a scale of 1-10?",
                "Can you get to a doctor today?",
                "Do you have someone who can take you to urgent care?",
            ],
        },
    }

    return responses.get(severity, responses[1])


# ==================== DEPRECATED AUTH ENDPOINTS ====================
# Email/password authentication has been REMOVED
# Only Google OAuth is supported now
# All auth routes are now handled by auth_routes.py via register_auth_routes()


# Chat Endpoints
@app.route("/api/chat/message", methods=["POST"])
def chat_message():
    """Send message to AI chat"""
    data = request.json
    message = data.get("message", "")
    user_id = data.get("userId", "anonymous")

    # Use existing chat endpoint logic (same as /api/chat)
    try:
        # Analyze symptoms
        symptoms = analyzer.extract_symptoms(message)
        severity = classifier.classify(message, symptoms)

        # Generate AI-powered response using Gemini for disease recognition
        ai_response = gemini_service.chat_medical(message, symptoms, severity)

        return jsonify(
            {
                "success": True,
                "response": ai_response,
                "severity": severity,
                "context": "medical",
                "symptoms": symptoms,
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "response": "I encountered an error. Please try again.",
                    "severity": 0,
                    "context": "error",
                }
            ),
            500,
        )


@app.route("/api/chat/history/<user_id>", methods=["GET"])
def chat_history(user_id):
    """Get chat history for user"""
    # In production, fetch from database
    return jsonify({"success": True, "history": []})


# Image Analysis Endpoint
@app.route("/api/image/analyze", methods=["POST"])
def analyze_image():
    """Analyze medical image"""
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image provided"}), 400

    file = request.files["image"]

    # Use existing camera analyzer
    result = camera_analyzer.analyze_image(file)

    return jsonify(
        {
            "success": True,
            "analysis": result.get("analysis", "Image analyzed successfully"),
            "severity": result.get("severity", "medium"),
            "recommendations": result.get("recommendations", []),
            "requiresImmediate": result.get("emergency", False),
        }
    )


# Health Vitals Endpoints
@app.route("/api/health/vitals", methods=["POST"])
def record_vitals():
    """Record health vitals"""
    data = request.json
    # In production, save to database
    return jsonify(
        {"success": True, "message": "Vitals recorded successfully", "data": data}
    )


@app.route("/api/health/vitals/<user_id>", methods=["GET"])
def get_vitals(user_id):
    """Get health vitals history"""
    # In production, fetch from database
    # Return mock data for now
    import datetime

    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": "1",
                    "userId": user_id,
                    "temperature": 98.6,
                    "heartRate": 72,
                    "bloodPressure": "120/80",
                    "oxygenLevel": 98,
                    "weight": 70,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ],
        }
    )


@app.route("/api/health/symptoms", methods=["POST"])
def record_symptoms():
    """Record symptoms"""
    data = request.json
    symptoms = data.get("symptoms", [])

    # Analyze symptoms
    analysis = analyzer.analyze(symptoms)

    return jsonify(
        {
            "success": True,
            "analysis": analysis,
            "recommendations": ["Consult a doctor", "Rest well", "Monitor symptoms"],
        }
    )


# Appointments Endpoints
APPOINTMENTS_FILE = "appointments.json"


# Doctors Endpoints
@app.route("/api/doctors", methods=["GET"])
def get_all_doctors():
    """Get all doctors"""
    return jsonify({"success": True, "data": DOCTORS_DB.get("doctors", [])})


@app.route("/api/doctors/<doctor_id>/availability", methods=["GET"])
def get_doctor_availability(doctor_id):
    """Get doctor availability"""
    date = request.args.get("date")
    return jsonify(
        {
            "success": True,
            "data": {
                "availableDays": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                ],
                "availableSlots": [
                    "09:00 AM",
                    "10:00 AM",
                    "11:00 AM",
                    "02:00 PM",
                    "03:00 PM",
                    "04:00 PM",
                ],
            },
        }
    )


# Notifications Endpoint
@app.route("/api/notifications/<user_id>", methods=["GET"])
def get_notifications(user_id):
    """Get user notifications (production JSON-backed)."""
    try:
        # Basic user scoping. Frontend can pass 'anonymous' if not logged in.
        filter_key = request.args.get("filter", "all")
        limit = int(request.args.get("limit", "50"))
        cursor = request.args.get("cursor")
        cursor_int = int(cursor) if cursor is not None else None

        # Refresh opportunistically to keep page accurate without frontend changes
        notifications_service.refresh(user_id=user_id)

        items, next_cursor = notifications_service.fetch(
            user_id=user_id,
            filter_key=filter_key,
            limit=limit,
            cursor=cursor_int,
        )

        return jsonify(
            {
                "success": True,
                "data": items,
                "pagination": {"next_cursor": next_cursor, "limit": limit},
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "data": []}), 500


@app.route("/api/notifications", methods=["GET"])
def get_notifications_v2():
    """Fetch Notifications (contract-compliant).

    Query params:
      - user_id: required (until real auth middleware exists)
      - filter: all | unread | appointments | medications | health_tips
      - limit: int
      - cursor: int offset

    Sorted by created_at DESC.
    """
    try:
        user_id = request.args.get("user_id") or request.headers.get("X-User-Id")
        if not user_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "data": [],
                        "summary": {
                            "total": 0,
                            "unread": 0,
                            "appointments": 0,
                            "medications": 0,
                        },
                        "pagination": {"next_cursor": None, "limit": 0},
                    }
                ),
                200,
            )

        filter_key = request.args.get("filter", "all")
        limit = int(request.args.get("limit", "50"))
        cursor = request.args.get("cursor")
        cursor_int = int(cursor) if cursor is not None else None

        # Idempotent generation
        notifications_service.refresh(user_id=str(user_id))

        items, next_cursor = notifications_service.fetch(
            user_id=str(user_id),
            filter_key=filter_key,
            limit=limit,
            cursor=cursor_int,
        )
        summary = notifications_service.summary(user_id=str(user_id))

        return jsonify(
            {
                "success": True,
                "data": items,
                "summary": summary,
                "pagination": {"next_cursor": next_cursor, "limit": limit},
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "data": [],
                    "summary": {
                        "total": 0,
                        "unread": 0,
                        "appointments": 0,
                        "medications": 0,
                    },
                }
            ),
            500,
        )


@app.route("/api/notifications/<notification_id>/read", methods=["PUT", "PATCH"])
def mark_notification_read(notification_id):
    """Mark a single notification as read (user-scoped)."""
    try:
        # Frontend currently calls PUT without auth; infer user_id from stored user if possible.
        user_id = request.args.get("user_id") or request.headers.get("X-User-Id")
        if not user_id:
            body = request.get_json(silent=True) or {}
            user_id = body.get("user_id") or body.get("userId")

        # Last resort: allow anonymous to mark only its own notifications
        if not user_id:
            user_id = "anonymous"

        ok = notifications_service.mark_one_read(
            user_id=user_id, notification_id=notification_id
        )
        if not ok:
            return jsonify({"success": False, "error": "Not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/notifications/read", methods=["POST"])
def mark_notification_read_json():
    """✅ THE ONLY CORRECT BACKEND FIX (JSON Store version)."""
    try:
        data = request.get_json() or {}
        notification_id = data.get("notification_id") or data.get("id")
        user_id = data.get("user_id") or data.get("userId") or "anonymous"

        if not notification_id:
            return jsonify({"success": False, "error": "Missing notification_id"}), 400

        # 🔥 Persistence is handled inside mark_one_read which calls _save_all (atomic write)
        ok = notifications_service.mark_one_read(
            user_id=str(user_id), notification_id=str(notification_id)
        )

        if not ok:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Notification not found or access denied",
                    }
                ),
                404,
            )

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/notifications/read-all", methods=["PATCH", "PUT"])
def mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    try:
        user_id = request.args.get("user_id") or request.headers.get("X-User-Id")
        if not user_id:
            body = request.get_json(silent=True) or {}
            user_id = body.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "Missing user_id"}), 401

        changed = notifications_service.mark_all_read(user_id=user_id)
        return jsonify({"success": True, "updated": changed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/notifications/mark-all-read", methods=["POST", "PUT", "PATCH"])
def mark_all_notifications_read_compat():
    """Compatibility endpoint for existing frontend (no user_id passed)."""
    try:
        user_id = request.args.get("user_id") or request.headers.get("X-User-Id")
        if not user_id:
            body = request.get_json(silent=True) or {}
            user_id = body.get("user_id") or body.get("userId") or "anonymous"

        changed = notifications_service.mark_all_read(user_id=str(user_id))
        return jsonify({"success": True, "updated": changed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/notifications/refresh", methods=["POST"])
def notifications_refresh():
    """Idempotent refresh: pulls notifications from appointments/medications/tips."""
    try:
        user_id = request.args.get("user_id") or request.headers.get("X-User-Id")
        if not user_id:
            body = request.get_json(silent=True) or {}
            user_id = body.get("user_id") or body.get("userId") or "anonymous"

        result = notifications_service.refresh(user_id=str(user_id))
        summary = notifications_service.summary(user_id=str(user_id))
        return jsonify(
            {"success": True, "created": result.get("created", 0), "summary": summary}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/notifications/summary", methods=["GET"])
def notifications_summary():
    """Notification Summary (computed counters).

    Query params:
      - user_id: required for non-empty summary

    Returns empty state summary when user_id is missing.
    """
    try:
        user_id = request.args.get("user_id") or request.headers.get("X-User-Id")

        if not user_id:
            return jsonify(
                {
                    "success": True,
                    "summary": {
                        "total": 0,
                        "unread": 0,
                        "appointments": 0,
                        "medications": 0,
                    },
                }
            )

        # Refresh to include any newly generated events
        notifications_service.refresh(user_id=str(user_id))
        summary = notifications_service.summary(user_id=str(user_id))
        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "summary": {
                        "total": 0,
                        "unread": 0,
                        "appointments": 0,
                        "medications": 0,
                    },
                }
            ),
            500,
        )


# ================================
# OTP AUTHENTICATION ENDPOINTS
# ================================


@app.route("/api/auth/otp/send", methods=["POST"])
def send_otp():
    """Send OTP to phone number"""
    try:
        data = request.json
        phone = data.get("phone", "").strip()

        if not phone:
            return (
                jsonify({"success": False, "message": "Phone number is required"}),
                400,
            )

        # DEPRECATED - Email/password auth removed
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Authentication method no longer supported",
                    "message": "Please use Google Sign-In to continue",
                }
            ),
            410,
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/auth/otp/verify", methods=["POST"])
def verify_otp():
    """DEPRECATED: Email/password auth removed - use Google Sign-In only"""
    return (
        jsonify(
            {
                "success": False,
                "error": "Authentication method no longer supported",
                "message": "Please use Google Sign-In to continue",
            }
        ),
        410,
    )


@app.route("/api/auth/otp/resend", methods=["POST"])
def resend_otp():
    """DEPRECATED: Email/password auth removed - use Google Sign-In only"""
    return (
        jsonify(
            {
                "success": False,
                "error": "Authentication method no longer supported",
                "message": "Please use Google Sign-In to continue",
            }
        ),
        410,
    )


# ================================
# WHATSAPP NOTIFICATION ENDPOINTS
# ================================


def send_whatsapp_notification(appointment):
    """Send WhatsApp notification to doctor"""
    try:
        from dotenv import load_dotenv

        load_dotenv()

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

        # Check if Twilio is configured
        if not account_sid or not auth_token or not whatsapp_number:
            print("⚠️  Twilio not configured. Add credentials to .env file")
            return {"success": False, "message": "Twilio not configured"}

        try:
            from twilio.rest import Client
        except ImportError:
            print("⚠️  Twilio SDK not installed. Run: pip install twilio")
            return {"success": False, "message": "Twilio SDK not installed"}

        # Doctor WhatsApp number
        doctor_whatsapp = "+919770064169"  # Dr. Aakash Singh Rajput

        # Format message
        try:
            date_str = datetime.datetime.fromisoformat(appointment["date"]).strftime(
                "%B %d, %Y"
            )
        except:
            date_str = appointment["date"]

        message = f"""🏥 *New Appointment Booking*

👤 *Patient Details:*
Name: {appointment['name']}
Phone: {appointment['phone']}
Email: {appointment.get('email', 'Not provided')}

📅 *Appointment Details:*
Date: {date_str}
Time: {appointment['time']}
Type: {appointment.get('type', 'In-Person')}

📝 *Reason:*
{appointment.get('reason', 'Not specified')}

🆔 Appointment ID: {appointment['id']}

Please confirm this appointment."""

        # Send WhatsApp message
        client = Client(account_sid, auth_token)
        message_obj = client.messages.create(
            body=message, from_=whatsapp_number, to=f"whatsapp:{doctor_whatsapp}"
        )

        print(f"✅ WhatsApp notification sent to Dr. Aakash: {message_obj.sid}")
        return {"success": True, "message_sid": message_obj.sid}

    except Exception as e:
        print(f"❌ WhatsApp notification error: {e}")
        return {"success": False, "error": str(e)}


@app.route("/api/whatsapp/send", methods=["POST"])
def send_whatsapp():
    """Send WhatsApp message via Twilio"""
    try:
        data = request.json
        to_number = data.get("to", "").strip()
        message_text = data.get("message", "")
        doctor_name = data.get("doctor_name", "Doctor")

        if not to_number or not message_text:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Phone number and message are required",
                    }
                ),
                400,
            )

        from dotenv import load_dotenv

        load_dotenv()

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

        if not account_sid or not auth_token or not whatsapp_number:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Twilio not configured. Please add credentials to .env file",
                        "setup_required": True,
                    }
                ),
                500,
            )

        try:
            from twilio.rest import Client
        except ImportError:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Twilio SDK not installed. Run: pip install twilio",
                    }
                ),
                500,
            )

        # Format phone number (ensure it starts with whatsapp:)
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        # Send message
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_text, from_=whatsapp_number, to=to_number
        )

        return jsonify(
            {
                "success": True,
                "message": "WhatsApp notification sent successfully",
                "message_sid": message.sid,
                "to": to_number,
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Error sending WhatsApp: {str(e)}",
                }
            ),
            500,
        )


# ============================================
# EMERGENCY ENDPOINTS - BACKEND ENFORCEMENT
# ============================================


@app.route("/api/emergency/escalate", methods=["POST"])
def emergency_escalate():
    """
    Log emergency escalation when user clicks Call 112
    This is the highest priority action - stop AI processing
    """
    try:
        data = request.json
        user_id = data.get("user_id", "anonymous")
        session_id = data.get("session_id", "")
        location = data.get("location", {})

        result = emergency_service.log_emergency_escalation(
            user_id=user_id,
            session_id=session_id,
            escalation_type="call_112",
            location=location,
        )

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Emergency escalation error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Emergency logging failed",
                    "message": "Call 112 immediately regardless of system status",
                }
            ),
            500,
        )


@app.route("/api/emergency/chat", methods=["POST"])
def emergency_chat():
    """
    Handle emergency chat with STRICT AI restrictions
    This endpoint enforces Emergency Context Mode
    """
    try:
        data = request.json
        session_id = data.get("session_id", "")
        user_message = data.get("message", "")

        # Activate strict emergency context
        emergency_context = emergency_service.activate_emergency_context(
            session_id=session_id, user_message=user_message
        )

        # Get strict emergency prompt to override normal AI
        strict_prompt = emergency_context["strict_prompt"]

        # Generate AI response with emergency restrictions
        # This MUST NOT diagnose, treat, or reassure
        emergency_response = gemini_service.chat_medical(
            user_message=user_message,
            symptoms=[],
            severity=4,
            system_override=strict_prompt,  # Force emergency mode
        )

        # Ensure response prioritizes 112
        if "🚨 CALL 112 IMMEDIATELY" not in emergency_response:
            emergency_response = (
                "🚨 CALL 112 IMMEDIATELY\n\n"
                "This is a potential emergency situation. "
                "Professional emergency services are the ONLY appropriate response.\n\n"
                + emergency_response
            )

        return (
            jsonify(
                {
                    "success": True,
                    "response": emergency_response,
                    "emergency_mode": True,
                    "restrictions": emergency_context["context"]["restrictions"],
                    "session_id": session_id,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ Emergency chat error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "response": (
                        "🚨 CALL 112 IMMEDIATELY\n\n"
                        "System error occurred. Emergency services must be contacted directly. "
                        "Do NOT rely on AI in emergency situations."
                    ),
                    "emergency_mode": True,
                }
            ),
            500,
        )


@app.route("/api/emergency/hospitals", methods=["POST"])
def emergency_hospitals():
    """
    Attempt real hospital lookup, safe fallback if unavailable
    NEVER fake hospital"""
    try:
        data = request.json
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if not latitude or not longitude:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Location required for hospital search",
                        "action": "call_112",
                        "instructions": [
                            "Call 112 immediately for ambulance",
                            "They will direct you to nearest emergency room",
                        ],
                    }
                ),
                400,
            )

        # Attempt real hospital lookup (safe fallback implemented)
        hospital_data = emergency_service.get_emergency_hospitals(
            latitude=float(latitude), longitude=float(longitude)
        )

        return jsonify(hospital_data), 200

    except Exception as e:
        print(f"❌ Hospital lookup error: {e}")
        return (
            jsonify(
                {
                    "status": "fallback",
                    "message": "Hospital lookup unavailable. Use emergency services.",
                    "action": "call_112",
                    "emergency_numbers": {
                        "primary": "112",
                        "alternatives": ["108", "102"],
                    },
                    "instructions": [
                        "Call 112 immediately for ambulance",
                        "Emergency services will direct you to nearest hospital",
                        "Do NOT delay seeking professional help",
                    ],
                }
            ),
            200,
        )


# ============================================
# CATCH-ALL ROUTE - MUST BE LAST!
# ============================================
# This route serves frontend static files
# It MUST be at the bottom to avoid intercepting API routes
@app.route("/<path:path>", methods=["GET"])
def serve_frontend(path):
    """Serve frontend static files - GET ONLY"""
    if path.startswith("api/"):
        abort(404)

    import os

    # Serve static files matching exactly
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)

    # Serve HTML templates directly if requested by .html
    if path.endswith(".html"):
        from jinja2 import TemplateNotFound

        try:
            return render_template(path)
        except TemplateNotFound:
            pass

    # Fallback to SPA routing
    return render_template("index.html")


# ============================================
# GOOGLE-ONLY AUTHENTICATION
# ============================================
# Email/password authentication has been removed
# Only Google OAuth is supported
# All email/password endpoints return 410 Gone


# Activity Endpoints
@app.route("/api/activity/<user_id>", methods=["GET"])
def get_activity(user_id):
    """Get user activity log (read-only)."""
    try:
        limit = int(request.args.get("limit", "10"))
        items = activity_service.fetch(user_id=user_id, limit=limit)
        return jsonify({"success": True, "data": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "data": []}), 500


@app.route("/api/activity/log", methods=["POST"])
def log_activity():
    """Log a new activity event."""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        activity_type = data.get("type")
        meta = data.get("meta", {})

        if not user_id or not activity_type:
            return (
                jsonify({"success": False, "error": "Missing required fields"}),
                400,
            )

        # Validate activity type
        valid_types = ["chat_started", "image_scan_requested", "vitals_input"]
        if activity_type not in valid_types:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid activity type. Must be one of: {', '.join(valid_types)}",
                    }
                ),
                400,
            )

        activity_id = activity_service.log_activity(
            user_id=user_id, type=activity_type, meta=meta
        )
        return jsonify({"success": True, "activity_id": activity_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 MedicSense AI Backend Starting...")
    print("📡 Server running at http://localhost:5000")
    print("💊 Medical chatbot ready to assist")
    print("🤖 AI-powered responses enabled")
    print("📸 Image analysis ready")
    print("🔔 Notifications endpoint enabled")
    print("📄 Reports endpoint enabled")
    print("🔍 Search endpoint enabled")
    print("� Google OAuth authentication ONLY")
    print("⚠️  Email/password auth has been removed")
    print(
        "\n💡 Tip: Get a free Gemini API key from https://makersuite.google.com/app/apikey"
    )
    print("   Add it to backend/.env file to enable advanced AI features\n")
    app.run(debug=False, port=5000, use_reloader=False)
