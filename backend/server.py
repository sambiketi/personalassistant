from fastapi import FastAPI, Form, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.messaging_response import MessagingResponse
from app_state import APP_STATE, UserSession, Task
from ai_engine import UniversalScheduler
from dotenv import load_dotenv
import os
import uvicorn
import json
import asyncio

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scheduler with DeepSeek
scheduler = UniversalScheduler(provider_model="deepseek-chat")

def get_chat_id():
    """Read chat ID from file"""
    try:
        with open("chat_id.txt", "r") as f:
            return f.read().strip()
    except:
        return None

@app.get("/")
async def root():
    return {
        "message": "Focus Companion API", 
        "status": "running", 
        "llm": "DeepSeek",
        "platforms": ["telegram", "whatsapp"]
    }

@app.get("/api/platforms/status")
async def get_platforms_status():
    """Get status of all communication platforms"""
    return {
        "telegram": {
            "configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            "chat_id": get_chat_id() is not None
        },
        "whatsapp": {
            "configured": bool(os.getenv("TWILIO_ACCOUNT_SID")),
            "running": False
        }
    }

@app.post("/api/register")
async def register_user(request_data: dict):
    """Register user with communication channels"""
    try:
        user_id = request_data.get("user_id")
        telegram_chat_id = request_data.get("telegram_chat_id")
        whatsapp_number = request_data.get("whatsapp_number")
        
        if not user_id:
            return {"status": "error", "message": "user_id required"}
        
        # Store in app state
        if user_id not in APP_STATE:
            APP_STATE[user_id] = UserSession(
                phone_number=whatsapp_number or "",
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                provider="deepseek",
                unsnoozables=[],
                tasks=[]
            )
        
        print(f"✅ User registered: {user_id}")
        print(f"   Telegram: {telegram_chat_id}")
        print(f"   WhatsApp: {whatsapp_number}")
        
        return {
            "status": "success",
            "message": f"User {user_id} registered",
            "telegram": bool(telegram_chat_id),
            "whatsapp": bool(whatsapp_number)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/schedule")
async def generate_schedule(request_data: dict):
    """Generate a schedule from a text prompt using DeepSeek"""
    try:
        prompt = request_data.get("prompt", "")
        unsnoozables = request_data.get("unsnoozables", [])
        
        if not prompt:
            return {"status": "error", "message": "No prompt provided"}
        
        schedule = scheduler.generate_schedule(prompt, unsnoozables)
        return {"status": "success", "schedule": schedule.model_dump()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/schedule/send")
async def generate_and_send_schedule(request_data: dict):
    """Generate schedule and send via configured platforms"""
    try:
        prompt = request_data.get("prompt", "")
        unsnoozables = request_data.get("unsnoozables", [])
        user_id = request_data.get("user_id", "default")
        platforms = request_data.get("platforms", ["telegram", "whatsapp"])
        
        if not prompt:
            return {"status": "error", "message": "No prompt provided"}
        
        # Generate schedule
        schedule = scheduler.generate_schedule(prompt, unsnoozables)
        schedule_dict = schedule.model_dump()
        
        results = {}
        
        # Send to Telegram
        if "telegram" in platforms:
            # Get chat ID from file
            chat_id = get_chat_id()
            
            if chat_id:
                token = os.getenv("TELEGRAM_BOT_TOKEN")
                if token:
                    import requests
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    
                    # Format schedule message
                    message = "📅 *YOUR DAILY SCHEDULE*\n\n"
                    for task in schedule_dict.get("tasks", []):
                        icon = "🔒" if task.get("is_unsnoozable") else "📌"
                        message += f"{icon} *{task.get('start_time')} - {task.get('end_time')}*\n"
                        message += f"   {task.get('task_name')}\n\n"
                    
                    message += "Reply with: START, SNOOZE, or DONE"
                    
                    payload = {
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                    
                    response = requests.post(url, json=payload)
                    result = response.json()
                    results["telegram"] = {"success": result.get("ok", False)}
                else:
                    results["telegram"] = {"success": False, "error": "No Telegram token"}
            else:
                results["telegram"] = {"success": False, "error": "No chat_id found. Run get_chat_id.py"}
        
        return {
            "status": "success", 
            "schedule": schedule_dict,
            "sent_to": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    """Handle WhatsApp incoming messages (Twilio webhook)"""
    try:
        user_phone = From.replace("whatsapp:", "").strip()
        command = Body.strip().upper()
        
        resp = MessagingResponse()
        session = APP_STATE.get(user_phone)
        
        if not session or not session.tasks:
            resp.message("Welcome! You have no active tasks scheduled. Send your schedule via Telegram or the web app.")
            return Response(content=str(resp), media_type="application/xml")
        
        current_task = session.tasks[0]
        
        if command == "START":
            current_task.status = "IN_PROGRESS"
            resp.message(f"✅ Started: {current_task.name}. Focus up!")
        elif command == "SNOOZE":
            if current_task.is_unsnoozable:
                resp.message(f"🔒 {current_task.name} is UNSNOOZABLE! Cannot delay.")
            else:
                current_task.status = "SNOOZED"
                resp.message(f"⏸️ Pushed {current_task.name} by 10 minutes.")
        elif command == "DONE":
            current_task.status = "COMPLETED"
            session.tasks.pop(0)
            next_msg = f" Up next: {session.tasks[0].name}" if session.tasks else " You cleared all tasks for today!"
            resp.message(f"✅ Task marked DONE!{next_msg}")
        else:
            resp.message("Reply: START, SNOOZE, or DONE")
        
        return Response(content=str(resp), media_type="application/xml")
    except Exception as e:
        print(f"❌ WhatsApp webhook error: {e}")
        resp = MessagingResponse()
        resp.message("Error processing request. Please try again.")
        return Response(content=str(resp), media_type="application/xml")

@app.post("/api/initialize")
async def initialize_session(data: dict):
    """Initialize a user session with tasks"""
    try:
        phone = data.get("phone")
        tasks_data = data.get("tasks", [])
        
        if not phone:
            return {"status": "error", "message": "Phone number required"}
        
        tasks = []
        for task_data in tasks_data:
            tasks.append(Task(
                name=task_data.get("name", ""),
                start_time=task_data.get("start_time", ""),
                end_time=task_data.get("end_time", ""),
                is_unsnoozable=task_data.get("is_unsnoozable", False)
            ))
        
        session = UserSession(
            phone_number=phone,
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            provider="deepseek",
            unsnoozables=[t.name for t in tasks if t.is_unsnoozable],
            tasks=tasks
        )
        
        APP_STATE[phone] = session
        return {"status": "success", "message": f"Session initialized for {phone}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
