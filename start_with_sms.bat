@echo off
echo Setting up Twilio environment variables...
set TWILIO_ACCOUNT_SID=`ACffaa1c8f115c16ef116dc68566eda696`
set TWILIO_AUTH_TOKEN=`fdae9ac8bd7c3d80fdb3229b107491b6`
set TWILIO_PHONE_NUMBER=`+17074189462`

echo Starting Currency Converter with SMS...
python app.py
pause
