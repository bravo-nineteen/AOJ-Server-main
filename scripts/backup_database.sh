#!/usr/bin/env bash
set -euo pipefail

# Create a timestamped backup of the AOJ Command OS SQLite database.
#
# This script only copies the database file into a backup directory under backend/.
# It does not delete old backups or modify the live database.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATABASE_FILE="${PROJECT_ROOT}/backend/aoj_command_os.db"
BACKUP_DIR="${PROJECT_ROOT}/backend/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/aoj_command_os_backup_${TIMESTAMP}.db"

if [[ ! -f "${DATABASE_FILE}" ]]; then
  echo "[AOJ] Database file not found at ${DATABASE_FILE}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
cp -a "${DATABASE_FILE}" "${BACKUP_FILE}"

echo "[AOJ] Database backup created: ${BACKUP_FILE}"