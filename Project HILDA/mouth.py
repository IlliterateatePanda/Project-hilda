import openai
import re
from google.auth import exceptions
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json  # Import the json module

# Path to your service account key file
SERVICE_ACCOUNT_FILE = ''
SCOPES = ['https://www.googleapis.com/auth/chat.bot']

# Authenticate using service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Google Chat API client
service = build('chat', 'v1', credentials=credentials)

# Space ID for the chat space
space_id = 'spaces/AAAAAAAA'

# Function to send a message to the space
def send_message(text):
    message = {
        "text": text
    }

    try:
        sent_message = service.spaces().messages().create(
            parent=space_id,
            body=message
        ).execute()
        print(f'Message sent: {sent_message["text"]}')
    except exceptions.GoogleAuthError as e:
        print(f"Authentication error: {e}")
    except Exception as e:
        print(f"Error sending message: {e}")

# Function to read the message from the queue.txt
def read_message():
    try:
        with open('queue.txt', 'r', encoding='utf-8') as file:  # Add encoding='utf-8'
            content = file.read().strip()
            if content:
                message_list = json.loads(content)  # Safely load the content as JSON
                return message_list[0] if message_list else None
            else:
                return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from queue.txt: {e}")
        return None
    except Exception as e:
        print(f"Error reading from queue.txt: {e}")
        return None

# Function to load the API key from key.txt
def load_api_key():
    try:
        with open('key.txt', 'r', encoding='utf-8') as file:  # Add encoding='utf-8'
            return file.read().strip()
    except FileNotFoundError:
        print("API key file 'key.txt' not found.")
        return None

# Function to read memory from memory.txt
def read_memory():
    try:
        with open('memory.txt', 'r', encoding='utf-8', errors='replace') as file:  # Add errors='replace'
            lines = file.readlines()
            return [line.strip() for line in lines[-20:]]  # Get the last 20 lines
    except FileNotFoundError:
        return []  # No memory file yet, return empty list
    except Exception as e:
        print(f"Error reading from memory.txt: {e}")
        return []

# Function to save response to memory.txt and create the file if it does not exist
def save_to_memory(response):
    try:
        with open('memory.txt', 'a', encoding='utf-8') as file:
            file.write(response + '\n')
    except Exception as e:
        print(f"Error writing to memory.txt: {e}")

# Function to interact with GPT-4o-mini using memory and custom parameters
def chat_with_gpt(user_message):
    api_key = load_api_key()
    if not api_key:
        return "API key is missing."

    openai.api_key = api_key

    memory_context = read_memory()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Replace with the correct model if necessary
            messages=[
                {"role": "system", "content": ""}
            ] + [{"role": "assistant", "content": mem} for mem in memory_context] + [
                {"role": "user", "content": user_message}
            ],
            temperature=1,
            frequency_penalty=1,
            presence_penalty=1
        )
        bot_response = response['choices'][0]['message']['content']
        save_to_memory(bot_response)  # Save the response to memory
        return bot_response
    except Exception as e:
        return f"An error occurred: {e}"

# Main function to handle reading and responding
def process_message():
    message_to_process = read_message()
    if message_to_process:
        gpt_response = chat_with_gpt(message_to_process)
        send_message(gpt_response)
    else:
        print("No message found in queue.txt.")

if __name__ == "__main__":
    process_message()
