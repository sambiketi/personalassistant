import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str = "focus_agent.db"):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    api_key TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    wake_time TEXT DEFAULT '06:00',
                    sleep_time TEXT DEFAULT '22:00',
                    preferred_work_hours TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Schedules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    schedule_data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, date)
                )
            """)
            
            # Goals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'active',
                    target_date TEXT,
                    progress REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Habits table
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
            
            # Habit logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    completed INTEGER DEFAULT 1,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
                    UNIQUE(habit_id, date)
                )
            """)
            
            # Task history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_name TEXT NOT NULL,
                    scheduled_time TEXT,
                    actual_time TEXT,
                    status TEXT,
                    duration INTEGER,
                    date TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            print("✅ Database initialized")
    
    # ==========================================
    # USER METHODS
    # ==========================================
    
    def get_or_create_user(self, user_id: str) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            if user:
                return dict(user)
            cursor.execute("""
                INSERT INTO users (user_id, created_at, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id,))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(cursor.fetchone())
    
    def save_api_key(self, user_id: str, api_key: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET api_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (api_key, user_id))
            conn.commit()
    
    def get_api_key(self, user_id: str) -> Optional[str]:
        """Get user's API key"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row['api_key'] if row else None
    
    # ==========================================
    # SCHEDULE METHODS
    # ==========================================
    
    def save_schedule(self, user_id: int, date: str, schedule_data: Dict) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM schedules WHERE user_id = ? AND date = ?
            """, (user_id, date))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE schedules 
                    SET schedule_data = ?, version = version + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(schedule_data), existing['id']))
                conn.commit()
                return existing['id']
            else:
                cursor.execute("""
                    INSERT INTO schedules (user_id, date, schedule_data)
                    VALUES (?, ?, ?)
                """, (user_id, date, json.dumps(schedule_data)))
                conn.commit()
                return cursor.lastrowid
    
    def get_schedule(self, user_id: int, date: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT schedule_data FROM schedules 
                WHERE user_id = ? AND date = ? AND is_active = 1
                ORDER BY version DESC LIMIT 1
            """, (user_id, date))
            row = cursor.fetchone()
            if row:
                return json.loads(row['schedule_data'])
            return None
    
    # ==========================================
    # GOAL METHODS
    # ==========================================
    
    def create_goal(self, user_id: int, data: Dict) -> int:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("""
                    SELECT * FROM goals WHERE user_id = ? AND status = ?
                    ORDER BY priority DESC, created_at DESC
                """, (user_id, status))
            else:
                cursor.execute("""
                    SELECT * FROM goals WHERE user_id = ?
                    ORDER BY priority DESC, created_at DESC
                """, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_goal_progress(self, goal_id: int, progress: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals SET progress = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (progress, goal_id))
            conn.commit()
    
    def complete_goal(self, goal_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals 
                SET status = 'completed', progress = 100, 
                    completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (goal_id,))
            conn.commit()
    
    # ==========================================
    # HABIT METHODS
    # ==========================================
    
    def create_habit(self, user_id: int, data: Dict) -> int:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM habits WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (user_id, status))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def log_habit(self, habit_id: int, date: str, completed: bool = True, notes: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM habit_logs WHERE habit_id = ? AND date = ?
            """, (habit_id, date))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE habit_logs SET completed = ?, notes = ?
                    WHERE id = ?
                """, (1 if completed else 0, notes, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO habit_logs (habit_id, date, completed, notes)
                    VALUES (?, ?, ?, ?)
                """, (habit_id, date, 1 if completed else 0, notes))
            
            conn.commit()
            self._update_streak(habit_id)
    
    def _update_streak(self, habit_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, completed FROM habit_logs 
                WHERE habit_id = ? ORDER BY date DESC LIMIT 30
            """, (habit_id,))
            logs = cursor.fetchall()
            if not logs:
                return
            
            streak = 0
            for log in logs:
                if log['completed']:
                    streak += 1
                else:
                    break
            
            cursor.execute("""
                UPDATE habits 
                SET current_streak = ?, longest_streak = MAX(longest_streak, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (streak, streak, habit_id))
            conn.commit()
    
    # ==========================================
    # TASK HISTORY METHODS
    # ==========================================
    
    def log_task(self, user_id: int, data: Dict):
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
                data.get('status'),
                data.get('duration'),
                data.get('date'),
                data.get('notes')
            ))
            conn.commit()
    
    def get_task_patterns(self, user_id: int, days: int = 30) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM task_history 
                WHERE user_id = ? AND date >= date('now', ?)
                ORDER BY created_at DESC
            """, (user_id, f'-{days} days'))
            
            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]
            
            patterns = {
                'total': len(tasks),
                'skipped': [],
                'postponed': [],
                'completion_rate': 0
            }
            
            if tasks:
                completed = sum(1 for t in tasks if t.get('status') == 'completed')
                patterns['completion_rate'] = (completed / len(tasks)) * 100 if tasks else 0
                
                skipped_count = {}
                postponed_count = {}
                for task in tasks:
                    if task.get('status') == 'skipped':
                        skipped_count[task['task_name']] = skipped_count.get(task['task_name'], 0) + 1
                    elif task.get('status') == 'postponed':
                        postponed_count[task['task_name']] = postponed_count.get(task['task_name'], 0) + 1
                
                patterns['skipped'] = sorted(skipped_count.items(), key=lambda x: x[1], reverse=True)[:5]
                patterns['postponed'] = sorted(postponed_count.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return patterns
