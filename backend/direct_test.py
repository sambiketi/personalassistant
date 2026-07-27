import requests
import json

print("=" * 50)
print("DIRECT API TEST")
print("=" * 50)

# Test server
print("\n1. Testing server...")
try:
    r = requests.get("http://localhost:8000/")
    print(f"✅ Server: {r.json()}")
except Exception as e:
    print(f"❌ Server not running: {e}")
    exit()

# Test schedule generation
print("\n2. Testing schedule generation...")
data = {
    "prompt": "Waking up at 6am. Exercise 1 hour, Code 2 hours, Break, Apply to jobs",
    "unsnoozables": ["Exercise", "Apply to jobs"]
}
try:
    r = requests.post("http://localhost:8000/api/schedule", json=data)
    result = r.json()
    print(f"✅ Status: {result.get('status')}")
    if result.get('schedule'):
        tasks = result['schedule'].get('tasks', [])
        print(f"📋 Generated {len(tasks)} tasks:")
        for task in tasks:
            print(f"   - {task.get('start_time')}: {task.get('task_name')} (Unsnoozable: {task.get('is_unsnoozable')})")
except Exception as e:
    print(f"❌ Error: {e}")

# Test send to Telegram
print("\n3. Testing Telegram send...")
send_data = {
    "user_id": "test_user",
    "prompt": "Waking up at 6am. Exercise 1 hour, Code 2 hours, Break, Apply to jobs",
    "unsnoozables": ["Exercise", "Apply to jobs"],
    "platforms": ["telegram"]
}
try:
    r = requests.post("http://localhost:8000/api/schedule/send", json=send_data)
    result = r.json()
    print(f"✅ Status: {result.get('status')}")
    print(f"📱 Sent to: {result.get('sent_to', {})}")
    print("\n📱 Check your Telegram @P_asst_bot!")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
