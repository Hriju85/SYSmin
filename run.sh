#!/usr/bin/env bash
# ==============================================================================
# SYSmin All-In-One Unified Controller (Linux & macOS)
# Runs executable / python backend, manages lifecycle, and opens browser
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PID_FILE="$SCRIPT_DIR/.server.pid"

# Stop helper function
stop_sysmin() {
    echo "Stopping SYSmin..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            sleep 0.5
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
    pkill -f "$SCRIPT_DIR/backend/main.py" 2>/dev/null || true
    pkill -f "$SCRIPT_DIR/dist/ProcessController" 2>/dev/null || true
    if command -v fuser >/dev/null 2>&1; then
        fuser -k 8000/tcp >/dev/null 2>&1 || true
    fi
    echo "SYSmin stopped."
}

# Handle 'stop' argument
if [ "$1" = "stop" ]; then
    stop_sysmin
    exit 0
fi

# Check if already running on port 8000
if curl -s -m 1 http://127.0.0.1:8000/api/privacy >/dev/null 2>&1; then
    echo "SYSmin is already running on http://127.0.0.1:8000"
    echo "Run './run.sh stop' to stop it."
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
    fi
    exit 0
fi

# Launch: Check for standalone binary first, otherwise use Python
if [ -x "dist/ProcessController" ]; then
    echo "Starting SYSmin binary (dist/ProcessController)..."
    nohup dist/ProcessController > /dev/null 2>&1 &
    SERVER_PID=$!
    disown $SERVER_PID 2>/dev/null || true
    echo "$SERVER_PID" > "$PID_FILE"
else
    # Python environment fallback
    if [ ! -d ".venv" ] || [ ! -f ".venv/bin/python" ]; then
        echo "Setting up Python virtual environment..."
        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt
    fi
    echo "Starting SYSmin backend service..."
    nohup .venv/bin/python backend/main.py > /dev/null 2>&1 &
    SERVER_PID=$!
    disown $SERVER_PID 2>/dev/null || true
    echo "$SERVER_PID" > "$PID_FILE"
fi

# Wait for port 8000
for i in {1..30}; do
    if curl -s -m 1 http://127.0.0.1:8000/api/privacy >/dev/null 2>&1; then
        echo "SYSmin is ready on http://127.0.0.1:8000"
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
        elif command -v sensible-browser >/dev/null 2>&1; then
            sensible-browser "http://127.0.0.1:8000" >/dev/null 2>&1 || true
        elif command -v open >/dev/null 2>&1; then
            open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
        fi
        exit 0
    fi
    sleep 0.5
done

echo "Error: Server failed to start on port 8000 within 15 seconds."
exit 1

