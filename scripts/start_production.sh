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

is_raspberry_pi() {
    if [[ ! -f /proc/device-tree/model ]]; then
        return 1
    fi
    grep -qi "raspberry pi" /proc/device-tree/model
}

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

# Use Ollama-only mode by default unless explicitly overridden.
export OLLAMA_BASE="${OLLAMA_BASE:-http://127.0.0.1:11434}"
export OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
export OLLAMA_STRICT="${OLLAMA_STRICT:-true}"

# Raspberry Pi defaults for Waveshare Core1262 on SPI1/CE1.
if is_raspberry_pi; then
    export LORA_MODE="${LORA_MODE:-rpi_spi}"
    export LORA_RPI_SPI_BUS="${LORA_RPI_SPI_BUS:-1}"
    export LORA_RPI_SPI_DEVICE="${LORA_RPI_SPI_DEVICE:-1}"
    export LORA_RPI_RST_PIN="${LORA_RPI_RST_PIN:-17}"
    export LORA_RPI_DIO1_PIN="${LORA_RPI_DIO1_PIN:-22}"
fi

echo "[AOJ] AI provider: Ollama strict=${OLLAMA_STRICT} base=${OLLAMA_BASE}"
echo "[AOJ] LoRa mode: ${LORA_MODE:-mock}"

cd "$BACKEND_DIR"
exec "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
