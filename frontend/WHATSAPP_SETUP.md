# WhatsApp API Setup Guide

## Overview
This guide explains how to set up WhatsApp notifications for Dr. Aakash Singh Rajput (+91 9770064169) using Twilio WhatsApp API.

## Recommended API Provider: Twilio

### Why Twilio?
- ✅ Easy to set up and integrate
- ✅ Developer-friendly documentation
- ✅ Free trial with $15.50 credit
- ✅ Supports WhatsApp Business API
- ✅ Reliable and scalable
- ✅ Good for production use

**Website:** https://www.twilio.com/whatsapp

---

## Alternative Options

### 1. WhatsApp Business API (Official)
- **Website:** https://business.whatsapp.com/products/business-api
- **Pros:** Official API, direct integration
- **Cons:** Requires business verification, more complex setup
- **Best for:** Large enterprises with high volume

### 2. MessageBird
- **Website:** https://www.messagebird.com/en/whatsapp
- **Pros:** Good alternative to Twilio
- **Cons:** Less popular, smaller community
- **Best for:** European businesses

### 3. 360dialog
- **Website:** https://www.360dialog.com/
- **Pros:** WhatsApp Business API provider
- **Cons:** Requires business verification
- **Best for:** Businesses already using WhatsApp Business

---

## Twilio Setup Instructions

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/try-twilio
2. Sign up for a free account
3. Verify your email and phone number
4. You'll receive $15.50 in trial credit

### Step 2: Get Twilio Credentials
1. Log in to Twilio Console: https://console.twilio.com/
2. Go to Account → API Keys & Tokens
3. Copy your:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click to reveal)

### Step 3: Get WhatsApp Number
1. In Twilio Console, go to Messaging → Try it out → Send a WhatsApp message
2. You'll see a Twilio WhatsApp number (format: `whatsapp:+14155238886`)
3. Copy this number

### Step 4: Verify Recipient Number (Important!)
1. In Twilio Console, go to Messaging → Try it out
2. Send a test message to your recipient number: `+919770064169`
3. The recipient needs to reply to this message to verify
4. Once verified, you can send messages

### Step 5: Configure Backend
1. Create/update `backend/.env` file:
```env
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

2. Install Twilio Python SDK:
```bash
cd backend
pip install twilio
```

### Step 6: Test the Integration
1. Book an appointment with Dr. Aakash Singh Rajput
2. Check Twilio Console → Logs for message status
3. Verify WhatsApp message is received

---

## Cost Information

### Twilio Pricing (as of 2024)
- **WhatsApp Messages:** ~$0.005 - $0.01 per message
- **Free Trial:** $15.50 credit (good for ~1,500-3,000 messages)
- **Monthly:** Pay-as-you-go, no monthly fees

### Cost Example
- 100 appointments/month = ~$0.50 - $1.00/month
- Very affordable for small to medium practices

---

## Security Notes

⚠️ **Important:**
- Never commit `.env` file to git
- Keep Auth Token secret
- Use environment variables in production
- Verify recipient numbers before sending

---

## Troubleshooting

### Message Not Received?
1. Check if recipient number is verified in Twilio
2. Verify recipient replied to initial Twilio message
3. Check Twilio Console → Logs for errors
4. Ensure phone number format is correct: `+919770064169` (no spaces)

### API Errors?
1. Verify Account SID and Auth Token are correct
2. Check Twilio account has sufficient balance
3. Ensure WhatsApp number is properly configured
4. Check Twilio status page: https://status.twilio.com/

---

## Support Resources

- **Twilio Docs:** https://www.twilio.com/docs/whatsapp
- **Twilio Support:** https://support.twilio.com/
- **Twilio Community:** https://github.com/twilio

---

## Quick Start Checklist

- [ ] Sign up for Twilio account
- [ ] Get Account SID and Auth Token
- [ ] Get WhatsApp number from Twilio
- [ ] Verify recipient number (+919770064169)
- [ ] Add credentials to backend/.env
- [ ] Install Twilio Python SDK
- [ ] Test with a sample appointment
- [ ] Verify message received on WhatsApp

---

## Current Configuration

**Doctor:** Dr. Aakash Singh Rajput  
**Phone:** +91 9770064169  
**WhatsApp:** +919770064169  
**Status:** Ready for integration (requires Twilio setup)

---

**Need Help?** Check Twilio documentation or contact Twilio support.

