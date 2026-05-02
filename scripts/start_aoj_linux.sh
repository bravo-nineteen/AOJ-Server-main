#!/usr/bin/env bash
set -euo pipefail

# Start both AOJ Command OS services on Linux in the current shell session.
#
# This script launches the backend and frontend as child processes and keeps
# running until both stop or the user interrupts the session.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/start_backend.sh" &
BACKEND_PID=$!

"${SCRIPT_DIR}/start_frontend.sh" &
FRONTEND_PID=$!

cleanup() {
  kill "${BACKEND_PID}" "${FRONTEND_PID}" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "[AOJ] Backend:  http://127.0.0.1:8000"
echo "[AOJ] Frontend: http://127.0.0.1:4173"

wait "${BACKEND_PID}" "${FRONTEND_PID}"
