import json
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VanguardAgentBrain:
    """
    Agentic Brain Engine with LLM Integration for dynamic responses.
    Uses DeepSeek API for generating intelligent, context-aware responses.
    """
    
    def __init__(self, user_name: str, core_ambition: str, starting_block_mins: int = 15, deepseek_service=None):
        self.user_name = user_name
        self.core_ambition = core_ambition
        self.current_block_mins = starting_block_mins
        self.target_block_mins = 240  # 4 Hours ultimate goal
        
        self.wins_history: List[Dict] = []
        self.skip_reasons_log: List[str] = []
        self.triage_actions: List[str] = []
        self.last_diagnosis: Optional[str] = None
        self.streak_count = 0
        self.longest_streak = 0
        
        # LLM Service
        self.llm = deepseek_service
        
        logger.info(f"🧠 VanguardAgentBrain initialized for {user_name} with LLM integration")
    
    def add_past_win(self, win_description: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.wins_history.append({"date": timestamp, "win": win_description, "block_size": self.current_block_mins})
        self.streak_count += 1
        if self.streak_count > self.longest_streak:
            self.longest_streak = self.streak_count
    
    def get_anchor_win(self) -> str:
        if self.wins_history:
            recent_win = self.wins_history[-1]["win"]
            return f"🌟 **WIN ANCHOR:** Remember when you {recent_win}? You've proven you can pull this off."
        return f"🌟 **WIN ANCHOR:** You took the single hardest step today—showing up to fight for your dream, {self.user_name}."
    
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
            "progress_to_target": min(100, int((self.current_block_mins / self.target_block_mins) * 100))
        }
    
    def process_daily_log(self, completed: bool, time_spent_mins: int = 0, 
                          skip_reason: str = None, user_input: str = "") -> Dict:
        """Process daily log with LLM-enhanced responses."""
        
        # 1. ALWAYS START WITH PAST WIN ANCHOR
        anchor = self.get_anchor_win()
        
        # 2. SUCCESS PATH: Log victory and scale
        if completed:
            win_description = f"completed {time_spent_mins} mins on '{self.core_ambition}'"
            self.add_past_win(win_description)
            
            # Progressive Time Scaling
            if len(self.wins_history) >= 3 and self.current_block_mins < self.target_block_mins:
                self.current_block_mins += 15
            
            # Generate LLM response for win
            message = self._generate_win_response(time_spent_mins)
            
        # 3. FRICTION PATH: Process skip & run Sabotage Diagnostic
        else:
            self.streak_count = 0
            
            if skip_reason or user_input:
                if skip_reason:
                    reason_clean = skip_reason.strip().lower()
                else:
                    reason_clean = user_input.strip().lower()[:100]
                
                self.skip_reasons_log.append(reason_clean)
                reason_counts = Counter(self.skip_reasons_log)
                frequency = reason_counts[reason_clean]
                
                # Check sabotage threshold
                if frequency >= 4:
                    intervention = self._diagnose_sabotage_pattern(reason_clean)
                    self.triage_actions.append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "reason": reason_clean,
                        "intervention": intervention
                    })
                    message = self._generate_sabotage_response(reason_clean, frequency, intervention)
                else:
                    message = self._generate_skip_response(reason_clean, frequency)
        
        return {
            "message": message,
            "action_taken": "escalated_block" if completed and len(self.wins_history) >= 3 else None,
            "data": self.get_stats()
        }
    
    def _generate_win_response(self, time_spent_mins: int) -> str:
        """Generate LLM response for a win."""
        stats = self.get_stats()
        anchor = self.get_anchor_win()
        
        prompt = f"""You are Vanguard, an elite focus coach. Generate a motivational response for this win:

User: {self.user_name}
Ambition: {self.core_ambition}
Time spent: {time_spent_mins} mins
Current streak: {stats['streak_count']} days
Current block size: {stats['current_block_mins']} mins
Progress to 4-hour target: {stats['progress_to_target']}%

Anchor: {anchor}

Generate a response that:
1. Celebrates the win with specific encouragement
2. Mentions the habit sandwich technique for the next block
3. Is concise (2-3 sentences)
4. Uses an encouraging, coach-like tone"""
        
        if self.llm:
            try:
                response = self.llm.generate(prompt, max_tokens=150, temperature=0.7)
                return response
            except Exception as e:
                logger.error(f"LLM error in win response: {e}")
                return self._fallback_win_response(time_spent_mins)
        
        return self._fallback_win_response(time_spent_mins)
    
    def _generate_skip_response(self, reason: str, frequency: int) -> str:
        """Generate LLM response for a skip."""
        prompt = f"""User: {self.user_name} skipped their block.
Reason: "{reason}"
This has happened {frequency} time(s).

Generate a supportive, no-shame response that:
1. Acknowledges the skip without judgment
2. Applies the 50% Floor Rule (reduce chores)
3. Encourages them to try again tomorrow
4. Is concise (2-3 sentences)
5. Uses a supportive, coach-like tone"""
        
        if self.llm:
            try:
                response = self.llm.generate(prompt, max_tokens=150, temperature=0.7)
                return response
            except Exception as e:
                logger.error(f"LLM error in skip response: {e}")
                return self._fallback_skip_response(reason, frequency)
        
        return self._fallback_skip_response(reason, frequency)
    
    def _generate_sabotage_response(self, reason: str, frequency: int, intervention: str) -> str:
        """Generate LLM response for sabotage detection."""
        prompt = f"""User: {self.user_name} has encountered a recurring roadblock.
Reason: "{reason}"
Occurrences: {frequency} times (>=4 threshold triggered)

Intervention: {intervention}

Generate a response that:
1. Acknowledges the pattern with care
2. Presents the intervention options clearly
3. Empowers the user to take action
4. Is supportive but direct
5. 3-4 sentences, coach-like tone"""
        
        if self.llm:
            try:
                response = self.llm.generate(prompt, max_tokens=200, temperature=0.7)
                return response
            except Exception as e:
                logger.error(f"LLM error in sabotage response: {e}")
                return self._fallback_sabotage_response(reason, intervention)
        
        return self._fallback_sabotage_response(reason, intervention)
    
    def _fallback_win_response(self, time_spent_mins: int) -> str:
        """Fallback when LLM is not available."""
        return f"""✅ **VICTORY LOGGED:** {time_spent_mins} minutes secured for '{self.core_ambition}'.

💡 **NEXT STEP (HABIT SANDWICH):**
Sandwich your next {self.current_block_mins}-min block immediately after an existing anchor."""
    
    def _fallback_skip_response(self, reason: str, frequency: int) -> str:
        """Fallback when LLM is not available."""
        return f"""⚠️ **BLOCK SKIPPED:** Zero shame—this is raw diagnostic data, not a failure.
📌 **Logged Reason:** '{reason}' (Occurrences: {frequency})

🛡️ **ACTION: APPLY 50% FLOOR & RESET**
Reduce maintenance chores by 50% tonight to preserve baseline energy."""
    
    def _fallback_sabotage_response(self, reason: str, intervention: str) -> str:
        """Fallback when LLM is not available."""
        return f"""🚨 **PATTERNS DETECTED (>= 4 OCCURRENCES) - STRUCTURAL INTERVENTION REQUIRED:**

{intervention}"""
    
    def _diagnose_sabotage_pattern(self, reason: str) -> str:
        """Diagnose sabotage pattern and return intervention."""
        reason_lower = reason.lower()
        
        if any(w in reason_lower for w in ["work", "boss", "overtime", "job", "office", "deadline", "client", "meeting"]):
            return (
                "👉 **Diagnosis:** Work Overreach / Boundary Creep.\n"
                "👉 **Strategic Leverage:** Your workplace is consuming your ambition hours. Options:\n"
                "   1. Draft a strict 5:30 PM log-off boundary email to your supervisor.\n"
                "   2. Re-negotiate current project scope.\n"
                "   3. Shift your growth block to the early morning before work communications open."
            )
        elif any(w in reason_lower for w in ["kids", "child", "family", "house", "cleaning", "cook", "chores", "dinner", "baby", "spouse"]):
            return (
                "👉 **Diagnosis:** Domestic Operational Bottleneck.\n"
                "👉 **Strategic Leverage:** You cannot out-work this alone. Options:\n"
                "   1. Delegate/Offload: Hire temporary domestic help or ask family to cover a 1-hour shift.\n"
                "   2. Switch to 15-minute simple assembly meals.\n"
                "   3. Lower the housekeeping floor permanently to survival mode."
            )
        elif any(w in reason_lower for w in ["tired", "exhausted", "sleep", "fatigue", "brain", "drained", "no energy", "low"]):
            return (
                "👉 **Diagnosis:** Physiological Depletion / Energy Misalignment.\n"
                "👉 **Strategic Leverage:** Evening blocks fail when energy is spent. Options:\n"
                "   1. Move your Ambition Block to the first 15 minutes after waking up.\n"
                "   2. Execute a 2-minute micro-floor to keep the habit chain alive.\n"
                "   3. Optimize sleep: 7-8 hours is non-negotiable."
            )
        elif any(w in reason_lower for w in ["phone", "social media", "distraction", "tv", "scroll", "video", "games"]):
            return (
                "👉 **Diagnosis:** Digital Friction / Attention Theft.\n"
                "👉 **Strategic Leverage:** Your devices are weaponized against your ambition. Options:\n"
                "   1. Install Freedom or Cold Turkey for your block time.\n"
                "   2. Use Focus Mode to block distracting apps.\n"
                "   3. Keep your phone in another room during your block."
            )
        else:
            return (
                "👉 **Diagnosis:** High System Friction.\n"
                "👉 **Strategic Leverage:** Let's reduce friction by dropping 1 optional daily commitment entirely."
            )
    
    def generate_ambition_block_plan(self, context: str = "") -> str:
        """Generate a plan using LLM."""
        stats = self.get_stats()
        
        prompt = f"""Create a personalized ambition block plan for {self.user_name}.

Context: {context or "No additional context provided"}

User Stats:
- Ambition: {self.core_ambition}
- Current Block Size: {stats['current_block_mins']} mins
- Target: {stats['target_block_mins']} mins (4 Hours)
- Streak: {stats['streak_count']} days
- Total Wins: {stats['total_wins']}

Generate a concise, actionable plan with:
1. A warm opening
2. The block structure (warm-up, deep focus, cool-down)
3. Practical tips for success
4. Encouraging closing

Keep it under 150 words."""
        
        if self.llm:
            try:
                response = self.llm.generate(prompt, max_tokens=300, temperature=0.7)
                return response
            except Exception as e:
                logger.error(f"LLM error in plan generation: {e}")
                return self._fallback_plan()
        
        return self._fallback_plan()
    
    def _fallback_plan(self) -> str:
        """Fallback plan when LLM is not available."""
        return f"""
🎯 **AMBITION BLOCK PLAN FOR {self.user_name.upper()}**

**Core Ambition:** {self.core_ambition}
**Current Block Size:** {self.current_block_mins} mins
**Target:** {self.target_block_mins} mins (4 Hours)

**Structure:**
1. **First 5 mins** - Warm-up: Review previous progress, set intention
2. **Next {self.current_block_mins - 10 if self.current_block_mins > 10 else self.current_block_mins - 5} mins** - Deep Focus Work
3. **Last 5 mins** - Document what you accomplished, plan next steps

💪 **Remember:** Consistency beats intensity. Show up every day, even for 5 minutes."""
    
    def get_progress_report(self) -> str:
        """Generate progress report using LLM."""
        stats = self.get_stats()
        
        prompt = f"""Generate a progress report for {self.user_name}.

Stats:
- Ambition: {stats['core_ambition']}
- Current Block: {stats['current_block_mins']} mins
- Target: {stats['target_block_mins']} mins
- Progress: {stats['progress_to_target']}%
- Streak: {stats['streak_count']} days
- Longest Streak: {stats['longest_streak']} days
- Total Wins: {stats['total_wins']}
- Recent Skips: {stats['skip_reasons_log']}

Generate a concise, encouraging progress report with:
1. A summary of their progress
2. Key metrics
3. Encouragement based on their streak
4. A tip for the next step

Keep it under 120 words."""
        
        if self.llm:
            try:
                response = self.llm.generate(prompt, max_tokens=250, temperature=0.7)
                return response
            except Exception as e:
                logger.error(f"LLM error in progress report: {e}")
                return self._fallback_progress_report()
        
        return self._fallback_progress_report()
    
    def _fallback_progress_report(self) -> str:
        """Fallback progress report when LLM is not available."""
        stats = self.get_stats()
        report = f"""
📊 **PROGRESS REPORT FOR {self.user_name}**

**Ambition:** {stats['core_ambition']}
**Current Block:** {stats['current_block_mins']} mins
**Target Block:** {stats['target_block_mins']} mins
**Progress:** {stats['progress_to_target']}%

🏆 **Streak:** {stats['streak_count']} days
**Longest Streak:** {stats['longest_streak']} days
**Total Wins:** {stats['total_wins']}
"""
        return report.strip()
