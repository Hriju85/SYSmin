#!/usr/bin/env bash
# ThrottlerOS Runner
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f ".venv/bin/python3" ]; then
    PY=".venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "[ERROR] Python 3 not found."
    exit 1
fi

echo "Starting ThrottlerOS on http://127.0.0.1:8742..."
exec "$PY" server.py --host 127.0.0.1 --port 8742 "$@"
