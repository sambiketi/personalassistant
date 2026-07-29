done learned and articulates the next steps
🎯 Focus Agent - Complete Project Documentation
📋 Executive Summary
Focus Agent is an AI-powered adaptive scheduling assistant that lives on your phone as a Progressive Web App (PWA). Unlike static schedulers, it dynamically adjusts to your life—handling skipped tasks, emergencies, and learning your patterns over time. The system integrates a Vanguard Agent Brain for behavioral tracking and DeepSeek LLM for intelligent scheduling and natural language understanding.

Core Philosophy
"Users are already on their phones. Why make them leave the app?"

🏗️ Architecture Overview
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FOCUS AGENT SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐         ┌─────────────────┐                          │
│  │   PWA Frontend  │  ◄──►   │  FastAPI        │                          │
│  │   (Offline)     │   API   │  Backend        │                          │
│  └─────────────────┘         └─────────────────┘                          │
│         │                           │                                      │
│         │                           ▼                                      │
│         │              ┌─────────────────────────┐                        │
│         │              │     SQLite Database      │                        │
│         │              │  - Users                │                        │
│         │              │  - Schedules            │                        │
│         │              │  - Goals                │                        │
│         │              │  - Habits               │                        │
│         │              │  - Task History         │                        │
│         │              └─────────────────────────┘                        │
│         │                           │                                      │
│         └───────────────────────────┼──────────────────────────────────┘  │
│                                     ▼                                      │
│                    ┌─────────────────────────────┐                        │
│                    │   DeepSeek LLM API           │                        │
│                    │   + Vanguard Agent Brain     │                        │
│                    └─────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
🧠 Core Components
1. Vanguard Agent Brain (vanguard_brain.py)
The behavioral intelligence engine that tracks user progress and patterns:

Feature	Description	Mechanism
Win Retrieval	Starts every response with past success	get_anchor_win() pulls from wins_history
Micro-Block Escalation	Gradually increases focus blocks	+15 mins after every 3 wins (up to 240 mins)
50% Floor Rule	Reduces chores after a skip	Applies after skipped blocks to preserve energy
Habit Sandwich	Anchors new habits to existing ones	Suggests immediate follow-up to anchors
Sabotage Detection	Identifies recurring blockers	≥4 occurrences triggers structural intervention
2. Robust JSON Parser (robust_parser.py)
Handles malformed AI responses with multiple fallback strategies:

Extracts JSON from markdown, text, or code blocks

Cleans common JSON issues (trailing commas, single quotes)

Fixes truncated JSON (adds missing brackets)

Salvages partial JSON data

Attempts 5+ parsing strategies before failing

3. Agent Engine (agent.py)
Orchestrates intent detection and routing:

Intent	Handler	Description
CREATE_SCHEDULE	handle_create_schedule()	Sends to DeepSeek for scheduling
LOG_VANGUARD_WIN	handle_vanguard_intent()	Logs win via Vanguard Brain
LOG_VANGUARD_SKIP	handle_vanguard_intent()	Logs skip via Vanguard Brain
SHOW_PROGRESS	handle_show_progress()	Returns Vanguard Brain progress report
GENERAL_CHAT	handle_general_chat()	Sends to DeepSeek for conversation
4. Database Layer (database.py)
SQLite-based storage with tables for:

Users (profiles, API keys, preferences)

Schedules (daily tasks with status)

Goals (title, progress, milestones)

Habits (streaks, frequency)

Task History (learning patterns)

🚀 What We've Built
Completed Features
✅ Backend API (FastAPI)

RESTful endpoints for agent, schedules, goals, habits

CORS enabled for frontend communication

Health and status endpoints

✅ Frontend PWA

Installable on mobile devices

Real-time chat interface

Dashboard with task count, goals, habits

Offline support via service worker

✅ Vanguard Agent Brain

Win/skip tracking with streaks

Progressive block escalation

Sabotage pattern detection (≥4 occurrences)

50% Floor Rule for skip recovery

✅ DeepSeek Integration

LLM-powered schedule generation

Natural language understanding

Mock mode for testing without API key

✅ Robust JSON Parsing

Handles malformed AI responses

Multiple fallback strategies

Partial data recovery

✅ Database Integration

SQLite for local storage

User profiles with API keys

Schedule persistence

Goal and habit tracking

📊 Current Status
Working Endpoints
Endpoint	Method	Status
/api/agent/process	POST	✅ Working
/api/schedule/{user_id}	GET	✅ Working
/api/schedule	POST	✅ Working
/api/goals/{user_id}	GET	✅ Working
/api/goal	POST	✅ Working
/api/habits/{user_id}	GET	✅ Working
/api/habit	POST	✅ Working
/api/habit/{id}/log	POST	✅ Working
/api/progress/{user_id}	GET	✅ Working
/api/analytics/{user_id}	GET	✅ Working
/api/user/apikey	POST	✅ Working
/api/user/apikey/status	GET	✅ Working
Known Issues
⚠️ API Key Propagation - Vanguard Brain needs explicit API key loading from database
⚠️ JSON Parser Edge Cases - Some DeepSeek responses still fail parsing
⚠️ Frontend Dashboard - Stats don't auto-update after agent responses
⚠️ Error Handling - Some errors return generic messages instead of specific feedback

💡 Key Learnings
Technical Insights
SQLite is perfect for mobile - No server needed, works offline, easy sync

PWA is the future - Install on any device without app store

Robust parsing is essential - LLMs don't always return perfect JSON

Agent should be dynamic - Static schedules are useless

API key propagation - Must be passed through the entire chain

