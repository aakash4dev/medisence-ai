/**
 * MedicSense AI - Central Configuration
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * HOW TO DEPLOY:
 *   1. Deploy backend to Render (or any host) and copy its URL.
 *   2. Set PRODUCTION_API_BASE_URL below to that URL (include /api at the end).
 *   3. Deploy the frontend folder to Netlify (drag & drop) or Vercel.
 *   4. Done! All fetch() calls across the app auto-pick the right base URL.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * LOCAL DEV:  http://localhost:5000/api
 * PRODUCTION: https://your-backend.onrender.com/api   ← replace this!
 */

const PRODUCTION_API_BASE_URL = 'https://medicsense-ai.onrender.com/api';
const LOCAL_API_BASE_URL      = 'http://localhost:5000/api';

// Auto-detect: use production URL when NOT running on localhost/127.0.0.1
const IS_LOCAL = (
  location.hostname === 'localhost' ||
  location.hostname === '127.0.0.1' ||
  location.hostname === ''
);

window.ENV = window.ENV || {};
window.ENV.API_BASE_URL = IS_LOCAL ? LOCAL_API_BASE_URL : PRODUCTION_API_BASE_URL;

window.ENV.FIREBASE = window.ENV.FIREBASE || {
  apiKey: '',
  authDomain: '',
  projectId: '',
  storageBucket: '',
  messagingSenderId: '',
  appId: '',
  measurementId: ''
};

window.ENV.WHATSAPP = window.ENV.WHATSAPP || {
  DOCTOR_Aakash: {
    name: 'Dr. Aakash Singh Rajput',
    phone: '+91 9770064169',
    whatsapp: '+919770064169'
  }
};

window.ENV.APP = window.ENV.APP || {
  AI_ENABLED: true,
  MAX_FILE_SIZE: 10485760,
  SUPPORTED_FORMATS: ['image/jpeg', 'image/png', 'image/webp']
};

console.log(
  `%c[MedicSense] API → ${window.ENV.API_BASE_URL}`,
  'color: #667eea; font-weight: bold;'
);
