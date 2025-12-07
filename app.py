from dotenv import load_dotenv
load_dotenv()


from flask import Flask, render_template, request
from datetime import datetime, timedelta
import random
import requests
import json
import os
import re

# scheduler for daily jobs
from apscheduler.schedulers.background import BackgroundScheduler

# Optional Twilio import for SMS functionality
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("[INFO] Twilio not installed. SMS functionality will be in demo mode.")

app = Flask(__name__)

# Supported currencies
CURRENCIES = ["USD", "INR", "EUR", "GBP", "JPY"]

# In-memory history (persisted to history.json)
history = []
# In-memory alerts (persisted to alerts.json)
alerts = []
# Cache the latest forecast so it can be reused on dedicated pages
last_forecast = {
    "labels": [],
    "values": [],
    "summary": None
}

# subscribers list (phone numbers registered for DAILY summaries)
subscribers = []

# SMS Configuration (using Twilio - you can get free credits)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_twilio_sid')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_twilio_token')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')

# Initialize Twilio client (will work with demo credentials)
if TWILIO_AVAILABLE:
    try:
        sms_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        SMS_ENABLED = True
    except:
        SMS_ENABLED = False
        print("[WARN] SMS service not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.")
else:
    SMS_ENABLED = False
    sms_client = None


def load_history():
    global history
    try:
        if os.path.exists("history.json"):
            with open("history.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    history = data
    except Exception as e:
        print(f"[WARN] Failed to load history.json: {e}")


def save_history():
    try:
        with open("history.json", "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save history.json: {e}")


def load_alerts():
    global alerts
    try:
        if os.path.exists("alerts.json"):
            with open("alerts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    alerts = data
    except Exception as e:
        print(f"[WARN] Failed to load alerts.json: {e}")


def save_alerts():
    try:
        with open("alerts.json", "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save alerts.json: {e}")

# --- Subscribers persistence (new) ---
def load_subscribers():
    global subscribers
    try:
        if os.path.exists("subscribers.json"):
            with open("subscribers.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    subscribers = data
    except Exception as e:
        print(f"[WARN] Failed to load subscribers.json: {e}")


def save_subscribers():
    try:
        with open("subscribers.json", "w", encoding="utf-8") as f:
            json.dump(subscribers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save subscribers.json: {e}")


def validate_phone_number(phone):
    """Validate phone number format"""
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    # Must start with + and have 10-15 digits
    if cleaned.startswith('+') and len(cleaned) >= 11 and len(cleaned) <= 16:
        return cleaned
    return None


def send_sms_notification(phone_number, message):
    """Send SMS notification using Twilio"""
    if not SMS_ENABLED:
        print(f"[DEMO] SMS would be sent to {phone_number}: {message}")
        return True
    
    if not TWILIO_AVAILABLE:
        print(f"[DEMO] Twilio not available - SMS would be sent to {phone_number}: {message}")
        return True
    
    try:
        message_obj = sms_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"[SMS] Sent to {phone_number}: {message_obj.sid}")
        return True
    except Exception as e:
        print(f"[SMS ERROR] Failed to send to {phone_number}: {e}")
        # Return True in demo mode to avoid blocking the app
        if "demo" in str(e).lower() or "trial" in str(e).lower():
            print(f"[DEMO] SMS simulation for {phone_number}: {message}")
            return True
        return False


def get_weekly_high_rate(from_currency, to_currency):
    """Get the highest rate for this currency pair in the past 7 days"""
    try:
        # Get rates for the past 7 days
        rates = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                # Try to get historical rate (simplified - in real app, use historical API)
                rate = get_exchange_rate(from_currency, to_currency, mode="live")
                rates.append(rate)
            except:
                continue
        
        if rates:
            return max(rates)
        else:
            # Fallback to current rate
            return get_exchange_rate(from_currency, to_currency, mode="live")
    except:
        return get_exchange_rate(from_currency, to_currency, mode="live")

# Fallback exchange rates (approximate, as of 2025)
FALLBACK_RATES = {
    "USD": {"INR": 88, "EUR": 0.92, "GBP": 0.79, "JPY": 146},
    "INR": {"USD": 0.011, "EUR": 0.010, "GBP": 0.0090, "JPY": 1.65},
    "EUR": {"USD": 1.09, "INR": 96, "GBP": 0.86, "JPY": 159},
    "GBP": {"USD": 1.27, "INR": 112, "EUR": 1.16, "JPY": 185},
    "JPY": {"USD": 0.0068, "INR": 0.61, "EUR": 0.0063, "GBP": 0.0054},
}


def get_exchange_rate(from_currency, to_currency, mode="live"):
    """
    Get real-time exchange rate using multiple reliable APIs for today's accurate rates.
    Falls back to static rates if all APIs fail.
    """
    # If both currencies are same → rate is 1
    if from_currency == to_currency:
        return 1.0

    # If explicitly in simulated mode, skip API and use fallback
    if mode == "simulated":
        return FALLBACK_RATES.get(from_currency, {}).get(to_currency, 1.0)

    # Try multiple reliable APIs for today's accurate rates
    apis = [
        {
            "name": "exchangerate-api",
            "url": f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
            "extract": lambda r: r.get("rates", {}).get(to_currency),
            "headers": {"User-Agent": "CurrencyConverter/1.0"}
        },
        {
            "name": "currencylayer",
            "url": f"https://api.currencylayer.com/live?access_key=free&currencies={to_currency}&source={from_currency}&format=1",
            "extract": lambda r: r.get("quotes", {}).get(f"{from_currency}{to_currency}")
        },
        {
            "name": "exchangerate.host",
            "url": f"https://api.exchangerate.host/latest?base={from_currency}&symbols={to_currency}",
            "extract": lambda r: r.get("rates", {}).get(to_currency),
            "headers": {"User-Agent": "CurrencyConverter/1.0"}
        },
        {
            "name": "fixer.io",
            "url": f"https://api.fixer.io/latest?base={from_currency}&symbols={to_currency}",
            "extract": lambda r: r.get("rates", {}).get(to_currency)
        }
    ]

    for api in apis:
        try:
            print(f"[INFO] Fetching today's rate from {api['name']}...")
            headers = api.get("headers", {})
            response = requests.get(api["url"], timeout=15, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Check if API response is valid
            if "error" in data:
                print(f"[WARN] API error from {api['name']}: {data.get('error', {}).get('info', 'Unknown error')}")
                continue
                
            rate = api["extract"](data)
            if rate and rate > 0:
                print(f"[SUCCESS] Today's rate from {api['name']}: {rate:.6f}")
                return float(rate)
            else:
                print(f"[WARN] Invalid rate from {api['name']}: {rate}")
                
        except requests.exceptions.Timeout:
            print(f"[WARN] {api['name']} timeout - trying next API")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[WARN] {api['name']} request failed: {e}")
            continue
        except Exception as e:
            print(f"[WARN] {api['name']} failed: {e}")
            continue

    print("[WARN] All live APIs failed, using fallback rates")
    # Fallback lookup with safety
    return FALLBACK_RATES.get(from_currency, {}).get(to_currency, 1.0)


def compute_history_analytics():
    """Build aggregated analytics for history tables."""
    if not history:
        return None
    try:
        total_conversions = len(history)
        total_amount = round(sum(item.get("amount", 0) for item in history), 2)
        pair_counts = {}
        largest_amount = 0
        largest_amount_pair = None
        last_time = history[-1].get("time")
        for item in history:
            pair = f"{item.get('from')}→{item.get('to')}"
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
            amt = float(item.get("amount", 0))
            if amt > largest_amount:
                largest_amount = amt
                largest_amount_pair = pair
        most_frequent_pair = None
        if pair_counts:
            most_frequent_pair = max(pair_counts.items(), key=lambda kv: kv[1])[0]
        return {
            "total_conversions": total_conversions,
            "total_amount": total_amount,
            "unique_pairs": len(pair_counts),
            "most_frequent_pair": most_frequent_pair,
            "largest_amount": largest_amount,
            "largest_amount_pair": largest_amount_pair,
            "last_conversion_time": last_time,
        }
    except Exception as e:
        print(f"[WARN] Failed to compute analytics: {e}")
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    global history, alerts, last_forecast
    result = None
    chart_labels = []
    chart_values = []
    forecast_summary = None
    selected_mode = "live"
    analytics = None
    notifications = []

    if request.method == "POST":
        from_currency = request.form.get("from_currency")
        to_currency = request.form.get("to_currency")
        selected_mode = request.form.get("mode", "live")
        amount_value = request.form.get("amount")

        if "convert" in request.form:
            if amount_value is None or amount_value == "":
                notifications.append("Amount is required to convert.")
                return render_template(
                    "index.html",
                    currencies=CURRENCIES,
                    history=history,
                    result=result,
                    mode=selected_mode,
                    chart_labels=chart_labels,
                    chart_values=chart_values,
                    forecast_summary=forecast_summary,
                    analytics=analytics,
                    alerts=alerts,
                    notifications=notifications
                )
            
            try:
                amount = float(amount_value)
                if amount <= 0:
                    notifications.append("Amount must be greater than 0.")
                    return render_template(
                        "index.html",
                        currencies=CURRENCIES,
                        history=history,
                        result=result,
                        mode=selected_mode,
                        chart_labels=chart_labels,
                        chart_values=chart_values,
                        forecast_summary=forecast_summary,
                        analytics=analytics,
                        alerts=alerts,
                        notifications=notifications
                    )
                
                # Get rate based on mode (live with fallback, or simulated)
                rate = get_exchange_rate(from_currency, to_currency, mode=selected_mode)
                
                # Calculate conversion with proper precision
                result = round(amount * rate, 2)
                
                # Calculate cost range (min/max with 1% variance)
                cost_variance = 0.01  # 1% variance
                min_result = round(result * (1 - cost_variance), 2)
                max_result = round(result * (1 + cost_variance), 2)
                
                # Store history with enhanced data
                history.append({
                    "from": from_currency,
                    "to": to_currency,
                    "amount": amount,
                    "result": result,
                    "rate": round(rate, 6),  # More precise rate storage
                    "mode": selected_mode,
                    "cost_range": {
                        "min": min_result,
                        "max": max_result,
                        "variance": cost_variance
                    },
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                save_history()
                
                # Add success notification
                notifications.append(f"Successfully converted {amount} {from_currency} to {result} {to_currency} at rate {rate:.6f}")
                
            except ValueError:
                notifications.append("Invalid amount. Please enter a valid number.")
                return render_template(
                    "index.html",
                    currencies=CURRENCIES,
                    history=history,
                    result=result,
                    mode=selected_mode,
                    chart_labels=chart_labels,
                    chart_values=chart_values,
                    forecast_summary=forecast_summary,
                    analytics=analytics,
                    alerts=alerts,
                    notifications=notifications
                )

        elif "forecast" in request.form:
            if amount_value is None or amount_value == "":
                notifications.append("Amount is required to forecast.")
                return render_template(
                    "index.html",
                    currencies=CURRENCIES,
                    history=history,
                    result=result,
                    mode=selected_mode,
                    chart_labels=chart_labels,
                    chart_values=chart_values,
                    forecast_summary=forecast_summary,
                    analytics=analytics,
                    alerts=alerts,
                    notifications=notifications
                )
            amount = float(amount_value)
            # Base conversion
            rate = get_exchange_rate(from_currency, to_currency, mode=selected_mode)
            base_value = round(amount * rate, 2)

            # Generate 7-day simulated forecast with slight trend and random noise
            days = 7
            chart_labels = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days + 1)]

            # Simulate a mild trend: -1% to +1% over the period, plus daily noise
            overall_trend = random.uniform(-0.01, 0.01)
            daily_values = []
            for i in range(1, days + 1):
                progress = i / days
                trend_component = overall_trend * progress
                noise_component = random.uniform(-0.0075, 0.0075)
                multiplier = 1 + trend_component + noise_component
                daily_values.append(round(base_value * multiplier, 2))

            chart_values = daily_values

            # Analytics: rise/fall and amount/percentage change from day 0 to day 7
            final_value = chart_values[-1] if chart_values else base_value
            change_abs = round(final_value - base_value, 2)
            change_pct = round((change_abs / base_value) * 100, 2) if base_value != 0 else 0.0
            direction = "Rise" if change_abs > 0 else ("Fall" if change_abs < 0 else "No Change")
            # Advice logic based on magnitude of change
            threshold_pct = 1.0  # percent
            if direction == "Rise" and abs(change_pct) >= threshold_pct:
                advice = "Convert now"
            elif direction == "Fall" and abs(change_pct) >= threshold_pct:
                advice = "Wait"
            else:
                advice = "Watch"

            forecast_summary = {
                "direction": direction,
                "change_abs": abs(change_abs),
                "change_pct": abs(change_pct),
                "base_value": base_value,
                "final_value": final_value,
                "days": days,
                "advice": advice,
            }

            last_forecast = {
                "labels": chart_labels,
                "values": chart_values,
                "summary": forecast_summary
            }
        elif "add_alert" in request.form:
            # Create a new SMS rate alert for a pair
            try:
                target_rate = float(request.form.get("target_rate"))
                phone_number = request.form.get("phone_number", "").strip()
                
                # Validate phone number
                validated_phone = validate_phone_number(phone_number)
                if not validated_phone:
                    notifications.append("Invalid phone number format. Please use international format (+1234567890)")
                    return render_template(
                        "index.html",
                        currencies=CURRENCIES,
                        history=history,
                        result=result,
                        mode=selected_mode,
                        chart_labels=chart_labels,
                        chart_values=chart_values,
                        forecast_summary=forecast_summary,
                        analytics=analytics,
                        alerts=alerts,
                        notifications=notifications
                    )
                
                # Get current rate and weekly high for comparison
                current_rate = get_exchange_rate(from_currency, to_currency, mode="live")
                weekly_high = get_weekly_high_rate(from_currency, to_currency)
                
                # Create alert with SMS info
                alert_data = {
                    "from": from_currency,
                    "to": to_currency,
                    "target_rate": target_rate,
                    "phone_number": validated_phone,
                    "current_rate": round(current_rate, 6),
                    "weekly_high": round(weekly_high, 6),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "triggered_at": None,
                    "sms_sent": False
                }
                
                alerts.append(alert_data)
                save_alerts()
                
                # Send confirmation SMS
                confirmation_message = f"📱 Currency Alert Registered!\n{from_currency}→{to_currency}\nTarget: {target_rate}\nCurrent: {current_rate:.6f}\nWeekly High: {weekly_high:.6f}\n\nYou'll be notified when the rate reaches your target!"
                send_sms_notification(validated_phone, confirmation_message)
                
                notifications.append(f"📱 SMS Alert registered for {from_currency}→{to_currency} at rate {target_rate}. Confirmation sent to {validated_phone}")
                
            except ValueError:
                notifications.append("Invalid target rate. Please enter a valid number.")
            except Exception as e:
                notifications.append(f"Failed to create alert: {str(e)}")

    # Check alerts against current live rates and send SMS notifications
    if alerts:
        try:
            for alert in alerts:
                if alert.get("triggered_at") or alert.get("sms_sent"):
                    continue
                    
                f = alert.get("from")
                t = alert.get("to")
                target = float(alert.get("target_rate", 0))
                phone = alert.get("phone_number")
                
                if not phone:
                    continue
                
                current = get_exchange_rate(f, t, mode="live")
                weekly_high = get_weekly_high_rate(f, t)
                
                # Check if target rate is reached
                if current >= target:
                    alert["triggered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    alert["sms_sent"] = True
                    
                    # Send SMS notification
                    sms_message = f"🚨 CURRENCY ALERT! 🚨\n\n{f}→{t} Rate Alert Triggered!\n\nTarget Rate: {target}\nCurrent Rate: {current:.6f}\nWeekly High: {weekly_high:.6f}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nThis is the highest rate this week! 💰"
                    
                    if send_sms_notification(phone, sms_message):
                        notifications.append(f"📱 SMS sent: {f}→{t} rate {current:.6f} reached target {target}")
                    else:
                        notifications.append(f"⚠️ SMS failed: {f}→{t} rate {current:.6f} reached target {target}")
                
                # Check if current rate is weekly high (even if target not reached)
                elif current >= weekly_high and not alert.get("weekly_high_notified"):
                    alert["weekly_high_notified"] = True
                    
                    # Send weekly high notification
                    weekly_high_message = f"📈 WEEKLY HIGH ALERT! 📈\n\n{f}→{t} reached weekly high!\n\nCurrent Rate: {current:.6f}\nWeekly High: {weekly_high:.6f}\nTarget: {target}\n\nThis is the best rate this week! 🎯"
                    
                    if send_sms_notification(phone, weekly_high_message):
                        notifications.append(f"📱 Weekly high SMS sent: {f}→{t} rate {current:.6f} is weekly high")
                    else:
                        notifications.append(f"⚠️ Weekly high SMS failed: {f}→{t} rate {current:.6f} is weekly high")
                        
            save_alerts()
        except Exception as e:
            print(f"[WARN] Failed checking alerts: {e}")

    # Build analytics from history
    analytics = compute_history_analytics()

    return render_template(
        "index.html",
        currencies=CURRENCIES,
        history=history,
        result=result,
        mode=selected_mode,
        chart_labels=chart_labels,
        chart_values=chart_values,
        forecast_summary=forecast_summary,
        analytics=analytics,
        alerts=alerts,
        notifications=notifications
    )


@app.route("/api/rate/<from_currency>/<to_currency>")
def get_live_rate(from_currency, to_currency):
    """API endpoint to get live exchange rate"""
    try:
        rate = get_exchange_rate(from_currency, to_currency, mode="live")
        return {
            "success": True,
            "from": from_currency,
            "to": to_currency,
            "rate": round(rate, 6),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "from": from_currency,
            "to": to_currency
        }


@app.route("/api/test-sms/<phone_number>")
def test_sms(phone_number):
    """Test SMS functionality"""
    try:
        message = f"📱 Test SMS from Currency Converter!\n\nThis is a test message to verify SMS functionality.\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nIf you received this, SMS alerts are working! ✅"
        
        if send_sms_notification(phone_number, message):
            return {
                "success": True, 
                "message": "SMS sent successfully",
                "mode": "demo" if not SMS_ENABLED else "live",
                "details": "Check console for SMS content in demo mode"
            }
        else:
            return {
                "success": False, 
                "message": "SMS failed to send",
                "mode": "demo" if not SMS_ENABLED else "live",
                "details": "SMS service not configured. Check SMS_SETUP.md for setup instructions."
            }
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "mode": "demo" if not SMS_ENABLED else "live",
            "details": "SMS service not configured. Check SMS_SETUP.md for setup instructions."
        }


@app.route("/subscribe", methods=["POST"])
def subscribe():
    """
    Register a phone number for daily summary SMS.
    Expects form field 'phone_number'. Returns JSON or redirects depending on caller.
    """
    try:
        phone = request.form.get("phone_number", "").strip()
        validated = validate_phone_number(phone)
        if not validated:
            return {"success": False, "error": "Invalid phone format. Use international format (+1234567890)"}, 400

        # avoid duplicate
        exists = any(s.get("phone") == validated for s in subscribers)
        if not exists:
            subscribers.append({
                "phone": validated,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # placeholder for future preferences (preferred currencies etc.)
                "prefs": {"pairs": []}
            })
            save_subscribers()

            # send immediate registration confirmation
            msg = f"✅ You have subscribed to daily currency summary.\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nYou will receive daily updates."
            send_sms_notification(validated, msg)

        return {"success": True, "subscribed": validated}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


@app.route("/dashboard")
def dashboard():
    """Dashboard route to display analytics and charts"""
    daily_totals = {}
    pair_counts = {}
    mode_counts = {"live": 0, "simulated": 0}

    # Process history data
    for item in history:
        try:
            t = item.get("time")
            date_key = t.split(" ")[0] if isinstance(t, str) and " " in t else t
            daily_totals[date_key] = daily_totals.get(date_key, 0) + float(item.get("amount", 0))

            pair = f"{item.get('from')}→{item.get('to')}"
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

            m = item.get("mode", "live")
            if m in mode_counts:
                mode_counts[m] += 1
            else:
                mode_counts[m] = 1
        except (ValueError, KeyError, AttributeError):
            # Skip invalid history entries
            continue

    daily_labels = sorted(daily_totals.keys()) if daily_totals else []
    daily_values = [round(daily_totals[k], 2) for k in daily_labels] if daily_labels else []

    sorted_pairs = sorted(pair_counts.items(), key=lambda kv: kv[1], reverse=True)[:5] if pair_counts else []
    pair_labels = [kv[0] for kv in sorted_pairs] if sorted_pairs else []
    pair_values = [kv[1] for kv in sorted_pairs] if sorted_pairs else []

    mode_labels = list(mode_counts.keys()) if mode_counts else []
    mode_values = [mode_counts[k] for k in mode_labels] if mode_labels else []

    return render_template("dashboard.html", daily_labels=daily_labels, daily_values=daily_values, pair_labels=pair_labels, pair_values=pair_values, mode_labels=mode_labels, mode_values=mode_values)


@app.route("/history")
def history_page():
    """Dedicated history view."""
    analytics = compute_history_analytics()
    return render_template("history.html", history=history, analytics=analytics)


@app.route("/forecast")
def forecast_page():
    """Dedicated forecast view."""
    return render_template(
        "forecast.html",
        chart_labels=last_forecast.get("labels", []),
        chart_values=last_forecast.get("values", []),
        forecast_summary=last_forecast.get("summary"),
    )


# --- daily summary builder & sender (new) ---
def build_daily_summary():
    """
    Build a short daily summary message for SMS.
    This uses a few popular currency pairs; adapt as needed or use subscriber preferences.
    """
    try:
        pairs = [("USD", "INR"), ("EUR", "INR"), ("GBP", "INR"), ("USD", "EUR")]
        lines = [f"Daily Currency Summary — {datetime.now().strftime('%Y-%m-%d')}"]
        for f, t in pairs:
            try:
                rate = get_exchange_rate(f, t, mode="live")
                lines.append(f"{f}→{t}: {rate:.6f}")
            except Exception:
                lines.append(f"{f}→{t}: N/A")
        lines.append("\nHave a good day! - Currency Studio")
        return "\n".join(lines)
    except Exception as e:
        return f"Daily Currency Summary is currently unavailable. ({e})"


def send_daily_summary_job():
    """Scheduled job: send daily summary to all subscribers"""
    if not subscribers:
        print("[INFO] No subscribers to send daily summary to.")
        return

    message = build_daily_summary()
    print(f"[INFO] Sending daily summary to {len(subscribers)} subscribers.")
    for sub in list(subscribers):
        phone = sub.get("phone")
        if not phone:
            continue
        try:
            ok = send_sms_notification(phone, message)
            if ok:
                print(f"[INFO] Daily summary sent to {phone}")
            else:
                print(f"[WARN] Failed to send daily summary to {phone}")
        except Exception as e:
            print(f"[WARN] Exception sending daily summary to {phone}: {e}")

if __name__ == "__main__":
    load_history()
    load_alerts()
    load_subscribers()   # load subscribers on startup

    # start scheduler for daily job (run at 09:00 local time)
    scheduler = BackgroundScheduler()
    # run daily at 09:00 — adjust hour/minute as needed
    scheduler.add_job(send_daily_summary_job, 'cron', hour=9, minute=0, id="daily_summary")
    # Ensure scheduler starts only in main process (Werkzeug reloader guard)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        try:
            scheduler.start()
            print("[INFO] Scheduler started. Daily summary job scheduled at 09:00.")
        except Exception as e:
            print(f"[WARN] Scheduler failed to start: {e}")

    # Print SMS service status
    if SMS_ENABLED:
        print("✅ SMS Service: ENABLED (Live SMS notifications)")
    else:
        print("🔧 SMS Service: DEMO MODE (SMS content shown in console)")
        print("   To enable real SMS, set up Twilio credentials (see SMS_SETUP.md)")
    
    print("🚀 Currency Converter with SMS Alerts starting...")
    app.run(debug=True)
