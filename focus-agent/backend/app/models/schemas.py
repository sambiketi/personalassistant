# backend/app/models/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class Task(BaseModel):
    id: str
    name: str
    start_time: str
    end_time: str
    duration: int
    priority: int
    status: str = "pending"
    category: str = "general"
    notes: Optional[str] = None

class Schedule(BaseModel):
    date: str
    tasks: List[Task]
    total_hours: float = 0
    completion_rate: float = 0

class Goal(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: int = 3
    status: str = "active"
    target_date: Optional[str] = None
    progress: float = 0

class Habit(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    frequency: str = "daily"
    target_count: int = 1
    current_streak: int = 0

class AgentRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[Dict] = None

class AgentResponse(BaseModel):
    intent: str
    message: str
    schedule: Optional[Schedule] = None
    suggestions: List[str] = []
    reasoning: str = ""
    changed_tasks: List[str] = []