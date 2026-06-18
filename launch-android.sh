#!/bin/bash
# Launch the Android emulator (Medium_Phone_API_36.1) in the background.
# Usage: ./launch-android.sh

AVD="Medium_Phone_API_36.1"
EMULATOR="$HOME/Library/Android/sdk/emulator/emulator"

if ! command -v "$EMULATOR" &>/dev/null; then
  echo "Error: Android emulator not found at $EMULATOR"
  exit 1
fi

# Check if already running
if pgrep -f "emulator.*$AVD" > /dev/null; then
  echo "Android emulator '$AVD' is already running."
  exit 0
fi

echo "==> Launching Android emulator: $AVD"
nohup "$EMULATOR" -avd "$AVD" -no-snapshot-save > /tmp/android-emulator.log 2>&1 &
echo "    PID $! — logs: /tmp/android-emulator.log"
echo "    Waiting for device to boot..."

# Wait until the device is online
until adb shell getprop sys.boot_completed 2>/dev/null | grep -q "1"; do
  sleep 3
done
echo "    Device ready: $(adb devices | grep emulator)"
