# AOJ Command OS - Kiosk Mode Setup Guide

This guide explains how to configure a Raspberry Pi to run AOJ Command OS as a dedicated embedded system that starts automatically without login or manual intervention.

## Overview

When configured in kiosk mode, the Pi will:
- Boot directly into the AOJ system interface
- Display the UI in fullscreen on an HDMI screen
- Run the backend automatically
- Require no login or startup commands
- Handle system restarts gracefully
- Behave like a dedicated operating system

## Hardware Requirements

- **Raspberry Pi 4 or newer** (2GB+ RAM recommended, 4GB+ ideal)
- **High-quality microSD card or SSD** (fast writes improve reliability)
- **Reliable 5V 3A power supply** (or better with battery backup)
- **HDMI-capable monitor or screen**
- **Keyboard + Mouse** (for initial setup and admin access)
- **Network connection** (Wi-Fi or Ethernet)

## Prerequisites

1. **Fresh Raspberry Pi OS Desktop installation**
   ```bash
   # Flash Raspberry Pi OS Desktop to microSD
   # Use Raspberry Pi Imager: https://www.raspberrypi.com/software/
   ```

2. **SSH enabled** (for remote administration)
   ```bash
   sudo systemctl start ssh
   sudo systemctl enable ssh
   ```

3. **Network connectivity**
   ```bash
   # Verify internet connection
   ping 8.8.8.8
   ```

## Automated Setup (Recommended)

### Step 1: Clone or Deploy the Project

```bash
# On the Raspberry Pi, clone the project
cd ~
git clone https://github.com/your-org/AOJ-Server.git
cd AOJ-Server
```

Or transfer the project via SSH/SCP:
```bash
scp -r ./AOJ-Server pi@raspberrypi.local:~/
```

### Step 2: Run the Kiosk Setup Script

```bash
chmod +x scripts/setup-kiosk-pi.sh
./scripts/setup-kiosk-pi.sh
```

This script will:
- Update system packages
- Install Chromium browser, X11, and lightdm
- Run the standard AOJ installation
- Set up Ollama for offline AI
- Install systemd services
- Configure autologin
- Set up X11 startup

### Step 3: Enable and Reboot

```bash
sudo systemctl enable aoj-production.service aoj-kiosk.service
sudo reboot
```

After reboot, the system will automatically:
1. Start the backend server
2. Wait for it to be ready
3. Launch Chromium in fullscreen kiosk mode
4. Display the AOJ UI

## Manual Setup (Advanced)

If you prefer manual control or need to customize:

### Step 1: Install Base Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  nodejs npm \
  chromium-browser \
  xserver-xorg xinit lightdm lightdm-gtk-greeter \
  unclutter curl
```

### Step 2: Install AOJ

```bash
cd ~/AOJ-Server
scripts/install_pi.sh
scripts/setup_pi_ollama.sh
```

### Step 3: Copy Systemd Services

```bash
sudo cp scripts/systemd/aoj-production.service /etc/systemd/system/
sudo cp scripts/systemd/aoj-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Step 4: Configure Autologin

Edit lightdm configuration:
```bash
sudo nano /etc/lightdm/lightdm.conf.d/99-autologin.conf
```

Add these lines:
```ini
[Seat:*]
autologin-user=pi
autologin-user-session=LXDE
```

### Step 5: Create X11 Startup Script

```bash
cat > ~/.xinitrc <<'EOF'
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
EOF
chmod +x ~/.xinitrc
```

### Step 6: Enable Services and Reboot

```bash
sudo systemctl enable aoj-production.service aoj-kiosk.service
sudo reboot
```

## System Architecture in Kiosk Mode

```
┌─────────────────────────────────────────────────┐
│  Raspberry Pi OS Boot                           │
│  (no login required - autologin as 'pi')        │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  systemd multi-user.target                      │
│  Starts: aoj-production.service                 │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Backend (uvicorn) starts on :8000              │
│  - Serves built React frontend                  │
│  - Initializes LoRa, Ollama, database           │
│  - Waits for health check endpoint               │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼ (when healthy)
┌─────────────────────────────────────────────────┐
│  X11 Desktop (graphical.target)                 │
│  Starts: aoj-kiosk.service                      │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Chromium in Kiosk Mode (fullscreen)            │
│  Navigates to: http://localhost:8000            │
│  No address bar, no tabs, fullscreen mode       │
└─────────────────────────────────────────────────┘
```

## Operation & Maintenance

### Viewing Live Logs

```bash
# Backend logs
sudo journalctl -u aoj-production -f

# Kiosk browser logs
sudo journalctl -u aoj-kiosk -f

# All AOJ-related logs
sudo journalctl -g AOJ -f
```

### Checking Service Status

```bash
sudo systemctl status aoj-production
sudo systemctl status aoj-kiosk
```

### Manual Restart

```bash
# Restart specific service
sudo systemctl restart aoj-production
sudo systemctl restart aoj-kiosk

# Restart everything
sudo systemctl restart aoj-production aoj-kiosk
```

