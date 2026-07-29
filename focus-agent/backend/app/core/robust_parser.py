import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class RobustJSONParser:
    """Robust JSON parser with multiple fallback strategies."""
    
    @staticmethod
    def extract_json(text: str) -> Optional[str]:
        if not text:
            return None
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group()
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            return json_match.group()
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1)
        return None
    
    @staticmethod
    def clean_json(json_str: str) -> str:
        if not json_str:
            return json_str
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        json_str = re.sub(r',\s*,', ',', json_str)
        json_str = re.sub(r'(?<!\\)"([^"]*)"(?=\s*:)', r'"\1"', json_str)
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        return json_str
    
    @staticmethod
    def parse_with_retry(text: str, max_retries: int = 3) -> Tuple[Optional[Dict], str]:
        if not text:
            return None, "Empty input"
        
        strategies = [
            lambda t: json.loads(t),
            lambda t: json.loads(RobustJSONParser.clean_json(t)),
            lambda t: json.loads(RobustJSONParser.clean_json(RobustJSONParser.extract_json(t) or t)),
            lambda t: json.loads(RobustJSONParser.extract_json(t) or t),
            lambda t: json.loads(RobustJSONParser._fix_common_json_issues(t)),
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                json_text = RobustJSONParser.extract_json(text) or text
                cleaned = RobustJSONParser.clean_json(json_text)
                result = strategy(cleaned)
                if result:
                    logger.info(f"JSON parsed successfully with strategy {i+1}")
                    return result, None
            except json.JSONDecodeError as e:
                logger.debug(f"Strategy {i+1} failed: {e}")
                continue
            except Exception as e:
                logger.debug(f"Strategy {i+1} failed: {e}")
                continue
        
        try:
            result = RobustJSONParser._salvage_partial_json(text)
            if result:
                return result, "Partial JSON recovered"
        except:
            pass
        
        return None, "Failed to parse JSON after all retries"
    
    @staticmethod
    def _fix_common_json_issues(text: str) -> str:
        text = re.sub(r'}\s*{', '},{', text)
        text = re.sub(r'"\s*"\s*:', '":', text)
        open_braces = text.count('{')
        close_braces = text.count('}')
        if open_braces > close_braces:
            text += '}' * (open_braces - close_braces)
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        if open_brackets > close_brackets:
            text += ']' * (open_brackets - close_brackets)
        return text
    
    @staticmethod
    def _salvage_partial_json(text: str) -> Optional[Dict]:
        try:
            pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', text)
            if pairs:
                result = {}
                for key, value in pairs:
                    result[key] = value
                return result
            objects = re.findall(r'\{([^{}]*)\}', text)
            if objects:
                result = {}
                for obj in objects:
                    pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', obj)
                    for key, value in pairs:
                        result[key] = value
                if result:
                    return result
            return None
        except:
            return None


class ScheduleParser:
    @staticmethod
    def parse_tasks(tasks_data: List[Dict]) -> List[Dict]:
        parsed_tasks = []
        for i, task in enumerate(tasks_data):
            try:
                task_id = task.get('id', str(i + 1))
                name = task.get('name', 'Untitled Task')
                start_time = task.get('start_time', '')
                end_time = task.get('end_time', '')
                
                if not start_time:
                    base_hour = 6 + (i * 2)
                    start_time = f"{base_hour:02d}:00"
                if not end_time:
                    base_hour = 7 + (i * 2)
                    end_time = f"{base_hour:02d}:00"
                
                duration = task.get('duration', 60)
                if not task.get('duration'):
                    try:
                        start_dt = datetime.strptime(start_time, '%H:%M')
                        end_dt = datetime.strptime(end_time, '%H:%M')
                        duration = int((end_dt - start_dt).total_seconds() / 60)
                    except:
                        duration = 60
                
                parsed_task = {
                    'id': task_id,
                    'name': name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'priority': task.get('priority', 3),
                    'status': task.get('status', 'pending'),
                    'category': task.get('category', 'general'),
                    'notes': task.get('notes', ''),
                    'is_flexible': task.get('is_flexible', True)
                }
                parsed_tasks.append(parsed_task)
            except Exception as e:
                logger.warning(f"Error parsing task {i}: {e}")
                continue
        return parsed_tasks
    
    @staticmethod
    def create_schedule_from_json(data: Dict, date: str = None) -> Dict:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        tasks_data = data.get('tasks', [])
        if not tasks_data:
            tasks_data = data.get('schedule', [])
            if not tasks_data:
                tasks_data = data.get('tasks_list', [])
        
        parsed_tasks = ScheduleParser.parse_tasks(tasks_data)
        total_hours = sum(t.get('duration', 0) for t in parsed_tasks) / 60
        
        return {
            'date': date,
            'tasks': parsed_tasks,
            'total_hours': total_hours,
            'completion_rate': data.get('completion_rate', 0),
            'reasoning': data.get('reasoning', ''),
            'suggestions': data.get('suggestions', [])
        }


def robust_parse_ai_response(response: str, date: str = None) -> Tuple[Optional[Dict], Optional[str]]:
    if not response:
        return None, "Empty response from AI"
    
    data, error = RobustJSONParser.parse_with_retry(response)
    
    if error and not data:
        return None, f"JSON parsing failed: {error}"
    
    if not data:
        return None, "No data extracted from response"
    
    try:
        schedule = ScheduleParser.create_schedule_from_json(data, date)
        return schedule, None
    except Exception as e:
        return None, f"Schedule creation failed: {str(e)}"
