import sqlite3
import json

conn = sqlite3.connect('focus_agent.db')
cursor = conn.cursor()

print("=" * 60)
print("DATABASE INSPECTION")
print("=" * 60)

# Check users
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()
print(f"\nUsers: {len(users)}")
for user in users:
    print(f"  ID: {user[0]}, User: {user[1]}, API Key: {user[2] or 'Not set'}")

# Check schedules
cursor.execute("SELECT user_id, date, schedule_data FROM schedules")
schedules = cursor.fetchall()
print(f"\nSchedules: {len(schedules)}")
for sched in schedules:
    print(f"  User: {sched[0]}, Date: {sched[1]}")
    try:
        data = json.loads(sched[2])
        if data and "tasks" in data:
            print(f"    Tasks: {len(data['tasks'])}")
            for task in data["tasks"][:3]:
                print(f"      - {task.get('start_time', '')} {task.get('name', '')}")
    except:
        pass

# Check goals
cursor.execute("SELECT title, progress, status FROM goals")
goals = cursor.fetchall()
print(f"\nGoals: {len(goals)}")
for goal in goals:
    print(f"  {goal[0]}: {goal[1]}% ({goal[2]})")

# Check habits
cursor.execute("SELECT name, current_streak FROM habits")
habits = cursor.fetchall()
print(f"\nHabits: {len(habits)}")
for habit in habits:
    print(f"  {habit[0]}: {habit[1]} day streak")

conn.close()
print("\n" + "=" * 60)
