import json
from abc import ABC, abstractmethod
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional

class TaskItem(BaseModel):
    task_name: str
    start_time: str = Field(description="Format: HH:MM AM/PM")
    end_time: str = Field(description="Format: HH:MM AM/PM")
    is_unsnoozable: bool = Field(default=False)

class DailySchedule(BaseModel):
    date_or_day: str
    tasks: List[TaskItem]

class BaseLLM(ABC):
    @abstractmethod
    def generate_schedule(self, prompt: str, unsnoozables: List[str]) -> DailySchedule:
        pass
    
    @abstractmethod
    def test_connection(self) -> dict:
        pass

class DeepSeekLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
    
    def test_connection(self) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_schedule(self, prompt: str, unsnoozables: List[str]) -> DailySchedule:
        system_prompt = f"""
        You are a productivity scheduling agent.
        Unsnoozable Tasks: {unsnoozables}
        
        Rules:
        1. Parse prompt into sequential start/end times
        2. Mark tasks in unsnoozables as is_unsnoozable=True
        3. Use 12-hour format (HH:MM AM/PM)
        4. Return valid JSON only
        
        Schema:
        {{
            "date_or_day": "Today",
            "tasks": [
                {{
                    "task_name": "Task name",
                    "start_time": "HH:MM AM/PM",
                    "end_time": "HH:MM AM/PM",
                    "is_unsnoozable": true/false
                }}
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return DailySchedule(**result)
        except Exception as e:
            return DailySchedule(
                date_or_day="Today",
                tasks=[TaskItem(
                    task_name=f"Error: {str(e)}. Please try again.",
                    start_time="09:00 AM",
                    end_time="09:01 AM",
                    is_unsnoozable=False
                )]
            )

class LLMFactory:
    @staticmethod
    def create_llm(provider: str, api_key: str, model: str = None) -> BaseLLM:
        if provider == "deepseek":
            return DeepSeekLLM(api_key, model or "deepseek-chat")
        elif provider == "openai":
            return OpenAIChat(api_key, model or "gpt-4o-mini")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

class OpenAIChat(BaseLLM):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(api_key=api_key)
    
    def test_connection(self) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_schedule(self, prompt: str, unsnoozables: List[str]) -> DailySchedule:
        system_prompt = f"""
        You are a productivity scheduling agent.
        Unsnoozable Tasks: {unsnoozables}
        
        Rules:
        1. Parse prompt into sequential start/end times
        2. Mark tasks in unsnoozables as is_unsnoozable=True
        3. Use 12-hour format (HH:MM AM/PM)
        4. Return valid JSON only
        
        Schema:
        {{
            "date_or_day": "Today",
            "tasks": [
                {{
                    "task_name": "Task name",
                    "start_time": "HH:MM AM/PM",
                    "end_time": "HH:MM AM/PM",
                    "is_unsnoozable": true/false
                }}
            ]
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return DailySchedule(**result)
        except Exception as e:
            return DailySchedule(
                date_or_day="Today",
                tasks=[TaskItem(
                    task_name=f"Error: {str(e)}. Please try again.",
                    start_time="09:00 AM",
                    end_time="09:01 AM",
                    is_unsnoozable=False
                )]
            )
