# AOJ Installation Cheat Sheet for Beginners

**Print this out or keep it handy while installing!**

---

## PART 1: Prepare SD Card (On Your Computer)

1. Download Raspberry Pi Imager: https://www.raspberrypi.com/software/
2. Flash Raspberry Pi OS 64-bit to SD card
3. Before writing, click settings and set:
   - Hostname: `raspberrypi`
   - Username: `pi`
   - Password: `raspberry`
   - Wi-Fi: (your network)
   - Timezone: (your timezone)

---

## PART 2: Boot and Test Connection

**On the Raspberry Pi:**

```bash
ping 8.8.8.8
```

Press `Ctrl+C` to stop. Should show "bytes from" if connected.

---

## PART 3: Install AOJ (Main Installation - 20-30 minutes)

**Open Terminal on Pi and run these commands:**

```bash
cd ~
git clone https://github.com/bravo-nineteen/AOJ-Server.git
cd AOJ-Server
chmod +x scripts/install_pi.sh
./scripts/install_pi.sh
```

**Answer: `raspberry` if asked for password**

Wait for it to finish. Should see:
```
[AOJ] Installation complete.
```

---

## PART 4: Optional - Setup AI (Ollama)

```bash
chmod +x scripts/setup_pi_ollama.sh
./scripts/setup_pi_ollama.sh
```

Takes 5-10 minutes.

---

## PART 5: Test It Works (Optional but Recommended)

```bash
./scripts/start_production.sh
```

Open browser on your Pi and go to: `http://localhost:8000`

Should see AOJ system interface!

Press `Ctrl+C` to stop.

---

## PART 6: Setup Automatic Startup (Kiosk Mode)

### Step 1: Create Services Directory

```bash
mkdir -p scripts/systemd
```

### Step 2: Copy Service Files

```bash
sudo cp scripts/systemd/aoj-production.service /etc/systemd/system/
sudo cp scripts/systemd/aoj-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
```

**Answer: `raspberry` if asked for password**

### Step 3: Setup Auto-Login

```bash
sudo nano /etc/lightdm/lightdm.conf.d/99-autologin.conf
```

**Type/Paste this:**
```
[Seat:*]
autologin-user=pi
autologin-user-session=LXDE
```

**Save with:** `Ctrl+X` then `y` then `Enter`

### Step 4: Create X11 Startup Script

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

**Paste entire block as-is, press Enter**

### Step 5: Enable Services on Boot

```bash
sudo systemctl enable aoj-production.service
sudo systemctl enable aoj-kiosk.service
```

### Step 6: Verify Services Enabled

```bash
sudo systemctl is-enabled aoj-production.service
sudo systemctl is-enabled aoj-kiosk.service
```

**Both should say:** `enabled`

### Step 7: Test Services

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

### Step 8: Reboot to Test

```bash
sudo reboot
```

**Wait 30-60 seconds. System should boot directly into AOJ!**

---

## PART 7: Access from Other Devices

**Find Pi's IP:**
```bash
hostname -I
```

**From tablet/laptop, go to:**
```
http://192.168.X.X:8000
```
(Replace X with IP address)

**Or use:**
```
http://raspberrypi.local:8000
```

---

## QUICK COMMANDS FOR DAILY USE

### Check if Running
```bash
sudo systemctl status aoj-production
```

### Restart Backend
```bash
sudo systemctl restart aoj-production
```

### Restart Browser
```bash
sudo systemctl restart aoj-kiosk
```

### View Live Logs
```bash
sudo journalctl -u aoj-production -f
```

### Reboot Pi
```bash
sudo reboot
```

### Get to Desktop (Stop Browser)
```bash
sudo systemctl stop aoj-kiosk
```

### Restart Everything
```bash
sudo systemctl restart aoj-production aoj-kiosk
```

### Check Space
```bash
df -h
```

### Check Temperature
```bash
vcgencmd measure_temp
```

---

## EMERGENCY COMMANDS

### If Browser Won't Close
```bash
sudo systemctl stop aoj-kiosk
```

### If Backend Crashes
```bash
sudo systemctl restart aoj-production
```

### If System Locks Up
- Hold power button 10 seconds
- Power back on

### Get IP Address Again
```bash
hostname -I
```

### SSH from Another Computer
```bash
ssh pi@192.168.X.X
```
(Password: `raspberry`)

---

## ERROR MESSAGES & FIXES

### "command not found"
- Check you typed exactly right (case-sensitive)
- Make sure you're in `/home/pi/AOJ-Server`
- Use: `cd ~/AOJ-Server` to go there

### "Permission denied"
- Add `sudo` to start of command
- Change from: `systemctl restart aoj-production`
- To: `sudo systemctl restart aoj-production`

### "Port 8000 already in use"
```bash
sudo systemctl restart aoj-production
```

### Blank Screen on Browser
- Wait 20-30 seconds
- Refresh browser (F5)
- Check: `sudo journalctl -u aoj-production -n 20`

### Can't Connect Over Network
- Check IP: `hostname -I`
- Try: `http://raspberrypi.local:8000` instead
- Make sure on same Wi-Fi network

---

## FILES LOCATIONS

- **Main project:** `/home/pi/AOJ-Server`
- **Backend:** `/home/pi/AOJ-Server/backend`
- **Frontend:** `/home/pi/AOJ-Server/frontend`
- **Database:** `/home/pi/AOJ-Server/backend/data`
- **Services:** `/etc/systemd/system`
- **Logs:** View with `sudo journalctl`

---

## IMPORTANT: Always Use Sudo!

Many commands need administrator access. When you see `sudo` at the start, use it. Example:
```bash
sudo systemctl restart aoj-production
```

---

## Getting Help

1. **Check logs:** `sudo journalctl -u aoj-production -n 50`
2. **Main guide:** See `BEGINNER_RASPBERRY_PI_SETUP.md`
3. **Quick reference:** See `KIOSK_MODE_QUICK_REFERENCE.md`
4. **Full documentation:** See `KIOSK_MODE_SETUP.md`

---

**Password Reminder:** `raspberry`

**Good luck! 🚀**
