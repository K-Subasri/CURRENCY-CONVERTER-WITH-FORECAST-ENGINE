# SMS Alert Setup Guide

## 📱 SMS Notifications for Currency Alerts

Your currency converter now supports SMS notifications for all registered users! The system automatically sends conversion rate updates to all registered users every 2 hours.

### Features:
- **Automatic Notifications**: All registered users receive SMS updates every 2 hours with current conversion rates
- **Rate Change Alerts**: Instant notifications when exchange rates change significantly (>= 0.5%)
- **Target Rate Alerts**: Notifies when specific target rates are reached
- **Real-time SMS**: Instant notifications via Twilio SMS API

### Setup Instructions:

#### 1. Install Dependencies
```bash
pip install twilio APScheduler
```

Or install all requirements:
```bash
pip install -r currency_curren/requirements.txt
```

#### 2. Twilio Credentials (Already Configured)
✅ **Your Twilio credentials are already configured in the code:**
- Account SID: `ACffaa1c8f115c16ef116dc68566eda696`
- Auth Token: `fdae9ac8bd7c3d80fdb3229b107491b6`
- Phone Number: `+17074189462`

These are set in `currency_curren/src/sms.py` and will be used automatically.

#### 3. Verify Twilio Installation
Make sure Twilio is installed:
```bash
pip install twilio==8.10.0
```

#### 4. How It Works
1. **Automatic Notifications**: Every 2 hours, the system automatically:
   - Fetches current conversion rates for popular currency pairs
   - Sends SMS notifications to ALL registered users with phone numbers
   
2. **Rate Change Alerts**: When exchange rates change by 0.5% or more:
   - All registered users receive instant SMS notifications
   
3. **Target Rate Alerts**: When a user's target rate is reached:
   - All registered users are notified via SMS

#### 5. Verify Installation
After installing Twilio, restart your Flask app. You should see in the console:
```
[INFO] Twilio package found, initializing client...
[INFO] ✅ SMS Service: ENABLED (Twilio configured and verified)
[INFO] 📱 Twilio Account: [Your Account Name]
[INFO] 📱 Twilio Phone: +17074189462
```

If you see warnings instead, check:
- Twilio package is installed: `pip list | grep twilio`
- Credentials are correct in `currency_curren/src/sms.py`
- Twilio account has sufficient credits
- Phone numbers are verified (for trial accounts)

#### 6. Troubleshooting

**Issue: "SMS service not configured"**
- Solution: Make sure Twilio is installed: `pip install twilio==8.10.0`
- Restart the Flask app after installation

**Issue: "Authentication failed"**
- Solution: Verify credentials in `currency_curren/src/sms.py` match your Twilio account
- Check Twilio console for Account SID and Auth Token

**Issue: "Phone number not verified"**
- Solution: For Twilio trial accounts, you must verify recipient phone numbers in Twilio console
- Go to Twilio Console > Phone Numbers > Verified Caller IDs
- Add and verify the phone numbers you want to send SMS to

**Issue: SMS sent but not received**
- Check Twilio console logs for delivery status
- Verify phone number format is correct (+1234567890)
- For trial accounts, ensure phone number is verified

#### 7. Demo Mode
If Twilio is not installed or credentials are invalid, the app will run in demo mode and show SMS messages in the console. This allows you to test the functionality without sending actual SMS.

### How It Works:

1. **Register Alert**: User enters currency pair, target rate, and phone number
2. **Confirmation SMS**: User receives confirmation SMS with current rates
3. **Weekly High Tracking**: System monitors rates and compares with past 7 days
4. **SMS Notifications**: 
   - When target rate is reached
   - When rate hits weekly high (even if target not reached)
5. **Real-time Updates**: Alerts are checked on every page load

### SMS Message Examples:

**Confirmation:**
```
📱 Currency Alert Registered!
USD→INR
Target: 0.0113
Current: 0.011300
Weekly High: 0.011500

You'll be notified when the rate reaches your target!
```

**Alert Triggered:**
```
🚨 CURRENCY ALERT! 🚨

USD→INR Rate Alert Triggered!

Target Rate: 0.0113
Current Rate: 0.011300
Weekly High: 0.011300

Time: 2025-01-27 14:30:00

This is the highest rate this week! 💰
```

### Testing:
- Use the "🧪 Test SMS" button to test SMS functionality
- Check console logs for demo mode messages
- Verify phone number format: +1234567890

### Free Twilio Trial:
- $15 free credit
- Can send SMS to verified numbers
- Perfect for testing and small-scale usage
