from abc import ABC, abstractmethod
from typing import Dict


class Brain(ABC):
    """Pluggable behavioral-tracking engine interface (e.g. VanguardBrain)."""

    @abstractmethod
    def process_vanguard_intent(self, intent, user_input: str) -> Dict:
        """Handle a win/skip style intent, return {'message': str, 'data': dict}."""
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def get_progress_report(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_analytics_summary(self) -> str:
        raise NotImplementedError
