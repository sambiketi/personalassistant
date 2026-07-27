import asyncio
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def test_full():
    # Load chat ID
    try:
        with open("chat_id.txt", "r") as f:
            chat_id = f.read().strip()
        print(f"✅ Using chat ID: {chat_id}")
    except:
        print("❌ Please run get_chat_id.py first")
        return
    
    print("\n" + "=" * 50)
    print("📅 GENERATING SCHEDULE WITH TELEGRAM")
    print("=" * 50 + "\n")
    
    # 1. Register user
    print("📝 Registering user...")
    register_data = {
        "user_id": "test_telegram_user",
        "telegram_chat_id": chat_id
    }
    
    try:
        response = requests.post("http://localhost:8000/api/register", json=register_data)
        print(f"   Result: {response.json()}")
    except Exception as e:
        print(f"   ❌ Server not running: {e}")
        print("   Start with: uvicorn server:app --host 0.0.0.0 --port 8000 --reload")
        return
    print()
    
    # 2. Generate and send schedule
    print("📅 Generating schedule...")
    schedule_data = {
        "user_id": "test_telegram_user",
        "prompt": "Tomorrow I'm waking up at 6am. Exercise 1 hour, Code for 2 hours, Break, Apply to jobs, Study 1 hour, Prepare dinner, Review day plan, Sleep at 10pm",
        "unsnoozables": ["Exercise", "Apply to jobs", "Study"],
        "platforms": ["telegram"]
    }
    
    try:
        response = requests.post("http://localhost:8000/api/schedule/send", json=schedule_data)
        result = response.json()
        print(f"   Status: {result.get('status')}")
        if result.get('sent_to'):
            print(f"   Sent to: {list(result['sent_to'].keys())}")
        print()
        print("📱 Check your Telegram @P_asst_bot - you should see the schedule!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_full())
