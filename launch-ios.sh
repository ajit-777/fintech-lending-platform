#!/bin/bash
# Launch the iOS simulator (iPhone 17 Pro) in the background.
# Usage: ./launch-ios.sh

UDID="02D219DA-E6BD-48C9-B285-02E643D84510"
DEVICE_NAME="iPhone 17 Pro"

if ! command -v xcrun &>/dev/null; then
  echo "Error: Xcode command line tools not found."
  exit 1
fi

# Check if already booted
STATUS=$(xcrun simctl list devices | grep "$UDID" | grep -o "Booted")
if [ "$STATUS" = "Booted" ]; then
  echo "iOS Simulator '$DEVICE_NAME' is already running."
  open -a Simulator
  exit 0
fi

echo "==> Launching iOS Simulator: $DEVICE_NAME ($UDID)"
xcrun simctl boot "$UDID"
open -a Simulator
echo "    Simulator booted."
