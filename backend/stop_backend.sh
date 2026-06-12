#!/bin/bash

if [ -f backend.pid ]; then
    PID=$(cat backend.pid)

    echo "Stopping PID $PID"

    kill $PID || true

    rm backend.pid

    echo "Backend stopped"
else
    echo "backend.pid not found"
fi
