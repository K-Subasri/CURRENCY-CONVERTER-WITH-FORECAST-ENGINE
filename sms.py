import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

sms_enabled = False
client = None

def init_sms():
    global sms_enabled, client

    if not ACCOUNT_SID or not AUTH_TOKEN or not FROM_NUMBER:
        print("[SMS] Missing Twilio credentials")
        sms_enabled = False
        return

    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.api.accounts(ACCOUNT_SID).fetch()
        sms_enabled = True
        print("[SMS] Twilio SMS Connected Successfully!")
    except Exception as e:
        sms_enabled = False
        print("[SMS ERROR] Twilio Initialization Failed:", e)


def send_sms(to, message):
    if not sms_enabled:
        print("[SMS DISABLED] SMS not sent.")
        return False

    try:
        client.messages.create(
            body=message,
            from_=FROM_NUMBER,
            to=to
        )
        print("[SMS SENT] →", to)
        return True

    except Exception as e:
        print("[SMS ERROR] Failed to send:", e)
        return False


# Initialize on import
init_sms()
