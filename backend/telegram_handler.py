import os
import requests
from redis_client import redis_client

class TelegramHandler:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "P_asst_bot")
    
    async def send_message(self, chat_id: str, text: str, parse_mode: str = "Markdown"):
        """Send message via Telegram API"""
        if not self.bot_token:
            return {"ok": False, "error": "Bot token not configured"}
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    async def handle_webhook(self, data: dict):
        """Handle incoming webhook data"""
        message = data.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1:
                user_id = parts[1]
                if redis_client.is_pending_connect(user_id):
                    redis_client.bind_telegram(user_id, chat_id)
                    await self.send_message(
                        chat_id=chat_id,
                        text="✅ *Connected to Focus Companion!*\n\nReturn to the app to continue."
                    )
                    return {"ok": True}
        
        return {"ok": True}
    
    def get_bot_username(self):
        return self.bot_username