Architectural Decisions
Decision	Rationale
SQLite over PostgreSQL	Mobile-first, offline support, no server required
PWA over Native	Single codebase, instant updates, no app store friction
Vanguard Brain + LLM	Behavioral tracking + intelligence = better adaptation
Robust Parser	LLMs are unpredictable; need multiple fallback strategies
What We'd Do Differently
API Key Management - Design a cleaner propagation path from the start

Error Handling - More granular error types for better debugging

Testing - More comprehensive unit tests for edge cases

Logging - Structured logging for easier debugging

📁 Project Structure
text
schedulerapp/
└── focus-agent/
    ├── backend/
    │   ├── app/
    │   │   ├── api/
    │   │   │   └── routes.py          # FastAPI endpoints
    │   │   ├── core/
    │   │   │   ├── agent.py           # Main agent logic
    │   │   │   ├── vanguard_brain.py  # Behavioral engine
    │   │   │   ├── robust_parser.py   # JSON parsing
    │   │   │   └── scheduler.py       # Scheduling logic
    │   │   ├── models/
    │   │   │   └── database.py        # SQLite operations
    │   │   └── services/
    │   │       └── deepseek.py        # LLM integration
    │   ├── main.py                    # FastAPI entry
    │   ├── run_server.py              # Server launcher
    │   └── requirements.txt           # Python deps
    ├── frontend/
    │   ├── index.html                 # Main dashboard
    │   ├── css/style.css              # Styles
    │   ├── js/app.js                  # Frontend logic
    │   ├── manifest.json              # PWA config
    │   └── sw.js                      # Service worker
    └── README.md                      # This file
🔧 Quick Commands
Start the Application
powershell
# Backend
cd C:\Users\Administrator\Desktop\schedulerapp\focus-agent\backend
python run_server.py

# Frontend (new terminal)
cd C:\Users\Administrator\Desktop\schedulerapp\focus-agent\frontend
python -m http.server 3000
Test API Endpoints
powershell
# Health check
curl http://localhost:8000/health

# API status
curl http://localhost:8000/api/status

# Check API key status
curl http://localhost:8000/api/user/apikey/status/demo_user

# Save API key
curl -X POST http://localhost:8000/api/user/apikey -H "Content-Type: application/json" -d '{"user_id":"demo_user","api_key":"YOUR_KEY"}'

# Chat with agent
curl -X POST http://localhost:8000/api/agent/process -H "Content-Type: application/json" -d '{"message":"Plan my day","user_id":"demo_user"}'
Database Commands
powershell
# Inspect database
cd C:\Users\Administrator\Desktop\schedulerapp\focus-agent\backend
sqlite3 focus_agent.db
.tables
SELECT * FROM users;
.quit
📝 Next Steps
Phase 1: Fix Core Issues (Immediate)
□ Fix API Key Propagation - Ensure Vanguard Brain receives API key from database
□ Improve JSON Parser - Handle truncated responses better
□ Auto-refresh Dashboard - Update stats after agent responses
□ Better Error Messages - Specific feedback instead of generic errors
Phase 2: Enhance Agent Intelligence (Week 1)
□ Context Awareness - Agent remembers previous conversations
□ Pattern Learning - Improve sabotage detection with ML
□ Proactive Suggestions - Agent offers help before being asked
□ Multi-day Planning - Schedule across multiple days
Phase 3: Feature Expansion (Week 2)
□ Voice Input - Speech-to-text for quick updates
□ Calendar Integration - Google Calendar, Outlook sync
□ Push Notifications - Reminders and alerts
□ Progress Analytics - Charts and visual insights
Phase 4: Production Readiness (Week 3)
□ Authentication - Secure user accounts
□ Cloud Sync - Backup user data across devices
□ App Store Deployment - iOS/Android via PWA
□ Performance Optimization - Faster load times
Phase 5: Advanced Features (Future)
□ Team Scheduling - Collaborative planning
□ Habit Coaching - AI-powered habit formation
□ Focus Timers - Pomodoro integration
□ Social Accountability - Share goals with friends
🐛 Known Issues & Fixes
Issue 1: API Key Not Loading
Symptoms: ⚠️ No valid API key - using mock response

Fix: Add API key loading in agent.py:

python
# In process() method
api_key = self.user_data.get('api_key')
if api_key and self.deepseek:
    self.deepseek.update_api_key(api_key)
Issue 2: JSON Parsing Fails
Symptoms: Parser warning: JSON parsing failed

Fix: Update robust_parser.py to handle truncated JSON:

python
@staticmethod
def fix_truncated_json(json_str: str) -> str:
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    if open_braces > close_braces:
        json_str += '}' * (open_braces - close_braces)
    return json_str
Issue 3: Dashboard Not Auto-Updating
Symptoms: Stats don't update after chat

Fix: Call loadDashboardData() after agent response:

javascript
// In handleSend() after response
if (response.schedule) {
    loadDashboardData();
}
🤝 Contributing
Development Environment
Clone the repository

Install Python dependencies: pip install -r requirements.txt

Start backend: python run_server.py

Start frontend: python -m http.server 3000

Code Standards
Python: Follow PEP 8

JavaScript: Use ES6+

Documentation: Add docstrings to all functions

Testing: Write tests for new features

📄 License
MIT License - See LICENSE file for details.

🙏 Acknowledgments
DeepSeek for the LLM API

FastAPI for the backend framework

SQLite for the database

PWA for mobile-first architecture

📞 Contact
For questions, issues, or contributions:

GitHub: [Your Repository URL]

Email: [Your Email]

Last Updated: July 29, 2026
Version: 0.2.0
Status: 🟢 Development - Core Features Complete

🎯 Key Takeaway
"Consistency beats intensity. Show up every day, even for 5 minutes."

The Focus Agent is designed to help you build consistent habits, adapt to life's interruptions, and make steady progress toward your goals—all from your phone, without leaving the app.

