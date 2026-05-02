#!/usr/bin/env bash
# AOJ Command OS - Release packager (Linux / macOS)
# Creates a distributable tar.gz archive of the project suitable for download and install.
# Excludes runtime artifacts: .venv, node_modules, __pycache__, dist, *.db, backups.
#
# Usage:
#   chmod +x ./scripts/package_release_linux.sh
#   ./scripts/package_release_linux.sh
#   ./scripts/package_release_linux.sh 1.2.0
#
# Output: aoj-command-os-1.0.0-linux.tar.gz in the project root.

set -e

VERSION="${1:-1.0.0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ARCHIVE_NAME="aoj-command-os-${VERSION}-linux.tar.gz"
OUTPUT_PATH="$PROJECT_ROOT/$ARCHIVE_NAME"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"
PROJECT_DIRNAME="$(basename "$PROJECT_ROOT")"

echo "[AOJ] Packaging release v${VERSION}..."
echo "[AOJ] Project root: $PROJECT_ROOT"
echo "[AOJ] Output: $OUTPUT_PATH"

# Remove existing archive if present
if [ -f "$OUTPUT_PATH" ]; then
    rm -f "$OUTPUT_PATH"
    echo "[AOJ] Removed existing archive."
fi

# Create tar.gz from parent directory, excluding runtime-generated paths
tar -czf "$OUTPUT_PATH" \
    -C "$PARENT_DIR" \
    --exclude="${PROJECT_DIRNAME}/.git" \
    --exclude="${PROJECT_DIRNAME}/backend/.venv" \
    --exclude="${PROJECT_DIRNAME}/frontend/node_modules" \
    --exclude="${PROJECT_DIRNAME}/frontend/dist" \
    --exclude="${PROJECT_DIRNAME}/backend/__pycache__" \
    --exclude="${PROJECT_DIRNAME}/backend/app/__pycache__" \
    --exclude="${PROJECT_DIRNAME}/backend/app/routes/__pycache__" \
    --exclude="${PROJECT_DIRNAME}/backend/app/services/__pycache__" \
    --exclude="*/__pycache__" \
    --exclude="*.pyc" \
    --exclude="${PROJECT_DIRNAME}/backend/*.db" \
    --exclude="${PROJECT_DIRNAME}/backend/*.db-shm" \
    --exclude="${PROJECT_DIRNAME}/backend/*.db-wal" \
    --exclude="${PROJECT_DIRNAME}/backend/backups" \
    --transform "s|^${PROJECT_DIRNAME}|aoj-command-os|" \
    "$PROJECT_DIRNAME"

SIZE_MB=$(du -sh "$OUTPUT_PATH" | cut -f1)
echo ""
echo "[AOJ] Release package created: $ARCHIVE_NAME ($SIZE_MB)"
echo "[AOJ] Recipients can install with:"
echo "      tar -xzf $ARCHIVE_NAME"
echo "      chmod +x ./aoj-command-os/scripts/*.sh"
echo "      ./aoj-command-os/scripts/install_linux.sh"
