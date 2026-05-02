#!/usr/bin/env bash
set -euo pipefail

# Start the AOJ Command OS FastAPI backend.
#
# This script expects dependencies to have been installed already.
# It starts the backend in the foreground so it can be supervised by systemd,
# tmux, screen, or manual shell usage on Linux and Raspberry Pi hosts.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"

if [[ ! -x "${VENV_DIR}/bin/uvicorn" ]]; then
  echo "[AOJ] Backend virtual environment not found. Run scripts/install_linux.sh or scripts/install_pi.sh first." >&2
  exit 1
fi

cd "${BACKEND_DIR}"

# Bind to all interfaces so operators on the local LAN can reach the API.
exec "${VENV_DIR}/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000