import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.core.brain_interface import Brain
from app.core.robust_parser import robust_parse_ai_response
from app.services.llm_interface import LLMService
from app.models.database import Database

logger = logging.getLogger(__name__)


class Intent(Enum):
    CREATE_SCHEDULE = "create_schedule"
    LOG_VANGUARD_WIN = "log_vanguard_win"
    LOG_VANGUARD_SKIP = "log_vanguard_skip"
    SHOW_SCHEDULE = "show_schedule"
    SHOW_PROGRESS = "show_progress"
    SHOW_ANALYTICS = "show_analytics"
    GENERAL_CHAT = "general_chat"


@dataclass
class Task:
    name: str
    start_time: str
    end_time: str
    duration: int
    priority: int
    status: str
    category: str
    notes: str = ""
    is_flexible: bool = True
    id: str = ""

@dataclass
class Schedule:
    date: str
    tasks: List[Task]
    total_hours: float = 0
    completion_rate: float = 0

    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "tasks": [t.__dict__ for t in self.tasks],
            "total_hours": self.total_hours,
            "completion_rate": self.completion_rate,
        }


@dataclass
class AgentResponse:
    intent: Intent
    message: str
    schedule: Optional[Schedule] = None
    suggestions: List[str] = field(default_factory=list)
    reasoning: str = ""
    changed_tasks: List[str] = field(default_factory=list)
    vanguard_data: Optional[Dict] = None


class FocusAgent:
    """Main agent engine orchestrating intents with pluggable Brain + LLM."""

    def __init__(self, db: Database, llm: LLMService, brain: Brain):
        self.db = db
        self.llm = llm
        self.brain = brain
        self.current_schedule: Optional[Schedule] = None
        self.user_id: Optional[str] = None
        self.user_data: Optional[Dict] = None

    def process(self, user_id: str, user_input: str) -> AgentResponse:
        try:
            self.user_id = user_id
            self.user_data = self.db.get_or_create_user(user_id)

            # REMOVED: API key lookup from database - now provided by frontend in the request
        # The LLM is updated in the route handler before calling this method

            today = datetime.now().strftime("%Y-%m-%d")
            schedule_data = self.db.get_schedule(self.user_data["id"], today)
            if schedule_data:
                self.current_schedule = Schedule(
                    date=schedule_data["date"],
                    tasks=[Task(**t) for t in schedule_data.get("tasks", [])],
                    total_hours=schedule_data.get("total_hours", 0),
                    completion_rate=schedule_data.get("completion_rate", 0),
                )

            vanguard_intent = self.detect_vanguard_intent(user_input)
            if vanguard_intent:
                return self.handle_vanguard_intent(vanguard_intent, user_input)

            intent, entities = self.detect_intent(user_input)
            handler_map = {
                Intent.CREATE_SCHEDULE: self.handle_create_schedule,
                Intent.SHOW_SCHEDULE: lambda *_: self.handle_show_schedule(),
                Intent.SHOW_PROGRESS: lambda *_: self.handle_show_progress(),
                Intent.SHOW_ANALYTICS: lambda *_: self.handle_show_analytics(),
                Intent.GENERAL_CHAT: self.handle_general_chat,
            }
            return handler_map.get(intent, self.handle_general_chat)(user_input, entities)

        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return AgentResponse(intent=Intent.GENERAL_CHAT, message=f"⚠️ Error: {e}")

    def detect_vanguard_intent(self, user_input: str) -> Optional[Intent]:
        text = user_input.lower()
        if "completed" in text or "win" in text:
            return Intent.LOG_VANGUARD_WIN
        if "skip" in text or "didn't" in text:
            return Intent.LOG_VANGUARD_SKIP
        return None

    def handle_vanguard_intent(self, intent: Intent, user_input: str) -> AgentResponse:
        result = self.brain.process_vanguard_intent(intent, user_input)
        return AgentResponse(intent=intent, message=result.get("message", ""), vanguard_data=result.get("data", {}))

    def detect_intent(self, user_input: str) -> Tuple[Intent, Dict]:
        text = user_input.lower()
        if "schedule" in text or "plan" in text:
            return Intent.CREATE_SCHEDULE, {"description": user_input}
        if "progress" in text or "status" in text:
            return Intent.SHOW_PROGRESS, {}
        if "analytics" in text or "stats" in text:
            return Intent.SHOW_ANALYTICS, {}
        return Intent.GENERAL_CHAT, {}

    def handle_create_schedule(self, user_input: str, entities: Dict) -> AgentResponse:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"Create a schedule for {today} based on: {user_input}"
        raw_response = self.llm.generate(prompt)
        parsed, error = robust_parse_ai_response(raw_response, today)

        if error or not parsed.get("tasks"):
            return AgentResponse(
                intent=Intent.CREATE_SCHEDULE,
                message="⚠️ Could not parse a schedule from that. Try being more specific, e.g. "
                "'Plan my day: gym at 7am, deep work 9-11, lunch at 12'.",
            )

        tasks = [Task(**t) for t in parsed["tasks"]]
        schedule = Schedule(date=today, tasks=tasks)
        self.db.save_schedule(self.user_data["id"], today, schedule.to_dict())
        self.current_schedule = schedule

        return AgentResponse(
            intent=Intent.CREATE_SCHEDULE,
            message=f"✅ Schedule created for {today}",
            schedule=schedule,
            suggestions=parsed.get("suggestions", []),
            reasoning=parsed.get("reasoning", ""),
        )

    def handle_show_schedule(self) -> AgentResponse:
        if not self.current_schedule:
            return AgentResponse(intent=Intent.SHOW_SCHEDULE, message="No active schedule.")
        return AgentResponse(
            intent=Intent.SHOW_SCHEDULE,
            message=f"📅 Schedule for {self.current_schedule.date}",
            schedule=self.current_schedule,
        )

    def handle_show_progress(self) -> AgentResponse:
        return AgentResponse(
            intent=Intent.SHOW_PROGRESS,
            message=self.brain.get_progress_report(),
            vanguard_data=self.brain.get_stats(),
        )

    def handle_show_analytics(self) -> AgentResponse:
        return AgentResponse(intent=Intent.SHOW_ANALYTICS, message=self.brain.get_analytics_summary())

    def handle_general_chat(self, user_input: str, entities: Dict = None) -> AgentResponse:
        response = self.llm.generate(f"User says: {user_input}")
        return AgentResponse(intent=Intent.GENERAL_CHAT, message=response)
