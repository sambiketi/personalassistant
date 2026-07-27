import os
import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MessageResponse:
    success: bool
    message: str
    platform: str

class DualCommunicationPipeline:
    """Handles both Telegram and WhatsApp communication"""
    
    def __init__(self):
        # Telegram Configuration
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_app = None
        
        # WhatsApp Configuration (Twilio)
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_whatsapp = os.getenv("TWILIO_WHATSAPP_FROM")
        self.twilio_client = None
        
        # Session storage for users
        self.user_sessions: Dict[str, Dict] = {}
        
        # Initialize clients
        self._init_telegram()
        self._init_whatsapp()
    
    def _init_telegram(self):
        """Initialize Telegram bot"""
        if self.telegram_token:
            self.telegram_app = Application.builder().token(self.telegram_token).build()
            logger.info("✅ Telegram bot initialized")
        else:
            logger.warning("⚠️ Telegram token not found")
    
    def _init_whatsapp(self):
        """Initialize WhatsApp client"""
        if self.twilio_sid and self.twilio_auth:
            self.twilio_client = Client(self.twilio_sid, self.twilio_auth)
            logger.info("✅ WhatsApp client initialized")
        else:
            logger.warning("⚠️ WhatsApp credentials not found")
    
    # ==================== TELEGRAM METHODS ====================
    
    async def send_telegram_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> MessageResponse:
        """Send message via Telegram"""
        try:
            if not self.telegram_app:
                return MessageResponse(False, "Telegram not configured", "telegram")
            
            bot = Bot(token=self.telegram_token)
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            logger.info(f"📱 Telegram message sent to {chat_id}")
            return MessageResponse(True, "Message sent via Telegram", "telegram")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
            return MessageResponse(False, str(e), "telegram")
    
    async def send_telegram_schedule(self, chat_id: str, schedule_data: Dict) -> MessageResponse:
        """Format and send schedule via Telegram"""
        try:
            # Format schedule as nice message
            message = "📅 *YOUR DAILY SCHEDULE*\n"
            message += "═══════════════════\n\n"
            
            for task in schedule_data.get("tasks", []):
                icon = "🔒" if task.get("is_unsnoozable") else "📌"
                message += f"{icon} *{task.get('start_time')} - {task.get('end_time')}*\n"
                message += f"   {task.get('task_name')}\n\n"
            
            message += "═══════════════════\n"
            message += "💡 Reply with:\n"
            message += "• START - Begin task\n"
            message += "• SNOOZE - Delay 10 min\n"
            message += "• DONE - Mark complete"
            
            return await self.send_telegram_message(chat_id, message)
        except Exception as e:
            return MessageResponse(False, str(e), "telegram")
    
    async def send_telegram_reminder(self, chat_id: str, task_name: str) -> MessageResponse:
        """Send task reminder via Telegram"""
        message = f"⏰ *TIME TO START!*\n\n"
        message += f"Task: *{task_name}*\n"
        message += "Reply with:\n"
        message += "• START - Begin now\n"
        message += "• SNOOZE - Delay 10 min"
        
        return await self.send_telegram_message(chat_id, message)
    
    # ==================== WHATSAPP METHODS ====================
    
    def send_whatsapp_message(self, to_number: str, text: str) -> MessageResponse:
        """Send message via WhatsApp Business API"""
        try:
            if not self.twilio_client:
                return MessageResponse(False, "WhatsApp not configured", "whatsapp")
            
            message = self.twilio_client.messages.create(
                from_=f"whatsapp:{self.twilio_whatsapp}",
                body=text,
                to=f"whatsapp:{to_number}"
            )
            logger.info(f"📱 WhatsApp message sent to {to_number}")
            return MessageResponse(True, message.sid, "whatsapp")
        except Exception as e:
            logger.error(f"❌ WhatsApp error: {e}")
            return MessageResponse(False, str(e), "whatsapp")
    
    def send_whatsapp_schedule(self, to_number: str, schedule_data: Dict) -> MessageResponse:
        """Format and send schedule via WhatsApp"""
        try:
            message = "📅 *YOUR DAILY SCHEDULE*\n"
            message += "═══════════════════\n\n"
            
            for task in schedule_data.get("tasks", []):
                icon = "🔒" if task.get("is_unsnoozable") else "📌"
                message += f"{icon} {task.get('start_time')} - {task.get('end_time')}\n"
                message += f"   {task.get('task_name')}\n\n"
            
            message += "═══════════════════\n"
            message += "Reply with: START, SNOOZE, or DONE"
            
            return self.send_whatsapp_message(to_number, message)
        except Exception as e:
            return MessageResponse(False, str(e), "whatsapp")
    
    def send_whatsapp_reminder(self, to_number: str, task_name: str) -> MessageResponse:
        """Send task reminder via WhatsApp"""
        message = f"⏰ TIME TO START!\n\n"
        message += f"Task: {task_name}\n"
        message += "Reply with: START or SNOOZE"
        
        return self.send_whatsapp_message(to_number, message)
    
    # ==================== DUAL PIPELINE METHODS ====================
    
    async def send_to_platforms(self, user_id: str, message: str, platforms: list = None) -> Dict:
        """
        Send message to multiple platforms
        platforms: ['telegram', 'whatsapp'] or None (all available)
        """
        results = {}
        
        if platforms is None:
            platforms = ['telegram', 'whatsapp']
        
        user_data = self.user_sessions.get(user_id, {})
        
        # Send to Telegram
        if 'telegram' in platforms and user_data.get('telegram_chat_id'):
            results['telegram'] = await self.send_telegram_message(
                user_data['telegram_chat_id'], 
                message
            )
        
        # Send to WhatsApp
        if 'whatsapp' in platforms and user_data.get('whatsapp_number'):
            results['whatsapp'] = self.send_whatsapp_message(
                user_data['whatsapp_number'],
                message
            )
        
        return results
    
    async def register_user(self, user_id: str, telegram_chat_id: str = None, whatsapp_number: str = None):
        """Register a user with their communication channels"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}
        
        if telegram_chat_id:
            self.user_sessions[user_id]['telegram_chat_id'] = telegram_chat_id
            logger.info(f"✅ User {user_id} registered on Telegram: {telegram_chat_id}")
        
        if whatsapp_number:
            self.user_sessions[user_id]['whatsapp_number'] = whatsapp_number
            logger.info(f"✅ User {user_id} registered on WhatsApp: {whatsapp_number}")
        
        return True
    
    # ==================== TELEGRAM WEBHOOK HANDLERS ====================
    
    async def telegram_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command from Telegram"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        
        await self.register_user(user_id, telegram_chat_id=chat_id)
        
        welcome_msg = (
            "👋 *Welcome to Focus Companion!*\n\n"
            "I'll help you plan your day and keep you accountable.\n\n"
            "📝 To get started, send me your schedule like this:\n"
            "`Waking up at 6am. Exercise 1 hour, Code 2 hours, Break`\n\n"
            "🔒 Mark tasks as unsnoozable by saying:\n"
            "`Make Exercise and Study unsnoozable`"
        )
        
        await self.send_telegram_message(chat_id, welcome_msg)
    
    async def telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages from Telegram"""
        user_id = str(update.effective_user.id)
        message = update.message.text
        
        # Process the message (will connect to your scheduler)
        # This will be handled by your main app
        response = f"Received: {message}\nGenerating schedule..."
        
        # Send the response
        await self.send_telegram_message(
            str(update.effective_chat.id),
            response
        )
    
    def setup_telegram_handlers(self):
        """Set up Telegram bot handlers"""
        if not self.telegram_app:
            return
        
        # Command handlers
        self.telegram_app.add_handler(CommandHandler("start", self.telegram_start))
        
        # Message handlers
        self.telegram_app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.telegram_message)
        )
        
        logger.info("✅ Telegram handlers configured")
    
    async def start_telegram_polling(self):
        """Start Telegram bot polling"""
        if self.telegram_app:
            self.setup_telegram_handlers()
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            await self.telegram_app.updater.start_polling()
            logger.info("🚀 Telegram bot started (polling mode)")
        else:
            logger.warning("⚠️ Telegram bot not configured")

# Create singleton instance
pipeline = DualCommunicationPipeline()

