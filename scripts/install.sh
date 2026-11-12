#!/usr/bin/env bash
# ThrottlerOS & SYSmin Linux / macOS Installer
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "===================================================="
echo "      ThrottlerOS & SYSmin Linux / macOS Setup"
echo "===================================================="

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10 or newer."
    exit 1
fi

echo "Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "Installing dependencies (fastapi, uvicorn, psutil)..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

chmod +x scripts/run.sh
chmod +x scripts/install.sh

echo ""
echo "===================================================="
echo "[SUCCESS] Installation complete!"
echo "To run locally:            ./scripts/run.sh"
echo "To allow LAN access:       ./scripts/run.sh --lan"
echo "Dashboard:                 http://127.0.0.1:8742"
echo "===================================================="
