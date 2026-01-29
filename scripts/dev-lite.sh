#!/bin/bash
# FindableX Lite Development Mode
# Run the API with SQLite and without Docker/Redis

echo "=== FindableX Lite Mode ==="
echo "Using SQLite + in-memory queue (no Docker needed)"
echo ""

# Navigate to API package
cd "$(dirname "$0")/../packages/api"

# Check if .env exists, if not copy from lite example
if [ ! -f ".env" ]; then
    echo "Creating .env from env.lite.example..."
    cp env.lite.example .env
fi

# Create data directory
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
fi

# Check Python virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Start the API server
echo ""
echo "Starting API server at http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
