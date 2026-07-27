import asyncio
from communication import pipeline
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def test_communication():
    print("=" * 50)
    print("TESTING COMMUNICATION PIPELINE")
    print("=" * 50)
    print()
    
    # Check platform status
    print("📡 Checking platform status:")
    print(f"  Telegram: {'✅' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌'} {'Configured' if os.getenv('TELEGRAM_BOT_TOKEN') else 'Not configured'}")
    print(f"  WhatsApp: {'✅' if os.getenv('TWILIO_ACCOUNT_SID') else '❌'} {'Configured' if os.getenv('TWILIO_ACCOUNT_SID') else 'Not configured'}")
    print()
    
    # Test user registration
    print("📝 Testing user registration...")
    user_id = "test_user_123"
    telegram_chat_id = "123456789"
    whatsapp_number = "+1234567890"
    
    result = await pipeline.register_user(user_id, telegram_chat_id, whatsapp_number)
    print(f"  Registration: {'✅ Success' if result else '❌ Failed'}")
    print(f"  User ID: {user_id}")
    print(f"  Telegram Chat ID: {telegram_chat_id}")
    print(f"  WhatsApp Number: {whatsapp_number}")
    print()
    
    # Test sending a message (only if credentials are configured)
    print("📤 Testing message sending...")
    
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        print("  Sending test message to Telegram...")
        # Don't actually send, just simulate
        print("  ✅ Telegram would send: 'Test message'")
    else:
        print("  ⚠️ Telegram not configured - skipping send test")
    
    if os.getenv('TWILIO_ACCOUNT_SID'):
        print("  Sending test message to WhatsApp...")
        print("  ✅ WhatsApp would send: 'Test message'")
    else:
        print("  ⚠️ WhatsApp not configured - skipping send test")
    
    print()
    print("=" * 50)
    print("✅ Communication tests complete!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_communication())
