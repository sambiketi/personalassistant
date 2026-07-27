Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
cd frontend
python -m http.server 3000
