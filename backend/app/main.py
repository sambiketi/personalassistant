import os
import time
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO if os.getenv("ENVIRONMENT") == "production" else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("focus_agent")

from app.models.database import Database
from app.services.llm_interface import LLMService
from app.services.deepseek import DeepSeekService
from app.services.openai import OpenAIService
from app.services.anthropic import AnthropicService
from app.core.vanguard_brain import VanguardBrain
from app.core.brain_interface import Brain
from app.routes import dashboard

# ==========================================
# CONFIG FROM ENV
# ==========================================
DB_PATH = os.getenv("DB_PATH", "focus_agent.db")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
origins = ["*"] if CORS_ORIGINS.strip() == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]

# ==========================================
# SINGLETONS (shared across requests)
# ==========================================
_db_instance = Database(db_path=DB_PATH)

_llm_map = {"openai": OpenAIService, "anthropic": AnthropicService, "deepseek": DeepSeekService}
_llm_instance: LLMService = _llm_map.get(LLM_PROVIDER, DeepSeekService)(LLM_API_KEY)

_brain_instance: Brain = VanguardBrain(llm=_llm_instance)


def get_database() -> Database:
    return _db_instance


def get_llm_service() -> LLMService:
    return _llm_instance


def get_brain() -> Brain:
    return _brain_instance


# ==========================================
# APP
# ==========================================
app = FastAPI(
    title="Focus Agent API",
    description="AI-powered adaptive scheduling agent with Vanguard Brain",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)")
    return response


# Wire the dashboard router's placeholder deps to real singletons
app.dependency_overrides[dashboard.get_database] = get_database
app.dependency_overrides[dashboard.get_llm_service] = get_llm_service
app.dependency_overrides[dashboard.get_brain] = get_brain

app.include_router(dashboard.router)


@app.get("/")
async def root():
    return {
        "message": "🎯 Focus Agent API",
        "status": "running",
        "version": "0.3.0",
        "features": ["Vanguard Brain", "Adaptive Scheduling", "Goal Tracking", "Habit Tracking"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/status")
async def api_status(
    db: Database = Depends(get_database),
    llm: LLMService = Depends(get_llm_service),
    brain: Brain = Depends(get_brain),
):
    return {
        "status": "online",
        "services": {
            "database": f"connected ({DB_PATH})",
            "llm_provider": llm.__class__.__name__,
            "llm_enabled": llm.enabled,
            "vanguard_brain": "active",
        },
    }
