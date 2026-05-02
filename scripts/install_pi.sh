#!/usr/bin/env bash
set -euo pipefail

# AOJ Command OS Raspberry Pi install script.
#
# This script installs backend/frontend dependencies and builds the frontend.
# It does not enable services or overwrite system files.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
VENV_DIR="${BACKEND_DIR}/.venv"

echo "[AOJ] Project root: ${PROJECT_ROOT}"

# Update package metadata before package installation.
sudo apt-get update

# Install the base packages required to run the backend and build the frontend.
# This is an intentional system change, but it is limited to package installation.
sudo apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  nodejs \
  npm

# Create the backend virtual environment if it does not already exist.
if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

# Install backend Python dependencies into the project-local virtual environment.
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

# Install frontend Node dependencies and build the production bundle.
cd "${FRONTEND_DIR}"
npm install
npm run build

echo "[AOJ] Installation complete."
echo "[AOJ] Backend virtual environment: ${VENV_DIR}"
echo "[AOJ] Frontend build output: ${FRONTEND_DIR}/dist"