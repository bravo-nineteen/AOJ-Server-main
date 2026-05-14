# 📚 AOJ Setup Guides - Complete Documentation

**Welcome! This folder contains everything you need to set up AOJ on your Raspberry Pi.**

---

## 🚀 START HERE

### Ultra-Fast Installation (One Command)

**👉 Read:** [ULTRA_QUICK_START.md](ULTRA_QUICK_START.md)

This is THE fastest way. On fresh Raspberry Pi OS:
```bash
curl -sL https://raw.githubusercontent.com/bravo-nineteen/AOJ-Server/main/scripts/quick-install.sh | bash
```
- Installation is fully automated
- Just run one command
- Everything else is automatic
- Takes 30-45 minutes
- Reboot and you're done!

---

### For Absolute Beginners (Zero Linux Knowledge)

**👉 Read:** [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md)

If you prefer step-by-step walkthrough:
- Assumes you've never touched Linux
- Explains every single command
- Takes you from zero to working system
- Includes detailed troubleshooting
- Takes about 1-2 hours

**This guide covers:**
1. Getting hardware ready
2. Flashing Raspberry Pi OS
3. Installing AOJ system
4. Setting up automatic startup
5. Accessing from other devices
6. Basic Linux concepts
7. Troubleshooting problems

---

## 📖 Choose Your Learning Style

### Visual Learner?
**👉 Read:** [INSTALLATION_VISUAL_GUIDE.md](INSTALLATION_VISUAL_GUIDE.md)

Features:
- Flowcharts and diagrams
- Shows what you should see at each step
- Visual representations of the process
- Great if you like pictures!

### Prefer Just the Commands?
**👉 Use:** [INSTALLATION_CHEAT_SHEET.md](INSTALLATION_CHEAT_SHEET.md)

Features:
- Just the commands
- Minimal explanation
- Great to print and keep at desk
- For people who already know Linux

### Want More Advanced Info?
**👉 Read:** [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)

Features:
- Full technical details
- Customization options
- Advanced configuration
- For power users

### Need Daily Operation Tips?
**👉 Read:** [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md)

Features:
- Common daily commands
- How to check if running
- How to restart services
- Quick troubleshooting

---

## 📋 Quick Navigation

### Installation (First Time)

| Goal | Read This |
|------|-----------|
| I'm a total beginner | [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md) |
| I want visual steps | [INSTALLATION_VISUAL_GUIDE.md](INSTALLATION_VISUAL_GUIDE.md) |
| I just want commands | [INSTALLATION_CHEAT_SHEET.md](INSTALLATION_CHEAT_SHEET.md) |
| I want auto-startup | [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md) |

### Daily Operations

| Goal | Read This |
|------|-----------|
| How do I restart it? | [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md) |
| How do I check logs? | [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md) |
| What are those .service files? | [scripts/systemd/README.md](scripts/systemd/README.md) |

### Find Specific Answer

