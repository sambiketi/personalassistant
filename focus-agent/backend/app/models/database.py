import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import os

# ============================================
# DATABASE MANAGER
# ============================================

class Database:
    def __init__(self, db_path="focus_agent.db"):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize all tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # ==========================================
            # USERS TABLE
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    api_key TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    wake_time TEXT DEFAULT '06:00',
                    sleep_time TEXT DEFAULT '22:00',
                    preferred_work_hours TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ==========================================
            # SCHEDULES TABLE
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,  -- YYYY-MM-DD
                    schedule_data TEXT NOT NULL,  -- JSON
                    version INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # ==========================================
            # GOALS TABLE
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'active',
                    target_date TEXT,  -- YYYY-MM-DD
                    progress REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # ==========================================
            # MILESTONES TABLE
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    "order" INTEGER DEFAULT 0,
                    is_completed INTEGER DEFAULT 0,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)
            
            # ==========================================
            # HABITS TABLE
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    frequency TEXT DEFAULT 'daily',
                    target_count INTEGER DEFAULT 1,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # ==========================================
            # HABIT LOGS TABLE
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    date TEXT NOT NULL,  -- YYYY-MM-DD
                    completed INTEGER DEFAULT 1,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
                    UNIQUE(habit_id, date)
                )
            """)
            
            # ==========================================
            # TASK HISTORY TABLE (for agent learning)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_name TEXT NOT NULL,
                    scheduled_time TEXT,  -- HH:MM
                    actual_time TEXT,  -- HH:MM (when actually done)
                    status TEXT,  -- completed, skipped, postponed
                    duration INTEGER,  -- minutes
                    date TEXT NOT NULL,  -- YYYY-MM-DD
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # ==========================================
            # ANALYTICS TABLE (cached stats)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,  -- YYYY-MM-DD
                    stats TEXT NOT NULL,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_user_date ON schedules(user_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_user_status ON goals(user_id, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_habits_user_status ON habits(user_id, status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_history_user_date ON task_history(user_id, date)")
            
            conn.commit()
            print("✅ Database initialized")

    # ==========================================
    # USER METHODS
    # ==========================================
    
    def get_or_create_user(self, user_id: str) -> Dict:
        """Get user or create if doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user:
                return dict(user)
            
            # Create new user
            cursor.execute("""
                INSERT INTO users (user_id, created_at, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id,))
            conn.commit()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(cursor.fetchone())
    
    def update_user(self, user_id: str, data: Dict):
        """Update user settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            fields = []
            values = []
            for key, value in data.items():
                if key != 'id' and key != 'user_id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
            cursor.execute(query, values)
            conn.commit()
    
    def save_api_key(self, user_id: str, api_key: str):
        """Save DeepSeek API key"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET api_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (api_key, user_id))
            conn.commit()
    
    # ==========================================
    # SCHEDULE METHODS
    # ==========================================
    
    def save_schedule(self, user_id: int, date: str, schedule_data: Dict) -> int:
        """Save or update schedule for a date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if schedule exists
            cursor.execute("""
                SELECT id FROM schedules 
                WHERE user_id = ? AND date = ? AND is_active = 1
            """, (user_id, date))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE schedules 
                    SET schedule_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(schedule_data), existing['id']))
                conn.commit()
                return existing['id']
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO schedules (user_id, date, schedule_data)
                    VALUES (?, ?, ?)
                """, (user_id, date, json.dumps(schedule_data)))
                conn.commit()
                return cursor.lastrowid
    
    def get_schedule(self, user_id: int, date: str) -> Optional[Dict]:
        """Get schedule for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM schedules 
                WHERE user_id = ? AND date = ? AND is_active = 1
                ORDER BY version DESC LIMIT 1
            """, (user_id, date))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result['schedule_data'] = json.loads(result['schedule_data'])
                return result
            return None
    
    def get_week_schedules(self, user_id: int, start_date: str) -> List[Dict]:
        """Get all schedules for a week"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate end date (7 days later)
            cursor.execute("""
                SELECT * FROM schedules 
                WHERE user_id = ? AND date >= ? AND date < date(?, '+7 days')
                AND is_active = 1
                ORDER BY date ASC
            """, (user_id, start_date, start_date))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result['schedule_data'] = json.loads(result['schedule_data'])
                results.append(result)
            return results
    
    # ==========================================
    # GOAL METHODS
    # ==========================================
    
    def create_goal(self, user_id: int, data: Dict) -> int:
        """Create a new goal"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO goals (
                    user_id, title, description, category, priority, 
                    status, target_date, progress
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('title'),
                data.get('description'),
                data.get('category'),
                data.get('priority', 3),
                data.get('status', 'active'),
                data.get('target_date'),
                data.get('progress', 0)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_goals(self, user_id: int, status: str = None) -> List[Dict]:
        """Get all goals for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM goals WHERE user_id = ?"
            params = [user_id]
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY priority DESC, created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_goal_progress(self, goal_id: int, progress: float):
        """Update goal progress"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals 
                SET progress = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (progress, goal_id))
            conn.commit()
    
    def complete_goal(self, goal_id: int):
        """Mark goal as completed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals 
                SET status = 'completed', 
                    progress = 100,
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (goal_id,))
            conn.commit()
    
    def add_milestone(self, goal_id: int, data: Dict) -> int:
        """Add a milestone to a goal"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO milestones (goal_id, title, description, "order")
                VALUES (?, ?, ?, ?)
            """, (
                goal_id,
                data.get('title'),
                data.get('description'),
                data.get('order', 0)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def complete_milestone(self, milestone_id: int):
        """Mark milestone as completed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE milestones 
                SET is_completed = 1, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (milestone_id,))
            conn.commit()
    
    # ==========================================
    # HABIT METHODS
    # ==========================================
    
    def create_habit(self, user_id: int, data: Dict) -> int:
        """Create a new habit"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO habits (
                    user_id, name, description, frequency, target_count
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('name'),
                data.get('description'),
                data.get('frequency', 'daily'),
                data.get('target_count', 1)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_habits(self, user_id: int, status: str = 'active') -> List[Dict]:
        """Get habits for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM habits 
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (user_id, status))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def log_habit(self, habit_id: int, date: str, completed: bool = True, notes: str = None):
        """Log habit completion for a day"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if already logged
            cursor.execute("""
                SELECT id FROM habit_logs 
                WHERE habit_id = ? AND date = ?
            """, (habit_id, date))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE habit_logs 
                    SET completed = ?, notes = ?
                    WHERE id = ?
                """, (1 if completed else 0, notes, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO habit_logs (habit_id, date, completed, notes)
                    VALUES (?, ?, ?, ?)
                """, (habit_id, date, 1 if completed else 0, notes))
            
            conn.commit()
            
            # Update streak
            self._update_habit_streak(habit_id)
    
    def _update_habit_streak(self, habit_id: int):
        """Update habit streak based on logs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get habit
            cursor.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
            habit = cursor.fetchone()
            if not habit:
                return
            
            # Get last 30 days of logs
            cursor.execute("""
                SELECT date, completed FROM habit_logs 
                WHERE habit_id = ? 
                ORDER BY date DESC 
                LIMIT 30
            """, (habit_id,))
            logs = cursor.fetchall()
            
            if not logs:
                return
            
            # Calculate streak
            streak = 0
            today = datetime.now().strftime('%Y-%m-%d')
            
            for log in logs:
                if log['completed']:
                    streak += 1
                else:
                    break
            
            # Update streak
            cursor.execute("""
                UPDATE habits 
                SET current_streak = ?,
                    longest_streak = MAX(longest_streak, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (streak, streak, habit_id))
            conn.commit()
    
    # ==========================================
    # TASK HISTORY METHODS (for agent learning)
    # ==========================================
    
    def log_task(self, user_id: int, data: Dict):
        """Log task completion/skip/postpone for learning"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO task_history (
                    user_id, task_name, scheduled_time, actual_time,
                    status, duration, date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('task_name'),
                data.get('scheduled_time'),
                data.get('actual_time'),
                data.get('status'),  # completed, skipped, postponed
                data.get('duration'),
                data.get('date'),
                data.get('notes')
            ))
            conn.commit()
    
    def get_task_patterns(self, user_id: int, days: int = 30) -> Dict:
        """Get task patterns for learning"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get tasks in date range
            cursor.execute("""
                SELECT * FROM task_history 
                WHERE user_id = ? 
                AND date >= date('now', ?)
                ORDER BY date DESC, created_at DESC
            """, (user_id, f'-{days} days'))
            
            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]
            
            # Analyze patterns
            patterns = {
                'skipped_tasks': [],
                'postponed_tasks': [],
                'missed_tasks': [],
                'completion_rate': 0,
                'total_tasks': len(tasks)
            }
            
            if tasks:
                completed = sum(1 for t in tasks if t['status'] == 'completed')
                patterns['completion_rate'] = (completed / len(tasks)) * 100
                
                # Find patterns
                skipped = {}
                postponed = {}
                
                for task in tasks:
                    if task['status'] == 'skipped':
                        skipped[task['task_name']] = skipped.get(task['task_name'], 0) + 1
                    elif task['status'] == 'postponed':
                        postponed[task['task_name']] = postponed.get(task['task_name'], 0) + 1
                
                # Sort by frequency
                patterns['skipped_tasks'] = sorted(skipped.items(), key=lambda x: x[1], reverse=True)[:5]
                patterns['postponed_tasks'] = sorted(postponed.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return patterns
    
    # ==========================================
    # ANALYTICS METHODS
    # ==========================================
    
    def save_analytics(self, user_id: int, date: str, stats: Dict):
        """Cache daily analytics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO analytics (user_id, date, stats)
                VALUES (?, ?, ?)
            """, (user_id, date, json.dumps(stats)))
            conn.commit()
    
    def get_analytics(self, user_id: int, date: str) -> Optional[Dict]:
        """Get cached analytics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analytics 
                WHERE user_id = ? AND date = ?
            """, (user_id, date))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result['stats'] = json.loads(result['stats'])
                return result
            return None
    
    def get_weekly_analytics(self, user_id: int, start_date: str) -> List[Dict]:
        """Get weekly analytics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM analytics 
                WHERE user_id = ? 
                AND date >= ? 
                AND date < date(?, '+7 days')
                ORDER BY date ASC
            """, (user_id, start_date, start_date))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result['stats'] = json.loads(result['stats'])
                results.append(result)
            return results