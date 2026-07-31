import logging
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional

from app.services.llm_interface import LLMService
from app.core.brain_interface import Brain

logger = logging.getLogger(__name__)


class VanguardBrain(Brain):
    """
    Pluggable Brain implementation: wins/skips, sabotage detection, progress reports.
    Delegates actual text generation to an injected LLMService.
    """

    def __init__(
        self,
        user_name: str = "friend",
        core_ambition: str = "your focus goal",
        llm: Optional[LLMService] = None,
        starting_block_mins: int = 15,
    ):
        self.user_name = user_name
        self.core_ambition = core_ambition
        self.llm = llm
        self.current_block_mins = starting_block_mins
        self.target_block_mins = 240

        self.wins_history: List[Dict] = []
        self.skip_reasons_log: List[str] = []
        self.streak_count = 0
        self.longest_streak = 0

        logger.info(f"🧠 VanguardBrain initialized for {user_name}")

    def get_stats(self) -> Dict:
        return {
            "user_name": self.user_name,
            "core_ambition": self.core_ambition,
            "current_block_mins": self.current_block_mins,
            "target_block_mins": self.target_block_mins,
            "streak_count": self.streak_count,
            "longest_streak": self.longest_streak,
            "total_wins": len(self.wins_history),
            "skip_reasons_log": self.skip_reasons_log[-5:],
            "progress_to_target": min(100, int((self.current_block_mins / self.target_block_mins) * 100)),
        }

    def process_vanguard_intent(self, intent, user_input: str) -> Dict:
        if intent.value == "log_vanguard_win":
            return self._process_win(user_input)
        elif intent.value == "log_vanguard_skip":
            return self._process_skip(user_input)
        return {"message": "No Vanguard intent detected", "data": self.get_stats()}

    def _process_win(self, user_input: str) -> Dict:
        self.streak_count += 1
        self.longest_streak = max(self.longest_streak, self.streak_count)

        win_description = f"Completed {self.current_block_mins} mins on '{self.core_ambition}'"
        self.wins_history.append({"date": datetime.now().isoformat(), "win": win_description})

        if len(self.wins_history) >= 3 and self.current_block_mins < self.target_block_mins:
            self.current_block_mins += 15

        message = self._generate_llm_response("win", user_input)
        return {"message": message, "data": self.get_stats()}

    def _process_skip(self, user_input: str) -> Dict:
        self.streak_count = 0
        reason = user_input.strip().lower()[:100]
        self.skip_reasons_log.append(reason)

        frequency = Counter(self.skip_reasons_log)[reason]
        mode = "sabotage" if frequency >= 4 else "skip"
        message = self._generate_llm_response(mode, reason)
        return {"message": message, "data": self.get_stats()}

    def get_progress_report(self) -> str:
        return self._generate_llm_response("progress", "")

    def get_analytics_summary(self) -> str:
        stats = self.get_stats()
        return f"📈 Analytics: {stats['total_wins']} wins, {stats['streak_count']} streak, {stats['progress_to_target']}% progress"

    def _generate_llm_response(self, mode: str, context: str) -> str:
        if not self.llm or not self.llm.enabled:
            return f"[Fallback] {mode.capitalize()} response for {self.user_name}"

        prompt = (
            f"Mode: {mode}\nUser: {self.user_name}\nAmbition: {self.core_ambition}\n"
            f"Context: {context}\nStats: {self.get_stats()}"
        )
        try:
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"LLM error in {mode} response: {e}")
            return f"[Fallback] {mode.capitalize()} response for {self.user_name}"
