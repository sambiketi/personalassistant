#!/usr/bin/env python3
"""
Focus Companion - Universal Setup Script
Run with: python setup.py
"""

import os
import subprocess
import sys

# File contents
FILES = {
    "backend/requirements.txt": """fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
twilio==8.10.0
litellm==1.12.0
instructor==1.0.0
pydantic==2.5.0
python-dotenv==1.0.0
aiofiles==23.2.1
APScheduler==3.10.4
httpx==0.25.2
""",

    "backend/__init__.py": "# Focus Companion backend package\n",

    "backend/ai_engine.py": '''import instructor
from litellm import completion
from pydantic import BaseModel, Field
from typing import List, Optional

class TaskItem(BaseModel):
    task_name: str
    start_time: str = Field(description="Format: HH:MM AM/PM")
    end_time: str = Field(description="Format: HH:MM AM/PM")
    is_unsnoozable: bool = Field(default=False)

class DailySchedule(BaseModel):
    date_or_day: str
    tasks: List[TaskItem]

class UniversalScheduler:
    def __init__(self, provider_model: str, api_key: str):
        self.model = provider_model
        self.api_key = api_key
        self.client = instructor.from_litellm(completion)

    def generate_schedule(self, user_prompt: str, unsnoozables: List[str]) -> DailySchedule:
        system_prompt = f"""
        You are an elite productivity scheduling agent.
        User Unsnoozable Tasks: {unsnoozables}

        Rules:
        1. Parse the prompt into sequential start and end times.
        2. Set is_unsnoozable=True for any task matching the user's unsnoozable list.
        3. Maintain strict time continuity without overlaps.
        """

        return self.client.chat.completions.create(
            model=self.model,
            api_key=self.api_key,
            response_model=DailySchedule,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
''',

    "backend/app_state.py": '''from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Task:
    name: str
    start_time: str
    end_time: str
    is_unsnoozable: bool = False
    status: str = "PENDING"

@dataclass
class UserSession:
    phone_number: str
    api_key: str
    provider: str
    unsnoozables: List[str]
    tasks: List[Task] = field(default_factory=list)

APP_STATE: Dict[str, UserSession] = {}
''',

    "backend/server.py": '''from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from app_state import APP_STATE, UserSession, Task
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Focus Companion API", "status": "running"}

@app.post("/api/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    user_phone = From.replace("whatsapp:", "").strip()
    command = Body.strip().upper()
    
    resp = MessagingResponse()
    session = APP_STATE.get(user_phone)

    if not session or not session.tasks:
        resp.message("Welcome! You have no active tasks scheduled. Set up your day in the app first.")
        return Response(content=str(resp), media_type="application/xml")

    current_task = session.tasks[0]

    if command == "START":
        current_task.status = "IN_PROGRESS"
        resp.message(f"Started: {current_task.name}. Focus up!")

    elif command == "SNOOZE":
        if current_task.is_unsnoozable:
            resp.message(f"Locked: {current_task.name} is flagged as UNSNOOZABLE. You cannot delay this task. Let's do it now!")
        else:
            current_task.status = "SNOOZED"
            resp.message(f"Pushed {current_task.name} by 10 minutes. Reminding you shortly!")

    elif command == "DONE":
        current_task.status = "COMPLETED"
        session.tasks.pop(0)
        next_msg = f" Up next: {session.tasks[0].name}" if session.tasks else " You cleared all tasks for today!"
        resp.message(f"Task marked DONE!{next_msg}")

    else:
        resp.message("Reply START to begin, SNOOZE to delay 10 mins, or DONE when finished.")

    return Response(content=str(resp), media_type="application/xml")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',

    "frontend/index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Focus Companion</title>
  <link rel="manifest" href="manifest.json">
  <meta name="theme-color" content="#FDFBF7">
  <style>
    :root {
      --bg-main: #FDFBF7;
      --card-bg: #FFFFFF;
      --primary-accent: #D97706;
      --text-main: #27272A;
      --text-muted: #71717A;
      --border-color: #F3E8DC;
      --badge-unsnoozable: #DC2626;
    }
    body {
      background: var(--bg-main);
      color: var(--text-main);
      font-family: system-ui, -apple-system, sans-serif;
      margin: 0; padding: 16px;
      display: flex; justify-content: center;
    }
    .container { width: 100%; max-width: 420px; }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: 0 4px 12px rgba(120, 53, 15, 0.04);
    }
    .now-card { border-left: 6px solid var(--primary-accent); }
    .next-card { border-left: 6px solid var(--text-muted); opacity: 0.85; }
    .badge {
      font-size: 0.75rem; font-weight: bold; padding: 4px 8px; border-radius: 6px; text-transform: uppercase;
    }
    .badge-now { background: #FEF3C7; color: #92400E; }
    .badge-locked { background: #FEE2E2; color: var(--badge-unsnoozable); }
    .install-btn {
      width: 100%; padding: 12px; background: var(--text-main); color: white;
      border: none; border-radius: 8px; font-weight: bold; cursor: pointer; display: none;
    }
  </style>
</head>
<body>

  <div class="container">
    <header style="margin-bottom: 20px;">
      <h2 style="margin: 0;">Daily Focus</h2>
      <p style="margin: 4px 0 0; color: var(--text-muted); font-size: 0.9rem;">One task at a time.</p>
    </header>

    <!-- HAPPENING NOW -->
    <div class="card now-card">
      <div style="display: flex; justify-content: space-between;">
        <span class="badge badge-now">Happening Now</span>
        <span style="color: var(--text-muted); font-size: 0.85rem;">10:00 AM - 12:00 PM</span>
      </div>
      <h3 style="margin: 12px 0 4px;">Setup Environment & Coding</h3>
      <p style="margin: 0; color: #059669; font-weight: 600; font-size: 0.9rem;">In Progress</p>
    </div>

    <!-- UP NEXT -->
    <div class="card next-card">
      <div style="display: flex; justify-content: space-between;">
        <span class="badge" style="background: #E4E4E7; color: #3F3F46;">Up Next</span>
        <span class="badge badge-locked">Locked</span>
      </div>
      <h4 style="margin: 10px 0 2px; color: #3F3F46;">Exercise & Stretch</h4>
      <span style="color: var(--text-muted); font-size: 0.85rem;">12:00 PM - 01:00 PM</span>
    </div>

    <!-- PWA INSTALL PROMPT -->
    <button id="install-btn" class="install-btn">Add App to Home Screen</button>
  </div>

  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }

    let deferredPrompt;
    const btn = document.getElementById('install-btn');

    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      btn.style.display = 'block';
    });

    btn.addEventListener('click', () => {
      btn.style.display = 'none';
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt = null;
      }
    });
  </script>
</body>
</html>
''',

    "frontend/manifest.json": '''{
  "name": "Focus Companion",
  "short_name": "Companion",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FDFBF7",
  "theme_color": "#FDFBF7",
  "icons": [
    {
      "src": "icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
''',

    "frontend/sw.js": '''const CACHE_NAME = 'companion-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});
''',

    ".env": '''# LLM Configuration
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=

# Twilio Configuration
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=+14155238886

# App Configuration
APP_NAME="Focus Companion"
APP_VERSION="1.0.0"
DEBUG=True
''',

    ".gitignore": '''venv/
__pycache__/
*.pyc
.env
.vscode/
.idea/
.DS_Store
*.log
''',

    "README.md": '''# Focus Companion

A dynamic daily scheduler with WhatsApp integration.

## Quick Start

1. Edit .env with your API keys
2. Run: .\\start.ps1 (or python backend/server.py)
3. Run: .\\start-frontend.ps1 (or python -m http.server 3000 in frontend/)
4. Use ngrok to expose for WhatsApp

## Features

- Universal AI scheduler (OpenAI, Anthropic, Gemini, Groq)
- WhatsApp integration with START/SNOOZE/DONE
- Unsnoozable tasks
- Installable PWA
- Minimalist focus UI

## Project Structure

- backend/ - FastAPI + AI engine
- frontend/ - PWA web app
- venv/ - Python environment

## License

MIT
''',

    "start.ps1": '''Write-Host "Starting Focus Companion..." -ForegroundColor Cyan
& ".\\venv\\Scripts\\Activate.ps1"
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
''',

    "start-frontend.ps1": '''Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
cd frontend
python -m http.server 3000
''',

    "start.sh": '''#!/bin/bash
source venv/bin/activate
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
''',

    "start-frontend.sh": '''#!/bin/bash
cd frontend
python -m http.server 3000
'''
}

