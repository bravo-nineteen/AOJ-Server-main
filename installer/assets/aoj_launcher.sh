#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# AOJ Command OS — Linux Launcher
# =============================================================================
# This script launches AOJ Command OS on Linux systems.
# Can be called from:
#   - Desktop shortcuts (.desktop file)
#   - Command line: /opt/aoj-command-os/assets/aoj_launcher.sh
#   - systemd: via aoj-command-os.service
#
# Features:
#   - Auto-detection of installation directory
#   - Dependency check (Python 3.11+, Node.js 18+)
#   - Virtual environment setup if needed
#   - Graceful failure messages
# =============================================================================

# Detect installation directory (works from install location or symlink)
INSTALL_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")/..")" && pwd)"
BACKEND_DIR="${INSTALL_DIR}/backend"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
SCRIPTS_DIR="${INSTALL_DIR}/scripts"
VENV_DIR="${BACKEND_DIR}/.venv"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         AOJ Command OS - Airsoft Online Japan                  ║"
echo "║              Tactical Server and Frontend                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""

# Check if running in terminal or from desktop
if [[ -z "${TERM:-}" ]]; then
  # Running from desktop: need to launch terminal
  echo "Launching in terminal..."
  if command -v gnome-terminal &>/dev/null; then
    exec gnome-terminal -- "$0"
  elif command -v xterm &>/dev/null; then
    exec xterm -e "$0"
  elif command -v konsole &>/dev/null; then
    exec konsole -e "$0"
  else
    # Fallback: run background and notify user
    nohup "$0" > "${INSTALL_DIR}/launcher.log" 2>&1 &
    sleep 2
    echo "'$0' started in background. Check ${INSTALL_DIR}/launcher.log for details."
    exit 0
  fi
fi

# Dependency checks
check_dependency() {
  local cmd="$1"
  local min_version="$2"
  
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ ERROR: $cmd not found"
    echo "   Please install $cmd and try again."
    exit 1
  fi
  
  if [[ -n "$min_version" ]]; then
    local version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || echo "0.0")
    echo "  ✓ $cmd ($version)"
  else
    echo "  ✓ $cmd available"
  fi
}

echo "Checking dependencies..."
check_dependency "python3" "3.11"
check_dependency "npm" "18"
echo ""

# Setup virtual environment if needed
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Setting up Python virtual environment..."
  python3 -m venv "$VENV_DIR"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip > /dev/null 2>&1
  echo "  ✓ Virtual environment ready"
fi

# Install/update dependencies if needed
if [[ ! -f "${VENV_DIR}/bin/uvicorn" ]]; then
  echo "Installing backend dependencies (first-time setup)..."
  "${VENV_DIR}/bin/python" -m pip install -q -r "${BACKEND_DIR}/requirements.txt"
  echo "  ✓ Backend dependencies installed"
fi

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
  echo "Installing frontend dependencies (first-time setup)..."
  cd "$FRONTEND_DIR"
  npm install --prefer-offline --no-audit > /dev/null 2>&1
  echo "  ✓ Frontend dependencies installed"
fi

# Build frontend if needed
if [[ ! -d "${FRONTEND_DIR}/dist" ]]; then
  echo "Building frontend..."
  cd "$FRONTEND_DIR"
  npm run build > /dev/null 2>&1
  echo "  ✓ Frontend built"
fi

echo ""
echo "Starting AOJ Command OS Dual Server..."
echo "  Backend (API):  http://127.0.0.1:8000"
echo "  Frontend (Web): http://127.0.0.1:4173"
echo ""
echo "Press Ctrl+C to stop both services."
echo ""

# Source startup script and run
cd "$INSTALL_DIR"

# Start backend and frontend
"${SCRIPTS_DIR}/start_backend.sh" &
BACKEND_PID=$!

sleep 2

"${SCRIPTS_DIR}/start_frontend.sh" &
FRONTEND_PID=$!

# Cleanup on exit
cleanup() {
  echo ""
  echo "Shutting down AOJ Command OS..."
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "✓ Services stopped"
}

trap cleanup EXIT INT TERM

wait "$BACKEND_PID" "$FRONTEND_PID"
