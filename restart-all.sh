#!/bin/bash
# Restart all platform services
# Usage: ./restart-all.sh [android|ios|chrome]

ROOT="$(cd "$(dirname "$0")" && pwd)"

"$ROOT/stop-all.sh"
echo ""
"$ROOT/start-all.sh" "${1:-android}"
