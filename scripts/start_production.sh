#!/usr/bin/env bash
# AOJ Command OS - Production launcher (Linux / Raspberry Pi)
# Serves the built React frontend AND the API from a single uvicorn process.
# Access the UI and API at http://MACHINE_IP:8000
#
# Prerequisites: run install_linux.sh (or install_pi.sh) first.
#
# Usage:
#   chmod +x ./scripts/start_production.sh
#   ./scripts/start_production.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VENV_PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIST="$PROJECT_ROOT/frontend/dist"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[AOJ] ERROR: Virtual environment not found at $VENV_PYTHON"
    echo "[AOJ] Run ./scripts/install_linux.sh first."
    exit 1
fi

if [ ! -d "$FRONTEND_DIST" ]; then
    echo "[AOJ] ERROR: Frontend build not found at $FRONTEND_DIST"
    echo "[AOJ] Run ./scripts/install_linux.sh first (it runs the frontend build)."
    exit 1
fi

echo "[AOJ] Starting production server on port 8000 (LAN-accessible)..."
echo "[AOJ] UI + API: http://0.0.0.0:8000"
echo "[AOJ] Press Ctrl+C to stop."
echo ""

cd "$BACKEND_DIR"
exec "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
