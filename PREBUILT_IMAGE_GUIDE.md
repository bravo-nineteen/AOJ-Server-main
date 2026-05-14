# Creating a Pre-Built AOJ Raspberry Pi OS Image

**This guide explains how to create a custom Raspberry Pi OS image with AOJ pre-installed.**

Once created, users can flash this image and have AOJ ready immediately (no installation needed).

---

## Why Create a Pre-Built Image?

### Advantages
- ✅ Users just flash and reboot (5 minutes total)
- ✅ No installation steps
- ✅ Everything works immediately
- ✅ No internet needed for installation
- ✅ Consistent across all Pis

### Disadvantages
- ⚠️ Requires 5-10GB storage to build
- ⚠️ Takes time to build (1-2 hours)
- ⚠️ Must be rebuilt for updates
- ⚠️ Larger file to distribute (2-3GB compressed)

---

## Method 1: Manual Image Creation (Advanced)

### Prerequisites
- Linux computer (Ubuntu/Debian)
- 5-10GB free storage
- Root/sudo access

### Step-by-Step

#### 1. Create Base Image
```bash
# Get Raspberry Pi OS Lite (smaller, faster)
# https://www.raspberrypi.com/software/operating-systems/

# Flash to USB device
# Use Raspberry Pi Imager or:
dd if=2024-03-15-raspios-bookworm-arm64-lite.img of=/dev/sdb bs=4M status=progress
```

#### 2. Mount and Customize
```bash
# Mount the image
sudo losetup -fP raspios.img
sudo mount /dev/loop0p2 /mnt/rpi-rootfs
sudo mount /dev/loop0p1 /mnt/rpi-boot

# Create chroot environment
sudo chroot /mnt/rpi-rootfs

# Inside chroot: download and run quick-install.sh
curl -sL https://raw.githubusercontent.com/bravo-nineteen/AOJ-Server/main/scripts/quick-install.sh | bash

# Exit chroot
exit

# Unmount
sudo umount /mnt/rpi-rootfs /mnt/rpi-boot
sudo losetup -d /dev/loop0
```

#### 3. Compress Image
```bash
# Compress for distribution
zip aoj-command-os-pi4-v1.0.0.zip raspios.img

# Size should be ~2-3GB compressed
```

#### 4. Share Image
- Upload to GitHub Releases
- Or host on your website
- Provide SHA256 checksum for verification

---

## Method 2: Using Raspberry Pi Imager Custom Script

### New Feature (Raspberry Pi Imager 1.8+)

#### Create `aoj-firstrun.sh`
```bash
#!/bin/bash
# This script runs on first boot

echo "AOJ First-Run Setup..."

# Clone and install
cd /home/pi
git clone https://github.com/bravo-nineteen/AOJ-Server.git
cd AOJ-Server

# Run quick install (non-interactive)
SKIP_REBOOT=1 ./scripts/quick-install.sh
```

#### Package for Imager
1. Place script in GitHub releases
2. Users select "Custom OS" in Imager
3. Point to your script
4. Imager embeds script in OS
5. Script runs on first boot

---

## Method 3: Docker-Based Build (Recommended)

### Benefits
- ✅ Reproducible builds
- ✅ No manual steps
- ✅ Works on any OS (Windows, Mac, Linux)
- ✅ Easy to automate

### Dockerfile
```dockerfile
FROM balenalib/rpi-raspbian:latest

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip \
    nodejs npm \
    chromium-browser \
    xserver-xorg xinit lightdm \
    curl git

# Clone AOJ
RUN git clone https://github.com/bravo-nineteen/AOJ-Server.git /home/pi/AOJ-Server
WORKDIR /home/pi/AOJ-Server

# Run installation
RUN chmod +x scripts/install_pi.sh && \
    ./scripts/install_pi.sh

# Setup kiosk
RUN chmod +x scripts/setup-kiosk-pi.sh && \
    ./scripts/setup-kiosk-pi.sh

CMD ["/bin/bash"]
```

### Build Command
```bash
docker build -t aoj-rpi:v1.0.0 .
```

---

## Method 4: Using `pi-gen` (Official Raspberry Pi Tool)

### What is pi-gen?
Official Raspberry Pi tool for building custom OS images

### Advantages
- ✅ Official tool (most reliable)
- ✅ Reproducible builds
- ✅ Smaller images
- ✅ Better compression

### Steps
1. Clone pi-gen: `git clone https://github.com/RPi-Distro/pi-gen`
2. Add AOJ in `stage2/01-sys-debs` and `stage2/02-net-tweaks`
3. Create `stage3` for AOJ-specific setup
4. Run build: `./build.sh`

---

## User Instructions for Pre-Built Image

### For Users (Super Simple)

1. **Download the image:**
   ```
   Download: aoj-command-os-pi4-v1.0.0.zip
   Size: ~2GB
   ```

2. **Verify integrity:**
   ```bash
   sha256sum -c aoj-command-os-pi4-v1.0.0.sha256
   ```

3. **Flash to SD card:**
   - Use Raspberry Pi Imager
   - Select "Use Custom"
   - Choose downloaded image

