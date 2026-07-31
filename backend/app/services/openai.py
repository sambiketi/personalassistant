import os
import httpx
import logging
from typing import Optional

from app.services.llm_interface import LLMService

logger = logging.getLogger(__name__)


class OpenAIService(LLMService):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self.model = model
        self._enabled = bool(self.api_key)

    def update_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self._enabled = bool(api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        if not self.enabled:
            return self._mock_response()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a helpful scheduling assistant."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                logger.error(f"OpenAI API error: {response.status_code}")
                return self._mock_response()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return self._mock_response()

    def _mock_response(self) -> str:
        return "🤖 [Mock] I'll help you plan your day. Tell me more about what you need."
