# Environment Variables Setup Guide

## Overview
This project uses environment variables to store sensitive configuration data. The `.env` file is **not committed to git** for security.

## Files

- `.env` - Your actual environment variables (DO NOT COMMIT)
- `.env.example` - Template file showing required variables (safe to commit)
- `env-loader.js` - Loads environment variables in the browser
- `load-env.js` - Node.js script to generate env-config.js from .env
- `.gitignore` - Ensures .env is not committed

## Setup Instructions

### 1. Create .env File

Copy the example file:
```bash
cd frontend
cp .env.example .env
```

### 2. Fill in Your Values

Edit `.env` and replace placeholder values with your actual credentials:

```env
# API Configuration
API_BASE_URL=http://localhost:5000/api

# Firebase Configuration
FIREBASE_API_KEY=your_actual_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
# ... etc
```

### 3. Generate env-config.js

Since browsers can't directly read .env files, run the loader script:

```bash
node load-env.js
```

This creates `env-config.js` which is loaded by the HTML.

### 4. Include in HTML

The `index.html` already includes the necessary scripts:
- `env-loader.js` - Loads environment variables
- `env-config.js` - Generated from .env (auto-generated)

## Development Workflow

1. **First time setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   node load-env.js
   ```

2. **When .env changes:**
   ```bash
   node load-env.js
   ```

3. **Start development server:**
   ```bash
   # Your normal dev server command
   ```

## Environment Variables

### API Configuration
- `API_BASE_URL` - Backend API URL (default: http://localhost:5000/api)

### Firebase Configuration
- `FIREBASE_API_KEY` - Firebase API key
- `FIREBASE_AUTH_DOMAIN` - Firebase auth domain
- `FIREBASE_PROJECT_ID` - Firebase project ID
- `FIREBASE_STORAGE_BUCKET` - Firebase storage bucket
- `FIREBASE_MESSAGING_SENDER_ID` - Firebase messaging sender ID
- `FIREBASE_APP_ID` - Firebase app ID
- `FIREBASE_MEASUREMENT_ID` - Firebase measurement ID

### WhatsApp Configuration
- `WHATSAPP_DOCTOR_Aakash_NAME` - Doctor name
- `WHATSAPP_DOCTOR_Aakash_PHONE` - Doctor phone
- `WHATSAPP_DOCTOR_Aakash_WHATSAPP` - Doctor WhatsApp number

### Application Configuration
- `AI_ENABLED` - Enable/disable AI features (true/false)
- `MAX_FILE_SIZE` - Maximum file upload size in bytes
- `SUPPORTED_FORMATS` - Comma-separated list of supported file formats

## Security Notes

⚠️ **Important:**
- Never commit `.env` file to git
- Never commit `env-config.js` to git (it's in .gitignore)
- Use `.env.example` as a template
- Keep secrets secure
- In production, use proper environment variable management

## Troubleshooting

### Variables not loading?
1. Check if `env-config.js` exists (run `node load-env.js`)
2. Check browser console for errors
3. Verify `.env` file exists and has correct format
4. Ensure `env-loader.js` is loaded before other scripts

### Variables showing as undefined?
- Make sure you've run `node load-env.js` after changing `.env`
- Check that variable names match exactly (case-sensitive)
- Verify the variable exists in `.env` file

## Production Deployment

For production, you have several options:

1. **Build-time injection** (recommended):
   - Use a build tool (Vite, Webpack, Parcel)
   - Inject env vars at build time
   - Never expose .env file to client

2. **Server-side rendering**:
   - Generate env-config.js on server
   - Serve it with proper security headers

3. **Environment-specific configs**:
   - Use different .env files for dev/staging/prod
   - Generate appropriate env-config.js for each

## Files Structure

```
frontend/
├── .env                 # Your secrets (NOT in git)
├── .env.example        # Template (in git)
├── .gitignore          # Ignores .env and env-config.js
├── env-loader.js       # Browser env loader
├── load-env.js         # Node.js script to generate env-config.js
├── env-config.js       # Generated file (NOT in git)
└── ENV_SETUP.md        # This file
```

---

**Remember:** Always run `node load-env.js` after modifying `.env` file!

