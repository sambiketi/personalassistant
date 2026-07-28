from fastapi import FastAPI, Form, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import uvicorn
import json
import uuid
from datetime import datetime

from redis_client import redis_client
from llm_factory import LLMFactory
from telegram_handler import TelegramHandler

load_dotenv()

app = FastAPI(title="Focus Companion API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
frontend_dir = os.path.join(os.path.dirname(__file__))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Serve HTML files
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/setup.html")
async def serve_setup():
    return FileResponse("setup.html")

@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse("manifest.json")

@app.get("/sw.js")
async def serve_sw():
    return FileResponse("sw.js")

# Initialize handlers
telegram = TelegramHandler()

# ==================== USER MANAGEMENT ====================

@app.post("/api/user/create")
async def create_user(data: dict):
    try:
        phone = data.get("phone")
        if not phone:
            return {"status": "error", "message": "Phone number required"}
        
        user_id = str(uuid.uuid4())
        
        print(f"📝 Creating user: {user_id}")
        print(f"   Phone: {phone}")
        
        redis_client.save_user(user_id, {
            "phone": phone,
            "created_at": datetime.now().isoformat(),
            "llm_provider": data.get("llm_provider", "deepseek"),
            "llm_api_key": data.get("llm_api_key", ""),
            "llm_model": data.get("llm_model", "")
        })
        
        print(f"   ✅ User created successfully")
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": "User created successfully"
        }
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/user/{user_id}")
async def get_user(user_id: str):
    try:
        user = redis_client.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        return {"status": "success", "user": user}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== LLM CONFIG ====================

@app.post("/api/llm/config")
async def configure_llm(data: dict):
    try:
        user_id = data.get("user_id")
        provider = data.get("provider")
        api_key = data.get("api_key")
        model = data.get("model", "")
        
        print(f"🔧 Configuring LLM for user: {user_id}")
        print(f"   Provider: {provider}")
        print(f"   API Key: {api_key[:15]}..." if api_key else "   API Key: None")
        print(f"   Model: {model}")
        
        if not user_id or not provider or not api_key:
            return {"status": "error", "message": "Missing required fields"}
        
        # Save config
        config_data = {
            "llm_provider": provider,
            "llm_api_key": api_key,
            "llm_model": model
        }
        
        redis_client.save_user_config(user_id, config_data)
        
        # Verify it was saved
        saved = redis_client.get_user_config(user_id)
        print(f"   ✅ Config saved: {saved}")
        
        return {
            "status": "success",
            "message": f"LLM configured: {provider}",
            "provider": provider
        }
    except Exception as e:
        print(f"❌ Error configuring LLM: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/llm/config/{user_id}")
async def get_llm_config(user_id: str):
    try:
        config = redis_client.get_user_config(user_id)
        if not config:
            return {"status": "error", "message": "Config not found"}
        return {"status": "success", "config": config}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== TELEGRAM CONNECTION ====================

@app.post("/api/telegram/connect")
async def connect_telegram(data: dict):
    try:
        user_id = data.get("user_id")
        phone = data.get("phone")
        
        if not user_id:
            if not phone:
                return {"status": "error", "message": "Phone number required"}
            user_id = str(uuid.uuid4())
            redis_client.save_user(user_id, {"phone": phone})
        
        redis_client.set_pending_connect(user_id)
        
        bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "P_asst_bot")
        deep_link = f"https://t.me/{bot_username}?start={user_id}"
        
        return {
            "status": "success",
            "deep_link": deep_link,
            "user_id": user_id,
            "message": "Click the link to connect Telegram"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/telegram/status/{user_id}")
async def check_telegram_status(user_id: str):
    try:
        connected = redis_client.is_telegram_connected(user_id)
        chat_id = redis_client.get_telegram_chat_id(user_id)
        
        return {
            "connected": connected,
            "user_id": user_id,
            "chat_id": chat_id
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== SCHEDULE MANAGEMENT ====================

@app.post("/api/schedule/generate")
async def generate_schedule(data: dict):
    try:
        user_id = data.get("user_id")
        prompt = data.get("prompt")
        unsnoozables = data.get("unsnoozables", [])
        
        print(f"📅 Generating schedule for: {user_id}")
        print(f"   Prompt: {prompt[:50]}..." if prompt else "   Prompt: None")
        
        if not user_id or not prompt:
            return {"status": "error", "message": "Missing required fields"}
        
        user_config = redis_client.get_user_config(user_id)
        print(f"   Config from Redis: {user_config}")
        
        if not user_config:
            return {"status": "error", "message": "LLM not configured. Please setup first."}
        
        llm = LLMFactory.create_llm(
            provider=user_config.get("llm_provider", "deepseek"),
            api_key=user_config.get("llm_api_key"),
            model=user_config.get("llm_model", "")
        )
        
        schedule = llm.generate_schedule(prompt, unsnoozables)
        redis_client.save_schedule(user_id, schedule.model_dump())
        
        return {
            "status": "success",
            "schedule": schedule.model_dump()
        }
    except Exception as e:
        print(f"❌ Error generating schedule: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/schedule/{user_id}")
async def get_schedule(user_id: str):
    try:
        schedule = redis_client.get_schedule(user_id)
        if not schedule:
            return {"status": "success", "schedule": None}
        return {"status": "success", "schedule": schedule}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== TELEGRAM WEBHOOK ====================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        return await telegram.handle_webhook(data)
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"ok": False}

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "redis": redis_client.ping(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api")
async def api_root():
    return {
        "message": "Focus Companion API",
        "status": "running",
        "version": "1.0.0",
        "features": ["multi-llm", "telegram-deep-link", "redis-persistence"]
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "True").lower() == "true"
    )
