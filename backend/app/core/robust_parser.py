import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class RobustJSONParser:
    """Robust JSON parser with multiple fallback strategies for messy LLM output."""

    @staticmethod
    def extract_json(text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return m.group()
        m = re.search(r"\[[\s\S]*\]", text)
        if m:
            return m.group()
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def clean_json(json_str: str) -> str:
        if not json_str:
            return json_str
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        json_str = re.sub(r",\s*,", ",", json_str)
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        json_str = re.sub(r"//.*?$", "", json_str, flags=re.MULTILINE)
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
        json_str = re.sub(r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', json_str)
        return json_str

    @staticmethod
    def parse_with_retry(text: str) -> Tuple[Optional[Dict], Optional[str]]:
        if not text:
            return None, "Empty input"

        strategies = [
            lambda t: json.loads(t),
            lambda t: json.loads(RobustJSONParser.clean_json(t)),
            lambda t: json.loads(RobustJSONParser._fix_common_json_issues(t)),
        ]
        for i, strategy in enumerate(strategies):
            try:
                json_text = RobustJSONParser.extract_json(text) or text
                cleaned = RobustJSONParser.clean_json(json_text)
                result = strategy(cleaned)
                if result:
                    logger.info(f"JSON parsed with strategy {i + 1}")
                    return result, None
            except Exception as e:
                logger.debug(f"Strategy {i + 1} failed: {e}")
                continue

        try:
            result = RobustJSONParser._salvage_partial_json(text)
            if result:
                return result, "Partial JSON recovered"
        except Exception:
            pass

        return None, "Failed to parse JSON after all retries"

    @staticmethod
    def _fix_common_json_issues(text: str) -> str:
        text = re.sub(r"}\s*{", "},{", text)
        open_braces, close_braces = text.count("{"), text.count("}")
        if open_braces > close_braces:
            text += "}" * (open_braces - close_braces)
        open_brackets, close_brackets = text.count("["), text.count("]")
        if open_brackets > close_brackets:
            text += "]" * (open_brackets - close_brackets)
        return text

    @staticmethod
    def _salvage_partial_json(text: str) -> Optional[Dict]:
        try:
            pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', text)
            if pairs:
                return {k: v for k, v in pairs}
            return None
        except Exception:
            return None


class ScheduleParser:
    @staticmethod
    def parse_tasks(tasks_data: List[Dict]) -> List[Dict]:
        parsed = []
        for i, task in enumerate(tasks_data):
            try:
                start_time = task.get("start_time") or f"{6 + i * 2:02d}:00"
                end_time = task.get("end_time") or f"{7 + i * 2:02d}:00"
                duration = task.get("duration")
                if not duration:
                    try:
                        sd = datetime.strptime(start_time, "%H:%M")
                        ed = datetime.strptime(end_time, "%H:%M")
                        duration = int((ed - sd).total_seconds() / 60)
                    except Exception:
                        duration = 60
                parsed.append(
                    {
                        "id": task.get("id", str(i + 1)),
                        "name": task.get("name", "Untitled Task"),
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "priority": task.get("priority", 3),
                        "status": task.get("status", "pending"),
                        "category": task.get("category", "general"),
                        "notes": task.get("notes", ""),
                        "is_flexible": task.get("is_flexible", True),
                    }
                )
            except Exception as e:
                logger.warning(f"Error parsing task {i}: {e}")
        return parsed

    @staticmethod
    def create_schedule_from_json(data: Dict, date_str: str = None) -> Dict:
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        tasks_data = data.get("tasks") or data.get("schedule") or data.get("tasks_list") or []
        parsed_tasks = ScheduleParser.parse_tasks(tasks_data)
        total_hours = sum(t.get("duration", 0) for t in parsed_tasks) / 60
        return {
            "date": date_str,
            "tasks": parsed_tasks,
            "total_hours": total_hours,
            "completion_rate": data.get("completion_rate", 0),
            "reasoning": data.get("reasoning", ""),
            "suggestions": data.get("suggestions", []),
        }


def robust_parse_ai_response(response: str, date_str: str = None) -> Tuple[Optional[Dict], Optional[str]]:
    if not response:
        return None, "Empty response from AI"
    data, error = RobustJSONParser.parse_with_retry(response)
    if not data:
        return None, error or "No data extracted from response"
    try:
        return ScheduleParser.create_schedule_from_json(data, date_str), None
    except Exception as e:
        return None, f"Schedule creation failed: {e}"
