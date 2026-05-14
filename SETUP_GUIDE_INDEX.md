# AOJ Setup Guide Index - Find Your Answer

**Use this to find the right guide for your situation.**

---

## ⚡ I Just Want It Done (One Command)

### **FASTEST WAY:** [ULTRA_QUICK_START.md](ULTRA_QUICK_START.md)

On fresh Raspberry Pi OS, just run:

```bash
curl -sL https://raw.githubusercontent.com/bravo-nineteen/AOJ-Server/main/scripts/quick-install.sh | bash
```

**This guide explains:**
- Fully automated installation
- Takes 30-45 minutes
- One command does everything
- Perfect if you don't want to think

---

## ✅ Check System Before Installing (Optional)

### **First Run This:** [Preflight Check](INSTALLATION_CHEAT_SHEET.md#quick-command-reference)

```bash
chmod +x scripts/preflight-check.sh
./scripts/preflight-check.sh
```

**Verifies:**
- Internet connection
- Storage space
- Memory available
- Python installed
- Git installed
- Permissions OK

---

## I'm a Beginner and Don't Know Linux

### **START HERE:** [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md)

This guide:
- Assumes you've never used Linux
- Explains every command in detail
- Teaches you Linux basics
- Has troubleshooting for common problems
- Takes 1-2 hours to complete

**Read this first.** Seriously. It's designed for you.

---

## I Want Visual Step-by-Step Instructions

### Check: [INSTALLATION_VISUAL_GUIDE.md](INSTALLATION_VISUAL_GUIDE.md)

This guide:
- Has diagrams and flowcharts
- Shows what you should see at each step
- Explains what's happening visually
- Great for visual learners

---

## I Just Want the Commands (Copy & Paste)

### Check: [INSTALLATION_CHEAT_SHEET.md](INSTALLATION_CHEAT_SHEET.md)

This guide:
- Just the commands, minimal explanation
- Good to print and keep at desk
- Fast reference while installing
- For people who understand Linux already

---

## I Want Automatic Startup (Kiosk Mode - No Login)

### Check: [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)

This guide explains:
- How to make Pi boot directly into AOJ
- No login screen required
- System acts like embedded OS
- How to manage kiosk mode after setup

---

## I Need Daily Operation Commands

### Check: [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md)

This has:
- How to check if running
- How to restart services
- How to view logs
- Common troubleshooting
- Daily maintenance tips

---

## I'm Having Specific Problems

### Backend won't start?
```
1. Check logs: sudo journalctl -u aoj-production -n 50
2. Check port: sudo lsof -i :8000
3. Read: BEGINNER_RASPBERRY_PI_SETUP.md → Troubleshooting
```

### Browser shows blank screen?
```
1. Wait 20-30 seconds (first startup is slow)
2. Refresh: Press F5
3. Check backend: curl http://localhost:8000/api/health
4. Read: KIOSK_MODE_QUICK_REFERENCE.md → Troubleshooting
```

### Can't access from tablet?
```
1. Get Pi's IP: hostname -I
2. Try: http://192.168.X.X:8000
3. Or try: http://raspberrypi.local:8000
4. Read: BEGINNER_RASPBERRY_PI_SETUP.md → Part 4
```

### System won't boot?
```
1. Check: sudo journalctl -n 100
2. Try: sudo systemctl stop aoj-kiosk
3. Reboot: sudo reboot
4. Read: KIOSK_MODE_QUICK_REFERENCE.md → Troubleshooting
```

---

## Choosing Your Setup

### What's Your Situation?

**"I'm a total beginner and need hand-holding"**
→ Read: [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md)
→ Then: [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)

**"I know Linux but want a visual guide"**
→ Read: [INSTALLATION_VISUAL_GUIDE.md](INSTALLATION_VISUAL_GUIDE.md)
→ Then: [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)

**"I know what I'm doing, just give me commands"**
→ Use: [INSTALLATION_CHEAT_SHEET.md](INSTALLATION_CHEAT_SHEET.md)

**"I just need to operate it day-to-day"**
→ Use: [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md)

**"I need more technical info"**
→ Read: [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)
→ Also: [docs/DEPLOYMENT_PI.md](docs/DEPLOYMENT_PI.md)

---

## Document Structure

