#!/usr/bin/env bash
set -euo pipefail

# AOJ Command OS - Raspberry Pi Kiosk Setup
# This script configures a Raspberry Pi to boot directly into the AOJ system
# without requiring login or manual startup.
#
# Prerequisites:
#   - Raspberry Pi OS (Desktop) installed and booted
#   - SSH access or local terminal
#   - User 'pi' with sudo privileges
#
# Usage:
#   chmod +x ./setup-kiosk-pi.sh
#   ./setup-kiosk-pi.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEMD_DIR="${SCRIPT_DIR}/systemd"

echo "=========================================="
echo "AOJ Command OS - Kiosk Mode Setup"
echo "=========================================="
echo ""

# Step 1: Ensure system is up to date
echo "[1/7] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install required packages
echo "[2/7] Installing required packages (Chromium, X11, lightdm)..."
sudo apt-get install -y \
  chromium-browser \
  xserver-xorg \
  xinit \
  lightdm \
  lightdm-gtk-greeter \
  unclutter \
  curl

# Step 3: Run the standard Pi installation
echo "[3/7] Running standard AOJ installation..."
"${PROJECT_ROOT}/scripts/install_pi.sh"

# Step 4: Setup Ollama (optional but recommended)
echo "[4/7] Setting up Ollama for local AI..."
if command -v ollama &> /dev/null; then
  echo "    Ollama already installed."
else
  "${PROJECT_ROOT}/scripts/setup_pi_ollama.sh"
fi

# Step 5: Install systemd services
echo "[5/7] Installing systemd services..."
sudo mkdir -p /etc/systemd/system
sudo cp "${SYSTEMD_DIR}/aoj-production.service" /etc/systemd/system/
sudo cp "${SYSTEMD_DIR}/aoj-kiosk.service" /etc/systemd/system/
sudo systemctl daemon-reload

# Step 6: Configure autologin for user 'pi'
echo "[6/7] Configuring automatic login for user 'pi'..."
sudo mkdir -p /etc/lightdm/lightdm.conf.d
sudo tee /etc/lightdm/lightdm.conf.d/99-autologin.conf > /dev/null <<EOF
[Seat:*]
autologin-user=pi
autologin-user-session=LXDE
user-session=LXDE
EOF

# Step 7: Configure LXDE/X11 to start the kiosk
echo "[7/7] Configuring X11 to launch AOJ kiosk..."
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/aoj-kiosk.desktop <<EOF
[Desktop Entry]
Type=Application
Exec=/home/pi/AOJ-Server/scripts/systemd/aoj-kiosk.service
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=AOJ Kiosk
EOF

# Alternative: Use .xinitrc for X11 startup
cat > ~/.xinitrc <<'XINITRC'
#!/bin/bash
# Launch AOJ kiosk on X startup
unclutter -idle 0 &
exec chromium-browser \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --disable-default-browser-check \
  --disable-extensions \
  --disable-sync \
  --disable-translate \
  --app=http://localhost:8000 \
  --kiosk
XINITRC
chmod +x ~/.xinitrc

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Enable the services:"
echo "     sudo systemctl enable aoj-production.service aoj-kiosk.service"
echo ""
echo "  2. Reboot the Raspberry Pi:"
echo "     sudo reboot"
echo ""
echo "After reboot, the AOJ system will:"
echo "  - Start automatically without login"
echo "  - Load the backend on port 8000"
echo "  - Display the UI in fullscreen kiosk mode"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u aoj-production -f"
echo "  sudo journalctl -u aoj-kiosk -f"
echo ""
echo "To disable kiosk mode (return to normal desktop):"
echo "  sudo systemctl disable aoj-kiosk.service"
echo "  sudo reboot"
echo ""
