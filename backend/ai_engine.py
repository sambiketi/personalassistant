import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class TaskItem(BaseModel):
    task_name: str
    start_time: str = Field(description="Format: HH:MM AM/PM")
    end_time: str = Field(description="Format: HH:MM AM/PM")
    is_unsnoozable: bool = Field(default=False)

class DailySchedule(BaseModel):
    date_or_day: str
    tasks: List[TaskItem]

class UniversalScheduler:
    def __init__(self, provider_model: str = "deepseek-chat", api_key: str = None):
        self.model = provider_model
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def generate_schedule(self, user_prompt: str, unsnoozables: List[str]) -> DailySchedule:
        system_prompt = f"""
        You are an elite productivity scheduling agent.
        User Unsnoozable Tasks: {unsnoozables}

        Rules:
        1. Parse the prompt into sequential start and end times.
        2. Set is_unsnoozable=True for any task matching the user's unsnoozable list.
        3. Maintain strict time continuity without overlaps.
        4. Use 12-hour format with AM/PM.
        5. Return ONLY valid JSON with this exact structure:
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
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            result = json.loads(response.choices[0].message.content)
            return DailySchedule(**result)
            
        except Exception as e:
            print(f"Error generating schedule: {e}")
            # Return a fallback schedule
            return DailySchedule(
                date_or_day="Today",
                tasks=[
                    TaskItem(
                        task_name=f"Error: {str(e)}. Please try again.",
                        start_time="09:00 AM",
                        end_time="09:01 AM",
                        is_unsnoozable=False
                    )
                ]
            )

# Test function
if __name__ == "__main__":
    print("Testing DeepSeek integration...")
    scheduler = UniversalScheduler()
    
    test_prompt = "Waking up at 6am. Exercise 1 hour, Code for 2 hours, Break, Apply to jobs"
    result = scheduler.generate_schedule(test_prompt, ["Exercise", "Apply to jobs"])
    
    print(f"\nSchedule for: {result.date_or_day}")
    for task in result.tasks:
        print(f"  {task.start_time} - {task.end_time}: {task.task_name} (Unsnoozable: {task.is_unsnoozable})")
