# AOJ Installation: Visual Step-by-Step Guide

**This is a visual companion to the beginner's guide. Follow these steps in order.**

---

## The Overall Process

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Prepare SD Card                                 │
│ (On your laptop/computer)                               │
│ Flash Raspberry Pi OS using Raspberry Pi Imager         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Boot Raspberry Pi                               │
│ Connect HDMI monitor, keyboard, mouse, power            │
│ System boots into desktop automatically                 │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Download AOJ Project                            │
│ (In terminal on Pi)                                     │
│ git clone https://github.com/.../AOJ-Server.git        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Run Installation                                │
│ (In terminal on Pi)                                     │
│ ./scripts/install_pi.sh                                 │
│ Takes 20-30 minutes, installs all dependencies          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 5: (Optional) Setup Ollama                         │
│ (In terminal on Pi)                                     │
│ ./scripts/setup_pi_ollama.sh                            │
│ Adds offline AI capabilities                            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 6: Setup Automatic Startup                         │
│ (In terminal on Pi)                                     │
│ Create service files, enable auto-login, reboot         │
│ Takes 10 minutes                                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 7: Verify it Works                                 │
│ Pi boots directly into AOJ system                       │
│ Browser launches automatically                          │
│ System is ready to use!                                 │
└─────────────────────────────────────────────────────────┘
```

---

## STEP 1: Prepare SD Card (On Your Computer)

### What You're Doing
Creating the operating system for the Raspberry Pi by putting it on an SD card.

### Visual Overview

```
Your Computer              Raspberry Pi
┌──────────────┐          ┌──────────────┐
│ Laptop/PC    │          │ Raspberry Pi │
│              │          │              │
│ 1. Download  │          │  (Empty)     │
│    Imager    │          │              │
│              │          │              │
│ 2. Install   │          │              │
│    OS on SD  │          │              │
└──────────────┘          └──────────────┘
       ▲                           │
       │                           │
       └───── Insert SD ───────────┘
              (now has OS)
```

### Step-by-Step

**On your laptop or desktop computer:**

1. Open browser and go to: **https://www.raspberrypi.com/software/**

2. Click **"Download Raspberry Pi Imager"** for your computer type:
   - Windows
   - Mac (Intel or Apple Silicon)
   - Linux

3. Install Raspberry Pi Imager like any other program

4. **Open Raspberry Pi Imager**

5. Click **"Choose Device"** and select:
   - `Raspberry Pi 4` (or your Pi model)

6. Click **"Choose OS"** and select:
   - `Raspberry Pi OS (64-bit)`
   - (This is the first option with a Raspberry logo)

7. Click **"Choose Storage"** and select:
   - Your microSD card
   - ⚠️ **WARNING: This will erase the card!**

8. Click **"Edit Settings"** (gear icon in bottom right corner)

9. **In Settings, check these boxes and fill in:**

   ```
   ☑ Set hostname:
     raspberrypi
   
   ☑ Set username and password:
     Username: pi
     Password: raspberry
   
   ☑ Configure wireless LAN:
     SSID: [Your Wi-Fi network name]
     Password: [Your Wi-Fi password]
   
   ☑ Set locale:
     Timezone: [Your timezone]
     Keyboard layout: [Your keyboard]
   
   ☑ Skip first-run wizard
   ```

10. Click **"Save"**

11. Click **"Write"** and wait (5-10 minutes)

12. When done, **safely eject** the SD card from your computer

13. **Insert into Raspberry Pi** (small slot on bottom of board)

---

## STEP 2: Boot the Raspberry Pi

### Visual Setup

```
Monitor                  Raspberry Pi              Power
  │                        │                        │
  │(HDMI)                  │(USB)                   │(5V)
  └──────────┐    ┌────────┘    ┌──────────────────┘
             │    │             │
          ┌──┴────┴─────┬───────┴──┐
          │   Keyboard  │  Mouse   │
          └─────────────┴──────────┘
