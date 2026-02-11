# MedicSense AI

## Project Overview

MedicSense AI is a full-stack AI-assisted healthcare support platform that helps users understand their symptoms, book appointments, and receive health notifications. The system uses Google's Gemini API for intelligent symptom analysis while maintaining strict safety protocols.

**This application does NOT provide medical diagnosis.** It is designed as a health awareness and navigation tool to help users make informed decisions about seeking appropriate medical care.

## Key Features

### 1. AI-Assisted Symptom Checker
- Natural language symptom input with duration and severity tracking
- Google Gemini-powered analysis for context-aware health insights
- Safety-first design with emergency keyword detection
- Non-diagnostic guidance with clear disclaimers
- Downloadable symptom reports

### 2. Smart Appointment Booking
- Real-time slot availability checking
- Multiple doctor/department selection
- In-person and video consultation options
- Automatic appointment confirmation notifications
- Appointment history tracking

### 3. Notification System
- Real-time notification badge updates (without page refresh)
- Persistent read/unread state (JSON-based storage)
- Appointment confirmations and reminders
- Health tips and medication reminders
- Filter by type (all, unread, appointments, medications, health tips)

### 4. Authentication
- Google Sign-In integration via Firebase
- Secure session management
- User profile with avatar and email display
- Persistent authentication state across sessions

### 5. Emergency Quick Action
- One-click emergency assistance button
- High-risk symptom detection (chest pain, stroke symptoms, severe bleeding, etc.)
- Immediate safety protocol activation

## Technology Stack

### Frontend
- **HTML5** - Semantic structure
- **CSS3** - Modern styling with glassmorphism effects
- **JavaScript (Vanilla)** - No frameworks, pure ES6+
- **Firebase SDK** - Authentication
- **AOS Library** - Scroll animations
- **Font Awesome** - Icons

### Backend
- **Python 3.8+** - Core language
- **Flask 2.3.3** - Web framework
- **Flask-CORS** - Cross-origin resource sharing

### AI Integration
- **Google Gemini API** - Natural language processing for symptom analysis
- **Custom safety classifiers** - Emergency detection and severity assessment

### Storage
- **JSON files** - Lightweight persistence for appointments, notifications, and user data
- No SQL database (demo-safe, portable)

## Application Flow

### Symptom Analysis Workflow
1. User enters symptoms in natural language
2. User selects duration (hours to weeks) and severity (1-10 scale)
3. Frontend validates all required fields before enabling analysis
4. Backend receives symptom data and checks for emergency keywords
5. If emergency detected: immediate safety protocol with severity level 4
6. If non-emergency: Gemini API analyzes symptoms and provides supportive guidance
7. Results displayed with severity classification (1-4) and recommended actions
8. User can book appointment or download report

### Notification System Behavior
1. Notifications generated on appointment booking, health tips, medication reminders
2. Backend stores notifications in `data/notifications.json` with read/unread status
3. Frontend polls `/api/notifications/summary` every 30 seconds
4. Bell badge updates WITHOUT page refresh when new notifications arrive
5. User clicks notification → marks as read → backend updates JSON → badge count decrements
6. Read/unread state persists across browser sessions and page refreshes

### Authentication Flow
1. User clicks profile icon → auth modal appears
2. User clicks "Sign in with Google" → Firebase popup
3. Firebase returns user token → saved to localStorage
4. Backend receives token at `/api/auth/google` → validates and creates session
5. Profile menu updates with user name, email, and avatar
6. Auth state persists until explicit sign-out

## How to Run the Project

### Prerequisites
- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Edge)
- Google Gemini API key (required for symptom analysis)

### Backend Setup

1. Navigate to backend directory:
```powershell
cd medisence-ai/backend
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Set up environment variables (create `.env` file in backend directory):
```
GEMINI_API_KEY=your_gemini_api_key_here
```

4. Start the Flask server:
```powershell
python app.py
```

The backend will start on **http://localhost:5000**

### Frontend Access

**Option 1: Direct File Open**
- Open `medisence-ai/frontend/index.html` directly in your browser
- File path: `file:///C:/Users/shivansh/OneDrive/Desktop/first hackathon project/medisence-ai/frontend/index.html`

**Option 2: Local Server (Recommended)**
- Use VS Code Live Server extension
- Right-click `index.html` → "Open with Live Server"
- Access at `http://localhost:5500` (or assigned port)

### Environment Variables
The application requires a Gemini API key for symptom analysis. Without it, the symptom checker will not function. All other features (appointments, notifications, authentication) work independently.

## API Endpoints

### Symptom Analysis
- `POST /api/chat` - Analyze symptoms with AI (requires message, user_id)
- `POST /api/chat/message` - Alternative chat endpoint

### Appointments
- `GET /api/appointments/slots` - Get available time slots (requires doctor, date)
- `POST /api/appointments/book` - Book appointment (requires name, phone, email, doctorId, date, time, reason, type)
- `GET /api/appointments/<user_id>` - Get user's appointments
- `PUT /api/appointments/<appointment_id>/cancel` - Cancel appointment
- `PUT /api/appointments/<appointment_id>/reschedule` - Reschedule appointment

