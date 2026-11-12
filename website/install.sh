#!/usr/bin/env bash
# ThrottlerOS Linux / macOS Installer
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "===================================================="
echo "          ThrottlerOS Linux / macOS Setup"
echo "===================================================="

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10 or newer."
    exit 1
fi

echo "Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "Installing required dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

chmod +x run.sh
chmod +x install.sh

echo ""
echo "===================================================="
echo "[SUCCESS] Installation complete!"
echo "Run './run.sh' to start ThrottlerOS."
echo "Run './run.sh --lan' to allow access from other devices."
echo "Dashboard: http://127.0.0.1:8742"
echo "===================================================="