### Emergency Access

If the system gets stuck in kiosk mode:

1. **Press Alt+F2** to access a run dialog (if available)
2. **Press Ctrl+Alt+F2** to switch to terminal TTY2
3. **Login as 'pi'** and run:
   ```bash
   sudo systemctl stop aoj-kiosk
   # Now you have access to desktop
   ```

### Disable Kiosk Mode (Return to Normal Desktop)

```bash
sudo systemctl disable aoj-kiosk.service
sudo reboot
```

The system will still run AOJ in the background but won't autolaunch the browser.

## Customization

### Change Browser Fullscreen Display

Edit the chromium flags in `/etc/systemd/system/aoj-kiosk.service`:

```bash
sudo nano /etc/systemd/system/aoj-kiosk.service
```

Common flags:
- `--kiosk` - Fullscreen mode
- `--app=URL` - Opens URL in app mode (no tabs/address bar)
- `--disable-extensions` - Disable browser extensions
- `--mute-audio` - Mute audio on startup
- `--start-fullscreen` - Alternative fullscreen method

### Change Startup Network Interface

If using a static IP, configure it in:
```bash
sudo nano /etc/dhcpcd.conf
```

### Add Custom Startup Scripts

Create a directory for pre-launch tasks:
```bash
mkdir -p ~/aoj-startup
```

Add scripts and source them from `aoj-production.service`:
```bash
ExecStartPre=/home/pi/aoj-startup/preflight-checks.sh
```

### Adjust Backend Startup Parameters

Edit environment variables in `/etc/systemd/system/aoj-production.service`:

```bash
# LoRa hardware configuration
Environment="LORA_MODE=rpi_spi"
Environment="LORA_RPI_SPI_BUS=1"
Environment="LORA_RPI_SPI_DEVICE=1"

# AI provider
Environment="OLLAMA_STRICT=true"
Environment="OLLAMA_BASE=http://127.0.0.1:11434"

# Performance tuning
Environment="WORKERS=2"
```

## Troubleshooting

### Issue: Browser starts but shows blank screen

**Solution:** Wait 10-15 seconds for the backend to fully initialize. Check logs:
```bash
sudo journalctl -u aoj-production -n 50
```

### Issue: System boots to black screen

**Solution:** The backend may be failing to start. SSH in and check:
```bash
sudo systemctl status aoj-production
sudo journalctl -u aoj-production -n 100
```

### Issue: Backend crashes on startup

**Common causes:**
- Missing dependencies: Run `./scripts/install_pi.sh` again
- Database corruption: Backup and delete `backend/data/*.db`
- Port 8000 already in use: `sudo lsof -i :8000`

### Issue: LoRa hardware not detected

**Solution:** Check hardware connection and SPI settings:
```bash
# Enable SPI
sudo raspi-config
# Select: Interface Options > SPI > Enable

# Verify SPI is available
ls -la /dev/spidev*
```

### Issue: Chromium won't start / crashes

**Solution:** Reinstall Chromium and clear cache:
```bash
sudo apt-get install --reinstall chromium-browser
rm -rf ~/.cache/chromium/
sudo reboot
```

## Advanced: Custom Embedded OS Look

To truly make it feel like an embedded OS (hide taskbar, customize boot splash, etc.):

### Hide Desktop Taskbar and Icons

Edit LXDE autostart:
```bash
nano ~/.config/lxsession/LXDE/autostart
```

Comment out or remove panel-related lines:
```bash
# @lxpanel --profile LXDE
# @pcmanfm --desktop --profile LXDE
```

### Add Custom Boot Splash

Create a splash screen script:
```bash
cat > /etc/systemd/system-sleep/aoj-display.sh <<'EOF'
#!/bin/bash
# Custom display management on sleep/wake
echo "AOJ Display Handler"
EOF
chmod +x /etc/systemd/system-sleep/aoj-display.sh
```

### Set Custom Wallpaper

```bash
# Create a solid color or AOJ logo background
pcmanfm-preferences
# Set background image to your AOJ logo
```

## Backup & Recovery

### Create System Backup

```bash
# Create bootable backup of entire SD card
sudo dd if=/dev/mmcblk0 of=aoj-backup.img bs=4M status=progress
gzip aoj-backup.img
```

### Restore from Backup

```bash
gunzip -c aoj-backup.img.gz | sudo dd of=/dev/mmcblk0 bs=4M status=progress
```

## Next Steps

- **Configure LoRa Hardware:** See [docs/LORA_HARDWARE_SETUP.md](docs/LORA_HARDWARE_SETUP.md)
- **Setup Ollama LLM:** See [scripts/setup_pi_ollama.sh](scripts/setup_pi_ollama.sh)
- **Custom Themes:** See [frontend/src/themes/](frontend/src/themes/)
- **API Documentation:** Visit `http://raspberrypi.local:8000/docs` after boot

---

**Last Updated:** May 2026  
**For issues:** Check [DEPLOYMENT.md](DEPLOYMENT.md) or create an issue on GitHub
