import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

token = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"Token: {token[:10]}...")

# Load chat ID
try:
    with open("chat_id.txt", "r") as f:
        chat_id = f.read().strip()
    print(f"✅ Chat ID: {chat_id}")
except:
    print("❌ No chat_id.txt found")
    print("Run: python get_chat_id.py")
    exit()

# Send message
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": "🤖 *Test Message from Focus Companion!*\n\nYour bot is working!\n\n✅ Connected successfully!",
    "parse_mode": "Markdown"
}

try:
    response = requests.post(url, json=payload)
    result = response.json()
    if result.get("ok"):
        print("✅ Message sent successfully!")
        print("📱 Check your Telegram @P_asst_bot")
    else:
        print(f"❌ Error: {result}")
except Exception as e:
    print(f"❌ Error: {e}")
