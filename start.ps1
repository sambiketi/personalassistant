Write-Host "Starting Focus Companion..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
