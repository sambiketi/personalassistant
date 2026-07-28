import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

class Intent(Enum):
    CREATE_SCHEDULE = "create_schedule"
    UPDATE_SCHEDULE = "update_schedule"
    HANDLE_EMERGENCY = "handle_emergency"
    SKIP_TASK = "skip_task"
    POSTPONE_TASK = "postpone_task"
    ADD_GOAL = "add_goal"
    UPDATE_GOAL = "update_goal"
    LOG_HABIT = "log_habit"
    SHOW_SCHEDULE = "show_schedule"
    SHOW_PROGRESS = "show_progress"
    SHOW_ANALYTICS = "show_analytics"
    GENERAL_CHAT = "general_chat"

@dataclass
class Task:
    id: str
    name: str
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    duration: int    # minutes
    priority: int    # 1-5
    status: str      # pending, in_progress, completed, skipped, postponed
    category: str    # work, health, learning, personal
    notes: str = ""
    is_flexible: bool = True
    depends_on: List[str] = field(default_factory=list)

@dataclass
class Schedule:
    date: str  # YYYY-MM-DD
    tasks: List[Task]
    total_hours: float = 0
    completion_rate: float = 0
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'tasks': [{
                'id': t.id,
                'name': t.name,
                'start_time': t.start_time,
                'end_time': t.end_time,
                'duration': t.duration,
                'priority': t.priority,
                'status': t.status,
                'category': t.category,
                'notes': t.notes
            } for t in self.tasks],
            'total_hours': self.total_hours,
            'completion_rate': self.completion_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Schedule':
        tasks = [Task(**t) for t in data.get('tasks', [])]
        return cls(
            date=data['date'],
            tasks=tasks,
            total_hours=data.get('total_hours', 0),
            completion_rate=data.get('completion_rate', 0)
        )

@dataclass
class AgentResponse:
    intent: Intent
    message: str
    schedule: Optional[Schedule] = None
    action_taken: Optional[Dict] = None
    suggestions: List[str] = field(default_factory=list)
    reasoning: str = ""
    changed_tasks: List[str] = field(default_factory=list)

