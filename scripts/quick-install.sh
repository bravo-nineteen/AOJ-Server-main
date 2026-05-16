#!/bin/bash
set -eu
# Enable pipefail when supported by the current shell.
if (set -o pipefail) 2>/dev/null; then
  set -o pipefail
fi

# AOJ Command OS - Quick Install (All-in-One for Fresh Raspberry Pi OS)
# 
# This script does EVERYTHING after you boot a fresh Raspberry Pi OS:
# - Downloads the AOJ project
# - Installs all dependencies
# - Sets up kiosk mode
# - Enables auto-startup
# 
# Run this ONCE on a fresh Raspberry Pi OS and you're done!
#
# Usage:
#   curl -sL https://github.com/your-org/AOJ-Server/raw/main/scripts/quick-install.sh | bash
#   
# Or download and run locally:
#   chmod +x scripts/quick-install.sh
#   ./scripts/quick-install.sh

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
LOCAL_PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_PROJECT_ROOT="${HOME}/AOJ-Server"
INSTALL_OLLAMA="false"
AUTO_REBOOT="false"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[AOJ]${NC} $1"; }
log_success() { echo -e "${GREEN}[AOJ]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[AOJ]${NC} $1"; }
log_error() { echo -e "${RED}[AOJ]${NC} $1"; }

relaunch_in_terminal() {
  if [[ -n "${AOJ_LAUNCHED_IN_TERMINAL:-}" ]]; then
    return
  fi

  if [[ -t 0 && -t 1 && -n "${TERM:-}" ]]; then
    return
  fi

  local launch_cmd
  printf -v launch_cmd 'cd %q; AOJ_LAUNCHED_IN_TERMINAL=1 %q' "$LOCAL_PROJECT_ROOT" "$SCRIPT_PATH"

  if command -v x-terminal-emulator &> /dev/null; then
    exec x-terminal-emulator -e bash -lc "$launch_cmd"
  elif command -v lxterminal &> /dev/null; then
    exec lxterminal -e bash -lc "$launch_cmd"
  elif command -v xterm &> /dev/null; then
    exec xterm -e bash -lc "$launch_cmd"
  fi

  log_error "No terminal launcher found for double-click execution"
  log_error "Run this script from Terminal instead"
  exit 1
}

is_local_project_copy() {
  [[ -f "${LOCAL_PROJECT_ROOT}/scripts/install_pi.sh" ]]
}

banner() {
  echo ""
  echo "╔════════════════════════════════════════════╗"
  echo "║   AOJ Command OS - Quick Install           ║"
  echo "║   Everything in one command!               ║"
  echo "╚════════════════════════════════════════════╝"
  echo ""
}

check_os() {
  log_info "Checking if this is Raspberry Pi OS..."

  local is_pi="false"
  if grep -qi "raspbian\|raspberry\|debian" /etc/os-release 2>/dev/null; then
    is_pi="true"
  fi
  if grep -qi "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    is_pi="true"
  fi

  if [[ "$is_pi" != "true" ]]; then
    log_warn "This might not be Raspberry Pi OS"
    log_warn "Continuing anyway... (things might not work)"
  else
    log_success "Raspberry Pi OS detected!"
  fi
}

check_internet() {
  log_info "Checking internet connection..."
  
  if ! ping -c 1 8.8.8.8 &> /dev/null; then
    log_error "No internet connection detected"
    log_error "Please connect to Wi-Fi and try again"
    exit 1
  fi
  
  log_success "Internet connection OK"
}

check_storage() {
  log_info "Checking available storage..."
  
  available=$(df ~ | tail -1 | awk '{print $4}')
  required=$((2000000)) # 2GB in KB
  
  if [[ $available -lt $required ]]; then
    log_warn "Low storage space available ($(($available / 1024 / 1024))GB)"
    log_warn "Continuing anyway..."
  else
    log_success "Storage space OK ($(($available / 1024 / 1024))GB available)"
  fi
}

welcome() {
  banner
  
  echo "This script will:"
  echo "  1. Update system packages"
  echo "  2. Download AOJ project from GitHub"
  echo "  3. Install Python dependencies"
  echo "  4. Build the frontend"
  echo "  5. Setup Ollama AI (optional)"
  echo "  6. Configure automatic startup (kiosk mode)"
  echo "  7. Reboot your Pi"
  echo ""
  echo "After reboot, your AOJ system will be ready!"
  echo ""
  
  echo "Defaults for this run:"
  echo "  - Reuse existing ~/AOJ-Server if present"
  echo "  - Skip Ollama install"
  echo "  - Do not auto-reboot"
  echo ""

  read -p "Continue with these defaults? (y/n) " -n 1 -r
  echo ""
  
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Installation cancelled"
    exit 0
  fi
}

update_system() {
  log_info "Updating system packages..."
  echo "  (this may take a few minutes)"
  
  sudo apt-get update &> /dev/null
  sudo apt-get upgrade -y &> /dev/null
  
  log_success "System updated"
}

install_dependencies() {
  log_info "Installing required packages..."
  echo "  Python, Node.js, Git, Chromium, X11, etc."

  # Newer Raspberry Pi OS releases often provide 'chromium' instead of 'chromium-browser'.
  if ! sudo apt-get install -y \
    python3 python3-venv python3-pip \
    nodejs npm \
    git \
    chromium-browser \
    xserver-xorg xinit lightdm lightdm-gtk-greeter \
    unclutter curl \
    &> /dev/null; then
    log_warn "Primary package list failed, retrying with 'chromium' package name..."
    sudo apt-get install -y \
      python3 python3-venv python3-pip \
      nodejs npm \
      git \
      chromium \
      xserver-xorg xinit lightdm lightdm-gtk-greeter \
      unclutter curl
  fi
  
  log_success "Dependencies installed"
}

