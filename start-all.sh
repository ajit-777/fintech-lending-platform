#!/bin/bash
# Start all platform services: backend, admin portal, Flutter
# Usage: ./start-all.sh [android|ios|chrome]   (Flutter target, default: android)

ROOT="$(cd "$(dirname "$0")" && pwd)"
FLUTTER_TARGET="${1:-android}"

mkdir -p "$ROOT/backend/logs" "$ROOT/admin/logs" "$ROOT/frontend/logs"

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

# ── Flutter ───────────────────────────────────────────────────────────────────
echo "==> Starting Flutter (target: $FLUTTER_TARGET)..."
pkill -f "flutter run" 2>/dev/null || true
cd "$ROOT/frontend"
# Auto-detect running emulator if target is 'android'
if [ "$FLUTTER_TARGET" = "android" ]; then
  EMULATOR_ID=$(flutter devices 2>/dev/null | grep emulator | awk '{print $4}' | head -1)
  if [ -n "$EMULATOR_ID" ]; then
    FLUTTER_TARGET="$EMULATOR_ID"
    echo "    Auto-detected emulator: $EMULATOR_ID"
  fi
fi
nohup flutter run -d "$FLUTTER_TARGET" > logs/flutter.log 2>&1 &
echo $! > flutter.pid
echo "    PID $(cat flutter.pid) — logs/flutter.log"

echo ""
echo "All services started. To tail logs:"
echo "  Backend : tail -f backend/logs/backend.log"
echo "  Admin   : tail -f admin/logs/admin.log"
echo "  Flutter : tail -f frontend/logs/flutter.log"
