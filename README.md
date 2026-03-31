# MedicSense AI - Complete Healthcare Assistant 🏥

A comprehensive AI-powered medical chatbot with symptom analysis, emergency detection, appointment scheduling, and health record management.

## 🚀 Features

### Core Features
- ✅ **AI Medical Chatbot** - Natural language symptom analysis
- ✅ **Emergency Detection** - Instant first-aid guidance for critical situations
- ✅ **Severity Classification** - 4-level urgency system (Mild to Critical)
- ✅ **Doctor Matching** - Find specialists based on symptoms
- ✅ **Appointment Scheduling** - Book and manage appointments
- ✅ **Health Records** - Track vitals, symptoms, and medical history
- ✅ **Image Analysis** - Analyze injury/medical images
- ✅ **Family Doctor System** - Save and consult family physician
- ✅ **Real-time Chat** - LLM-style conversational interface

### Advanced Features
- 📊 **Health Dashboard** - Visualize health trends
- 🔔 **Smart Notifications** - Appointment reminders and health alerts
- 📱 **Responsive Design** - Works on all devices
- 🌐 **Multi-language Support** - (Coming soon)
- 🔒 **Data Privacy** - Local storage, HIPAA-compliant ready

## 📁 Project Structure

```
medisence-ai/
├── backend/                    # Flask backend server
│   ├── app.py                 # Main Flask application
│   ├── database.py            # Database management
│   ├── auth_manager.py        # Authentication & sessions
│   ├── symptom_analyzer.py    # Symptom extraction
│   ├── severity_classifier.py # Urgency classification
│   ├── emergency_detector.py  # Emergency detection
│   ├── camera_analyzer.py     # Image analysis
│   ├── gemini_service.py      # AI integration
│   ├── otp_service.py         # OTP management
│   ├── medical_kb.json        # Medical knowledge base
│   ├── doctors_db.json        # Doctors database
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # Frontend application
│   ├── index.html             # Main page
│   ├── script.js              # Core JavaScript
│   ├── dashboard.js           # Dashboard functionality
│   ├── style.css              # Styles
│   └── auth.html              # Authentication page
│
├── API_DOCUMENTATION.md        # Complete API docs
└── README.md                   # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Modern web browser
- VS Code (recommended)

### Step 1: Clone the Repository
```bash
git clone https://github.com/Shivansh1146/MedicSense-AI
```

### Step 2: Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

**Dependencies installed:**
- Flask 2.3.3 - Web framework
- flask-cors 4.0.0 - Cross-origin support
- Pillow 10.1.0 - Image processing

### Step 3: Start the Backend Server
```bash
python app.py
```

You should see:
```
🚀 MedicSense AI Backend Starting...
📡 Server running at http://localhost:5000
💊 Medical chatbot ready to assist
```

### Step 4: Access the Application
Open your browser and go to:
```
http://localhost:5000
```

## 🎯 How to Use

### 1. Start a Conversation
- Click the chat icon in the bottom-right corner
- Describe your symptoms naturally
- Get instant AI-powered analysis

### 2. Example Queries
```
"I have a severe headache and fever"
"My chest hurts and I feel dizzy"
"I twisted my ankle while playing"
"I need a doctor for heart problems"
```

### 3. Emergency Situations
The system automatically detects emergencies and provides first-aid guidance:
- Chest pain
- Severe bleeding
- Difficulty breathing
- Loss of consciousness

### 4. Book Appointments
- Save your family doctor
- Book appointments with specialists
- Manage and reschedule appointments

### 5. Track Health
- Record vital signs
- Monitor health trends
- Store medical history

## 🏥 Severity Levels

| Level | Severity | Action Required |
|-------|----------|----------------|
| 1 | Mild | Self-care, monitor symptoms |
| 2 | Moderate | Consult family doctor |
| 3 | Serious | See specialist soon |
| 4 | Critical | Emergency - Call 911 |

## 📡 API Endpoints

### Main Endpoints
- `POST /api/chat` - Chat with AI
- `POST /api/auth/otp/send` - Send OTP
- `POST /api/auth/otp/verify` - Verify OTP
- `POST /api/appointments/book` - Book appointment
- `GET /api/appointments/<user_id>` - Get appointments
- `POST /api/health/vitals` - Save vital signs
- `GET /api/health/vitals/<user_id>` - Get health records
- `POST /api/analyze-injury-image` - Analyze images
- `GET /api/find-doctors` - Search doctors

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.

## 🔧 Configuration

### Optional: Add Gemini API Key (Enhanced AI)
1. Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create `.env` file in backend folder:
```bash
GEMINI_API_KEY=your_api_key_here
```
3. Restart the server

### Customize Medical Knowledge
Edit `backend/medical_kb.json` to add:
- New symptoms
- Medical conditions
- Treatment recommendations

### Add Doctors
Edit `backend/doctors_db.json` to add local doctors and hospitals.

## 🔒 Security Features

- ✅ Session token management
- ✅ Local data storage
- ✅ CORS protection
- ✅ Input sanitization
- ✅ Secure file uploads

## 🧪 Testing

### Test the Chatbot
```python
# In backend folder
python test_api.py
```

### Test Emergency Detection
Send messages with emergency keywords:
- "chest pain"
- "can't breathe"
- "severe bleeding"

## 🚀 Deployment

### Deploy to Heroku
```bash
heroku create medisense-ai
git push heroku main
```

### Deploy to Railway
1. Connect your GitHub repository
2. Deploy from `main` branch
3. Set environment variables

### Deploy to AWS/GCP
See deployment guides in `docs/` folder.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Shivansh**
- GitHub: [@Shivansh1146](https://github.com/Shivansh1146)

## 🙏 Acknowledgments

- Flask framework
- Google Gemini AI
- Medical knowledge databases
- Open-source community

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Email: support@MedicSense-AI.com

## 🔮 Roadmap

### Coming Soon
- [ ] Multi-language support
- [ ] Prescription management
- [ ] Lab report analysis
- [ ] Medicine reminders
- [ ] Telemedicine integration
- [ ] Insurance integration
- [ ] Mobile app (React Native)

## ⚠️ Disclaimer

**MedicSense AI is an educational tool and should not replace professional medical advice.**

Always consult with qualified healthcare professionals for medical concerns. In emergencies, call your local emergency number (911 in the US).

---

Made with ❤️ for better healthcare access

**Star ⭐ this repository if you find it helpful!**
