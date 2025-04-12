import asyncio
import os
import sys

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from dotenv import load_dotenv
import qrcode

# Load credentials from the .env file
load_dotenv()
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

if not api_id or not api_hash:
    print("Please ensure that API_ID and API_HASH are set in your .env file.")
    sys.exit(1)

# Define session file and load the session if it exists
SESSION_FILE = "session.json"
session_str = None
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        session_str = f.read().strip()

# Initialize the Telegram client using a StringSession
client = TelegramClient(StringSession(session_str), int(api_id), api_hash)


async def otp_login():
    """
    Performs OTP login (via phone number and code). The built-in client.start() method
    handles prompting for the phone number and OTP code.
    """
    print("Starting OTP login...")
    await client.start()  # Prompts for phone number and code
    new_session = client.session.save()
    with open(SESSION_FILE, "w") as f:
        f.write(new_session)
    print("Logged in with OTP. Session saved to", SESSION_FILE)


async def qr_login():
    """
    Performs QR code login.
    
    - Generates a QR code image from the login URL and waits for it to be scanned.
    - If the login process fails due to two-step verification being enabled,
      it will prompt for your password and complete the login.
    - The QR code image is deleted after a successful login.
    - The session is then saved.
    """
    qr_folder = "qr_codes"
    os.makedirs(qr_folder, exist_ok=True)
    
    while True:
        print("Starting QR code login session...")
        try:
            # Initiate the QR login process.
            qr = await client.qr_login()
        except Exception as e:
            print("Failed to initiate QR login:", e)
            return

        qr_url = qr.url
        qr_file = os.path.join(qr_folder, "qr_code.png")

        # Generate and save the QR code image
        qr_img = qrcode.make(qr_url)
        qr_img.save(qr_file)
        print(f"QR Code saved to {qr_file}. Please scan this QR with your Telegram app.")
        
        try:
            # Wait until the QR login process completes
            await qr.wait()
            print("QR code login successful!")
            
            # Clean up: remove the QR code image file after a successful login
            if os.path.exists(qr_file):
                os.remove(qr_file)
                print("QR code image deleted.")
                
            # Save the session to file
            new_session = client.session.save()
            with open(SESSION_FILE, "w") as f:
                f.write(new_session)
            print("Session saved to", SESSION_FILE)
            break  # Exit the loop since login succeeded
            
        except Exception as e:
            error_message = str(e)
            print("QR code login attempt failed with error:", error_message)
            # Handle two-step verification error by prompting for the password
            if "Two-steps verification" in error_message and "password is required" in error_message:
                print("Your account has two-step verification enabled. A password is required to complete login.")
                pw = input("Please enter your password: ")
                try:
                    await client.sign_in(password=pw)
                    print("Logged in successfully with two-step verification!")
                    
                    # Remove the QR code image after successful login
                    if os.path.exists(qr_file):
                        os.remove(qr_file)
                        print("QR code image deleted.")
                    
                    new_session = client.session.save()
                    with open(SESSION_FILE, "w") as f:
                        f.write(new_session)
                    print("Session saved to", SESSION_FILE)
                    break  # Exit the loop
                except Exception as sign_e:
                    print("Failed to sign in with password:", sign_e)
                    # Optionally, break out or loop again after failure.
                    break
            else:
                # For any other error, remove QR code file and exit
                if os.path.exists(qr_file):
                    os.remove(qr_file)
                break  # Exit the loop on unexpected errors


async def main():
    print("Choose login method:")
    print("1. OTP (via phone number and code)")
    print("2. QR code login")
    
    method = input("Enter your choice (1 or 2): ").strip()

    # Connect the client only after making the choice.
    await client.connect()
    
    if method == "1":
        await otp_login()
    elif method == "2":
        await qr_login()
    else:
        print("Invalid choice. Exiting.")
        await client.disconnect()
        sys.exit(1)
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
