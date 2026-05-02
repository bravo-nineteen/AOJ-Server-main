#!/usr/bin/env bash
set -euo pipefail

# Generate systemd service templates for AOJ Command OS.
#
# This script writes template service files into scripts/systemd/ only.
# It does not copy them into /etc/systemd/system and does not enable services.
# Review the generated files before any manual installation.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEMD_DIR="${SCRIPT_DIR}/systemd"
AOJ_USER="${AOJ_USER:-pi}"
AOJ_GROUP="${AOJ_GROUP:-${AOJ_USER}}"

mkdir -p "${SYSTEMD_DIR}"

cat > "${SYSTEMD_DIR}/aoj-backend.service" <<EOF
[Unit]
Description=AOJ Command OS Backend
After=network.target

[Service]
Type=simple
User=${AOJ_USER}
Group=${AOJ_GROUP}
WorkingDirectory=${PROJECT_ROOT}/backend
ExecStart=${PROJECT_ROOT}/scripts/start_backend.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "${SYSTEMD_DIR}/aoj-frontend.service" <<EOF
[Unit]
Description=AOJ Command OS Frontend
After=network.target

[Service]
Type=simple
User=${AOJ_USER}
Group=${AOJ_GROUP}
WorkingDirectory=${PROJECT_ROOT}/frontend/dist
ExecStart=${PROJECT_ROOT}/scripts/start_frontend.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[AOJ] Service templates created in ${SYSTEMD_DIR}"
echo "[AOJ] Manual install steps (not executed automatically):"
echo "  sudo cp ${SYSTEMD_DIR}/aoj-backend.service /etc/systemd/system/"
echo "  sudo cp ${SYSTEMD_DIR}/aoj-frontend.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now aoj-backend.service aoj-frontend.service"