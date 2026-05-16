# AOJ Command OS - Ultra Quick Start Guide

**Want the easiest possible installation? Here's the fastest way.**

---

## ⚡ One-Command Installation

### Option 1: Direct from GitHub (Fastest)

**On your fresh Raspberry Pi OS, just run:**

```bash
curl -sL https://raw.githubusercontent.com/bravo-nineteen/AOJ-Server-main/main/scripts/quick-install.sh | bash
```

**That's it!** The script will:
- ✅ Check your system
- ✅ Download AOJ
- ✅ Install everything
- ✅ Setup kiosk mode
- ✅ Reboot automatically

**Total time:** 30-45 minutes (mostly waiting for downloads)

### Option 2: Local Installation

**If you already have the project:**

```bash
cd ~/AOJ-Server
chmod +x scripts/quick-install.sh
./scripts/quick-install.sh
```

---

## ✅ Pre-Flight Check (Optional)

**Before installing, verify your system:**

```bash
chmod +x scripts/preflight-check.sh
./scripts/preflight-check.sh
```

**This checks:**
- ✅ Raspberry Pi OS detected
- ✅ Internet connection working
- ✅ Storage space available (2GB+)
- ✅ Memory available (2GB+)
- ✅ Python 3 installed
- ✅ Git installed
- ✅ Sudo access
- ✅ Display available

---

## 🎯 What Happens During Installation

### Step by Step

```
1. System Check (30 sec)
   - Verifies OS is Raspberry Pi
   - Checks internet and storage
   - Validates permissions

2. System Update (2-5 min)
   - apt-get update && upgrade

3. Dependencies (5-10 min)
   - Python, Node.js, Chromium
   - X11 server, lightdm
   - Other required packages

4. Download Project (2-5 min)
   - Clone from GitHub
   - About 200MB

5. AOJ Installation (10-20 min)
   - Install backend Python deps
   - Build frontend React app
   - Create database

6. Optional: Ollama AI (5-10 min)
   - You'll be asked if you want this
   - Provides offline AI capabilities
   - Skip if you don't want it

7. Kiosk Setup (2-3 min)
   - Configure auto-login
   - Setup fullscreen browser
   - Enable systemd services

8. Reboot (Automatic)
   - System restarts
   - AOJ loads automatically
   - Ready to use!

Total Time: 30-45 minutes
```

---

## 📊 What You Need

### Hardware
- Raspberry Pi 4 or newer
- microSD card (32GB+, fast)
- Power adapter (5V 3A+)
- HDMI monitor
- USB keyboard and mouse
- Wi-Fi or ethernet

### Software
- Fresh Raspberry Pi OS (just flashed)
- Internet connection
- Nothing else!

---

## 🚀 After Installation

### System Will Boot To:
1. Raspberry Pi OS desktop (auto-login as 'pi')
2. Chromium launches automatically
3. AOJ interface appears fullscreen
4. No login needed
5. Ready to use!

### Access From Other Devices

**On your tablet/laptop on the same Wi-Fi:**

```
http://raspberrypi.local:8000
```

Or use the IP address:
```
http://192.168.1.50:8000
```

---

## 🆘 Troubleshooting

### "Installer script not found"
- Make sure you're in `~/AOJ-Server` directory
- Check: `ls scripts/quick-install.sh`

### "Permission denied" during installation
- You'll be asked for password: `raspberry`
- Just type it and continue

### "Network error" during download
- Check internet connection: `ping 8.8.8.8`
- Make sure Pi is on Wi-Fi
- Try again

### Installation hangs or seems stuck
- These scripts take time (10-20 minutes)
- Look for downloading/compiling messages
- Wait at least 30 minutes before giving up

### Blank screen after reboot
- Wait 60 seconds for system to boot
- Check if you see any activity on the monitor
- Check logs: `sudo journalctl -u aoj-production -n 50`

### Browser won't start
- Wait 30 seconds after boot (first startup is slow)
- Refresh browser page (F5)
- Check backend: `sudo systemctl status aoj-production`

---

## 📋 Manual Installation (If Automation Fails)

**If the quick installer doesn't work:**

1. Follow: [BEGINNER_RASPBERRY_PI_SETUP.md](../BEGINNER_RASPBERRY_PI_SETUP.md)
2. Or use: [INSTALLATION_CHEAT_SHEET.md](../INSTALLATION_CHEAT_SHEET.md)

Both will guide you step-by-step.

---

## 🎓 How the Quick Installer Works

### What `quick-install.sh` Does
```bash
1. Welcome and confirmation
   ↓
2. System checks (OS, internet, storage, memory)
   ↓
3. Update system packages
   ↓
4. Install dependencies
   ↓
5. Download AOJ project
   ↓
6. Run main installation (install_pi.sh)
   ↓
7. Optionally setup Ollama
   ↓
8. Setup kiosk mode
   ↓
9. Prompt to reboot
```

### What `preflight-check.sh` Does
```bash
- Verifies Raspberry Pi OS
- Checks internet connectivity
- Checks storage space
- Checks available memory
- Verifies Python installation
- Verifies Git installation
- Checks sudo permissions
- Checks for display
- Shows summary report
```

---

## 💡 Tips & Tricks

### Skip Ollama if You Don't Want AI
- When asked "Install Ollama?", answer `n`
- Saves 10-15 minutes

### Run Preflight Check First
```bash
./scripts/preflight-check.sh
```
- Takes 10 seconds
- Tells you if system is ready
- Fixes any obvious issues before wasting time

### Monitor Installation Progress
- Installation outputs to terminal
- You'll see progress messages
- Totally normal to see lots of text scrolling

### Keep Terminal Window Open
- Don't close the terminal during installation
- Closing it stops the script
- If you need to pause, press Ctrl+Z (then `fg` to resume)

---

## 🎯 Success Indicators

### Installation Complete When You See:
```
╔════════════════════════════════════════════╗
║     Installation Complete!                ║
╚════════════════════════════════════════════╝

Your AOJ system is ready!

Next step: REBOOT YOUR PI
  sudo reboot
```

### Post-Reboot Success When:
- ✅ System boots without login prompt
- ✅ Desktop appears (auto-login as 'pi')
- ✅ Chromium browser launches
- ✅ AOJ interface displays fullscreen
- ✅ You can access from tablet on Wi-Fi

---

## 📞 Need Help?

### Quick Commands
```bash
# Check if running
sudo systemctl status aoj-production aoj-kiosk

# View logs
sudo journalctl -u aoj-production -f

# Get IP address
hostname -I

# Restart everything
sudo systemctl restart aoj-production aoj-kiosk

# Get to desktop (stop browser)
sudo systemctl stop aoj-kiosk
```

### Full Documentation
- [BEGINNER_RASPBERRY_PI_SETUP.md](../BEGINNER_RASPBERRY_PI_SETUP.md)
- [KIOSK_MODE_QUICK_REFERENCE.md](../KIOSK_MODE_QUICK_REFERENCE.md)
- [GUIDES_START_HERE.md](../GUIDES_START_HERE.md)

---

## ✨ That's It!

**The entire installation is just:**

```bash
curl -sL https://raw.githubusercontent.com/bravo-nineteen/AOJ-Server-main/main/scripts/quick-install.sh | bash
```

Then wait 30-45 minutes and reboot. Your AOJ system will be ready! 🎉

---

**Last Updated:** May 14, 2026
