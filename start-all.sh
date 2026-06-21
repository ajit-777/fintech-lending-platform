#!/bin/bash
# Start backend and admin portal.
# For Flutter/Android: run ./launch-android.sh (launches emulator + Flutter together)
# Usage: ./start-all.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
ADB="$HOME/Library/Android/sdk/platform-tools/adb"

mkdir -p "$ROOT/backend/logs" "$ROOT/admin/logs"

# ── Backend ───────────────────────────────────────────────────────────────────
echo "==> Starting backend..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
cd "$ROOT/backend"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    > logs/backend.log 2>&1 &
echo $! > backend.pid
echo "    PID $(cat backend.pid) — logs/backend.log"
echo "    Swagger: http://127.0.0.1:8000/docs"

# ── Admin portal ──────────────────────────────────────────────────────────────
echo "==> Starting admin portal..."
pkill -f "vite.*admin" 2>/dev/null || true
cd "$ROOT/admin"
export PATH="/usr/local/bin:$PATH"
nohup npm run dev > logs/admin.log 2>&1 &
echo $! > admin.pid
echo "    PID $(cat admin.pid) — logs/admin.log"
echo "    URL: http://localhost:5173"

echo ""
echo "Backend and admin portal started."
echo "To start Flutter: ./launch-android.sh  (or ./launch-ios.sh)"
echo ""
echo "Logs:"
echo "  Backend : tail -f backend/logs/backend.log"
echo "  Admin   : tail -f admin/logs/admin.log"
