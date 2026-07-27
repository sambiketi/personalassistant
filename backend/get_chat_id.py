import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def get_chat_id():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ No token found in .env")
        return
    
    bot = Bot(token=token)
    
    print("📱 Getting recent messages...")
    print("   Make sure you've sent a message to @P_asst_bot first!\n")
    
    try:
        # Get updates (messages sent to the bot)
        updates = await bot.get_updates()
        
        if updates:
            print(f"📨 Found {len(updates)} recent messages:\n")
            for update in updates:
                if update.message:
                    chat_id = update.message.chat.id
                    text = update.message.text
                    from_user = update.message.from_user.id
                    print(f"✅ Chat ID: {chat_id}")
                    print(f"   From User ID: {from_user}")
                    print(f"   Message: {text}")
                    print()
                    
                    # Save the chat ID to a file
                    with open("chat_id.txt", "w") as f:
                        f.write(str(chat_id))
                    print(f"💾 Chat ID saved to chat_id.txt: {chat_id}")
                    return chat_id
        else:
            print("❌ No messages found!")
            print("\n📝 Please:")
            print("   1. Open Telegram")
            print("   2. Search for @P_asst_bot")
            print("   3. Send any message (e.g., 'Hello')")
            print("   4. Run this script again")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(get_chat_id())
