import os
import json
import logging
from typing import Optional, Dict, Any
import httpx
from app.core.vanguard_brain import VanguardAgentBrain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekService:
    """DeepSeek API service with Vanguard Agent Brain integration"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self.enabled = bool(self.api_key)
        
        # Initialize Vanguard Brain for each user (lazy initialization)
        self.user_brains = {}
        self._last_error = None
        
        if self.enabled:
            logger.info(f"✅ DeepSeek API enabled with key: {self.api_key[:10]}...")
        else:
            logger.warning("⚠️ DeepSeek API key not set - using enhanced mock responses")
    
    def update_api_key(self, api_key: str) -> bool:
        """Update the API key dynamically"""
        if api_key and api_key != self.api_key:
            self.api_key = api_key
            self.enabled = bool(api_key)
            logger.info(f"✅ DeepSeek API key updated: {api_key[:10]}...")
            return True
        return False
    
    def test_connection(self) -> Dict:
        """Test if the API connection is working"""
        if not self.api_key:
            return {"success": False, "error": "No API key set"}
        
        try:
            test_prompt = "Say 'Connection successful' in one sentence."
            response = self.generate(test_prompt, max_tokens=20)
            return {
                "success": True, 
                "message": "API connection successful",
                "response": response[:50] + "..." if response else "Empty response"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_vanguard_brain(self, user_id: str, user_name: str = "User", core_ambition: str = "Personal Growth") -> VanguardAgentBrain:
        """Get or create Vanguard Brain for a user."""
        if user_id not in self.user_brains:
            self.user_brains[user_id] = VanguardAgentBrain(
                user_name=user_name,
                core_ambition=core_ambition,
                starting_block_mins=15
            )
            logger.info(f"🧠 Created Vanguard Brain for {user_name} (ID: {user_id})")
        return self.user_brains[user_id]
    
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7,
                 user_id: str = None, user_name: str = "User", 
                 core_ambition: str = "Personal Growth",
                 context: Dict = None) -> str:
        """Generate response from DeepSeek with Vanguard Brain integration"""
        
        # Get or create Vanguard Brain
        brain = None
        if user_id:
            brain = self.get_vanguard_brain(user_id, user_name, core_ambition)
        
        # Check if this is a Vanguard Brain specific request
        prompt_lower = prompt.lower()
        
        # Handle Vanguard Brain specific intents
        if brain and ("completed" in prompt_lower or "skip" in prompt_lower or "win" in prompt_lower):
            return self._handle_vanguard_request(prompt, brain, context)
        
        # Check if we have a valid API key
        if not self.enabled or not self.api_key:
            logger.warning("⚠️ No valid API key - using mock response")
            return self._enhanced_mock_response(prompt, brain)
        
        try:
            logger.info(f"📤 Sending request to DeepSeek API (tokens: {max_tokens})")
            
            # Build system prompt with Vanguard context
            system_prompt = "You are a helpful scheduling assistant with Vanguard Agent Brain integration."
            if brain:
                stats = brain.get_stats()
                system_prompt += f"""
                
User Context:
- Name: {brain.user_name}
- Ambition: {brain.core_ambition}
- Current Block: {stats['current_block_mins']} mins
- Streak: {stats['streak_count']} days
- Total Wins: {stats['total_wins']}

