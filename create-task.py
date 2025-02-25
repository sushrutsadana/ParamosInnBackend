from flask import Flask, request, jsonify
import openai
import os
import requests
from dotenv import load_dotenv  # Import dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client with the API key from .env file
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get Telegram Bot Token & Group Chat ID from .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Example: "-123456789"

# Vercel Deployment URL
VERCEL_APP_URL = "https://paramos-hotel-backend.vercel.app"

def send_telegram_message(message):
    """Send a message to the Telegram group"""
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(telegram_url, json=payload)
        response_data = response.json()

        if not response.ok or not response_data.get("ok"):
            print(f"Telegram API Error: {response_data}")
            return {"error": "Failed to send message to Telegram", "details": response_data}

        return response_data
    
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return {"error": "Telegram request failed", "details": str(e)}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    transcript = data.get('transcript')

    if not transcript:
        return jsonify({'error': 'No transcript provided'}), 400

    # Use GPT-4o-mini to extract task and room number
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Extract the task and room number from the following transcript. If the room number or task is missing, specify it as 0."},
            {"role": "user", "content": transcript}
        ],
        max_tokens=100,
        temperature=0.5,
    )

    output = response.choices[0].message.content.strip()

    # Try to extract task and room number
    try:
        lines = output.split("\n")
        task = lines[0].split(": ")[1] if len(lines) > 0 else "0"
        room_number = lines[1].split(": ")[1] if len(lines) > 1 else "0"
    except IndexError:
        return jsonify({"error": "Unexpected response format", "response": output}), 500

    # Create the message for Telegram
    telegram_message = f"🏨 *New Task Assigned*\n\n📌 *Task:* {task}\n🏠 *Room Number:* {room_number}"

    # Send message to Telegram group
    telegram_response = send_telegram_message(telegram_message)

    return jsonify({
        'task': task,
        'room_number': room_number,
        'telegram_response': telegram_response
    })

# Only required when running locally; Vercel handles execution automatically
if __name__ == '__main__':
    app.run(port=5000)
