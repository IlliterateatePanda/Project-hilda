import os
import time
import threading
import subprocess
import sys
from flask import Flask, redirect, request, url_for
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timezone
import json

# Allowing insecure transport for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Path to your OAuth 2.0 client secrets file
CLIENT_SECRET_FILE = ''
SCOPES = ['https://www.googleapis.com/auth/chat.messages.readonly', 'https://www.googleapis.com/auth/chat.messages']

# Define the redirect URI
REDIRECT_URI = ''

app = Flask(__name__)

# Function to handle and log errors, and then exit the script
def handle_error(e):
    crashes_dir = 'crashes'
    if not os.path.exists(crashes_dir):
        os.makedirs(crashes_dir)  # Create the crashes folder if it doesn't exist

    # Use MM-DD-YYYY HH-MM for the filename
    error_time = datetime.now().strftime('%m-%d-%Y_%H-%M')
    error_file = os.path.join(crashes_dir, f'error_{error_time}.txt')

    # Get the full timestamp for the crash
    crash_timestamp = datetime.now().strftime('%m-%d-%Y %H:%M')

    with open(error_file, 'w') as file:
        file.write(f"Crash occurred at: {crash_timestamp}\n")  # Include exact crash time
        file.write(f"Error details: {str(e)}\n")  # Log the error message

    print(f"Error logged in {error_file}")
    sys.exit(1)  # Exit the script with a non-zero status to indicate an error

@app.route('/')
def home():
    try:
        return 'Hello, go to /login to authenticate.'
    except Exception as e:
        handle_error(e)

@app.route('/login')
def login():
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        flow.redirect_uri = REDIRECT_URI
        authorization_url, state = flow.authorization_url(include_granted_scopes='true')
        return redirect(authorization_url)
    except Exception as e:
        handle_error(e)

@app.route('/oauth2callback')
def oauth2callback():
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        flow.redirect_uri = REDIRECT_URI
        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials  # Extract the credentials object

        # Save credentials to file for reuse (including refresh_token)
        with open('token.json', 'w') as token_file:
            token_file.write(credentials.to_json())

        # Check if the token is expired, and refresh it if needed
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        # Save updated credentials
        with open('token.json', 'w') as token_file:
            token_file.write(credentials.to_json())

        # Build the service with the credentials
        service = build('chat', 'v1', credentials=credentials)

        # Function to fetch and print the most recent message mentioning "@Hilda"
        def fetch_new_messages():
            try:
                space_id = 'spaces/AAAAAAAA'  # Replace with the actual space ID
                script_start_time = datetime.now(timezone.utc)  # Using timezone-aware datetime
                latest_message_time = script_start_time  # Variable to store the latest message time

                while True:
                    response = service.spaces().messages().list(
                        parent=space_id,
                        pageSize=100,
                        orderBy='createTime desc'  # Order messages by creation time
                    ).execute()

                    messages = response.get('messages', [])

                    # Filter and process messages posted after the latest processed message time
                    for message in messages:
                        message_time = datetime.strptime(message['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        message_time = message_time.replace(tzinfo=timezone.utc)  # Make message time timezone-aware

                        # Check if the sender is a bot and ignore the message if true
                        if 'sender' in message and message['sender'].get('type') == 'BOT':
                            continue

                        # Only consider messages posted after the latest processed message time
                        if message_time > latest_message_time and 'text' in message:
                            message_text = message['text']
                            
                            # Check if the message contains the prefix "@Hilda"
                            if '@Hilda' in message_text:
                                print(f"Message mentioning '@Hilda' at {message['createTime']}: {message_text}")
                                latest_message_time = message_time  # Update the latest message time

                                # Store the new message in queue.txt, ensuring it's in a JSON-compatible list format
                                with open('queue.txt', 'w', encoding='utf-8') as file:
                                    # Write the message as a JSON-formatted list
                                    json.dump([message_text], file, ensure_ascii=False, indent=2)

                                # Launch receiver script as a subprocess
                                subprocess.Popen(['python', 'mouth.py'])

                    # Delay to prevent excessive API calls
                    time.sleep(1)
            except Exception as e:
                handle_error(e)

        # Run the fetch_new_messages function in a separate thread to prevent blocking
        thread = threading.Thread(target=fetch_new_messages)
        thread.daemon = True  # Set as a daemon thread to exit when the main program exits
        thread.start()

        # After starting the thread, redirect the user to the home page or another appropriate page
        return redirect(url_for('home'))
    except Exception as e:
        handle_error(e)

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        handle_error(e)
