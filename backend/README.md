# Focus Companion

An AI-powered dynamic daily scheduler and accountability assistant with Telegram integration.

================================================================================
PROJECT OVERVIEW
================================================================================

Focus Companion is a dynamic daily scheduler and accountability assistant that uses AI (DeepSeek) to generate personalized daily schedules and sends them via Telegram (free) with optional WhatsApp Business (paid) support. The system acts as a "Pact Observer" to help users stay accountable to their non-negotiable tasks.

================================================================================
KEY FEATURES
================================================================================

AI-Powered Scheduling - Uses DeepSeek to generate smart, personalized daily schedules
Telegram Integration - Free and instant schedule delivery via Telegram bot
Unsnoozable Tasks - Lock in non-negotiable tasks that cannot be skipped
Task Prioritization - Automatically prioritizes tasks based on user goals
Dual Communication - Supports both Telegram (free) and WhatsApp Business (paid)
PWA Ready - Installable progressive web app for mobile and desktop
Warm Design - Comforting color palette for stress-free planning

================================================================================
SYSTEM ARCHITECTURE
================================================================================

User Interface Layer
  - Telegram (FREE)
  - WhatsApp Business (PAID)
  - Web App (PWA)

Communication Layer
  - Dual Communication Pipeline
  - Platform-specific handlers

API Layer
  - FastAPI Server (Port 8000)
  - RESTful Endpoints
  - Webhook Handlers

AI Layer
  - DeepSeek API Integration
  - Schedule Generation Engine
  - Task Prioritization Logic

Data Layer
  - In-memory State Management
  - User Session Storage

================================================================================
TECHNOLOGY STACK
================================================================================

Backend
  - Python 3.10+
  - FastAPI (Web Framework)
  - DeepSeek API (AI Engine)
  - python-telegram-bot (Telegram Integration)
  - Twilio (WhatsApp Integration)
  - Uvicorn (ASGI Server)

Frontend
  - HTML5 / CSS3 / JavaScript
  - PWA (Progressive Web App)
  - Service Worker
  - Web App Manifest

Libraries & Dependencies
  - fastapi==0.104.1
  - uvicorn==0.24.0
  - python-multipart==0.0.6
  - twilio==8.10.0
  - openai==1.6.1
  - instructor==1.0.0
  - pydantic==2.5.0
  - python-dotenv==1.0.0
  - aiofiles==23.2.1
  - APScheduler==3.10.4
  - httpx==0.25.2
  - python-telegram-bot==20.7
  - requests==2.31.0

================================================================================
PROJECT STRUCTURE
================================================================================

focus-companion/
  backend/
    server.py              # FastAPI server with all endpoints
    ai_engine.py           # DeepSeek AI integration and scheduling logic
    app_state.py           # In-memory state management for user sessions
    communication.py       # Dual pipeline for Telegram and WhatsApp
    requirements.txt       # Python dependencies list
    __init__.py            # Package initialization
  
  frontend/
    index.html             # Main PWA web interface
    manifest.json          # PWA manifest for installability
    sw.js                  # Service worker for offline support
    icons/                 # PWA icons for different devices
  
  .env                      # Environment variables (API keys, config)
  .env.example             # Template for environment variables
  .gitignore               # Git ignore rules
  README.md                # This file
  LICENSE                  # MIT License
  start.ps1                # Server start script (Windows)
  start.sh                 # Server start script (Mac/Linux)
  start-frontend.ps1       # Frontend start script (Windows)
  start-frontend.sh        # Frontend start script (Mac/Linux)

================================================================================
API ENDPOINTS
================================================================================

GET /
  Description: Server status check
  Response: { "message": "Focus Companion API", "status": "running", "llm": "DeepSeek" }

GET /api/platforms/status
  Description: Check configuration status of all platforms
  Response: { "telegram": { "configured": true, "chat_id": "123" }, "whatsapp": { "configured": false } }

POST /api/schedule
  Description: Generate a schedule without sending it
  Request Body: { "prompt": "Waking up at 6am...", "unsnoozables": ["Exercise"] }
  Response: { "status": "success", "schedule": { "date_or_day": "Today", "tasks": [...] } }

POST /api/schedule/send
  Description: Generate and send schedule to specified platforms
  Request Body: { "prompt": "...", "unsnoozables": [...], "platforms": ["telegram"], "user_id": "user123" }
  Response: { "status": "success", "schedule": {...}, "sent_to": { "telegram": { "success": true } } }

POST /api/register
  Description: Register user with communication channels
  Request Body: { "user_id": "user123", "telegram_chat_id": "123", "whatsapp_number": "+1234567890" }
  Response: { "status": "success", "telegram": true, "whatsapp": true }

POST /api/initialize
  Description: Initialize user session with tasks
  Request Body: { "phone": "+1234567890", "tasks": [{"name": "Exercise", "start_time": "6:00 AM", ...}] }
  Response: { "status": "success", "message": "Session initialized" }

POST /api/whatsapp
  Description: WhatsApp webhook handler (Twilio)
  Request: Form data (From, Body)
  Response: TwiML response

================================================================================
QUICK START GUIDE
================================================================================

Prerequisites
  - Python 3.10 or higher
  - Telegram account (for bot setup)
  - DeepSeek API key (free tier available at deepseek.com)

