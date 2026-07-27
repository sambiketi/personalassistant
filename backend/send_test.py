import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def send_test():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ No token found")
        return
    
    # Try to load chat ID from file
    try:
        with open("chat_id.txt", "r") as f:
            CHAT_ID = int(f.read().strip())
        print(f"✅ Using chat ID from file: {CHAT_ID}")
    except:
        print("❌ Chat ID not found. Please run get_chat_id.py first")
        return
    
    bot = Bot(token=token)
    try:
        message = await bot.send_message(
            chat_id=CHAT_ID,
            text="🎯 *Focus Companion Test*\n\nYour Telegram bot is working!\n\n✅ Connected successfully!\n\n🤖 Ready to help you plan your day!",
            parse_mode="Markdown"
        )
        print(f"✅ Message sent successfully!")
        print(f"   Message ID: {message.message_id}")
        print(f"   Chat ID: {message.chat.id}")
        print(f"\n📱 Check your Telegram @P_asst_bot!")
    except Exception as e:
        print(f"❌ Error sending message: {e}")

if __name__ == "__main__":
    asyncio.run(send_test())
