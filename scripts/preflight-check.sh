#!/usr/bin/env bash
set -euo pipefail

# AOJ Command OS - Pre-Flight Checker
# 
# Validates system before installation
# Checks: internet, storage, Python, Node.js, permissions
#
# Usage:
#   chmod +x scripts/preflight-check.sh
#   ./scripts/preflight-check.sh

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[✓]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

check_os() {
  echo ""
  echo "=== Operating System ==="
  
  if grep -qi "raspbian\|raspberry" /etc/os-release 2>/dev/null; then
    log_success "Raspberry Pi OS detected"
    ((PASS_COUNT++))
  else
    log_warn "Not Raspberry Pi OS (might still work)"
    ((WARN_COUNT++))
  fi
}

check_internet() {
  echo ""
  echo "=== Internet Connection ==="
  
  if ping -c 1 8.8.8.8 &> /dev/null; then
    log_success "Internet connection OK"
    ((PASS_COUNT++))
  else
    log_error "No internet connection"
    ((FAIL_COUNT++))
  fi
}

check_storage() {
  echo ""
  echo "=== Storage Space ==="
  
  available=$(df ~ | tail -1 | awk '{print $4}')
  available_gb=$((available / 1024 / 1024))
  required_gb=2
  
  if [[ $available_gb -ge $required_gb ]]; then
    log_success "Storage OK (${available_gb}GB available, need ${required_gb}GB)"
    ((PASS_COUNT++))
  elif [[ $available_gb -ge 1 ]]; then
    log_warn "Low storage (${available_gb}GB available, ${required_gb}GB recommended)"
    ((WARN_COUNT++))
  else
    log_error "Insufficient storage (${available_gb}GB available, need ${required_gb}GB)"
    ((FAIL_COUNT++))
  fi
}

check_memory() {
  echo ""
  echo "=== Memory ==="
  
  total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
  total_gb=$((total_mem / 1024 / 1024))
  
  if [[ $total_gb -ge 2 ]]; then
    log_success "Memory OK (${total_gb}GB)"
    ((PASS_COUNT++))
  else
    log_warn "Low memory (${total_gb}GB, 2GB recommended)"
    ((WARN_COUNT++))
  fi
}

check_python() {
  echo ""
  echo "=== Python ==="
  
  if command -v python3 &> /dev/null; then
    version=$(python3 --version 2>&1 | awk '{print $2}')
    log_success "Python 3 installed (v${version})"
    ((PASS_COUNT++))
  else
    log_error "Python 3 not installed"
    ((FAIL_COUNT++))
  fi
}

check_git() {
  echo ""
  echo "=== Git ==="
  
  if command -v git &> /dev/null; then
    version=$(git --version | awk '{print $3}')
    log_success "Git installed (v${version})"
    ((PASS_COUNT++))
  else
    log_warn "Git not installed (will download separately)"
    ((WARN_COUNT++))
  fi
}

check_permissions() {
  echo ""
  echo "=== Permissions ==="
  
  if sudo -n true 2> /dev/null; then
    log_success "Sudo access available (no password prompt needed)"
    ((PASS_COUNT++))
  else
    log_warn "Sudo might require password during installation"
    ((WARN_COUNT++))
  fi
}

check_display() {
  echo ""
  echo "=== Display ==="
  
  if [[ -n "${DISPLAY:-}" ]]; then
    log_success "Display detected: $DISPLAY"
    ((PASS_COUNT++))
  else
    log_warn "No display detected (needed for kiosk mode)"
    ((WARN_COUNT++))
  fi
}

check_existing() {
  echo ""
  echo "=== Existing Installation ==="
  
  if [[ -d ~/AOJ-Server ]]; then
    log_warn "AOJ-Server already exists at ~/AOJ-Server"
    ((WARN_COUNT++))
  else
    log_success "Fresh installation (no existing AOJ-Server)"
    ((PASS_COUNT++))
  fi
}

summary() {
  echo ""
  echo "╔════════════════════════════════════════════╗"
  echo "║           Pre-Flight Check Summary         ║"
  echo "╚════════════════════════════════════════════╝"
  echo ""
  echo -e "${GREEN}Passed:${NC}   ${PASS_COUNT}"
  echo -e "${YELLOW}Warnings:${NC} ${WARN_COUNT}"
  echo -e "${RED}Failed:${NC}   ${FAIL_COUNT}"
  echo ""
  
  if [[ $FAIL_COUNT -eq 0 ]]; then
    log_success "System ready for installation!"
    echo ""
    echo "Run: ./scripts/quick-install.sh"
    return 0
  else
    log_error "System not ready for installation"
    echo ""
    echo "Fix the errors above and try again"
    return 1
  fi
}

main() {
  echo ""
  echo "╔════════════════════════════════════════════╗"
  echo "║    AOJ Command OS - Pre-Flight Check       ║"
  echo "╚════════════════════════════════════════════╝"
  
  check_os
  check_internet
  check_storage
  check_memory
  check_python
  check_git
  check_permissions
  check_display
  check_existing
  
  summary
}

main "$@"
