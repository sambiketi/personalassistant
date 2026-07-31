import logging
import re
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator

from app.models.database import Database, DatabaseError
from app.services.llm_interface import LLMService
from app.core.agent import FocusAgent
from app.core.brain_interface import Brain

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["dashboard"])

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


# ==========================================
# Dependency wiring (overridden by main.py)
# ==========================================
def get_database() -> Database:
    raise RuntimeError("Database dependency not configured")


def get_llm_service() -> LLMService:
    raise RuntimeError("LLM dependency not configured")


def get_brain() -> Brain:
    raise RuntimeError("Brain dependency not configured")


def get_agent(
    db: Database = Depends(get_database),
    llm: LLMService = Depends(get_llm_service),
    brain: Brain = Depends(get_brain),
) -> FocusAgent:
    return FocusAgent(db=db, llm=llm, brain=brain)


# ==========================================
# REQUEST / VALIDATION MODELS
# ==========================================
class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="demo_user", min_length=1, max_length=100)
    api_key: Optional[str] = Field(default=None, description="LLM API key from frontend")  # ✅ ADDED


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    start_time: Optional[str] = Field(default=None, description="HH:MM 24h format")
    end_time: Optional[str] = None
    duration: Optional[int] = Field(default=None, ge=0, le=1440)
    priority: int = Field(default=3, ge=1, le=5)
    category: str = Field(default="general", max_length=50)
    status: str = Field(default="pending")

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_time(cls, v):
        if v and not _TIME_RE.match(v):
            raise ValueError("must be HH:MM 24-hour format")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        allowed = {"pending", "in_progress", "completed", "skipped", "postponed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: Optional[str] = Field(default=None, max_length=50)
    priority: int = Field(default=3, ge=1, le=5)
    status: str = Field(default="active")
    target_date: Optional[str] = None
    progress: float = Field(default=0, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        allowed = {"active", "completed", "archived"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    frequency: str = Field(default="daily")
    target_count: int = Field(default=1, ge=1, le=100)

    @field_validator("frequency")
    @classmethod
    def valid_frequency(cls, v):
        if v not in {"daily", "weekly"}:
            raise ValueError("frequency must be 'daily' or 'weekly'")
        return v


class HabitLogRequest(BaseModel):
    date: str
    completed: bool = True
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("date")
    @classmethod
    def valid_date(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("date must be ISO format YYYY-MM-DD")
        return v


class TaskLog(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=200)
    scheduled_time: Optional[str] = None
    actual_time: Optional[str] = None
    status: str = Field(default="pending")
    duration: Optional[int] = Field(default=None, ge=0, le=1440)
    date: str
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        allowed = {"pending", "in_progress", "completed", "skipped", "postponed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

    @field_validator("date")
    @classmethod
    def valid_date(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("date must be ISO format YYYY-MM-DD")
        return v


# ==========================================
# Helper: convert DatabaseError -> HTTP 500 consistently
# ==========================================
def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except DatabaseError as e:
        logger.error(f"DB error: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected server error")


# ==========================================
# AGENT CHAT - UPDATED with API key support
# ==========================================
@router.post("/agent/process")
async def process_message(request: MessageRequest, agent: FocusAgent = Depends(get_agent)):
    def _process():
        # 🔑 Update LLM with API key from frontend
        if request.api_key:
            agent.llm.update_api_key(request.api_key)
            logger.info(f"✅ API key updated for user {request.user_id}")
        elif not agent.llm.enabled:
            logger.warning(f"❌ No API key provided for user {request.user_id}")
            return {
                "success": False,
                "error": "No API key provided",
                "response": {
                    "message": "🔑 Please enter your LLM API key in the settings above to enable AI features.",
                    "intent": "error",
                }
            }
        
        response = agent.process(request.user_id, request.message)
        return {
            "success": True,
            "response": {
                "message": response.message,
                "intent": response.intent.value if response.intent else "unknown",
                "schedule": response.schedule.to_dict() if response.schedule else None,
                "suggestions": response.suggestions,
                "reasoning": response.reasoning,
                "vanguard_data": response.vanguard_data,
            },
        }
    return _run(_process)


# ==========================================
# API KEY - REMOVED (now handled by frontend localStorage)
# ==========================================
# The following endpoints are no longer needed since API keys are
# managed entirely in the frontend via localStorage.
#
# @router.post("/user/apikey")
# async def save_api_key(req: ApiKeyRequest, db: Database = Depends(get_database)):
#     def _save():
#         db.get_or_create_user(req.user_id)
#         db.save_api_key(req.user_id, req.api_key)
#         return {"success": True}
#     return _run(_save)
#
# @router.get("/user/apikey/status")
# async def api_key_status(user_id: str = "demo_user", db: Database = Depends(get_database)):
#     def _status():
#         key = db.get_api_key(user_id)
#         return {"success": True, "has_key": bool(key)}
#     return _run(_status)


# ==========================================
# SCHEDULE
# ==========================================
@router.get("/schedule/{user_id}")
async def get_schedule(user_id: str, target_date: Optional[str] = None, db: Database = Depends(get_database)):
    def _get():
        user = db.get_or_create_user(user_id)
        d = target_date or date.today().isoformat()
        schedule = db.get_schedule(user["id"], d)
        return {"success": True, "date": d, "schedule": schedule or {"tasks": []}}
    return _run(_get)


@router.post("/schedule/{user_id}")
async def add_task(user_id: str, task: TaskCreate, db: Database = Depends(get_database)):
    def _add():
        user = db.get_or_create_user(user_id)
        today = date.today().isoformat()
        updated = db.add_task_to_schedule(user["id"], today, task.model_dump())
        return {"success": True, "task": task.model_dump(), "schedule": updated}
    return _run(_add)


# ==========================================
# GOALS
# ==========================================
@router.get("/goals/{user_id}")
async def get_goals(user_id: str, db: Database = Depends(get_database)):
    def _get():
        user = db.get_or_create_user(user_id)
        return {"success": True, "goals": db.get_goals(user["id"])}
    return _run(_get)


@router.post("/goals/{user_id}")
async def add_goal(user_id: str, goal: GoalCreate, db: Database = Depends(get_database)):
    def _add():
        user = db.get_or_create_user(user_id)
        goal_id = db.create_goal(user["id"], goal.model_dump())
        return {"success": True, "goal_id": goal_id, "goal": goal.model_dump()}
    return _run(_add)


# ==========================================
# HABITS
# ==========================================
@router.get("/habits/{user_id}")
async def get_habits(user_id: str, db: Database = Depends(get_database)):
    def _get():
        user = db.get_or_create_user(user_id)
        return {"success": True, "habits": db.get_habits(user["id"])}
    return _run(_get)


@router.post("/habits/{user_id}")
async def add_habit(user_id: str, habit: HabitCreate, db: Database = Depends(get_database)):
    def _add():
        user = db.get_or_create_user(user_id)
        habit_id = db.create_habit(user["id"], habit.model_dump())
        return {"success": True, "habit_id": habit_id, "habit": habit.model_dump()}
    return _run(_add)


@router.post("/habits/{habit_id}/log")
async def log_habit(habit_id: int, log: HabitLogRequest, db: Database = Depends(get_database)):
    def _log():
        db.log_habit(habit_id, log.date, log.completed, log.notes)
        return {"success": True}
    return _run(_log)


# ==========================================
# PROGRESS / ANALYTICS (extended)
# ==========================================
@router.get("/progress/{user_id}")
async def get_progress(user_id: str, days: int = 30, db: Database = Depends(get_database)):
    def _get():
        user = db.get_or_create_user(user_id)
        analytics = db.get_progress_analytics(user["id"], days=days)
        return {"success": True, **analytics}
    return _run(_get)


@router.post("/progress/{user_id}/log")
async def log_task(user_id: str, log: TaskLog, db: Database = Depends(get_database)):
    def _log():
        user = db.get_or_create_user(user_id)
        db.log_task(user["id"], log.model_dump())
        return {"success": True, "log": log.model_dump()}
    return _run(_log)