#!/bin/bash
# Stop all platform services: backend, admin portal, Flutter

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Backend ───────────────────────────────────────────────────────────────────
echo "==> Stopping backend..."
if [ -f "$ROOT/backend/backend.pid" ]; then
    PID=$(cat "$ROOT/backend/backend.pid")
    kill "$PID" 2>/dev/null && echo "    Stopped (PID $PID)" || echo "    Process not running"
    rm -f "$ROOT/backend/backend.pid"
else
    pkill -f "uvicorn app.main:app" 2>/dev/null && echo "    Stopped" || echo "    Not running"
fi

# ── Admin portal ──────────────────────────────────────────────────────────────
echo "==> Stopping admin portal..."
if [ -f "$ROOT/admin/admin.pid" ]; then
    PID=$(cat "$ROOT/admin/admin.pid")
    kill "$PID" 2>/dev/null && echo "    Stopped (PID $PID)" || echo "    Process not running"
    rm -f "$ROOT/admin/admin.pid"
else
    pkill -f "vite.*admin" 2>/dev/null && echo "    Stopped" || echo "    Not running"
fi

# ── Flutter ───────────────────────────────────────────────────────────────────
echo "==> Stopping Flutter..."
if [ -f "$ROOT/frontend/flutter.pid" ]; then
    PID=$(cat "$ROOT/frontend/flutter.pid")
    kill "$PID" 2>/dev/null && echo "    Stopped (PID $PID)" || echo "    Process not running"
    rm -f "$ROOT/frontend/flutter.pid"
else
    pkill -f "flutter run" 2>/dev/null && echo "    Stopped" || echo "    Not running"
fi

echo ""
echo "All services stopped."
