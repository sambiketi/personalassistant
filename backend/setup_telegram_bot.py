import os
import asyncio
import sys
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def setup_telegram_bot():
    """Setup and test Telegram bot"""
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ Please set TELEGRAM_BOT_TOKEN in .env file")
        print("\n📝 To create a Telegram bot:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot")
        print("3. Choose a name for your bot (e.g., 'Focus Companion')")
        print("4. Choose a username (must end with 'bot', e.g., 'focuscompanion_bot')")
        print("5. Copy the API token and add to .env")
        print("\nExample token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        return False
    
    try:
        # Test the bot
        print("🔄 Testing Telegram bot connection...")
        bot = Bot(token=token)
        bot_info = await bot.get_me()  # Fixed: added await
        print(f"\n✅ Telegram bot connected successfully!")
        print(f"   🤖 Name: {bot_info.first_name}")
        print(f"   📱 Username: @{bot_info.username}")
        print(f"   🆔 Bot ID: {bot_info.id}")
        print(f"\n📱 Your bot is ready!")
        print(f"   Start it: https://t.me/{bot_info.username}")
        print(f"   Webhook URL: http://localhost:8000/webhook/telegram")
        print(f"\n💡 Test your bot:")
        print(f"   Open Telegram and send /start to @{bot_info.username}")
        print(f"\n📱 To find your chat ID:")
        print(f"   Message your bot, then check the server logs")
        return True
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(setup_telegram_bot())