4. **Boot:**
   - Insert SD card
   - Connect power
   - Wait 3-5 minutes for first boot setup

5. **Done! 🎉**
   - System boots directly to AOJ
   - No login, no installation
   - Ready to use immediately

---

## Distribution Options

### GitHub Releases
```bash
# Create release
gh release create v1.0.0 aoj-command-os-pi4-v1.0.0.zip \
  --notes "Pre-built Raspberry Pi OS with AOJ"
```

### Self-Hosted
- Host on your website
- Use CDN for faster downloads
- Provide checksums for verification

### Cloud Storage
- Google Drive / OneDrive
- Provide direct download links
- Share via QR code

---

## Maintenance & Updates

### When to Rebuild
- AOJ gets major update
- Security vulnerability found
- OS updates released
- New Raspberry Pi version
- Dependencies need upgrading

### Version Naming
```
aoj-command-os-[pi-model]-v[VERSION].zip
  ↓
aoj-command-os-pi4-v1.0.0.zip
aoj-command-os-pi5-v1.0.0.zip
```

---

## Verification & Security

### Create Checksum
```bash
sha256sum aoj-command-os-pi4-v1.0.0.zip > aoj-command-os-pi4-v1.0.0.sha256
```

### Users Can Verify
```bash
sha256sum -c aoj-command-os-pi4-v1.0.0.sha256
# Output: aoj-command-os-pi4-v1.0.0.zip: OK
```

### Sign Image (Optional)
```bash
gpg --sign aoj-command-os-pi4-v1.0.0.zip
```

---

## Hybrid Approach (Recommended)

**Best of both worlds:**

1. **Provide quick-install script** (current)
   - Users with existing Raspberry Pi OS can use it
   - No pre-built image needed
   - Easy to update

2. **Also provide pre-built image** (for convenience)
   - Users who want fastest option
   - Guaranteed consistency
   - No installation needed

### Users Choose

**Fast installation (30-45 min):**
```bash
curl -sL https://github.com/bravo-nineteen/AOJ-Server/raw/main/scripts/quick-install.sh | bash
```

**Ultra-fast zero-setup (5 min):**
- Download pre-built image
- Flash with Raspberry Pi Imager
- Boot and done

---

## Troubleshooting Image Builds

### Image Build Fails
```bash
# Check log
tail -f build.log

# Rebuild with verbose output
./build.sh -vv

# Clean and retry
rm -rf work/
./build.sh
```

### Image Too Large
- Remove unnecessary packages
- Use Lite version as base
- Exclude languages you don't need

### Image Won't Boot
- Verify Raspberry Pi model compatibility
- Check filesystem integrity: `fsck`
- Try different SD card

---

## Quick Start: Pre-Built Image Creation

### Fastest Method (Quick Install Script)
```bash
# Build on any Linux computer:
mkdir aoj-image-build
cd aoj-image-build

# Flash Raspberry Pi OS Lite to image file
dd if=raspios-lite.img of=aoj.img bs=4M

# Install AOJ (via loop device)
sudo losetup -fP aoj.img
sudo chroot /mnt mount-point /bin/bash

# Inside chroot:
curl -sL https://github.com/bravo-nineteen/AOJ-Server/raw/main/scripts/quick-install.sh | bash
exit

# Compress
zip aoj-command-os-pi4-v1.0.0.zip aoj.img
```

---

## Documentation for Pre-Built Image

### For Users

**Create file:** `PREBUILT_IMAGE_INSTRUCTIONS.md`

```markdown
# AOJ Pre-Built Raspberry Pi OS Image

## Installation (5 minutes)

1. Download: aoj-command-os-pi4-v1.0.0.zip (2GB)
2. Verify: sha256sum -c aoj-command-os-pi4-v1.0.0.sha256
3. Flash: Use Raspberry Pi Imager, select custom image
4. Boot: Insert SD card, connect power
5. Done! System boots to AOJ automatically

## What's Included

- Raspberry Pi OS (latest)
- AOJ Command OS (pre-installed)
- Ollama AI (optional, can be enabled)
- All dependencies ready
- Kiosk mode configured
- Auto-startup enabled

## First Boot

- Takes 2-3 minutes
- Auto-login as 'pi'
- Chromium launches
- AOJ interface appears
- Access from other devices: http://raspberrypi.local:8000

## Support

- Check logs: sudo journalctl -u aoj-production -f
- Read docs: ~/AOJ-Server/BEGINNER_RASPBERRY_PI_SETUP.md
```

---

## Summary

| Method | Time | Complexity | Result |
|--------|------|-----------|--------|
| Quick Install Script | 30-45 min | Easy | Installation-based |
| Pre-Built Image | 5 min | Very Easy | Ready to use |
| Manual Build | 1-2 hours | Hard | Reproducible |
| Docker Build | 1 hour | Medium | Automated |
| pi-gen | 2 hours | Hard | Most reliable |

**Recommendation:** Start with quick-install.sh, then create pre-built image for convenience.

---

**Last Updated:** May 14, 2026