```

### Step-by-Step

1. **Connect to your Pi:**
   - Monitor to HDMI port
   - Keyboard to USB port
   - Mouse to USB port
   - Power adapter to power port

2. **Plug in power** — Pi will start automatically (no power button!)

3. **Wait 30-60 seconds** for desktop to appear

4. You should see a desktop similar to Windows or Mac

---

## STEP 3: Download AOJ Project

### What You're Doing
Getting the AOJ Command OS software from the internet and putting it on your Pi.

### Step-by-Step

1. **Open Terminal** on your Pi:
   - Right-click desktop → "Open in Terminal"
   - Or find the terminal icon in the taskbar

2. **You should see:**
   ```
   pi@raspberrypi:~ $
   ```
   This is the command prompt. It means the terminal is ready.

3. **Copy and paste this:**
   ```bash
   cd ~
   git clone https://github.com/bravo-nineteen/AOJ-Server.git
   cd AOJ-Server
   ```

4. **Press Enter** after the last line

5. **Wait 1-2 minutes** while it downloads (~200MB)

6. **You should see:**
   ```
   pi@raspberrypi:~/AOJ-Server $
   ```

---

## STEP 4: Install Everything

### What You're Doing
Running an automated script that downloads and installs all the software needed to run AOJ.

### What Gets Installed

```
┌──────────────────────┐
│ AOJ Installation     │
├──────────────────────┤
│ ✓ Python             │
│ ✓ Node.js            │
│ ✓ Dependencies       │
│ ✓ Frontend (React)   │
│ ✓ Backend (FastAPI)  │
│ ✓ Database (SQLite)  │
└──────────────────────┘
```

### Step-by-Step

1. **You should be in terminal at:**
   ```
   pi@raspberrypi:~/AOJ-Server $
   ```

2. **Copy and paste this:**
   ```bash
   chmod +x scripts/install_pi.sh
   ./scripts/install_pi.sh
   ```

3. **Press Enter**

4. **The script will:**
   - Update system packages (2-5 minutes)
   - Ask for your password → type: `raspberry` and press Enter
   - Download and install software (10-20 minutes)
   - Compile the frontend (5 minutes)

5. **You'll see lots of text** scrolling past — this is normal!

6. **When complete, you should see:**
   ```
   [AOJ] Installation complete.
   [AOJ] Backend virtual environment: /home/pi/AOJ-Server/backend/.venv
   [AOJ] Frontend build output: /home/pi/AOJ-Server/frontend/dist
   ```

7. **If you see errors,** try running it again

---

## STEP 5: (Optional) Add Offline AI

### What You're Doing
Installing Ollama so the system can use AI features without needing the internet.

### Step-by-Step

1. **In terminal, copy and paste:**
   ```bash
   chmod +x scripts/setup_pi_ollama.sh
   ./scripts/setup_pi_ollama.sh
   ```

2. **Press Enter**

3. **This will:**
   - Download Ollama (10-15 minutes, depending on internet)
   - Download an AI model (5-10 minutes)
   - Set it up to run automatically

4. **You can skip this if you don't want AI features**

---

## STEP 6: Setup Automatic Startup

### What You're Doing
Setting up the system so it automatically starts AOJ whenever the Pi boots up, without any human intervention.

### Diagram: What Happens on Boot

```
Power On
   │
   ▼
Raspberry Pi starts up
   │
   ▼
Linux loads (no login needed)
   │
   ▼
Backend service starts → runs AOJ server
   │
   ▼
Browser service starts → launches Chromium
   │
   ▼
AOJ system appears fullscreen on monitor
   │
   ▼
Ready to use!
```

### Step-by-Step

**In terminal, run these commands one by one:**

#### Command 1:
```bash
mkdir -p scripts/systemd
```

#### Command 2:
```bash
sudo cp scripts/systemd/aoj-production.service /etc/systemd/system/
sudo cp scripts/systemd/aoj-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Type password: `raspberry` if asked

#### Command 3:
```bash
sudo nano /etc/lightdm/lightdm.conf.d/99-autologin.conf
```

A text editor will open. **Type:**
```
[Seat:*]
autologin-user=pi
autologin-user-session=LXDE
```

**Save by pressing:** `Ctrl+X` then `y` then `Enter`

#### Command 4:
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

**Paste entire block as-is and press Enter**

#### Command 5:
```bash
sudo systemctl enable aoj-production.service
sudo systemctl enable aoj-kiosk.service
```

#### Command 6: Verify
```bash
sudo systemctl is-enabled aoj-production.service
sudo systemctl is-enabled aoj-kiosk.service
```

**Both should say:** `enabled`

#### Command 7: Test
```bash
sudo systemctl start aoj-production.service
sleep 5
sudo systemctl start aoj-kiosk.service
```

**Check status:**
```bash
sudo systemctl status aoj-production.service
sudo systemctl status aoj-kiosk.service
```

**Both should say:** `Active: active (running)`

**If you see errors, check:** `sudo journalctl -u aoj-production -n 20`

---

## STEP 7: Reboot and Verify

### What You're Doing
Restarting the Pi to make sure everything starts automatically.

