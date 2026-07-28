import os
import json
from typing import Optional, Dict, Any
import httpx

class DeepSeekService:
    """DeepSeek API service for agent intelligence"""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self.enabled = bool(self.api_key)
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate response from DeepSeek"""
        if not self.enabled:
            return self._mock_response(prompt)
        
        try:
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
                            {"role": "system", "content": "You are a helpful scheduling assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content']
                else:
                    print(f"DeepSeek API error: {response.status_code}")
                    return self._mock_response(prompt)
                    
        except Exception as e:
            print(f"DeepSeek error: {e}")
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """Mock response when API is not available"""
        return "I understand you're asking about scheduling. I'll help you plan your day. Can you tell me more about what you need?"
