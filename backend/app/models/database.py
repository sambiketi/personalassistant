"""
SQLite data-access layer for Focus Agent.

Design notes for this refactor:
- Lightweight migration system driven by `PRAGMA user_version` so the schema
  can evolve without wiping data. Add new steps to `_MIGRATIONS`.
- CHECK constraints enforce invariants at the DB layer (progress 0-100, etc.)
  as a second line of defense behind Pydantic validation in the routes.
- Streak calculation now walks actual calendar dates (not just "last 30 rows"),
  so a habit logged sporadically over months still gets a correct streak
  instead of silently truncating at 30 log rows.
"""
import sqlite3
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised for any unexpected DB failure; routes translate this to HTTP 500."""
    pass


# ==========================================
# MIGRATIONS
# ==========================================
# Each entry is (target_version, sql_or_callable). Applied in order, once,
# tracked via PRAGMA user_version. Never edit a past migration - append new ones.

def _migration_v1(conn: sqlite3.Connection):
    conn.executescript("""
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
        );

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
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            priority INTEGER DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
            status TEXT DEFAULT 'active' CHECK(status IN ('active','completed','archived')),
            target_date TEXT,
            progress REAL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            frequency TEXT DEFAULT 'daily' CHECK(frequency IN ('daily','weekly')),
            target_count INTEGER DEFAULT 1 CHECK(target_count > 0),
            current_streak INTEGER DEFAULT 0 CHECK(current_streak >= 0),
            longest_streak INTEGER DEFAULT 0 CHECK(longest_streak >= 0),
            status TEXT DEFAULT 'active' CHECK(status IN ('active','paused','archived')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER DEFAULT 1 CHECK(completed IN (0,1)),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
            UNIQUE(habit_id, date)
        );

        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            scheduled_time TEXT,
            actual_time TEXT,
            status TEXT CHECK(status IN ('pending','in_progress','completed','skipped','postponed')),
            duration INTEGER CHECK(duration IS NULL OR duration >= 0),
            date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_habit_logs_habit_date ON habit_logs(habit_id, date);
        CREATE INDEX IF NOT EXISTS idx_task_history_user_date ON task_history(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_schedules_user_date ON schedules(user_id, date);
    """)


_MIGRATIONS = [
    (1, _migration_v1),
    # (2, _migration_v2), append future migrations here
]

CURRENT_SCHEMA_VERSION = _MIGRATIONS[-1][0]


class Database:
    def __init__(self, db_path: str = "focus_agent.db"):
        self.db_path = db_path
        self._migrate()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _migrate(self):
        """Apply any migrations not yet applied, tracked via PRAGMA user_version."""
        with self.get_connection() as conn:
            current = conn.execute("PRAGMA user_version").fetchone()[0]
            for version, step in _MIGRATIONS:
                if current < version:
                    logger.info(f"Applying DB migration -> v{version}")
                    step(conn)
                    conn.execute(f"PRAGMA user_version = {version}")
                    conn.commit()
                    current = version
            logger.info(f"✅ Database ready (schema v{current})")

    # ==========================================
    # USER METHODS
    # ==========================================

    def get_or_create_user(self, user_id: str) -> Dict:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                if user:
                    return dict(user)
                cursor.execute(
                    "INSERT INTO users (user_id, created_at, updated_at) "
                    "VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                    (user_id,),
                )
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                return dict(cursor.fetchone())
        except sqlite3.Error as e:
            raise DatabaseError(f"get_or_create_user failed: {e}") from e

    def save_api_key(self, user_id: str, api_key: str):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE users SET api_key = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (api_key, user_id),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"save_api_key failed: {e}") from e

    def get_api_key(self, user_id: str) -> Optional[str]:
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT api_key FROM users WHERE user_id = ?", (user_id,)
                ).fetchone()
                return row["api_key"] if row else None
        except sqlite3.Error as e:
            raise DatabaseError(f"get_api_key failed: {e}") from e

    # ==========================================
    # SCHEDULE METHODS
    # ==========================================

    def save_schedule(self, user_id: int, date_str: str, schedule_data: Dict) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                existing = cursor.execute(
                    "SELECT id FROM schedules WHERE user_id = ? AND date = ?",
                    (user_id, date_str),
                ).fetchone()
                if existing:
                    cursor.execute(
                        "UPDATE schedules SET schedule_data = ?, version = version + 1, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (json.dumps(schedule_data), existing["id"]),
                    )
                    conn.commit()
                    return existing["id"]
                cursor.execute(
                    "INSERT INTO schedules (user_id, date, schedule_data) VALUES (?, ?, ?)",
                    (user_id, date_str, json.dumps(schedule_data)),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseError(f"save_schedule failed: {e}") from e

    def add_task_to_schedule(self, user_id: int, date_str: str, task: Dict) -> Dict:
        """Merge a single task into the day's schedule instead of overwriting it."""
        try:
            existing = self.get_schedule(user_id, date_str) or {"tasks": []}
            existing.setdefault("tasks", []).append(task)
            self.save_schedule(user_id, date_str, existing)
            return existing
        except sqlite3.Error as e:
            raise DatabaseError(f"add_task_to_schedule failed: {e}") from e

    def get_schedule(self, user_id: int, date_str: str) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT schedule_data FROM schedules "
                    "WHERE user_id = ? AND date = ? AND is_active = 1 "
                    "ORDER BY version DESC LIMIT 1",
                    (user_id, date_str),
                ).fetchone()
                return json.loads(row["schedule_data"]) if row else None
        except sqlite3.Error as e:
            raise DatabaseError(f"get_schedule failed: {e}") from e

    # ==========================================
    # GOAL METHODS
    # ==========================================

    def create_goal(self, user_id: int, data: Dict) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO goals (user_id, title, description, category, priority, "
                    "status, target_date, progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        data.get("title"),
                        data.get("description"),
                        data.get("category"),
                        data.get("priority", 3),
                        data.get("status", "active"),
                        data.get("target_date"),
                        data.get("progress", 0),
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            raise DatabaseError(f"Invalid goal data: {e}") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"create_goal failed: {e}") from e

    def get_goals(self, user_id: int, status: Optional[str] = None) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM goals WHERE user_id = ? AND status = ? "
                        "ORDER BY priority DESC, created_at DESC",
                        (user_id, status),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM goals WHERE user_id = ? ORDER BY priority DESC, created_at DESC",
                        (user_id,),
                    ).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise DatabaseError(f"get_goals failed: {e}") from e

    def update_goal_progress(self, goal_id: int, progress: float):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE goals SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (progress, goal_id),
                )
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise DatabaseError(f"Invalid progress value: {e}") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"update_goal_progress failed: {e}") from e

    # ==========================================
    # HABIT METHODS
    # ==========================================

    def create_habit(self, user_id: int, data: Dict) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO habits (user_id, name, description, frequency, target_count) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        user_id,
                        data.get("name"),
                        data.get("description"),
                        data.get("frequency", "daily"),
                        data.get("target_count", 1),
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            raise DatabaseError(f"Invalid habit data: {e}") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"create_habit failed: {e}") from e

    def get_habits(self, user_id: int, status: str = "active") -> List[Dict]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM habits WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                    (user_id, status),
                ).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise DatabaseError(f"get_habits failed: {e}") from e

    def log_habit(self, habit_id: int, date_str: str, completed: bool = True, notes: str = None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                existing = cursor.execute(
                    "SELECT id FROM habit_logs WHERE habit_id = ? AND date = ?",
                    (habit_id, date_str),
                ).fetchone()
                if existing:
                    cursor.execute(
                        "UPDATE habit_logs SET completed = ?, notes = ? WHERE id = ?",
                        (1 if completed else 0, notes, existing["id"]),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO habit_logs (habit_id, date, completed, notes) VALUES (?, ?, ?, ?)",
                        (habit_id, date_str, 1 if completed else 0, notes),
                    )
                conn.commit()
            self._recalculate_streak(habit_id)
        except sqlite3.Error as e:
            raise DatabaseError(f"log_habit failed: {e}") from e

    def _recalculate_streak(self, habit_id: int):
        """
        Walk backwards day-by-day from today (calendar-aware, unbounded by row count)
        so streaks stay correct even with months of history or gaps in logging.
        """
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT date, completed FROM habit_logs WHERE habit_id = ? ORDER BY date DESC",
                    (habit_id,),
                ).fetchall()
                log_by_date = {r["date"]: bool(r["completed"]) for r in rows}

                if not log_by_date:
                    return

                # Current streak: consecutive completed days ending today or yesterday
                # (yesterday allowed so today's not-yet-logged day doesn't zero the streak)
                current_streak = 0
                cursor_date = date.today()
                # if today has no log yet, start checking from yesterday
                if cursor_date.isoformat() not in log_by_date:
                    cursor_date -= timedelta(days=1)
                while True:
                    key = cursor_date.isoformat()
                    if log_by_date.get(key) is True:
                        current_streak += 1
                        cursor_date -= timedelta(days=1)
                    else:
                        break

                # Longest streak: scan full history for the longest consecutive run
                sorted_dates = sorted(
                    (date.fromisoformat(d) for d, done in log_by_date.items() if done)
                )
                longest = running = 0
                prev = None
                for d in sorted_dates:
                    if prev is not None and (d - prev).days == 1:
                        running += 1
                    else:
                        running = 1
                    longest = max(longest, running)
                    prev = d

                conn.execute(
                    "UPDATE habits SET current_streak = ?, longest_streak = MAX(longest_streak, ?), "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (current_streak, longest, habit_id),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"_recalculate_streak failed: {e}") from e

    # ==========================================
    # TASK HISTORY METHODS
    # ==========================================

    def log_task(self, user_id: int, data: Dict):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO task_history (user_id, task_name, scheduled_time, actual_time, "
                    "status, duration, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        data.get("task_name"),
                        data.get("scheduled_time"),
                        data.get("actual_time"),
                        data.get("status"),
                        data.get("duration"),
                        data.get("date"),
                        data.get("notes"),
                    ),
                )
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise DatabaseError(f"Invalid task log data: {e}") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"log_task failed: {e}") from e

    def get_task_patterns(self, user_id: int, days: int = 30) -> Dict:
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM task_history WHERE user_id = ? AND date >= date('now', ?) "
                    "ORDER BY created_at DESC",
                    (user_id, f"-{days} days"),
                ).fetchall()
                tasks = [dict(r) for r in rows]

            patterns = {
                "total": len(tasks),
                "skipped": [],
                "postponed": [],
                "completion_rate": 0,
                "avg_duration_minutes": 0,
            }
            if tasks:
                completed = [t for t in tasks if t.get("status") == "completed"]
                patterns["completion_rate"] = round((len(completed) / len(tasks)) * 100, 1)

                durations = [t["duration"] for t in tasks if t.get("duration")]
                patterns["avg_duration_minutes"] = (
                    round(sum(durations) / len(durations), 1) if durations else 0
                )

                skipped_count, postponed_count = {}, {}
                for t in tasks:
                    if t.get("status") == "skipped":
                        skipped_count[t["task_name"]] = skipped_count.get(t["task_name"], 0) + 1
                    elif t.get("status") == "postponed":
                        postponed_count[t["task_name"]] = postponed_count.get(t["task_name"], 0) + 1

                patterns["skipped"] = sorted(skipped_count.items(), key=lambda x: x[1], reverse=True)[:5]
                patterns["postponed"] = sorted(postponed_count.items(), key=lambda x: x[1], reverse=True)[:5]

            return patterns
        except sqlite3.Error as e:
            raise DatabaseError(f"get_task_patterns failed: {e}") from e

    def get_progress_analytics(self, user_id: int, days: int = 30) -> Dict:
        """Extended analytics: task patterns + habit streaks, all in one call."""
        patterns = self.get_task_patterns(user_id, days)
        habits = self.get_habits(user_id, status="active")
        habit_streaks = [
            {"name": h["name"], "current_streak": h["current_streak"], "longest_streak": h["longest_streak"]}
            for h in habits
        ]
        return {**patterns, "habit_streaks": habit_streaks}
