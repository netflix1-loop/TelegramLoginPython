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

# Define session file and load existing session if available
SESSION_FILE = "session.json"
session_str = None
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        session_str = f.read().strip()

# Initialize the Telegram client with a StringSession
client = TelegramClient(StringSession(session_str), int(api_id), api_hash)

async def otp_login():
    """
    Performs login via OTP (phone number + code). Telethon's start() method
    handles prompting for the phone number and OTP code.
    """
    print("Starting OTP login...")
    await client.start()  # Prompts for phone number and then the OTP code.
    new_session = client.session.save()
    with open(SESSION_FILE, "w") as f:
        f.write(new_session)
    print("Logged in with OTP. Session saved to", SESSION_FILE)

async def qr_login():
    """
    Performs QR code login.
    
    - Generates an ASCII QR code from the login URL and displays it in the terminal.
    - If the login process fails due to two-step verification being enabled,
      it will prompt for your password and complete the login.
    - After a successful login, the session is saved.
    
    If the client is already authorized (the session is valid), it prints a message
    and returns without reattempting QR login.
    """
    # Await the asynchronous check to see if the user is already authorized.
    if await client.is_user_authorized():
        print("Session is already authorized. No need for QR login.")
        return

    while True:
        print("Starting QR code login session...")
        try:
            # Initiate the QR login process.
            qr = await client.qr_login()
        except Exception as e:
            print("Failed to initiate QR login:", e)
            return

        # Generate and display the ASCII QR code in the terminal.
        qr_url = qr.url
        # Create a QRCode object and add the data.
        qr_obj = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr_obj.add_data(qr_url)
        qr_obj.make(fit=True)
        matrix = qr_obj.get_matrix()

        # Build the ASCII QR code string, using block characters for filled modules.
        qr_ascii = ""
        for row in matrix:
            line = ""
            for col in row:
                if col:
                    line += "██"  # Two blocks for a filled module.
                else:
                    line += "  "  # Two spaces for an empty module.
            qr_ascii += line + "\n"
        print(qr_ascii)
        print("Please scan the above QR code with your Telegram app.")
        
        try:
            # Wait until the QR login process completes.
            await qr.wait()
            print("QR code login successful!")
            
            # Save the new session to file.
            new_session = client.session.save()
            with open(SESSION_FILE, "w") as f:
                f.write(new_session)
            print("Session saved to", SESSION_FILE)
            break  # Exit the loop since login succeeded
            
        except Exception as e:
            error_message = str(e)
            print("QR code login attempt failed with error:", error_message)
            # Handle two-step verification error by prompting for the password.
            if "Two-steps verification" in error_message and "password is required" in error_message:
                print("Your account has two-step verification enabled. A password is required to complete login.")
                pw = input("Please enter your password: ")
                try:
                    await client.sign_in(password=pw)
                    print("Logged in successfully with two-step verification!")
                    new_session = client.session.save()
                    with open(SESSION_FILE, "w") as f:
                        f.write(new_session)
                    print("Session saved to", SESSION_FILE)
                    break  # Exit the loop.
                except Exception as sign_e:
                    print("Failed to sign in with password:", sign_e)
                    break
            else:
                break  # Exit the loop on unexpected errors.

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
