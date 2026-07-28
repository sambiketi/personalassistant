from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

from app.core.agent import FocusAgent, AgentResponse, Schedule
from app.models.database import Database
from app.services.deepseek import DeepSeekService

router = APIRouter()

# Initialize services
db = Database()
deepseek = DeepSeekService()

# Agent instance (created per request)
def get_agent(user_id: str) -> FocusAgent:
    return FocusAgent(db, deepseek)

# ==========================================
# REQUEST/ RESPONSE MODELS
# ==========================================

class MessageRequest(BaseModel):
    message: str
    user_id: str = "default_user"

class ScheduleRequest(BaseModel):
    user_id: str
    date: Optional[str] = None
    description: str

class GoalRequest(BaseModel):
    user_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = 3
    target_date: Optional[str] = None

class HabitRequest(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None
    frequency: str = "daily"

class TaskLogRequest(BaseModel):
    user_id: str
    task_name: str
    status: str  # completed, skipped, postponed
    date: str
    notes: Optional[str] = None

class ApiKeyRequest(BaseModel):
    user_id: str
    api_key: str

# ==========================================
# MAIN AGENT ENDPOINT
# ==========================================

@router.post("/agent/process")
async def process_message(request: MessageRequest):
    """Main agent endpoint - process any user message"""
    try:
        agent = get_agent(request.user_id)
        response = agent.process(request.user_id, request.message)
        
        return {
            "success": True,
            "response": {
                "message": response.message,
                "intent": response.intent.value,
                "schedule": response.schedule.to_dict() if response.schedule else None,
                "suggestions": response.suggestions,
                "reasoning": response.reasoning,
                "changed_tasks": response.changed_tasks
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# SCHEDULE ENDPOINTS
# ==========================================

@router.get("/schedule/{user_id}")
async def get_schedule(user_id: str, date: Optional[str] = None):
    """Get schedule for a date"""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        user = db.get_or_create_user(user_id)
        schedule = db.get_schedule(user['id'], date)
        
        return {
            "success": True,
            "date": date,
            "schedule": schedule or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule")
async def create_schedule(request: ScheduleRequest):
    """Create a new schedule"""
    try:
        agent = get_agent(request.user_id)
        response = agent.process(
            request.user_id,
            f"Create a schedule for {request.date or 'today'}: {request.description}"
        )
        
        return {
            "success": True,
            "schedule": response.schedule.to_dict() if response.schedule else None,
            "message": response.message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# GOAL ENDPOINTS
# ==========================================

@router.get("/goals/{user_id}")
async def get_goals(user_id: str, status: Optional[str] = None):
    """Get user goals"""
    try:
        user = db.get_or_create_user(user_id)
        goals = db.get_goals(user['id'], status)
        
        return {
            "success": True,
            "goals": goals
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goal")
async def create_goal(request: GoalRequest):
    """Create a new goal"""
    try:
        user = db.get_or_create_user(request.user_id)
        
        goal_id = db.create_goal(user['id'], {
            'title': request.title,
            'description': request.description,
            'category': request.category,
            'priority': request.priority,
            'target_date': request.target_date
        })
        
        return {
            "success": True,
            "goal_id": goal_id,
            "message": f"Goal '{request.title}' created successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/goal/{goal_id}/progress")
async def update_goal_progress(goal_id: int, progress: float):
    """Update goal progress"""
    try:
        db.update_goal_progress(goal_id, progress)
        return {
            "success": True,
            "message": f"Progress updated to {progress}%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goal/{goal_id}/complete")
async def complete_goal(goal_id: int):
    """Mark goal as completed"""
    try:
        db.complete_goal(goal_id)
        return {
            "success": True,
            "message": "Goal completed! 🎉"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# HABIT ENDPOINTS
# ==========================================

@router.get("/habits/{user_id}")
async def get_habits(user_id: str, status: str = "active"):
    """Get user habits"""
    try:
        user = db.get_or_create_user(user_id)
        habits = db.get_habits(user['id'], status)
        
        return {
            "success": True,
            "habits": habits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/habit")
async def create_habit(request: HabitRequest):
    """Create a new habit"""
    try:
        user = db.get_or_create_user(request.user_id)
        
        habit_id = db.create_habit(user['id'], {
            'name': request.name,
            'description': request.description,
            'frequency': request.frequency
        })
        
        return {
            "success": True,
            "habit_id": habit_id,
            "message": f"Habit '{request.name}' created!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/habit/{habit_id}/log")
async def log_habit(habit_id: int, date: Optional[str] = None, completed: bool = True):
    """Log habit completion"""
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        db.log_habit(habit_id, date, completed)
        
        return {
            "success": True,
            "message": f"Habit logged for {date}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# TASK HISTORY ENDPOINTS
# ==========================================

@router.post("/task/log")
async def log_task(request: TaskLogRequest):
    """Log task for agent learning"""
    try:
        user = db.get_or_create_user(request.user_id)
        
        db.log_task(user['id'], {
            'task_name': request.task_name,
            'status': request.status,
            'date': request.date,
            'notes': request.notes
        })
        
        return {
            "success": True,
            "message": "Task logged successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/patterns/{user_id}")
async def get_task_patterns(user_id: str, days: int = 30):
    """Get task patterns for learning"""
    try:
        user = db.get_or_create_user(user_id)
        patterns = db.get_task_patterns(user['id'], days)
        
        return {
            "success": True,
            "patterns": patterns
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# USER ENDPOINTS
# ==========================================

@router.post("/user/init")
async def init_user(user_id: str):
    """Initialize or get user"""
    try:
        user = db.get_or_create_user(user_id)
        return {
            "success": True,
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user/apikey")
async def save_api_key(request: ApiKeyRequest):
    """Save DeepSeek API key"""
    try:
        db.save_api_key(request.user_id, request.api_key)
        return {
            "success": True,
            "message": "API key saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/apikey/{user_id}")
async def get_api_key(user_id: str):
    """Get user's API key (hidden)"""
    try:
        api_key = db.get_api_key(user_id)
        return {
            "success": True,
            "has_key": bool(api_key)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# ANALYTICS ENDPOINTS
# ==========================================

@router.get("/analytics/{user_id}")
async def get_analytics(user_id: str):
    """Get user analytics"""
    try:
        user = db.get_or_create_user(user_id)
        agent = get_agent(user_id)
        response = agent.handle_show_analytics()
        
        return {
            "success": True,
            "analytics": {
                "message": response.message,
                "patterns": db.get_task_patterns(user['id'])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{user_id}")
async def get_progress(user_id: str):
    """Get user progress"""
    try:
        user = db.get_or_create_user(user_id)
        agent = get_agent(user_id)
        response = agent.handle_show_progress()
        
        return {
            "success": True,
            "progress": response.message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))