#!/bin/bash
# Launch the Android emulator (Medium_Phone_API_36.1) in the background.
# Usage: ./launch-android.sh

AVD="Medium_Phone_API_36.1"
EMULATOR="$HOME/Library/Android/sdk/emulator/emulator"

if ! command -v "$EMULATOR" &>/dev/null; then
  echo "Error: Android emulator not found at $EMULATOR"
  exit 1
fi

if pgrep -f "emulator.*$AVD" > /dev/null; then
  echo "Android emulator '$AVD' is already running."
  exit 0
fi

echo "==> Launching Android emulator: $AVD (background)"
nohup "$EMULATOR" -avd "$AVD" -no-snapshot-save > /tmp/android-emulator.log 2>&1 &
EMULATOR_PID=$!
echo "    PID $EMULATOR_PID — logs: /tmp/android-emulator.log"
echo "    Emulator booting in the background. Run: adb devices to check when ready."
