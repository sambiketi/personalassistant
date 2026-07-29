import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from app
from app.api.routes import router
from app.models.database import Database
from app.services.deepseek import DeepSeekService

load_dotenv()

# Initialize services
db = Database()
deepseek = DeepSeekService()

# Initialize routes with services
from app.api.routes import init_services
init_services(db, deepseek)

app = FastAPI(
    title="Focus Agent API",
    description="AI-powered adaptive scheduling agent with Vanguard Brain",
    version="0.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "🎯 Focus Agent API",
        "status": "running",
        "version": "0.2.0",
        "features": ["Vanguard Brain", "Adaptive Scheduling", "Goal Tracking", "Habit Tracking"]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2026-07-28"}

@app.get("/api/status")
async def api_status():
    return {
        "status": "online",
        "services": {
            "database": "connected",
            "deepseek": "ready" if deepseek.enabled else "mock_mode",
            "vanguard_brain": "active"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
