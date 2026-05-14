#!/usr/bin/env bash
# AOJ Command OS - Production Startup (Kiosk-Optimized)
# 
# This version is optimized for embedded kiosk mode:
# - Runs in foreground with clean logging
# - Validates environment before startup
# - Performs health checks
# - Handles graceful shutdown
#
# Usage: ./start_production_kiosk.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIST="$PROJECT_ROOT/frontend/dist"

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}[AOJ]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[AOJ]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[AOJ]${NC} $1"
}

log_error() {
  echo -e "${RED}[AOJ]${NC} $1"
}

# Check if running on Raspberry Pi
is_raspberry_pi() {
  [[ -f /proc/device-tree/model ]] && grep -qi "raspberry pi" /proc/device-tree/model
}

# Detect IP address
get_ip_address() {
  hostname -I | awk '{print $1}'
}

# Validate environment
validate_environment() {
  log_info "Validating environment..."
  
  if [[ ! -f "$VENV_PYTHON" ]]; then
    log_error "Python venv not found at $VENV_PYTHON"
    log_error "Run: $PROJECT_ROOT/scripts/install_pi.sh"
    return 1
  fi
  
  if [[ ! -d "$FRONTEND_DIST" ]]; then
    log_error "Frontend build not found at $FRONTEND_DIST"
    log_error "Run: $PROJECT_ROOT/scripts/install_pi.sh"
    return 1
  fi
  
  log_success "Environment validated"
  return 0
}

# Configure environment for production
configure_production() {
  log_info "Configuring production environment..."
  
  # Default to Ollama-only mode (offline AI)
  export OLLAMA_BASE="${OLLAMA_BASE:-http://127.0.0.1:11434}"
  export OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
  export OLLAMA_STRICT="${OLLAMA_STRICT:-true}"
  
  # Raspberry Pi LoRa defaults
  if is_raspberry_pi; then
    export LORA_MODE="${LORA_MODE:-rpi_spi}"
    export LORA_RPI_SPI_BUS="${LORA_RPI_SPI_BUS:-1}"
    export LORA_RPI_SPI_DEVICE="${LORA_RPI_SPI_DEVICE:-1}"
    export LORA_RST_PIN="${LORA_RST_PIN:-17}"
    export LORA_DIO1_PIN="${LORA_DIO1_PIN:-22}"
  else
    export LORA_MODE="${LORA_MODE:-mock}"
  fi
  
  # Performance tuning
  export WORKERS="${WORKERS:-2}"
  export LOG_LEVEL="${LOG_LEVEL:-info}"
  
  log_success "Production environment configured"
}

# Print startup banner
print_banner() {
  echo ""
  echo "╔════════════════════════════════════════╗"
  echo "║    AOJ Command OS - Production Start   ║"
  echo "╚════════════════════════════════════════╝"
  echo ""
  echo "📊 System Information:"
  echo "   IP Address: $(get_ip_address)"
  echo "   Frontend: http://$(get_ip_address):8000"
  echo "   API Docs: http://$(get_ip_address):8000/docs"
  echo ""
  if is_raspberry_pi; then
    echo "🥧 Raspberry Pi Detected"
    echo "   LoRa Mode: $LORA_MODE"
  else
    echo "💻 Non-Pi Environment (Mock mode)"
  fi
  echo ""
  echo "🤖 AI Provider:"
  echo "   Ollama Base: $OLLAMA_BASE"
  echo "   Ollama Strict: $OLLAMA_STRICT"
  echo ""
  echo "📝 Backend:"
  echo "   Python: $VENV_PYTHON"
  echo "   Workers: $WORKERS"
  echo "   Log Level: $LOG_LEVEL"
  echo ""
  echo "⏳ Starting backend..."
  echo ""
}

# Main startup sequence
main() {
  validate_environment || exit 1
  configure_production
  print_banner
  
  # Change to backend directory
  cd "$BACKEND_DIR"
  
  # Start uvicorn server
  # Using app:app with explicit host/port for clarity
  exec "$VENV_PYTHON" -m uvicorn \
    app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level "${LOG_LEVEL}" \
    --access-log \
    --use-colors
}

# Handle shutdown gracefully
trap 'log_warn "Shutdown signal received"; exit 0' SIGTERM SIGINT

main "$@"