download_project() {
  if is_local_project_copy; then
    log_info "Using local AOJ project files..."

    if [[ "$LOCAL_PROJECT_ROOT" == "$TARGET_PROJECT_ROOT" ]]; then
      cd "$TARGET_PROJECT_ROOT"
      log_success "AOJ project ready at ~/AOJ-Server"
      return
    fi

    if [[ -d "$TARGET_PROJECT_ROOT" ]]; then
      log_warn "AOJ-Server already exists at ~/AOJ-Server"
      log_info "Using existing AOJ project at ~/AOJ-Server"
      cd "$TARGET_PROJECT_ROOT"
      return
    fi

    cp -a "$LOCAL_PROJECT_ROOT" "$TARGET_PROJECT_ROOT"
    cd "$TARGET_PROJECT_ROOT"
    log_success "AOJ project copied to ~/AOJ-Server"
    return
  fi

  log_info "Downloading AOJ project from GitHub..."

  if [[ -d "$TARGET_PROJECT_ROOT" ]]; then
    log_warn "AOJ-Server already exists at ~/AOJ-Server"
    log_info "Using existing AOJ project at ~/AOJ-Server"
  else
    if ! git clone https://github.com/bravo-nineteen/AOJ-Server-main.git "$TARGET_PROJECT_ROOT"; then
      log_error "Failed to download AOJ project from GitHub"
      log_error "Check internet connectivity and GitHub access, then retry"
      exit 1
    fi
  fi

  cd "$TARGET_PROJECT_ROOT"
  log_success "AOJ project ready at ~/AOJ-Server"
}

install_aoj() {
  log_info "Installing AOJ system..."
  echo "  This will take 10-20 minutes"

  local install_log="${HOME}/aoj-install.log"
  chmod +x scripts/install_pi.sh
  if ! bash scripts/install_pi.sh 2>&1 | tee "$install_log"; then
    log_error "AOJ installation failed. See log: $install_log"
    exit 1
  fi
  
  log_success "AOJ installation complete"
}

setup_ollama() {
  log_info "Setting up Ollama AI (optional offline AI)..."
  if [[ "$INSTALL_OLLAMA" == "true" ]]; then
    chmod +x scripts/setup_pi_ollama.sh
    ./scripts/setup_pi_ollama.sh &> /dev/null
    log_success "Ollama installed"
  else
    log_warn "Skipping Ollama installation"
  fi
}

setup_kiosk() {
  log_info "Setting up kiosk mode (auto-startup)..."
  
  chmod +x scripts/setup-kiosk-pi.sh
  
  # Run the kiosk setup script but suppress some output
  {
    bash -c '
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
    SYSTEMD_DIR="${SCRIPT_DIR}/systemd"
    
    mkdir -p "${SYSTEMD_DIR}"
    
    sudo cp "${SYSTEMD_DIR}/aoj-production.service" /etc/systemd/system/
    sudo cp "${SYSTEMD_DIR}/aoj-kiosk.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    
    sudo mkdir -p /etc/lightdm/lightdm.conf.d
    sudo tee /etc/lightdm/lightdm.conf.d/99-autologin.conf > /dev/null <<EOF
[Seat:*]
autologin-user=pi
autologin-user-session=LXDE
user-session=LXDE
EOF
    
    mkdir -p ~/.config/autostart
    cat > ~/.xinitrc <<'\''XINITRC'\''
#!/bin/bash
unclutter -idle 0 &
exec chromium-browser \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --disable-extensions \
  --disable-sync \
  --app=http://localhost:8000 \
  --kiosk
XINITRC
    chmod +x ~/.xinitrc
    
    sudo systemctl enable aoj-production.service aoj-kiosk.service
    ' 2> /dev/null
  }
  
  log_success "Kiosk mode configured"
}

final_status() {
  echo ""
  echo "╔════════════════════════════════════════════╗"
  echo "║     Installation Complete!                ║"
  echo "╚════════════════════════════════════════════╝"
  echo ""
  echo "Your AOJ system is ready!"
  echo ""
  echo "Next step: REBOOT YOUR PI"
  echo "  sudo reboot"
  echo ""
  echo "After reboot:"
  echo "  ✓ System boots directly to AOJ"
  echo "  ✓ No login required"
  echo "  ✓ Fullscreen interface"
  echo "  ✓ Access from tablets: http://raspberrypi.local:8000"
  echo ""
  echo "Need help?"
  echo "  - Check logs: sudo journalctl -u aoj-production -f"
  echo "  - Read guide: ~/AOJ-Server/BEGINNER_RASPBERRY_PI_SETUP.md"
  echo "  - Quick ref: ~/AOJ-Server/KIOSK_MODE_QUICK_REFERENCE.md"
  echo ""
}

reboot_prompt() {
  if [[ "$AUTO_REBOOT" == "true" ]]; then
    log_info "Rebooting in 10 seconds..."
    sleep 10
    sudo reboot
  else
    log_info "Reboot skipped. Run 'sudo reboot' when ready."
  fi
}

main() {
  relaunch_in_terminal
  welcome
  check_os
  check_internet
  check_storage
  update_system
  install_dependencies
  download_project
  install_aoj
  setup_ollama
  setup_kiosk
  final_status
  reboot_prompt
}

main "$@"