class FocusAgent:
    """Main agent engine for dynamic scheduling"""
    
    def __init__(self, db, deepseek_service):
        self.db = db
        self.deepseek = deepseek_service
        self.current_schedule: Optional[Schedule] = None
        self.user_id: Optional[str] = None
        self.user_data: Optional[Dict] = None
    
    def process(self, user_id: str, user_input: str) -> AgentResponse:
        """Main entry point - process user input and return agent response"""
        # 1. Load user context
        self.user_id = user_id
        self.user_data = self.db.get_or_create_user(user_id)
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 2. Load current schedule
        schedule_data = self.db.get_schedule(self.user_data['id'], today)
        if schedule_data:
            self.current_schedule = Schedule.from_dict(schedule_data)
        
        # 3. Detect intent
        intent, entities = self.detect_intent(user_input)
        
        # 4. Process based on intent
        if intent == Intent.CREATE_SCHEDULE:
            return self.handle_create_schedule(user_input, entities)
        elif intent == Intent.UPDATE_SCHEDULE:
            return self.handle_update_schedule(user_input, entities)
        elif intent == Intent.HANDLE_EMERGENCY:
            return self.handle_emergency(user_input, entities)
        elif intent == Intent.SKIP_TASK:
            return self.handle_skip_task(user_input, entities)
        elif intent == Intent.POSTPONE_TASK:
            return self.handle_postpone_task(user_input, entities)
        elif intent == Intent.ADD_GOAL:
            return self.handle_add_goal(user_input, entities)
        elif intent == Intent.SHOW_SCHEDULE:
            return self.handle_show_schedule()
        elif intent == Intent.SHOW_PROGRESS:
            return self.handle_show_progress()
        elif intent == Intent.SHOW_ANALYTICS:
            return self.handle_show_analytics()
        else:
            return self.handle_general_chat(user_input)
    
    # ==========================================
    # INTENT DETECTION
    # ==========================================
    
    def detect_intent(self, user_input: str) -> Tuple[Intent, Dict]:
        """Detect user intent using pattern matching + AI"""
        input_lower = user_input.lower()
        entities = {}
        
        # Pattern-based detection (fast path)
        patterns = {
            Intent.CREATE_SCHEDULE: [
                r'schedule', r'plan', r'tomorrow', r'today',
                r'wake up', r'waking', r'morning', r'day'
            ],
            Intent.UPDATE_SCHEDULE: [
                r'change', r'move', r'shift', r'adjust', r'update',
                r'reschedule', r'rearrange'
            ],
            Intent.HANDLE_EMERGENCY: [
                r'emergency', r'urgent', r'critical', r'immediate',
                r'sudden', r'unexpected', r'panic'
            ],
            Intent.SKIP_TASK: [
                r'skip', r'cancel', r'drop', r'remove',
                r'don\'t want', r'not doing'
            ],
            Intent.POSTPONE_TASK: [
                r'postpone', r'delay', r'later', r'push back',
                r'reschedule for later'
            ],
            Intent.ADD_GOAL: [
                r'goal', r'aim', r'objective', r'target',
                r'want to achieve', r'plan to'
            ],
            Intent.SHOW_SCHEDULE: [
                r'what.*schedule', r'show.*schedule',
                r'display.*schedule', r'current schedule'
            ],
            Intent.SHOW_PROGRESS: [
                r'progress', r'how am i doing', r'status',
                r'check in', r'update'
            ]
        }
        
        # Check patterns
        for intent, patterns_list in patterns.items():
            for pattern in patterns_list:
                if re.search(pattern, input_lower):
                    # Extract entities
                    if intent == Intent.CREATE_SCHEDULE:
                        entities['text'] = user_input
                    elif intent == Intent.SKIP_TASK:
                        # Try to extract task name
                        for word in ['workout', 'exercise', 'study', 'code', 'meeting', 'call']:
                            if word in input_lower:
                                entities['task'] = word
                                break
                    elif intent == Intent.HANDLE_EMERGENCY:
                        # Extract emergency description
                        entities['description'] = user_input
                    elif intent == Intent.ADD_GOAL:
                        entities['description'] = user_input
                    
                    return intent, entities
        
        # If no pattern matches, use AI for intent detection
        return self.detect_intent_ai(user_input)
    
    def detect_intent_ai(self, user_input: str) -> Tuple[Intent, Dict]:
        """Use DeepSeek to detect intent for complex queries"""
        prompt = f"""
        Analyze this user input and determine the intent:
        "{user_input}"
        
        Possible intents:
        - CREATE_SCHEDULE: User wants to create/plan a schedule
        - UPDATE_SCHEDULE: User wants to change existing schedule
        - HANDLE_EMERGENCY: User has an urgent task
        - SKIP_TASK: User wants to skip a task
        - POSTPONE_TASK: User wants to delay a task
        - ADD_GOAL: User wants to add a goal
        - SHOW_SCHEDULE: User wants to see schedule
        - SHOW_PROGRESS: User wants progress update
        - GENERAL_CHAT: General conversation
        
        Return only the intent name.
        """
        
        response = self.deepseek.generate(prompt)
        try:
            intent_name = response.strip().upper()
            intent = Intent[intent_name]
            return intent, {'text': user_input}
        except (KeyError, ValueError):
            return Intent.GENERAL_CHAT, {'text': user_input}
    
    # ==========================================
    # SCHEDULE HANDLERS
    # ==========================================
    
    def handle_create_schedule(self, user_input: str, entities: Dict) -> AgentResponse:
        """Create a new schedule from user description"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get user preferences
        wake_time = self.user_data.get('wake_time', '06:00')
        sleep_time = self.user_data.get('sleep_time', '22:00')
        
        # Build prompt for DeepSeek
        prompt = f"""
        Create a detailed daily schedule based on this user request:
        "{user_input}"
        
        User preferences:
        - Wake time: {wake_time}
        - Sleep time: {sleep_time}
        - Current date: {today}
        
        Return schedule as JSON with tasks containing:
        - id: unique task id
        - name: task name
        - start_time: HH:MM
        - end_time: HH:MM
        - duration: minutes
        - priority: 1-5 (5 highest)
        - category: work, health, learning, personal
        - is_flexible: true/false
        
        Also include:
        - reasoning: explanation of schedule choices
        - suggestions: tips for success
        """
        
        response = self.deepseek.generate(prompt)
        
        try:
            # Parse AI response
            data = json.loads(response)
            tasks = [Task(**t) for t in data.get('tasks', [])]
            
            schedule = Schedule(
                date=today,
                tasks=tasks,
                total_hours=sum(t.duration for t in tasks) / 60
            )
            
            # Save to database
            self.db.save_schedule(
                self.user_data['id'],
                today,
                schedule.to_dict()
            )
            
            self.current_schedule = schedule
            
            return AgentResponse(
                intent=Intent.CREATE_SCHEDULE,
                message=f"✅ Schedule created for {today}!\n\n{self.format_schedule(schedule)}",
                schedule=schedule,
                suggestions=data.get('suggestions', []),
                reasoning=data.get('reasoning', '')
            )
            
        except json.JSONDecodeError:
            # Fallback - return raw response
            return AgentResponse(
                intent=Intent.CREATE_SCHEDULE,
                message=response,
                schedule=None
            )
    
    def handle_update_schedule(self, user_input: str, entities: Dict) -> AgentResponse:
        """Update existing schedule based on user request"""
        if not self.current_schedule:
            return AgentResponse(
                intent=Intent.UPDATE_SCHEDULE,
                message="No active schedule found. Let me create one for you! 🗓️"
            )
        
        # Build prompt for DeepSeek
        current_schedule = self.current_schedule.to_dict()
        
        prompt = f"""
        User wants to update their schedule:
        "{user_input}"
        
        Current schedule:
        {json.dumps(current_schedule, indent=2)}
        
        Update the schedule based on the user request.
        Return the updated schedule in the same JSON format.
        Also include:
        - reasoning: explanation of changes made
        - changed_tasks: list of task names that were modified
        """
        
        response = self.deepseek.generate(prompt)
        
        try:
            data = json.loads(response)
            tasks = [Task(**t) for t in data.get('tasks', [])]
            
            updated_schedule = Schedule(
                date=self.current_schedule.date,
                tasks=tasks,
                total_hours=sum(t.duration for t in tasks) / 60
            )
            
            # Save to database
            self.db.save_schedule(
                self.user_data['id'],
                self.current_schedule.date,
                updated_schedule.to_dict()
            )
            
            self.current_schedule = updated_schedule
            
            return AgentResponse(
                intent=Intent.UPDATE_SCHEDULE,
                message=f"✅ Schedule updated!\n\n{self.format_schedule(updated_schedule)}",
                schedule=updated_schedule,
                changed_tasks=data.get('changed_tasks', []),
                reasoning=data.get('reasoning', '')
            )
            
        except json.JSONDecodeError:
            return AgentResponse(
                intent=Intent.UPDATE_SCHEDULE,
                message="I couldn't update the schedule. Let me try again with more details."
            )
    
    def handle_emergency(self, user_input: str, entities: Dict) -> AgentResponse:
        """Handle emergency task insertion"""
        if not self.current_schedule:
            return AgentResponse(
                intent=Intent.HANDLE_EMERGENCY,
                message="No active schedule. Creating one for you with the emergency included!"
            )
        
        prompt = f"""
        Emergency situation from user:
        "{user_input}"
        
        Current schedule:
        {json.dumps(self.current_schedule.to_dict(), indent=2)}
        
        Insert this emergency task while minimizing disruption.
        Consider:
        1. Task priority (emergency is HIGHEST)
        2. Which tasks can be shifted
        3. Which tasks can be shortened
        4. Protected time blocks (deep work, important meetings)
        
        Return updated schedule in JSON format.
        Also include:
        - reasoning: why you made these changes
        - protected_tasks: tasks that were not changed
        - suggestions: how to handle future emergencies
        """
        
        response = self.deepseek.generate(prompt)
        
        try:
            data = json.loads(response)
            tasks = [Task(**t) for t in data.get('tasks', [])]
            
            updated_schedule = Schedule(
                date=self.current_schedule.date,
                tasks=tasks,
                total_hours=sum(t.duration for t in tasks) / 60
            )
            
            # Save to database
            self.db.save_schedule(
                self.user_data['id'],
                self.current_schedule.date,
                updated_schedule.to_dict()
            )
            
            self.current_schedule = updated_schedule
            
            return AgentResponse(
                intent=Intent.HANDLE_EMERGENCY,
                message=f"🚨 Emergency handled!\n\n{self.format_schedule(updated_schedule)}",
                schedule=updated_schedule,
                suggestions=data.get('suggestions', []),
                reasoning=data.get('reasoning', '')
            )
            
        except json.JSONDecodeError:
            return AgentResponse(
                intent=Intent.HANDLE_EMERGENCY,
                message="Emergency handling in progress. Let me re-optimize..."
            )
    
    def handle_skip_task(self, user_input: str, entities: Dict) -> AgentResponse:
        """Handle task skipping"""
        if not self.current_schedule:
            return AgentResponse(
                intent=Intent.SKIP_TASK,
                message="No schedule to skip tasks from. Let me create one!"
            )
        
        task_name = entities.get('task', '').lower()
        
        # Find task to skip
        task_to_skip = None
        for task in self.current_schedule.tasks:
            if task_name in task.name.lower() or task_name in task.category.lower():
                task_to_skip = task
                break
        
        if not task_to_skip and task_name:
            # Try fuzzy match
            for task in self.current_schedule.tasks:
                if any(word in task.name.lower() for word in task_name.split()):
                    task_to_skip = task
                    break
        
        if not task_to_skip:
            # Let AI decide
            prompt = f"""
            User wants to skip a task:
            "{user_input}"
            
            Current schedule:
            {json.dumps(self.current_schedule.to_dict(), indent=2)}
            
            Determine which task to skip and redistribute the time.
            Return updated schedule in JSON format.
            Also include reasoning for your choice.
            """
            
            response = self.deepseek.generate(prompt)
            try:
                data = json.loads(response)
                tasks = [Task(**t) for t in data.get('tasks', [])]
                
                updated_schedule = Schedule(
                    date=self.current_schedule.date,
                    tasks=tasks,
                    total_hours=sum(t.duration for t in tasks) / 60
                )
                
                self.current_schedule = updated_schedule
                self.db.save_schedule(
                    self.user_data['id'],
                    self.current_schedule.date,
                    updated_schedule.to_dict()
                )
                
                return AgentResponse(
                    intent=Intent.SKIP_TASK,
                    message=f"✅ Task skipped and time redistributed!\n\n{self.format_schedule(updated_schedule)}",
                    schedule=updated_schedule,
                    reasoning=data.get('reasoning', '')
                )
            except:
                return AgentResponse(
                    intent=Intent.SKIP_TASK,
                    message="Which task would you like to skip? Please specify the task name."
                )
        
        # Remove task and redistribute time
        index = self.current_schedule.tasks.index(task_to_skip)
        removed_task = self.current_schedule.tasks.pop(index)
        
        # Adjust subsequent tasks
        for i in range(index, len(self.current_schedule.tasks)):
            if i < len(self.current_schedule.tasks):
                # Shift tasks earlier
                current = self.current_schedule.tasks[i]
                if i == index:
                    current.start_time = removed_task.start_time
                else:
                    prev = self.current_schedule.tasks[i-1]
                    current.start_time = prev.end_time
                
                # Recalculate end time
                start = datetime.strptime(current.start_time, '%H:%M')
                end = start + timedelta(minutes=current.duration)
                current.end_time = end.strftime('%H:%M')
        
        # Update total hours
        self.current_schedule.total_hours = sum(t.duration for t in self.current_schedule.tasks) / 60
        
        # Log for learning
        self.db.log_task(self.user_data['id'], {
            'task_name': removed_task.name,
            'scheduled_time': removed_task.start_time,
            'status': 'skipped',
            'date': self.current_schedule.date,
            'notes': f"Skipped task: {removed_task.name}"
        })
        
        # Save updated schedule
        self.db.save_schedule(
            self.user_data['id'],
            self.current_schedule.date,
            self.current_schedule.to_dict()
        )
        
        return AgentResponse(
            intent=Intent.SKIP_TASK,
            message=f"✅ Skipped '{removed_task.name}'. Time has been redistributed.\n\n{self.format_schedule(self.current_schedule)}",
            schedule=self.current_schedule,
            changed_tasks=[removed_task.name],
            reasoning=f"Skipped '{removed_task.name}' and shifted subsequent tasks earlier."
        )
    
    def handle_postpone_task(self, user_input: str, entities: Dict) -> AgentResponse:
        """Handle task postponing"""
        if not self.current_schedule:
            return AgentResponse(
                intent=Intent.POSTPONE_TASK,
                message="No schedule to postpone tasks from. Let me create one!"
            )
        
        # Extract time from input
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', user_input, re.IGNORECASE)
        new_time = None
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm:
                if ampm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif ampm.lower() == 'am' and hour == 12:
                    hour = 0
            new_time = f"{hour:02d}:{minute:02d}"
        
        prompt = f"""
        User wants to postpone a task:
        "{user_input}"
        {"New time suggestion: " + new_time if new_time else ""}
        
        Current schedule:
        {json.dumps(self.current_schedule.to_dict(), indent=2)}
        
        Determine which task to postpone and when.
        Return updated schedule in JSON format.
        Also include reasoning.
        """
        
        response = self.deepseek.generate(prompt)
        
        try:
            data = json.loads(response)
            tasks = [Task(**t) for t in data.get('tasks', [])]
            
            updated_schedule = Schedule(
                date=self.current_schedule.date,
                tasks=tasks,
                total_hours=sum(t.duration for t in tasks) / 60
            )
            
            self.current_schedule = updated_schedule
            self.db.save_schedule(
                self.user_data['id'],
                self.current_schedule.date,
                updated_schedule.to_dict()
            )
            
            return AgentResponse(
                intent=Intent.POSTPONE_TASK,
                message=f"✅ Task postponed!\n\n{self.format_schedule(updated_schedule)}",
                schedule=updated_schedule,
                reasoning=data.get('reasoning', '')
            )
        except:
            return AgentResponse(
                intent=Intent.POSTPONE_TASK,
                message="I'll help you postpone a task. Please specify which task and when to reschedule it."
            )
    
    # ==========================================
    # GOAL HANDLERS
    # ==========================================
    
    def handle_add_goal(self, user_input: str, entities: Dict) -> AgentResponse:
        """Add a new goal with tracking"""
        prompt = f"""
        User wants to add a goal:
        "{user_input}"
        
        Extract the goal details and create a structured goal.
        Return JSON with:
        - title: goal title
        - description: detailed description
        - category: health, career, learning, personal
        - priority: 1-5 (5 highest)
        - target_date: YYYY-MM-DD (if mentioned, else null)
        - milestones: list of milestones to track progress
        - suggestions: how to achieve this goal
        """
        
        response = self.deepseek.generate(prompt)
        
        try:
            data = json.loads(response)
            
            goal_id = self.db.create_goal(self.user_data['id'], {
                'title': data.get('title', 'New Goal'),
                'description': data.get('description', ''),
                'category': data.get('category', 'personal'),
                'priority': data.get('priority', 3),
                'target_date': data.get('target_date')
            })
            
            # Add milestones
            for milestone in data.get('milestones', []):
                self.db.add_milestone(goal_id, milestone)
            
            return AgentResponse(
                intent=Intent.ADD_GOAL,
                message=f"🎯 Goal added: '{data.get('title')}'\n\n{data.get('description', '')}\n\n💡 {data.get('suggestions', '')}",
                suggestions=data.get('suggestions', []),
                reasoning=f"Created goal with {len(data.get('milestones', []))} milestones"
            )
            
        except json.JSONDecodeError:
            return AgentResponse(
                intent=Intent.ADD_GOAL,
                message="I'll help you set up your goal. Can you tell me more about what you want to achieve?"
            )
    
    # ==========================================
    # DISPLAY HANDLERS
    # ==========================================
    
    def handle_show_schedule(self) -> AgentResponse:
        """Show current schedule"""
        if not self.current_schedule:
            return AgentResponse(
                intent=Intent.SHOW_SCHEDULE,
                message="No active schedule. Let me create one for you! Just tell me about your day."
            )
        
        return AgentResponse(
            intent=Intent.SHOW_SCHEDULE,
            message=f"📅 Your schedule for {self.current_schedule.date}:\n\n{self.format_schedule(self.current_schedule)}",
            schedule=self.current_schedule
        )
    
    def handle_show_progress(self) -> AgentResponse:
        """Show progress on goals and tasks"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get goals
        goals = self.db.get_goals(self.user_data['id'], 'active')
        
        # Get task patterns
        patterns = self.db.get_task_patterns(self.user_data['id'])
        
        # Get habits
        habits = self.db.get_habits(self.user_data['id'])
        
        # Build progress report
        messages = ["📊 Your Progress Report:\n"]
        
        if goals:
            messages.append("🎯 Goals:")
            for goal in goals:
                progress = goal.get('progress', 0)
                bar = self.progress_bar(progress)
                messages.append(f"  {bar} {goal['title']} ({progress:.0f}%)")
            messages.append("")
        
        if habits:
            messages.append("🔥 Habits:")
            for habit in habits:
                streak = habit.get('current_streak', 0)
                messages.append(f"  ✅ {habit['name']} - {streak} day streak")
            messages.append("")
        
        if patterns.get('total', 0) > 0:
            messages.append(f"📈 Completion Rate: {patterns.get('completion_rate', 0):.0f}%")
            
            skipped = patterns.get('skipped', [])
            if skipped:
                messages.append("  ⚠️ Frequently skipped: " + ", ".join([s[0] for s in skipped[:3]]))
        
        return AgentResponse(
            intent=Intent.SHOW_PROGRESS,
            message="\n".join(messages)
        )
    
    def handle_show_analytics(self) -> AgentResponse:
        """Show analytics"""
        patterns = self.db.get_task_patterns(self.user_data['id'])
        goals = self.db.get_goals(self.user_data['id'])
        
        message = f"""
📈 Analytics Summary:

📋 Tasks tracked: {patterns.get('total', 0)}
✅ Completion rate: {patterns.get('completion_rate', 0):.0f}%

{"🔴" if patterns.get('skipped') else "✅"} Skipped tasks: {len(patterns.get('skipped', []))}
{"🟡" if patterns.get('postponed') else "✅"} Postponed tasks: {len(patterns.get('postponed', []))}

🎯 Active goals: {len([g for g in goals if g.get('status') == 'active'])}
🏆 Completed goals: {len([g for g in goals if g.get('status') == 'completed'])}
        """
        
        return AgentResponse(
            intent=Intent.SHOW_ANALYTICS,
            message=message.strip()
        )
    
    # ==========================================
    # GENERAL HANDLER
    # ==========================================
    
    def handle_general_chat(self, user_input: str) -> AgentResponse:
        """Handle general conversation"""
        prompt = f"""
        User says: "{user_input}"
        
        Respond as a helpful scheduling assistant.
        Be friendly, concise, and ask clarifying questions if needed.
        """
        
        response = self.deepseek.generate(prompt)
        
        return AgentResponse(
            intent=Intent.GENERAL_CHAT,
            message=response
        )
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def format_schedule(self, schedule: Schedule) -> str:
        """Format schedule for display"""
        if not schedule or not schedule.tasks:
            return "No tasks scheduled."
        
        lines = []
        now = datetime.now().strftime('%H:%M')
        
        for task in schedule.tasks:
            status_icon = {
                'pending': '⚪',
                'in_progress': '🔴',
                'completed': '✅',
                'skipped': '❌',
                'postponed': '⏰'
            }.get(task.status, '⚪')
            
            # Check if task is now
            is_now = task.start_time <= now <= task.end_time
            if is_now and task.status == 'pending':
                status_icon = '🔴'
                task.status = 'in_progress'
            
            lines.append(f"{status_icon} {task.start_time}-{task.end_time} {task.name}")
            
            if is_now and task.status == 'in_progress':
                lines[-1] = f"🔴 NOW: {task.start_time}-{task.end_time} {task.name}"
        
        return "\n".join(lines)
    
    def progress_bar(self, progress: float, width: int = 20) -> str:
        """Create ASCII progress bar"""
        filled = int(width * progress / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}]"