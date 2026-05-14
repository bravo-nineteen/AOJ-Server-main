# AOJ Systemd Services

These are the "service files" that tell your Raspberry Pi to automatically run AOJ when it boots.

**Think of them like Windows services or tasks that run in the background.**

## Files in This Directory

### `aoj-production.service`

**What it does:** Starts the AOJ backend server (the application)

**When it runs:** Automatically on boot

**Command it runs:** `scripts/start_production.sh`

**What you need to know:**
- This is the main server that handles all the logic
- It runs continuously in the background
- It starts before the browser loads

### `aoj-kiosk.service`

**What it does:** Launches Chromium browser in fullscreen kiosk mode

**When it runs:** After the backend is ready

**What you need to know:**
- This displays the AOJ interface fullscreen on your monitor
- No address bar, no tabs, just the app
- Can't close it without SSH or terminal

### `aoj-production-wallscreen.service` (Alternative)

**What it does:** Launches Firefox for wallscreen displays

**When to use:** If you prefer Firefox or have a landscape screen

**Otherwise:** Ignore this one

---

## How to Use These Files

### Automatic Installation

**Run this script to handle everything automatically:**

```bash
cd ~/AOJ-Server
chmod +x scripts/setup-kiosk-pi.sh
./scripts/setup-kiosk-pi.sh
```

### Manual Installation

**If you want to do it manually:**

1. **Copy the files to systemd:**
   ```bash
   sudo cp aoj-production.service /etc/systemd/system/
   sudo cp aoj-kiosk.service /etc/systemd/system/
   ```

2. **Tell systemd about the new services:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable them to run on boot:**
   ```bash
   sudo systemctl enable aoj-production.service
   sudo systemctl enable aoj-kiosk.service
   ```

4. **Reboot to test:**
   ```bash
   sudo reboot
   ```

---

## Commands to Use

### Check Status

```bash
# Check if backend is running
sudo systemctl status aoj-production.service

# Check if browser is running
sudo systemctl status aoj-kiosk.service

# Check both
sudo systemctl status aoj-production.service aoj-kiosk.service
```

### Start/Stop/Restart

```bash
# Start backend
sudo systemctl start aoj-production.service

# Start browser
sudo systemctl start aoj-kiosk.service

# Restart backend
sudo systemctl restart aoj-production.service

# Restart browser
sudo systemctl restart aoj-kiosk.service

# Restart both
sudo systemctl restart aoj-production.service aoj-kiosk.service
```

### View Logs

```bash
# View last 50 lines of backend log
sudo journalctl -u aoj-production.service -n 50

# View live backend log (press Ctrl+C to stop)
sudo journalctl -u aoj-production.service -f

# View last 50 lines of browser log
sudo journalctl -u aoj-kiosk.service -n 50
```

### Enable/Disable on Boot

```bash
# Enable to run on boot
sudo systemctl enable aoj-production.service
sudo systemctl enable aoj-kiosk.service

# Disable from running on boot
sudo systemctl disable aoj-production.service
sudo systemctl disable aoj-kiosk.service

# Check if enabled
sudo systemctl is-enabled aoj-production.service
```

---

## What Happens on Boot

```
1. Pi powers on
2. Linux kernel loads
3. Systemd starts services (in order)
   a) aoj-production.service starts
      - Waits for network
      - Starts backend on port 8000
      - Server initializes database, LoRa, etc.
   
   b) aoj-kiosk.service starts
      - Waits for backend to be healthy
      - Launches Chromium fullscreen
      - Loads http://localhost:8000
      - Shows AOJ interface on monitor
4. System is ready to use!
```

---

## Understanding Service Files

A service file looks like this:

```ini
[Unit]
Description=AOJ Command OS Backend
After=network.target
# ↑ Tells systemd this needs network to be ready first

[Service]
Type=simple
User=pi
# ↑ Runs as user 'pi' (not root)
WorkingDirectory=/home/pi/AOJ-Server/backend
ExecStart=/home/pi/AOJ-Server/scripts/start_production.sh
# ↑ The command to run
Restart=on-failure
RestartSec=5
# ↑ If it crashes, restart after 5 seconds

[Install]
WantedBy=multi-user.target
# ↑ Start when system reaches multi-user target (normal boot)
```

---

## Troubleshooting

### Service won't start

1. Check the logs:
   ```bash
   sudo journalctl -u aoj-production.service -n 50
   ```

2. Try starting manually:
   ```bash
   sudo systemctl start aoj-production.service
   sudo systemctl status aoj-production.service
   ```

3. Check if port is already in use:
   ```bash
   sudo lsof -i :8000
   ```

### Browser starts before backend is ready

- This is handled by `ExecStartPre` which waits for the health check
- If it fails, check backend logs:
  ```bash
  sudo journalctl -u aoj-production.service -f
  ```

### Service keeps restarting

- Check logs for the error
- May be port conflict or permission issue
- Try restarting manually and checking logs

### Need to edit a service file

```bash
# Edit aoj-production.service
sudo nano /etc/systemd/system/aoj-production.service

# After editing, reload
sudo systemctl daemon-reload

# Restart the service
sudo systemctl restart aoj-production.service
```

---

## Getting Back to Desktop

If you're stuck in fullscreen kiosk mode:

```bash
# Stop the browser service
sudo systemctl stop aoj-kiosk.service
```

Now you should see the desktop. To go back to kiosk:

```bash
sudo systemctl start aoj-kiosk.service
```

---

## For More Information

- **Beginner guide:** [BEGINNER_RASPBERRY_PI_SETUP.md](../BEGINNER_RASPBERRY_PI_SETUP.md)
- **Kiosk setup:** [KIOSK_MODE_SETUP.md](../KIOSK_MODE_SETUP.md)
- **Quick reference:** [KIOSK_MODE_QUICK_REFERENCE.md](../KIOSK_MODE_QUICK_REFERENCE.md)
- **All guides:** [SETUP_GUIDE_INDEX.md](../SETUP_GUIDE_INDEX.md)

---

**Last Updated:** May 2026