### Notifications
- `GET /api/notifications` - Fetch notifications (requires user_id query param)
- `GET /api/notifications/summary` - Get notification counts (requires user_id query param)
- `POST /api/notifications/read` - Mark single notification as read (requires notification_id, user_id)
- `PATCH /api/notifications/mark-all-read` - Mark all notifications as read (requires user_id)
- `POST /api/notifications/refresh` - Refresh notifications from appointments/tips

### Authentication
- `POST /api/auth/google` - Google OAuth login (requires idToken, user object)
- `POST /api/auth/logout` - Sign out
- `GET /api/auth/session` - Check session status

### Emergency
- `POST /api/emergency/escalate` - Emergency escalation
- `POST /api/emergency/chat` - Emergency-specific chat
- `POST /api/emergency/hospitals` - Find nearby emergency hospitals

### Doctors
- `GET /api/doctors` - List all doctors
- `GET /api/find-doctors` - Find doctors by city and specialization
- `POST /api/save-doctor` - Save family doctor
- `GET /api/get-doctor/<user_id>` - Get user's family doctor

## UX & Safety Notes

### Non-Diagnostic Disclaimer
This application explicitly states on every symptom analysis:
> "This tool supports health awareness and does not provide medical diagnosis."

The AI responses are designed to:
- Provide educational information about symptoms
- Suggest appropriate next steps (rest, consult doctor, seek emergency care)
- Never claim to diagnose conditions
- Always recommend professional medical consultation for serious concerns

### Safety Protocols
1. **Emergency Detection**: 50+ high-risk keywords trigger immediate safety protocol
2. **Severity Classification**: 4-level system (Mild, Moderate, Serious, Emergency)
3. **Clear Escalation**: Emergency symptoms automatically set severity to level 4
4. **Professional Referral**: All moderate-to-serious symptoms recommend doctor consultation

### Hackathon Compliance
- No medical diagnosis claims
- No treatment prescriptions
- No medication recommendations
- Educational and awareness purpose only
- Suitable for demonstration and evaluation

## Screenshots

*Screenshots can be added here to demonstrate:*
- Symptom checker interface
- Appointment booking flow
- Notification panel with read/unread states
- Emergency quick action
- Google Sign-In authentication

## Project Structure

```
medisence-ai/
├── frontend/
│   ├── index.html              # Main application page
│   ├── notifications.html      # Notifications page
│   ├── style_ultra.css         # Complete styling
│   ├── script_ultra.js         # Core application logic
│   ├── firebase.js             # Firebase authentication
│   ├── sw.js                   # Service worker (PWA)
│   └── [other HTML/JS files]
├── backend/
│   ├── app.py                  # Main Flask server (1869 lines, 40+ endpoints)
│   ├── gemini_service.py       # Gemini API integration
│   ├── symptom_analyzer.py    # Symptom extraction
│   ├── severity_classifier.py # Severity assessment
│   ├── emergency_detector.py  # Emergency keyword detection
│   ├── notifications_service.py # Notification management
│   ├── auth_routes.py          # Authentication endpoints
│   ├── database.py             # JSON database wrapper
│   ├── medical_kb.json         # Medical knowledge base
│   ├── doctors_db.json         # Doctor database
│   └── requirements.txt        # Python dependencies
└── data/
    ├── notifications.json      # Notification persistence
    ├── appointments.json       # Appointment records
    └── family_doctor.json      # User's family doctor info
```

## Technical Highlights

### Real-Time Updates
- Notification badge updates every 30 seconds without page refresh
- Polling-based architecture for demo simplicity
- Persistent state across sessions via JSON storage

### Responsive Design
- Mobile-first approach
- Glassmorphism UI effects
- Smooth animations and transitions
- Accessible color contrast

### Error Handling
- Timeout protection on all API calls (10-15 second limits)
- Graceful degradation when services unavailable
- User-friendly error messages
- Loading states for all async operations

## Limitations & Scope

This is a **hackathon demonstration project**, not production-ready software:

- **No SQL database**: Uses JSON files for simplicity and portability
- **No HIPAA compliance**: Not suitable for real patient data
- **Demo-level security**: Authentication is functional but not hardened
- **No audit logging**: No comprehensive tracking of system interactions
- **AI safety is heuristic-based**: Emergency detection uses keyword matching, not ML
- **No regulatory approval**: Educational and demonstration purposes only

## Disclaimer

**IMPORTANT**: This is a hackathon project for educational and demonstration purposes only.

**This application does NOT:**
- Provide medical diagnoses
- Replace professional medical advice
- Offer treatment recommendations
- Prescribe medications
- Guarantee accuracy of health information

**Always consult qualified healthcare professionals for medical advice.**

In life-threatening emergencies, call your local emergency services immediately:
- 🇺🇸 USA: 911
- 🇬🇧 UK: 999 or 112
- 🇮🇳 India: 102 (Ambulance), 108 (Emergency)
- 🇦🇺 Australia: 000

## License

This is a hackathon project. Feel free to use, modify, and extend for educational purposes.

---

**Built for healthcare awareness and intelligent patient engagement**

*Last updated: February 2026*