| Problem | Look Here |
|---------|-----------|
| Backend won't start | [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md#troubleshooting) → Troubleshooting |
| Browser shows blank screen | [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md#troubleshooting) → Troubleshooting |
| Can't access from tablet | [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md#part-4-access-and-use-your-system) → Part 4 |
| System won't boot | [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md#troubleshooting) → Troubleshooting |

---

## 📄 All Guides at a Glance

### **BEGINNER_RASPBERRY_PI_SETUP.md** ⭐ START HERE
- **For:** Total beginners, no Linux knowledge
- **Length:** Long but thorough (2000+ lines)
- **Time:** 1-2 hours to complete
- **Covers:**
  - Part 1: Prepare Your Raspberry Pi (Initial Setup)
  - Part 2: Install the AOJ System
  - Part 3: Set Up Automatic Startup (Kiosk Mode)
  - Part 4: Access and Use Your System
  - Troubleshooting section with detailed solutions
  - Important Linux Concepts (explained simply)

### **INSTALLATION_VISUAL_GUIDE.md** 🎨
- **For:** Visual learners who like diagrams
- **Length:** Medium with flowcharts
- **Time:** 1-2 hours to complete
- **Features:**
  - Visual flowcharts
  - Step-by-step with expected output
  - Decision trees for troubleshooting
  - Diagrams of hardware setup

### **INSTALLATION_CHEAT_SHEET.md** 📋
- **For:** Experienced users who know Linux
- **Length:** Short and compact
- **Time:** Quick reference
- **Features:**
  - Just the commands
  - Copy and paste ready
  - Perfect to print
  - Common commands at the bottom

### **KIOSK_MODE_SETUP.md** 🎯
- **For:** Setting up automatic boot to AOJ
- **Length:** Long and detailed
- **Time:** 1 hour setup + reference
- **Covers:**
  - What is kiosk mode
  - Automated setup script
  - Manual advanced setup
  - System architecture explanation
  - Customization options
  - Advanced embedded OS looks

### **KIOSK_MODE_QUICK_REFERENCE.md** ⚡
- **For:** Daily operation after installation
- **Length:** Quick reference guide
- **Time:** Lookup when needed
- **Covers:**
  - System status checks
  - Common restart commands
  - Emergency procedures
  - Performance tips
  - Maintenance schedule

### **scripts/systemd/README.md** 🔧
- **For:** Understanding service files
- **Length:** Medium with examples
- **Time:** Quick reference
- **Covers:**
  - What are service files
  - How to use them
  - Common commands
  - Troubleshooting services

---

## ⏱️ Time Estimates

| Task | Time | Difficulty |
|------|------|-----------|
| Flash SD card | 10 min | Easy |
| Boot Pi and test network | 5 min | Easy |
| Install AOJ system | 20-30 min | Easy |
| (Optional) Install Ollama AI | 10-15 min | Easy |
| Setup kiosk mode | 10-15 min | Medium |
| Test everything | 5 min | Easy |
| **Total First Time** | **1-2 hours** | **Very Easy** |

**After that, it's automatic!**

---

## 🎯 What You'll Get

After following these guides, you'll have:

```
✅ A dedicated command center on your Raspberry Pi
✅ Boots automatically - no login needed
✅ Displays in fullscreen on a monitor
✅ Accessible from tablets/phones on same Wi-Fi
✅ Automatic updates and restarts
✅ Local AI advisor (Ollama)
✅ Full LoRa support for field props
✅ Mission control and team management
✅ Zero manual startup steps needed
```

---

## 🔧 Quick Command Cheat Sheet

### Most Important Commands

```bash
# Check if running
sudo systemctl status aoj-production.service aoj-kiosk.service

# View logs (when something goes wrong)
sudo journalctl -u aoj-production -f

# Get your Pi's IP (to access from other devices)
hostname -I

# Restart everything
sudo systemctl restart aoj-production.service aoj-kiosk.service

# Reboot
sudo reboot

# Stop browser (to get to desktop)
sudo systemctl stop aoj-kiosk.service
```

---

## 📞 Get Help

### 1. Read the Relevant Guide
- Did you hit an error? Read the Troubleshooting section
- Each guide has one!

### 2. Check System Logs
```bash
sudo journalctl -u aoj-production -n 50
```

Logs usually tell you exactly what's wrong.

### 3. Try SSH from Another Computer
```bash
ssh pi@raspberrypi.local
# Password: raspberry
```

This makes debugging easier.

### 4. Google It
- Most Raspberry Pi/Linux issues have been solved before
- Search: "raspberry pi [your error]"

### 5. Check GitHub Issues
- Someone else probably had the same problem

---

## 🗂️ File Structure

```
AOJ-Server/
│
├── 📄 README.md                               ← Main project info
├── 📄 BEGINNER_RASPBERRY_PI_SETUP.md         ← ⭐ START HERE
├── 📄 INSTALLATION_VISUAL_GUIDE.md            ← Visual guide
├── 📄 INSTALLATION_CHEAT_SHEET.md             ← Commands only
├── 📄 KIOSK_MODE_SETUP.md                     ← Auto-boot guide
├── 📄 KIOSK_MODE_QUICK_REFERENCE.md          ← Daily operations
├── 📄 SETUP_GUIDE_INDEX.md                    ← All guides index
│
├── scripts/
│   ├── 📄 systemd/README.md                   ← Service files explained
│   ├── install_pi.sh                          ← Main installer
│   ├── setup_pi_ollama.sh                     ← AI setup
│   ├── setup-kiosk-pi.sh                      ← Auto-kiosk setup
│   ├── start_production.sh                    ← Start backend
│   ├── start_production_kiosk.sh              ← Kiosk-optimized start
│   └── systemd/
│       ├── aoj-production.service             ← Backend service
│       ├── aoj-kiosk.service                  ← Browser service
│       └── aoj-production-wallscreen.service  ← Firefox alternative
│
├── backend/                                    ← Python FastAPI server
├── frontend/                                   ← React web interface
├── docs/                                       ← Technical documentation
└── ...
```

---

## 💡 Pro Tips

1. **Print the cheat sheet** - Keep it at your desk during setup
2. **Use hostname -I** - Easy way to get your Pi's IP
3. **SSH makes it easier** - Set up SSH access from another computer
4. **Bookmark these guides** - You'll need them for daily operations
5. **Check logs first** - 90% of problems are revealed in the logs

---

## ✅ Verification Checklist

**Before saying "it's done," verify:**

- [ ] Pi boots without manual input
- [ ] System loads into AOJ fullscreen
- [ ] Can access from tablet on same Wi-Fi
- [ ] Backend responds to: `curl http://localhost:8000/api/health`
- [ ] Logs are clean: `sudo journalctl -u aoj-production -n 20`
- [ ] System survives a reboot (run: `sudo reboot`)

If all these pass, you're done! ✨

---

## 🚀 You're Ready!

Pick your guide above and get started. Don't worry - these guides are made for people with zero Linux experience.

**Seriously. Start with [BEGINNER_RASPBERRY_PI_SETUP.md](BEGINNER_RASPBERRY_PI_SETUP.md) if you're unsure.**

Good luck! 🎉

---

**Last Updated:** May 2026  
**For detailed info:** See individual guide files  
**For quick commands:** See [INSTALLATION_CHEAT_SHEET.md](INSTALLATION_CHEAT_SHEET.md)
