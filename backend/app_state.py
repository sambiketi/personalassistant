from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Task:
    name: str
    start_time: str
    end_time: str
    is_unsnoozable: bool = False
    status: str = "PENDING"

@dataclass
class UserSession:
    phone_number: str
    api_key: str
    provider: str
    unsnoozables: List[str]
    tasks: List[Task] = field(default_factory=list)

APP_STATE: Dict[str, UserSession] = {}
