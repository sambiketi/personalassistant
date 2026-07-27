#!/bin/bash
source venv/bin/activate
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
