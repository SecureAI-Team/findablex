# FindableX Lite Development Mode
# Run the API with SQLite and without Docker/Redis

Write-Host "=== FindableX Lite Mode ===" -ForegroundColor Cyan
Write-Host "Using SQLite + in-memory queue (no Docker needed)" -ForegroundColor Yellow
Write-Host ""

# Navigate to API package
Set-Location -Path "$PSScriptRoot\..\packages\api"

# Check if .env exists, if not copy from lite example
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from env.lite.example..." -ForegroundColor Yellow
    Copy-Item "env.lite.example" ".env"
}

# Create data directory
if (-not (Test-Path "data")) {
    Write-Host "Creating data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# Check Python virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -q

# Start the API server
Write-Host ""
Write-Host "Starting API server at http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