Respond with practical, actionable advice. Use markdown formatting for clarity.
"""
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    logger.info(f"✅ DeepSeek response received ({len(content)} chars)")
                    return content
                else:
                    error_msg = f"DeepSeek API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    self._last_error = error_msg
                    return self._enhanced_mock_response(prompt, brain)
                    
        except httpx.TimeoutException:
            logger.error("⏰ DeepSeek API timeout")
            self._last_error = "Timeout"
            return self._enhanced_mock_response(prompt, brain)
        except Exception as e:
            logger.error(f"❌ DeepSeek error: {e}")
            self._last_error = str(e)
            return self._enhanced_mock_response(prompt, brain)
    
    def _handle_vanguard_request(self, prompt: str, brain: VanguardAgentBrain, context: Dict = None) -> str:
        """Handle Vanguard Brain specific requests."""
        try:
            # Parse the request
            is_completed = "completed" in prompt.lower() or "win" in prompt.lower()
            is_completed = is_completed and "not" not in prompt.lower()
            
            time_spent = 0
            skip_reason = None
            
            # Extract time spent
            import re
            time_match = re.search(r'(\d+)\s*(min|minutes|mins|hour|hours)', prompt.lower())
            if time_match:
                amount = int(time_match.group(1))
                unit = time_match.group(2)
                if unit in ['hour', 'hours']:
                    time_spent = amount * 60
                else:
                    time_spent = amount
            
            # Extract skip reason
            if "skip" in prompt.lower() or "didn't" in prompt.lower() or "not" in prompt.lower() or "couldn't" in prompt.lower():
                reason_match = re.search(r'(?:because|due to|reason:?|skipped (?:because|due to)) (.+?)(?:\.|$)', prompt, re.IGNORECASE)
                if reason_match:
                    skip_reason = reason_match.group(1).strip()
                else:
                    skip_reason = "Unknown friction"
                is_completed = False
            
            # Process with Vanguard Brain
            result = brain.process_daily_log(
                completed=is_completed,
                time_spent_mins=time_spent or 15,
                skip_reason=skip_reason,
                user_input=prompt
            )
            
            return result["message"]
            
        except Exception as e:
            logger.error(f"❌ Vanguard Brain error: {e}")
            return f"I had trouble processing that. Please try again. Error: {str(e)}"
    
    def _enhanced_mock_response(self, prompt: str, brain: Optional[VanguardAgentBrain] = None) -> str:
        """Generate enhanced mock responses with Vanguard Brain context."""
        
        # If we have a brain, use it for scheduling responses
        if brain:
            prompt_lower = prompt.lower()
            
            if "schedule" in prompt_lower or "plan" in prompt_lower:
                return brain.generate_ambition_block_plan(prompt)
            elif "progress" in prompt_lower or "report" in prompt_lower:
                return brain.get_progress_report()
            elif "win" in prompt_lower or "victory" in prompt_lower:
                result = brain.process_daily_log(completed=True, time_spent_mins=15)
                return result["message"]
            elif "skip" in prompt_lower or "friction" in prompt_lower:
                result = brain.process_daily_log(completed=False, skip_reason=prompt[:100])
                return result["message"]
        
        # Default responses with clear mock indicator
        if "schedule" in prompt.lower() or "plan" in prompt.lower():
            return """{
    "tasks": [
        {"id": "1", "name": "Wake up & Morning routine", "start_time": "06:00", "end_time": "06:30", "duration": 30, "priority": 3, "status": "pending", "category": "personal"},
        {"id": "2", "name": "Ambition Block: Core Work", "start_time": "06:30", "end_time": "07:00", "duration": 30, "priority": 5, "status": "pending", "category": "growth"},
        {"id": "3", "name": "Exercise", "start_time": "07:00", "end_time": "08:00", "duration": 60, "priority": 4, "status": "pending", "category": "health"}
    ],
    "reasoning": "Created a balanced schedule with priority on the ambition block",
    "suggestions": ["Start your day with your most important task", "Use the habit sandwich technique"]
}"""
        elif "goal" in prompt.lower():
            return """{
    "title": "Goal Achievement Plan",
    "description": "Structured goal with milestones and accountability",
    "category": "growth",
    "priority": 4,
    "milestones": [
        {"title": "Define clear outcome", "order": 1},
        {"title": "Create action plan", "order": 2},
        {"title": "Execute daily blocks", "order": 3}
    ]
}"""
        else:
            # Return a helpful message with API key guidance
            return f"""📝 **I'm using mock responses right now.**

To connect to the real DeepSeek API:
1. Get your API key from https://platform.deepseek.com/
2. Enter it in the dashboard's API key field
3. Click "Save Key"

Current Status:
- API Key: {"✅ Set" if self.api_key else "❌ Not Set"}
- Mode: {"🔴 Mock Mode" if not self.enabled else "🟢 API Mode (if working)"}

{brain.get_progress_report() if brain else "Start by logging your first win! 🏆"}"""
