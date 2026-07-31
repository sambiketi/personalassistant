import os
import httpx
import logging
from typing import Optional

from app.services.llm_interface import LLMService

logger = logging.getLogger(__name__)


class DeepSeekService(LLMService):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self._enabled = bool(self.api_key)

    def update_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self._enabled = bool(api_key)
        # Log when API key is updated
        if self._enabled:
            logger.info("🔑 DeepSeek API key updated successfully")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        if not self.enabled:
            logger.warning("❌ DeepSeek disabled - returning mock response")
            return self._mock_response()
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system", 
                                "content": "You are a helpful scheduling assistant. Return your response as a JSON object with a 'tasks' array. Each task should have 'name', 'start_time', 'end_time', 'duration', and 'status'. Include optional 'suggestions' and 'reasoning' fields."
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                if response.status_code == 200:
                    # Extract just the content from the response
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"✅ DeepSeek API call successful ({len(content)} chars)")
                    return content
                else:
                    logger.error(f"❌ DeepSeek API error: {response.status_code}")
                    logger.error(f"Response: {response.text[:200]}")
                    return self._mock_response()
        except Exception as e:
            logger.error(f"❌ DeepSeek error: {e}")
            return self._mock_response()

    def _mock_response(self) -> str:
        """Fallback mock response when API is unavailable - Returns VALID JSON!"""
        return """{
    "tasks": [
        {
            "name": "Morning routine",
            "start_time": "07:00",
            "end_time": "08:00",
            "duration": 60,
            "status": "pending"
        },
        {
            "name": "Deep work session",
            "start_time": "09:00",
            "end_time": "12:00",
            "duration": 180,
            "status": "pending"
        },
        {
            "name": "Lunch break",
            "start_time": "12:00",
            "end_time": "13:00",
            "duration": 60,
            "status": "pending"
        },
        {
            "name": "Afternoon work",
            "start_time": "13:00",
            "end_time": "17:00",
            "duration": 240,
            "status": "pending"
        },
        {
            "name": "Exercise",
            "start_time": "18:00",
            "end_time": "19:00",
            "duration": 60,
            "status": "pending"
        },
        {
            "name": "Dinner",
            "start_time": "19:00",
            "end_time": "20:00",
            "duration": 60,
            "status": "pending"
        },
        {
            "name": "Relax and wind down",
            "start_time": "20:00",
            "end_time": "22:00",
            "duration": 120,
            "status": "pending"
        }
    ],
    "suggestions": [
        "Break your work into 90-minute focus blocks",
        "Take a 5-minute break every hour",
        "Stay hydrated throughout the day"
    ],
    "reasoning": "Structured your day around a typical work schedule with focused work periods, breaks, and personal time."
}"""