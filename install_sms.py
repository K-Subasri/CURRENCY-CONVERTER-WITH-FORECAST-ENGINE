#!/usr/bin/env python3
"""
SMS Setup Helper for Currency Converter
This script helps you set up SMS functionality
"""

import os
import subprocess
import sys

def install_twilio():
    """Install Twilio package"""
    try:
        print("[INSTALL] Installing Twilio package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "twilio"])
        print("[SUCCESS] Twilio installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to install Twilio")
        return False

def setup_environment():
    """Help user set up environment variables"""
    print("\n[SETUP] SMS Setup Instructions:")
    print("=" * 50)
    print("1. Sign up for a free Twilio account at: https://www.twilio.com")
    print("2. Get your credentials from the Twilio Console:")
    print("   - Account SID")
    print("   - Auth Token")
    print("   - Phone Number")
    print("\n3. Set environment variables:")
    print("   Windows:")
    print("   set TWILIO_ACCOUNT_SID=your_account_sid")
    print("   set TWILIO_AUTH_TOKEN=your_auth_token")
    print("   set TWILIO_PHONE_NUMBER=+1234567890")
    print("\n   Linux/Mac:")
    print("   export TWILIO_ACCOUNT_SID=your_account_sid")
    print("   export TWILIO_AUTH_TOKEN=your_auth_token")
    print("   export TWILIO_PHONE_NUMBER=+1234567890")
    print("\n4. Restart the application")
    print("\n[INFO] Free Twilio Trial includes $15 credit for testing!")

def check_current_setup():
    """Check current SMS setup"""
    print("[CHECK] Checking current SMS setup...")
    
    # Check if Twilio is installed
    try:
        import twilio
        print("[OK] Twilio package is installed")
    except ImportError:
        print("[ERROR] Twilio package not found")
        return False
    
    # Check environment variables
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    phone = os.getenv('TWILIO_PHONE_NUMBER')
    
    if sid and token and phone:
        print("[OK] Environment variables are set")
        print(f"   Account SID: {sid[:8]}...")
        print(f"   Phone Number: {phone}")
        return True
    else:
        print("[ERROR] Environment variables not set")
        print("   Missing:")
        if not sid:
            print("   - TWILIO_ACCOUNT_SID")
        if not token:
            print("   - TWILIO_AUTH_TOKEN")
        if not phone:
            print("   - TWILIO_PHONE_NUMBER")
        return False

def main():
    print("SMS Setup Helper for Currency Converter")
    print("=" * 40)
    
    # Check current setup
    if check_current_setup():
        print("\n[SUCCESS] SMS is already configured!")
        print("Your currency converter should be able to send real SMS notifications.")
    else:
        print("\n[SETUP] SMS needs to be configured")
        
        # Install Twilio if needed
        try:
            import twilio
            print("[OK] Twilio is already installed")
        except ImportError:
            if input("\nInstall Twilio package? (y/n): ").lower() == 'y':
                if not install_twilio():
                    return
        
        # Show setup instructions
        setup_environment()
    
    print("\n[SUCCESS] You can now run your currency converter with SMS alerts!")
    print("   python app.py")

if __name__ == "__main__":
    main()