### Step-by-Step

1. **In terminal, type:**
   ```bash
   sudo reboot
   ```

2. **Press Enter** — Pi will restart

3. **Wait 30-60 seconds**

4. **You should see:**
   - Black screen
   - Linux boot text
   - Browser starting
   - AOJ system interface appearing fullscreen

5. **Success!** Your system is now running automatically! 🎉

---

## STEP 8: Access from Other Devices

### What You're Doing
Connecting to the AOJ system from tablets, phones, or other computers on your network.

### Finding Your Pi's IP Address

1. **On your Pi, open Terminal**

2. **Type:**
   ```bash
   hostname -I
   ```

3. **You'll see something like:**
   ```
   192.168.1.50
   ```

4. **Remember this number**

### Connect from Another Device

**On your tablet, phone, or laptop:**

1. Open web browser

2. Go to:
   ```
   http://192.168.1.50:8000
   ```
   (Replace 192.168.1.50 with your Pi's IP)

3. Or try:
   ```
   http://raspberrypi.local:8000
   ```

4. You should see the AOJ system!

### Network Diagram

```
WiFi Router
    │
    ├── Raspberry Pi (192.168.1.50)
    │       │
    │       └── Running AOJ Server
    │
    ├── Tablet (192.168.1.100)
    │       │
    │       └── Connects to: http://192.168.1.50:8000
    │
    ├── Phone (192.168.1.101)
    │       │
    │       └── Connects to: http://192.168.1.50:8000
    │
    └── Laptop (192.168.1.102)
            │
            └── Connects to: http://192.168.1.50:8000
```

---

## STEP 9: Troubleshooting

### Problem: Screen stays black after reboot

```
Did this happen?
    │
    ├─ Yes ─────┬─ Wait 60 seconds (might just be loading)
    │           ├─ Press Alt+F2 (might wake screen)
    │           └─ Check if backend is working:
    │               ssh pi@raspberrypi.local
    │               sudo systemctl status aoj-production
    │
    └─ No ──── Check other issues below
```

### Problem: Browser won't show AOJ

```
Did this happen?
    │
    ├─ Shows blank/gray ──┬─ Wait 30 seconds
    │                     ├─ Refresh page (F5)
    │                     └─ Check: sudo journalctl -u aoj-production -n 20
    │
    ├─ Shows error ───────┬─ Check internet connection
    │                     └─ Check IP address: hostname -I
    │
    └─ Won't load at all ─ Check: http://raspberrypi.local:8000/api/health
```

### Problem: Can't access from tablet

```
Did this happen?
    │
    ├─ IP address not found ──┬─ Get Pi's IP: hostname -I
    │                         └─ Use that IP: http://192.168.X.X:8000
    │
    ├─ Can't find Pi on network ─ Make sure tablet on same Wi-Fi
    │                             Try: http://raspberrypi.local:8000
    │
    └─ Connection refused ────── Check backend: sudo systemctl status aoj-production
```

### Get Back to Desktop (Stop Fullscreen Browser)

```bash
sudo systemctl stop aoj-kiosk
```

Now you can access the desktop.

---

## STEP 10: Daily Operation

### Starting System (Automatic After Reboot)

The system starts automatically when you plug in power!

No manual steps needed. 🎉

### Emergency Access

If system gets stuck:

1. **SSH from another computer:**
   ```bash
   ssh pi@raspberrypi.local
   ```
   Password: `raspberry`

2. **Or press:** `Alt+Ctrl+F2` for command prompt

### Common Commands

```bash
sudo systemctl restart aoj-production  # Restart backend
sudo systemctl restart aoj-kiosk       # Restart browser
sudo reboot                             # Reboot system
sudo journalctl -u aoj-production -f   # View live logs
```

---

## Summary

```
┌─────────────────────────────────────────────┐
│ You have successfully:                      │
├─────────────────────────────────────────────┤
│ ✓ Installed Raspberry Pi OS                 │
│ ✓ Installed AOJ Command OS                  │
│ ✓ Set up automatic startup (kiosk mode)     │
│ ✓ Verified it works                         │
│ ✓ Connected from other devices              │
├─────────────────────────────────────────────┤
│ Your system is now a dedicated embedded     │
│ command center that starts automatically!   │
└─────────────────────────────────────────────┘
```

---

**Need help?** Check `BEGINNER_RASPBERRY_PI_SETUP.md` for detailed explanations!

**Quick commands?** Check `INSTALLATION_CHEAT_SHEET.md` to print and keep nearby!
