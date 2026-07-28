import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import from app
from app.api.routes import router
from app.models.database import Database
from app.services.deepseek import DeepSeekService

load_dotenv()

# Initialize database
db = Database()
deepseek = DeepSeekService()

app = FastAPI(
    title="Focus Agent API",
    description="AI-powered adaptive scheduling agent",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "🎯 Focus Agent API",
        "status": "running",
        "version": "0.1.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2026-07-28"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",  # Changed from "app.main:app" to "main:app"
        host="0.0.0.0",
        port=8000,
        reload=True
    )
