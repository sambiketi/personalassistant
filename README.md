# 🎯 Focus Agent v2

AI-powered adaptive scheduling PWA. Refactor of the original `focus-agent`
prototype with a hardened backend and a more forgiving frontend.

## What changed from v1

| Area | Fix |
|---|---|
| **Database** | Lightweight `PRAGMA user_version` migration system, CHECK constraints (goal progress 0–100, valid statuses, etc.), calendar-aware streak calc that no longer truncates at 30 log rows |
| **Validation** | All POST bodies are Pydantic models with field-level validators (time format, ISO dates, enums, length limits); DB errors are caught and returned as clean HTTP errors instead of leaking stack traces |
| **Frontend UX** | Every form button shows a spinner while in-flight and a message that fades out after a few seconds; a single `reportError()`/`showFormMessage()` pair centralizes error handling in `app.js` |
| **Progress analytics** | `/progress/{user_id}` now also returns habit streaks and average task duration, not just completion/skip counts |
| **Agent integration** | `agent.js` recognizes structured phrasing ("add task X at 10am", "add goal X", "add habit X") and calls the matching POST helper directly instead of always round-tripping through the LLM |
| **Deployment** | `.env` / `.env.example`, `Dockerfile` and `docker-compose.yml` all read `DB_PATH`, `LLM_PROVIDER`, `LLM_API_KEY`, `PORT` from the environment |
| **Duplication** | Removed the unused SQLAlchemy `schemas.py` and one-off `fix_*.py` patch scripts — `database.py` is the single source of truth for persistence |

## Project structure

```
scheduleappv2/
├── backend/
│   ├── app/
│   │   ├── core/          # agent.py, vanguard_brain.py, robust_parser.py, brain_interface.py
│   │   ├── models/        # database.py (SQLite + migrations)
│   │   ├── routes/        # dashboard.py (all API endpoints)
│   │   ├── services/      # llm_interface.py + deepseek/openai/anthropic adapters
│   │   └── main.py        # FastAPI app, DI wiring, logging middleware
│   ├── run_server.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js          # UI logic, centralized error handling
│   ├── js/agent.js         # API client + NL command router
│   ├── manifest.json
│   └── sw.js
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Run locally

```bash
cd backend
cp ../.env.example ../.env      # then edit .env with your LLM_API_KEY
pip install -r requirements.txt
python run_server.py            # http://localhost:8000

# new terminal
cd frontend
python -m http.server 3000      # http://localhost:3000
```

## Run with Docker

```bash
cp .env.example .env            # edit as needed
docker compose up --build
```

## API quick reference

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/agent/process \
  -H "Content-Type: application/json" \
  -d '{"message":"Plan my day","user_id":"demo_user"}'
curl http://localhost:8000/api/progress/demo_user
```