```
BEGINNER_RASPBERRY_PI_SETUP.md
├── What You'll Need (Hardware)
├── Part 1: Prepare Your Raspberry Pi
├── Part 2: Install the AOJ System
├── Part 3: Set Up Automatic Startup
├── Part 4: Access and Use Your System
├── Troubleshooting
└── Linux Concepts Explained

INSTALLATION_VISUAL_GUIDE.md
├── Overall Process (flowchart)
├── Step 1: Prepare SD Card (with diagram)
├── Step 2: Boot the Raspberry Pi
├── Step 3: Download AOJ Project
├── Step 4: Install Everything
├── Step 5: Add Offline AI
├── Step 6: Setup Automatic Startup
├── Step 7: Reboot and Verify
├── Step 8: Access from Other Devices
├── Step 9: Troubleshooting (decision trees)
└── Step 10: Daily Operation

INSTALLATION_CHEAT_SHEET.md
├── Part 1: Prepare SD Card (commands only)
├── Part 2: Boot and Test
├── Part 3: Install AOJ
├── Part 4: Setup Kiosk Mode
├── Part 5-7: Enable Services
├── Quick Commands for Daily Use
├── Emergency Commands
├── Error Messages & Fixes
└── File Locations

KIOSK_MODE_SETUP.md
├── Overview
├── Hardware Requirements
├── Prerequisites
├── Automated Setup (Recommended)
├── Manual Setup (Advanced)
├── System Architecture
├── Operation & Maintenance
├── Customization
├── Troubleshooting
└── Advanced: Custom Embedded OS Look

KIOSK_MODE_QUICK_REFERENCE.md
├── System Status
├── Common Operations
├── Troubleshooting
├── Performance Tips
├── System Maintenance
├── Contact & Support
└── Quick Commands
```

---

## Quick Command Reference

### Most Important Commands

```bash
# Check if system is running
sudo systemctl status aoj-production aoj-kiosk

# View live logs (when something goes wrong)
sudo journalctl -u aoj-production -f

# Get your Pi's IP address (to access from other devices)
hostname -I

# Restart everything
sudo systemctl restart aoj-production aoj-kiosk

# Reboot the system
sudo reboot

# Stop browser (to get back to desktop)
sudo systemctl stop aoj-kiosk
```

---

## Reading Tips

1. **Start with the beginner guide** — don't skip it just because you know some tech
2. **Use the cheat sheet** — bookmark it or print it
3. **Keep the quick reference handy** — for daily operations
4. **Check logs when stuck** — `sudo journalctl -u aoj-production -f`
5. **Google the error message** — usually someone else had the same issue

---

## File Locations in This Project

```
AOJ-Server/
├── BEGINNER_RASPBERRY_PI_SETUP.md     ← START HERE (beginners)
├── INSTALLATION_VISUAL_GUIDE.md        ← Visual flowcharts
├── INSTALLATION_CHEAT_SHEET.md         ← Commands only (print this)
├── KIOSK_MODE_SETUP.md                 ← Auto-startup guide
├── KIOSK_MODE_QUICK_REFERENCE.md      ← Daily operations
├── README.md                            ← Main project info
├── docs/
│   ├── DEPLOYMENT_PI.md                 ← Technical details
│   └── ...
├── scripts/
│   ├── install_pi.sh                    ← Main installer
│   ├── setup_pi_ollama.sh               ← AI setup
│   ├── setup-kiosk-pi.sh                ← Kiosk automation
│   ├── start_production.sh              ← Start server
│   ├── start_production_kiosk.sh        ← Kiosk-optimized startup
│   └── systemd/
│       ├── aoj-production.service       ← Backend service
│       ├── aoj-kiosk.service            ← Browser service
│       └── aoj-production-wallscreen.service
└── ...
```

---

## Common Questions Answered

### "How long does installation take?"
- Total: 1-2 hours for first-time setup
- Breakdown: 10 min prep, 30 min install, 20 min kiosk setup, rest is waiting/testing

### "Do I need Linux knowledge?"
- No! The BEGINNER_RASPBERRY_PI_SETUP.md guide teaches you everything

### "Can I do this on Windows PC instead?"
- Yes! Use README.md → "Quick Install — Windows"

### "What if I mess up?"
- Just re-flash the SD card and start over (takes 15 minutes)

### "How do I update the system?"
- Instructions in KIOSK_MODE_QUICK_REFERENCE.md

### "Can I access from my phone?"
- Yes! Go to http://raspberrypi.local:8000 from your phone's browser on the same Wi-Fi

### "What if I forget the password?"
- Flash the SD card again with a new password

### "Is it secure?"
- It's a local network system only (not exposed to internet by default)
- Same security as any local network device

---

## Getting Help

If you're stuck:

1. **Check the relevant guide** — find the section for your problem
2. **View the logs** — `sudo journalctl -u aoj-production -n 50`
3. **Try the troubleshooting section** — each guide has one
4. **Google the error** — "raspberry pi [your error]"
5. **Check GitHub issues** — someone might have had the same problem
6. **SSH from another computer** — easier to debug remotely:
   ```bash
   ssh pi@raspberrypi.local
   # password: raspberry
   ```

---

## Document Versions

| Document | For | Time | Difficulty |
|---|---|---|---|
| BEGINNER_RASPBERRY_PI_SETUP.md | Total beginners | 1-2 hours | Very Easy |
| INSTALLATION_VISUAL_GUIDE.md | Visual learners | 1-2 hours | Easy |
| INSTALLATION_CHEAT_SHEET.md | Experienced users | 30 min | Medium |
| KIOSK_MODE_SETUP.md | Detailed setup | 1 hour | Medium |
| KIOSK_MODE_QUICK_REFERENCE.md | Daily operations | Reference | Easy |
| docs/DEPLOYMENT_PI.md | Technical details | Reference | Hard |

---

**Pick your guide, take your time, and follow the steps. You've got this!** 🚀

Last Updated: May 2026
