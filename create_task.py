from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get Telegram Bot Token & Group Chat ID from .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    
    # Check if we're receiving structured data from function call
    task = data.get('task')
    room_number = data.get('roomNumber')
    transcript = data.get('transcript', '')
    
    # If we didn't get structured data, fall back to the transcript extraction
    if not task or not room_number:
        if not transcript:
            return jsonify({'error': 'No task details or transcript provided'}), 400
            
        # Fall back to the existing extraction logic
        task = "Unknown task"
        room_number = "Unknown room"
        
        # Look for room numbers
        import re
        room_patterns = [
            r'room (\d+)',
            r'room number (\d+)',
            r'room #(\d+)',
            r'#(\d+)'
        ]
        
        for pattern in room_patterns:
            room_match = re.search(pattern, transcript.lower())
            if room_match:
                room_number = room_match.group(1)
                break
        
        # Extract the task
        task_indicators = [
            "need", "want", "please", "could you", "can you", "would like"
        ]
        
        for indicator in task_indicators:
            if indicator in transcript.lower():
                parts = transcript.lower().split(indicator, 1)
                if len(parts) > 1:
                    task = parts[1].strip().capitalize()
                    task = task[:50] + "..." if len(task) > 50 else task
                    break

    # Create the message for Telegram
    telegram_message = f"🏨 *New Task Assigned*\n\n📌 *Task:* {task}\n🏠 *Room Number:* {room_number}"
    
    # Add transcript excerpt if available
    if transcript:
        telegram_message += f"\n\n💬 *Original Request:* {transcript[:100]}..."

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
