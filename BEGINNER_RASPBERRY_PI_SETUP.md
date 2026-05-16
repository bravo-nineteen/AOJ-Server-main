# AOJ Command OS - Beginner's Complete Setup Guide for Raspberry Pi

**This guide assumes you have ZERO Linux experience. We'll explain everything.**

---

## Table of Contents

1. [What You'll Need (Hardware)](#what-youll-need-hardware)
2. [Part 1: Prepare Your Raspberry Pi (Initial Setup)](#part-1-prepare-your-raspberry-pi-initial-setup)
3. [Part 2: Install the AOJ System](#part-2-install-the-aoj-system)
4. [Part 3: Set Up Automatic Startup (Kiosk Mode)](#part-3-set-up-automatic-startup-kiosk-mode)
5. [Part 4: Access and Use Your System](#part-4-access-and-use-your-system)
6. [Troubleshooting](#troubleshooting)
7. [Important Linux Concepts](#important-linux-concepts)

---

## What You'll Need (Hardware)

✅ **Absolutely Required:**
- Raspberry Pi 4 or newer (with at least 2GB RAM, 4GB is better)
- microSD card (32GB or larger, fast speed recommended)
- Power adapter for Raspberry Pi (5V, 3A or better)
- USB keyboard and mouse
- HDMI cable and monitor/TV screen
- Network cable or Wi-Fi router nearby

✅ **Highly Recommended:**
- A second computer (laptop/desktop) for easier management via SSH
- Raspberry Pi fan or case with cooling (Pi gets hot!)
- Uninterruptible Power Supply (UPS) if this is for critical field use

---

## Part 1: Prepare Your Raspberry Pi (Initial Setup)

### Step 1a: Get Raspberry Pi OS on Your SD Card

This is the operating system that will run on your Pi. Think of it like Windows or Mac, but for Raspberry Pi.

**What you're doing:** Copying Raspberry Pi OS (a Linux operating system) onto your microSD card so the Pi can boot up and run.

1. **On your laptop/computer** (not the Pi), go to: https://www.raspberrypi.com/software/

2. **Download** "Raspberry Pi Imager" for your computer's operating system (Windows, Mac, or Linux)

3. **Install and run** Raspberry Pi Imager

4. **In the Imager window:**
   - Click "Choose Device" → Select "Raspberry Pi 4" (or your Pi model)
   - Click "Choose OS" → Select "Raspberry Pi OS (64-bit)" (the first one in the list)
   - Click "Choose Storage" → Select your microSD card
   - Click "Edit Settings" (the gear icon at bottom right)

5. **In Settings window:**
   - Check "Set hostname" → type: `raspberrypi`
   - Check "Set username and password":
     - Username: `pi`
     - Password: `raspberry` (you can change this later)
   - Check "Configure wireless LAN":
     - SSID: (your Wi-Fi network name)
     - Password: (your Wi-Fi password)
   - Check "Set locale":
     - Timezone: (select your timezone)
     - Keyboard layout: (select your keyboard)
   - Check "Skip first-run wizard"
   - Click "Save"

6. **Click "Write"** and wait for it to finish (5-10 minutes)

7. **Safely eject** the microSD card when done

### Step 1b: Boot Up Your Raspberry Pi

**What you're doing:** Starting up the Pi and connecting to it for the first time.

1. **Insert** the microSD card into your Pi (small slot on the bottom)

2. **Connect monitor and keyboard** to your Pi

3. **Plug in the power adapter** - the Pi will start automatically (no power button!)

4. **Wait** 30-60 seconds for the desktop to appear

5. **You should see** a desktop similar to Windows or Mac

### Step 1c: Verify Your Internet Connection

**What you're doing:** Checking that your Pi can reach the internet, which is essential for downloading software.

1. **Open a terminal window** (black box icon in taskbar, or search for "Terminal")

2. **Copy and paste this command:**
```bash
ping 8.8.8.8
```

3. **Press Enter**

You should see lines appearing. If you see "connection timeout" or "unreachable," your internet isn't working. Fix this first!

**To stop the ping, press: `Ctrl+C`** (hold Control and press C)

---

## Part 2: Install the AOJ System

### What We're About to Do

We're going to:
1. Download the AOJ project from GitHub
2. Install Python (programming language) and Node.js (web technology)
3. Build and compile the system
4. Test that it works

### Step 2a: Open Terminal and Navigate to Home

**What you're doing:** Opening a command-line interface where you can type commands. This is called a "terminal" or "console." Think of it like the command prompt in Windows.

1. **Open Terminal:** Right-click on desktop → Open in Terminal
   (Or click the terminal icon if you see one)

2. **You'll see something like:**
```
pi@raspberrypi:~ $
```

This means:
- `pi` = your username
- `raspberrypi` = your computer name
- `~` = you're in your home directory (home folder)
- `$` = ready for a command

### Step 2b: Download AOJ System

**What you're doing:** Copying the entire AOJ project from the internet to your Pi.

**In your terminal, type this command exactly:**

```bash
cd ~
git clone https://github.com/bravo-nineteen/AOJ-Server.git
cd AOJ-Server
```

**Press Enter after each line** (or paste all three and press Enter once)

**What's happening:**
- `cd ~` = change to home directory
- `git clone ...` = download the project (this takes 1-2 minutes)
- `cd AOJ-Server` = go into the project folder

**After it's done, you should see:**
```
pi@raspberrypi:~/AOJ-Server $
```

The `$` means it's ready for the next command. If you see an error, check your internet connection.

### Step 2c: Run the Installation Script

**What you're doing:** Running an automated script that installs all necessary software (Python, Node.js, dependencies, etc.). This is the main installation - it will take 15-30 minutes.

**In your terminal, run:**

```bash
chmod +x scripts/install_pi.sh
./scripts/install_pi.sh
```

**What's happening:**
- `chmod +x` = make the script executable (give it permission to run)
- `./scripts/install_pi.sh` = run the installation script
- The script will automatically install everything with `sudo` (administrator privileges)

**You might see:**
- Lots of text scrolling past (normal!)
- A question asking for your password (type: `raspberry`)
- Progress bars and `[###...]` indicators
- Warnings in yellow (usually OK)
- Errors should be red and obvious

**Once it's done, you should see:**
```
[AOJ] Installation complete.
[AOJ] Backend virtual environment: /home/pi/AOJ-Server/backend/.venv
[AOJ] Frontend build output: /home/pi/AOJ-Server/frontend/dist
```

**If you see errors:**
- Try running it again: `./scripts/install_pi.sh`
- Check [Troubleshooting](#troubleshooting) section

### Step 2d: Setup Ollama (Optional but Recommended for AI Features)

**What you're doing:** Installing Ollama, which allows the system to run AI models offline (no internet needed during operation).

**In your terminal, run:**

```bash
chmod +x scripts/setup_pi_ollama.sh
./scripts/setup_pi_ollama.sh
```

**This will:**
- Download and install Ollama
- Download a small AI model (takes 5-10 minutes depending on internet)
- Enable it to run automatically

**You can skip this if you don't want AI features or are low on time.**

### Step 2e: Test the Backend Manually (Optional but Recommended)

**What you're doing:** Starting the AOJ system manually to verify everything works before setting up automatic startup.

**In your terminal, run:**

```bash
./scripts/start_production.sh
```

**You should see:**
```
[AOJ] Starting production server on port 8000 (LAN-accessible)...
[AOJ] UI + API: http://0.0.0.0:8000
[AOJ] Press Ctrl+C to stop.
```

**Now test in a browser:**
1. Open Firefox or Chrome
2. Go to: `http://localhost:8000`
3. You should see the AOJ system interface!

**To stop the server, press:** `Ctrl+C` (hold Control, press C)

If this works, you know the installation was successful!

---

## Part 3: Set Up Automatic Startup (Kiosk Mode)

**What we're doing:** Setting up your Pi so that when it powers on, it automatically starts AOJ without needing to type any commands. It will look and feel like a dedicated embedded system.

### Step 3a: Create Systemd Services

**What you're doing:** Creating "service files" that tell the Pi to automatically start AOJ on boot. A service is like a scheduled task in Windows.

**First, make sure the directory exists:**

```bash
mkdir -p scripts/systemd
```

**Then copy the service files we created:**

```bash
sudo cp scripts/systemd/aoj-production.service /etc/systemd/system/
sudo cp scripts/systemd/aoj-kiosk.service /etc/systemd/system/
```

**You might be asked for your password (type: `raspberry`)**

**Reload systemd to recognize the new services:**

```bash
sudo systemctl daemon-reload
```

### Step 3b: Configure Automatic Login (No Password Required)

**What you're doing:** Setting up the Pi so it logs in automatically without asking for a password or username. This makes it act like a kiosk or embedded device.

**Create the configuration file:**

```bash
sudo nano /etc/lightdm/lightdm.conf.d/99-autologin.conf
```

**The `nano` editor will open.** Type (or paste) the following:

```ini
[Seat:*]
autologin-user=pi
autologin-user-session=LXDE
```

**To save:**
1. Press: `Ctrl+X` (hold Control, press X)
2. Type: `y` (for yes)
3. Press: `Enter`

### Step 3c: Set Up X11 Startup Script

**What you're doing:** Creating a startup script that tells X11 (the graphical system) to launch Chromium fullscreen when it starts.

**Create the file:**

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

**Paste this entire block** (everything from `cat` to `EOF`) and press Enter. It will create the startup script automatically.

### Step 3d: Enable Services to Run on Boot

**What you're doing:** Telling the Pi that every time it starts, it should automatically run the AOJ services.

**Run these commands:**

```bash
sudo systemctl enable aoj-production.service
sudo systemctl enable aoj-kiosk.service
```

**Verify they're enabled:**

```bash
sudo systemctl is-enabled aoj-production.service
sudo systemctl is-enabled aoj-kiosk.service
```

**Both should output:** `enabled`

### Step 3e: Test the Services Before Rebooting

**What you're doing:** Starting the services manually to make sure everything works before committing to automatic startup.

**Start the backend:**

```bash
sudo systemctl start aoj-production.service
```

**Check if it's running:**

```bash
sudo systemctl status aoj-production.service
```

**You should see:** `Active: active (running)`

**Wait 5 seconds, then start the browser:**

```bash
sudo systemctl start aoj-kiosk.service
```

**Check the browser:**

```bash
sudo systemctl status aoj-kiosk.service
```

**Should also show:** `Active: active (running)`

**If you see errors, check the logs:**

```bash
sudo journalctl -u aoj-production -n 20
sudo journalctl -u aoj-kiosk -n 20
```

### Step 3f: Reboot to Test Automatic Startup

**What you're doing:** Restarting the Pi to verify everything starts automatically.

**Reboot the system:**

```bash
sudo reboot
```

**The Pi will restart. Wait 30-60 seconds.**

**You should see:**
1. Linux boot messages
2. Black screen
3. Chromium browser starting
4. Your AOJ interface appearing in fullscreen

**If this works perfectly, you're done!** 🎉

---

## Part 4: Access and Use Your System

### From Your Tablet/Laptop on the Same Network

**What you're doing:** Connecting to the AOJ system from other devices (tablets, phones, laptops) over your Wi-Fi.

**Find your Pi's IP address:**

1. **On your Pi**, open Terminal and type:
```bash
hostname -I
```

2. **You'll see something like:** `192.168.1.50`

3. **On your tablet/laptop**, open a web browser and go to:
```
http://192.168.1.50:8000
```

(Replace `192.168.1.50` with whatever IP address you got)

**Or use the easy hostname:**

```
http://raspberrypi.local:8000
```

**This should work from any device on your network!**

### Access API Documentation

The system has built-in documentation for developers:

```
http://raspberrypi.local:8000/docs
```

This shows all the commands and features available.

---

## Troubleshooting

### Problem: Terminal shows "command not found"

**Cause:** You typed the command wrong or you're in the wrong directory

**Solution:**
- Double-check you typed it exactly (commands are CASE-SENSITIVE)
- Make sure you're in `/home/pi/AOJ-Server` directory
- Check with: `pwd` (should show `/home/pi/AOJ-Server`)
- Go there with: `cd ~/AOJ-Server`

### Problem: "Permission denied" error

**Cause:** You need administrator (sudo) privileges

**Solution:** Add `sudo` to the beginning of the command

**Before:** `systemctl restart aoj-production`
**After:** `sudo systemctl restart aoj-production`

### Problem: Installation hangs or gets stuck

**Cause:** Internet connection is slow or interrupted

**Solution:**
- Wait 5 minutes (seriously, large installations take time)
- Press `Ctrl+C` to cancel
- Check internet: `ping 8.8.8.8`
- Try again: `./scripts/install_pi.sh`

### Problem: Browser won't start, shows blank screen

**Cause:** Backend might not be ready yet

**Solution:**
- Wait 20-30 seconds (the first startup is slow)
- Restart: `sudo systemctl restart aoj-kiosk`
- Check if backend is running: `curl http://localhost:8000/api/health`
- View logs: `sudo journalctl -u aoj-production -n 50`

### Problem: Can't SSH from another computer

**Cause:** SSH might not be enabled

**Solution:**
- On Pi, open Terminal
- Type: `sudo systemctl enable ssh`
- Type: `sudo systemctl start ssh`
- Find your Pi's IP: `hostname -I`
- From laptop: `ssh pi@192.168.1.50` (use your Pi's IP)
- Password: `raspberry`

### Problem: System crashes or keeps rebooting

**Cause:** Usually storage is full or power supply is too weak

**Solution:**
1. Check storage: `df -h`
2. If it shows 100% or high percentages, delete old files
3. Check power: Use a 3A+ power supply with a good cable
4. Check temperature: `vcgencmd measure_temp` (should be under 80°C)

### Problem: "Port 8000 already in use"

**Cause:** Another service is using that port

**Solution:**
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill it (replace PID with the number shown)
sudo kill -9 PID
```

### Problem: Can't connect to network

**Cause:** Wi-Fi credentials wrong or no Ethernet

**Solution:**
1. Open Terminal
2. Type: `sudo raspi-config`
3. Select: System Options → Wireless LAN
4. Re-enter your Wi-Fi name and password
5. Reboot: `sudo reboot`

### Problem: Forgot Password

**Cause:** You can't log in anymore

**Solution:** You'll need to reflash the SD card with Raspberry Pi Imager (start over with Part 1a)

---

## Important Linux Concepts

### Understanding File Paths

Think of the file system like folders inside folders:

```
/home/pi/AOJ-Server/backend/
                  ↑         ↑
              folder     subfolder
```

- `/` = root (the very top)
- `~` = home folder (shortcut for `/home/pi`)
- `.` = current folder
- `..` = parent folder (one level up)

**Example commands:**
```bash
cd ~/AOJ-Server      # Go to AOJ-Server folder
cd ..                # Go up one level
ls                   # List files in current folder
pwd                  # Show current folder path
```

### Understanding Commands

Most commands follow this pattern:

```bash
command [options] [arguments]
```

Example:
```bash
systemctl restart aoj-production
↑         ↑        ↑
command   option   argument
```

### Understanding Permissions

Files can have three types of permissions:
- **r** (read) - can view the file
- **w** (write) - can edit the file
- **x** (execute) - can run the file

**Example:**
```bash
chmod +x script.sh    # Add execute permission (make it runnable)
chmod 644 file.txt    # Set specific permissions
sudo command          # Run as administrator (superuser do)
```

### Understanding Services

A service is a background program that runs automatically. Think of it like Windows services:

```bash
sudo systemctl status aoj-production    # Check if running
sudo systemctl start aoj-production     # Start it
sudo systemctl stop aoj-production      # Stop it
sudo systemctl restart aoj-production   # Restart it
sudo systemctl enable aoj-production    # Start on boot
sudo systemctl disable aoj-production   # Don't start on boot
```

### Understanding Pipes and Redirection

The `|` (pipe) sends output from one command to another:

```bash
sudo journalctl -u aoj-production -f
                                   ↑
                                 pipe
```

This sends logs from journalctl to be displayed continuously (`-f` means "follow").

### Understanding Environment Variables

Variables that programs use for configuration:

```bash
export LORA_MODE=rpi_spi
       ↑          ↑
    variable    value
```

These are stored and used by programs to know how to behave.

---

## Quick Command Reference

Here are the most useful commands for day-to-day use:

### System Management
```bash
sudo reboot                              # Restart Pi
sudo shutdown -h now                     # Shut down Pi
df -h                                    # Check storage space
free -h                                  # Check memory usage
top                                      # View running processes (press q to exit)
vcgencmd measure_temp                    # Check temperature
```

### Service Management
```bash
sudo systemctl status aoj-production     # Check if running
sudo systemctl restart aoj-production    # Restart backend
sudo systemctl restart aoj-kiosk         # Restart browser
sudo systemctl stop aoj-kiosk            # Stop browser (to get to desktop)
```

### Viewing Logs
```bash
sudo journalctl -u aoj-production -f     # Live backend logs
sudo journalctl -u aoj-kiosk -f          # Live browser logs
sudo journalctl -u aoj-production -n 50  # Last 50 lines
```

### File Management
```bash
ls                                       # List files
ls -la                                   # List with details
cd ~/AOJ-Server                          # Go to folder
pwd                                      # Show current location
mkdir folder_name                        # Create folder
cp file1 file2                           # Copy file
rm file                                  # Delete file (careful!)
nano file.txt                            # Edit file (Ctrl+X to save)
```

### Network
```bash
hostname -I                              # Show IP address
ping 8.8.8.8                             # Test internet (Ctrl+C to stop)
curl http://localhost:8000               # Test if backend is running
ssh pi@192.168.1.50                      # SSH to Pi from another computer
```

---

## Still Stuck? Debugging Steps

1. **Check for error messages** - read them carefully, they often explain the problem
2. **Google the error message** - odds are someone else had the same issue
3. **Check the logs** - they contain detailed information:
   ```bash
   sudo journalctl -u aoj-production -n 100  # View error log
   ```
4. **Reboot and try again** - sometimes this fixes mysterious issues:
   ```bash
   sudo reboot
   ```
5. **Reinstall from scratch** - if all else fails:
   ```bash
   cd ~
   rm -rf AOJ-Server
   git clone https://github.com/bravo-nineteen/AOJ-Server.git
   cd AOJ-Server
   ./scripts/install_pi.sh
   ```

---

## Next Steps

**Once everything is working:**

1. **Configure your teams and game modes** in the Settings tab
2. **Set up LoRa hardware** if you have physical radio modules
3. **Backup your system** regularly
4. **Read the API documentation** at `http://raspberrypi.local:8000/docs`
5. **Create an account** in the system for your team

---

## Getting Help

If you're stuck:

1. **Check the main documentation:** [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)
2. **Quick reference:** [KIOSK_MODE_QUICK_REFERENCE.md](KIOSK_MODE_QUICK_REFERENCE.md)
3. **View system logs:** `sudo journalctl -xe`
4. **Contact admin** or check GitHub issues

---

**Congratulations! You now have AOJ Command OS running on your Raspberry Pi! 🎉**

Your system is now a dedicated command center for your operations, automatically starting whenever the Pi powers on.

---

**Last Updated:** May 2026
**Questions?** Check the documentation or check system logs with: `sudo journalctl -u aoj-production -f`
