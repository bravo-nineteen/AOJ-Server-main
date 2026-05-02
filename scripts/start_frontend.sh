#!/usr/bin/env bash
set -euo pipefail

# Serve the built frontend for local network access.
#
# This uses Python's standard HTTP server against the Vite dist output.
# It does not run a development server and does not alter system configuration.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIST_DIR="${PROJECT_ROOT}/frontend/dist"
PORT="${AOJ_FRONTEND_PORT:-4173}"

if [[ ! -d "${FRONTEND_DIST_DIR}" ]]; then
  echo "[AOJ] Frontend build directory not found. Run scripts/install_pi.sh first." >&2
  exit 1
fi

cd "${FRONTEND_DIST_DIR}"

# Serve static assets in the foreground for systemd or manual supervision.
exec python3 -m http.server "${PORT}" --bind 0.0.0.0