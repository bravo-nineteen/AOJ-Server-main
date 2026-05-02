#!/usr/bin/env bash
set -euo pipefail

# AOJ Command OS Linux installer.
#
# This prepares the backend virtual environment, installs Python dependencies,
# installs frontend dependencies, and builds the frontend bundle.
#
# The script only performs package-manager installation when required commands
# are missing and apt-get is available. It does not modify system services.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
VENV_DIR="${BACKEND_DIR}/.venv"

need_command() {
  command -v "$1" >/dev/null 2>&1
}

install_with_apt_if_needed() {
  if need_command python3 && need_command npm; then
    return 0
  fi

  if ! need_command apt-get; then
    echo "[AOJ] Missing required commands and apt-get is not available." >&2
    echo "[AOJ] Install python3, python3-venv, python3-pip, nodejs, and npm manually, then rerun this script." >&2
    exit 1
  fi

  echo "[AOJ] Installing missing system packages with apt-get."
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip nodejs npm
}

install_with_apt_if_needed

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${BACKEND_DIR}/requirements.txt"

cd "${FRONTEND_DIR}"
npm install
npm run build

echo "[AOJ] Linux installation complete."
echo "[AOJ] Backend start: ${PROJECT_ROOT}/scripts/start_backend.sh"
echo "[AOJ] Frontend start: ${PROJECT_ROOT}/scripts/start_frontend.sh"