def create_dirs():
    """Create all necessary directories"""
    dirs = ['backend', 'frontend', 'frontend/icons']
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"  Created directory: {d}")

def create_files():
    """Create all files from the dictionary"""
    for filepath, content in FILES.items():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Created file: {filepath}")

def setup_venv():
    """Create virtual environment and install dependencies"""
    print("\n[3/4] Setting up virtual environment...")
    
    if not os.path.exists('venv'):
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        print("  Virtual environment created")
    else:
        print("  Virtual environment already exists")
    
    print("\n[4/4] Installing Python dependencies...")
    print("  This may take a few minutes...")
    
    if sys.platform == 'win32':
        pip_cmd = '.\\venv\\Scripts\\pip'
    else:
        pip_cmd = './venv/bin/pip'
    
    subprocess.run([pip_cmd, 'install', '-r', 'backend/requirements.txt'], check=True)
    print("  Dependencies installed")

def main():
    print("=" * 50)
    print("     FOCUS COMPANION SETUP")
    print("=" * 50)
    print()
    
    print("[1/4] Creating directories...")
    create_dirs()
    
    print("\n[2/4] Creating files...")
    create_files()
    
    setup_venv()
    
    print("\n" + "=" * 50)
    print("         SETUP COMPLETE!")
    print("=" * 50)
    print()
    print(f"Project created at: {os.getcwd()}")
    print()
    print("Next steps:")
    print("  1. Edit .env with your API keys")
    print("  2. Run: .\\start.ps1 (Windows) or ./start.sh (Mac/Linux)")
    print("  3. Run: .\\start-frontend.ps1 for web UI")
    print()
    print("Open http://localhost:3000 in your browser")
    print("WhatsApp webhook: http://localhost:8000/api/whatsapp")
    print()
    print("Happy coding!")

if __name__ == "__main__":
    main()
