#!/bin/bash
# Launch the Android emulator and wait for it to be ready, then start Flutter.
# Usage: ./launch-android.sh

AVD="Medium_Phone_API_36.1"
EMULATOR="$HOME/Library/Android/sdk/emulator/emulator"
ADB="$HOME/Library/Android/sdk/platform-tools/adb"
ROOT="$(cd "$(dirname "$0")" && pwd)"

if ! command -v "$EMULATOR" &>/dev/null; then
  echo "Error: Android emulator not found at $EMULATOR"
  exit 1
fi

if pgrep -f "emulator.*$AVD" > /dev/null; then
  echo "Android emulator '$AVD' is already running."
else
  echo "==> Launching Android emulator: $AVD"
  nohup "$EMULATOR" -avd "$AVD" -no-snapshot-save > /tmp/android-emulator.log 2>&1 &
  echo "    PID $! — logs: /tmp/android-emulator.log"
fi

echo "==> Waiting for emulator to boot (this takes ~30-60s)..."
for i in $(seq 1 40); do
  EMULATOR_ID=$("$ADB" devices 2>/dev/null | grep "emulator.*device$" | awk '{print $1}' | head -1)
  if [ -n "$EMULATOR_ID" ]; then
    echo "    Emulator ready: $EMULATOR_ID"
    break
  fi
  printf "    [%d/40] waiting...\r" "$i"
  sleep 3
done

if [ -z "$EMULATOR_ID" ]; then
  echo "    Timed out waiting for emulator. Check /tmp/android-emulator.log"
  exit 1
fi

echo "==> Starting Flutter on $EMULATOR_ID..."
pkill -f "flutter run" 2>/dev/null
mkdir -p "$ROOT/frontend/logs"
cd "$ROOT/frontend" && nohup flutter run -d "$EMULATOR_ID" > "$ROOT/frontend/logs/flutter.log" 2>&1 &
echo "    Flutter PID $! — tail -f frontend/logs/flutter.log"
