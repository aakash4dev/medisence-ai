# MedicSense AI – Intelligent Healthcare Triage & Appointment Assistant

> **⚠️ STATUS: UNDER PRODUCTION**
> This project is currently under active development and is intended for demonstration and testing purposes only. It is NOT a certified medical device and should not be used for actual medical emergencies.

## 📌 Project Overview
MedicSense AI is an AI-powered healthcare assistant designed to streamline patient triage and appointment management. It leverages Google's Gemini API to analyze symptoms and provide preliminary triage recommendations, while also offering a robust appointment scheduling system for doctors and administrators.

### Key Features
- **AI Symptom Triage**: Uses Gemini API to analyze natural language symptoms and classify urgency (Self-care, Consult Soon, Urgent).
- **Smart Chat Interface**: User-friendly chat UI for patients to describe symptoms and receive immediate feedback.
- **Appointment Management**: Complete booking system with conflict detection and status tracking.
- **Doctor Dashboard**: Admin interface for healthcare providers to view appointments, patient history, and triage alerts.
- **Secure Architecture**: Built with privacy and security in mind, utilizing role-based access and data encryption standards.

## 🏗️ Architecture
The project follows a clean, modular architecture:

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, Shadcn UI
- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic
- **AI Engine**: Google Gemini Pro
- **Database**: PostgreSQL (Cloud SQL compatible)
- **Infrastructure**: Docker, Google Cloud Run

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.10+
- Docker (optional)
- Google Cloud Project with Gemini API enabled

### Local Development

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Configure your GEMINI_API_KEY and DATABASE_URL
uvicorn main:app --reload
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000` and the backend API at `http://localhost:8000`.

## 📂 Project Structure
```
medisence-ai/
├── ai/                 # AI logic and prompt templates
├── backend/            # FastAPI application
│   ├── routers/        # API endpoints
│   ├── models.py       # Database models
│   └── schemas.py      # Pydantic schemas
├── frontend/           # Next.js application
│   ├── app/            # App router pages
│   ├── components/     # React components
│   └── lib/            # Utilities
├── infra/              # Infrastructure configuration
└── shared/             # Shared types/interfaces
```

## 🛡️ Disclaimer
MedicSense AI provides informational suggestions based on user input. It does not provide medical diagnosis or treatment. Always consult a qualified healthcare professional for medical advice. In case of a medical emergency, contact your local emergency services immediately.