Installation Steps

  1. Clone the repository:
     git clone https://github.com/yourusername/focus-companion.git
     cd focus-companion

  2. Create and activate virtual environment:
     python -m venv venv
     # On Windows:
     venv\Scripts\activate
     # On Mac/Linux:
     source venv/bin/activate

  3. Install dependencies:
     pip install -r backend/requirements.txt

  4. Configure environment:
     cp .env.example .env
     # Edit .env with your API keys

  5. Start the backend server:
     cd backend
     python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

  6. Start the frontend (in a new terminal):
     cd frontend
     python -m http.server 3000

  7. Open your browser:
     http://localhost:3000 (Frontend)
     http://localhost:8000 (API)

================================================================================
TELEGRAM BOT SETUP
================================================================================

Creating a Telegram Bot

  1. Open Telegram and search for @BotFather
  2. Send /newbot command
  3. Choose a name for your bot (e.g., "Focus Companion")
  4. Choose a username (must end with 'bot', e.g., "focuscompanion_bot")
  5. Copy the API token you receive
  6. Add token to .env file: TELEGRAM_BOT_TOKEN=your_token_here

Testing the Bot

  - Run: python setup_telegram_bot.py
  - Message your bot on Telegram
  - Run: python get_chat_id.py to get your chat ID
  - Run: python tg_test.py to test sending messages

Our Bot
  - Username: @P_asst_bot
  - Link: https://t.me/P_asst_bot

================================================================================
TESTING
================================================================================

Test the API
  cd backend
  python direct_test.py

Test Telegram Integration
  cd backend
  python tg_test.py

Get Your Chat ID
  cd backend
  python get_chat_id.py

Test Schedule Generation
  cd backend
  python test_api.py

Test Complete Flow
  cd backend
  python test_full_flow.py

================================================================================
COST BREAKDOWN
================================================================================

DeepSeek API
  Status: Configured
  Cost: Free (500M tokens included)
  Notes: Approximately $0.001-0.005 per schedule

Telegram Bot
  Status: Working
  Cost: FREE
  Notes: Unlimited messages, no charges

WhatsApp Business
  Status: Optional
  Cost: ~$0.005-0.015 per message
  Notes: Requires Twilio account

Hosting
  Status: Not deployed
  Cost: Free tiers available
  Options: Render, Vercel, Heroku, PythonAnywhere

Domain
  Status: Optional
  Cost: ~$10-15/year
  Notes: Only needed for production deployment

================================================================================
CURRENT STATUS (MVP Complete)
================================================================================

DeepSeek API - Operational (500M free tokens)
Telegram Bot - Operational (@P_asst_bot)
FastAPI Server - Running (Port 8000)
WhatsApp - Pending (Needs Twilio setup)
Frontend - Demo only (PWA ready)
Database - In-memory (No persistence)

================================================================================
WHAT'S WORKING
================================================================================

AI Schedule Generation
  - DeepSeek API integration working
  - Structured JSON output
  - Task prioritization
  - Unsnoozable task flags
  - Time slot calculation

Telegram Bot
  - Bot @P_asst_bot operational
  - Chat ID retrieval working
  - Message sending working
  - Schedule formatting working
  - Markdown support working

API Server
  - FastAPI backend running
  - CORS configured
  - All endpoints functional
  - Error handling implemented
  - In-memory state management

================================================================================
WHAT'S NEXT
================================================================================

Phase 2: Enhancement (In Progress)
  - 5-question onboarding flow
  - User-friendly dashboard
  - Schedule visualization
  - PWA optimization
  - WhatsApp Business integration

Phase 3: Advanced Features (Planned)
  - Pact Observer (task locking)
  - 5-minute reminder alerts
  - Daily motivational snippets
  - Progress tracking
  - Gamification (streaks, rewards)
  - Mini-goals and milestones

Phase 4: Production (Planned)
  - Deploy to Render/Vercel
  - Domain setup
  - SSL certificate
  - Production monitoring
  - User authentication
  - Subscription plans

================================================================================
KNOWN ISSUES
================================================================================

Virtual Environment
  - PowerShell execution policy may block activation
  - Workaround: Use "python -m uvicorn" directly

WhatsApp
  - Not yet configured
  - Requires Twilio account and business verification

Frontend
  - UI not yet connected to backend
  - Static demo only

Data Persistence
  - In-memory only
  - Data resets on restart
  - No database yet

================================================================================
SECURITY NOTES
================================================================================

- API keys stored in .env (not committed to git)
- No user authentication yet (add in production)
- In-memory storage only (data resets on restart)
- CORS configured for development (restrict in production)
- Tokens should be regenerated if exposed

================================================================================
LESSONS LEARNED
================================================================================

1. Telegram bot tokens must include a colon (format: 1234567890:ABCdefGHIjkl...)
2. Async/await is essential for Telegram operations
3. DeepSeek API provides excellent schedule generation
4. In-memory storage is sufficient for MVP
5. PowerShell vs Python - use Python for complex scripts
6. Always test API keys before integrating
7. Proper error handling prevents crashes

================================================================================
CONTACT & SUPPORT
================================================================================

Project: Focus Companion
Telegram Bot: @P_asst_bot (https://t.me/P_asst_bot)
Status: MVP Complete
Last Updated: July 27, 2026

================================================================================
LICENSE
================================================================================

MIT License - See LICENSE file for details

================================================================================
CONTRIBUTING
================================================================================

Contributions are welcome! Please submit a Pull Request.

1. Fork the repository
2. Create feature branch (git checkout -b feature/AmazingFeature)
3. Commit changes (git commit -m 'Add some AmazingFeature')
4. Push to branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

================================================================================
ACKNOWLEDGMENTS
================================================================================

DeepSeek (https://deepseek.com) - AI API
Telegram (https://telegram.org) - Bot platform
FastAPI (https://fastapi.tiangolo.com) - Web framework

================================================================================
END OF DOCUMENT
================================================================================
