#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$PROJECT_DIR"

echo "Stopping old uvicorn processes..."
pkill -f "uvicorn app.main:app" || true

echo "Activating venv..."
source venv/bin/activate

echo "Starting backend..."

nohup uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    > logs/backend.log 2>&1 &

PID=$!

echo $PID > backend.pid

echo ""
echo "Backend started"
echo "PID: $PID"
echo "Log file: logs/backend.log"
echo "Swagger: http://127.0.0.1:8000/docs"
