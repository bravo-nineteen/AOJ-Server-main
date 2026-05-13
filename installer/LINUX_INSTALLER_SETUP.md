# AOJ Command OS Linux Installer - Setup & Configuration

## Overview

The Linux installer provides multiple distribution methods for AOJ Command OS:

| Format | Use Case | Command |
|--------|----------|---------|
| **tar.gz** | Portable, manual install | `tar xzf AOJ_CommandOS_v*.tar.gz` |
| **.deb** | Ubuntu/Debian systems | `sudo dpkg -i aoj-command-os_*.deb` |
| **.rpm** | Red Hat/CentOS/Fedora | `sudo rpm -i aoj-command-os-*.rpm` |

---

## Features (v1.0.1)

### ✅ Complete Features Added

1. **Version Management**
   - Version tracked in `VERSION.txt` (single source of truth)
   - All packages include version in filename: `AOJ_CommandOS_v1.0.1_x64.tar.gz`
   - Automatic version propagation to all installation methods

2. **Desktop Integration**
   - `.desktop` file for application menu and shortcuts
   - Icon support (32×32, 64×64, 256×256 PNG)
   - System-wide accessibility without terminal

3. **Automatic Upgrades**
   - New version installation safely overwrites previous
   - Data and configuration preserved in upgrade
   - Graceful service restart on upgrade

4. **Branding**
   - Airsoft Online Japan application icon
   - Professional desktop entry and menu integration
   - Version display in UI and system information

5. **Multi-User & Multi-System Support**
   - System user `aoj-os` for privilege isolation
   - Predictable install location: `/opt/aoj-command-os`
   - Systemd service for optional auto-startup

6. **Dependency Management**
   - Automatic detection and installation of system packages
   - Virtual environment isolation for Python
   - Version checking at runtime

---

## Build Instructions

### Prerequisites

**On Ubuntu/Debian:**
```bash
sudo apt-get install python3.11 python3.11-venv python3-dev nodejs npm git build-essential
```

**On Red Hat/CentOS/Fedora:**
```bash
sudo dnf install python3 python3-venv python3-devel nodejs npm git
```

**For .deb/.rpm packages (optional):**
```bash
gem install fpm
# OR
sudo apt-get install ruby ruby-dev  # then gem install fpm
```

### Quick Build (tar.gz default)

From the project root:
```bash
bash installer/build_linux.sh
```

Output: `dist/installer/AOJ_CommandOS_v1.0.1_x64.tar.gz`

### Build All Formats

```bash
bash installer/build_linux.sh --all
```

Outputs:
```
dist/installer/AOJ_CommandOS_v1.0.1_x64.tar.gz
dist/installer/aoj-command-os_1.0.1_amd64.deb
dist/installer/aoj-command-os-1.0.1-1.x86_64.rpm
```

### Build Specific Format

```bash
bash installer/build_linux.sh --tar      # tar.gz only
bash installer/build_linux.sh --deb      # .deb only
bash installer/build_linux.sh --rpm      # .rpm only
```

---

## Installation Methods

### Method 1: Portable tar.gz Installation

Best for: Manual deployment, testing, non-standard systems

```bash
# Extract
mkdir -p ~/aoj-command-os
tar xzf AOJ_CommandOS_v1.0.1_x64.tar.gz -C ~/aoj-command-os --strip-components=1

# Run setup
cd ~/aoj-command-os
bash scripts/install_linux.sh

# Start
bash assets/aoj_launcher.sh
```

**Data Location:** `~/aoj-command-os/backend/data/`

### Method 2: Ubuntu/Debian (.deb)

Best for: Ubuntu, Debian, Linux Mint

```bash
# Install
sudo dpkg -i aoj-command-os_1.0.1_amd64.deb

# Setup dependencies (first time only)
sudo /opt/aoj-command-os/scripts/install_linux.sh

# Start
/opt/aoj-command-os/assets/aoj_launcher.sh
```

**Install Location:** `/opt/aoj-command-os/`  
**System User:** `aoj-os`  
**Menu:** Applications → Utilities → AOJ Command OS

### Method 3: Red Hat/CentOS/Fedora (.rpm)

Best for: Red Hat, CentOS, Fedora

```bash
# Install
sudo rpm -i aoj-command-os-1.0.1-1.x86_64.rpm

# Setup dependencies (first time only)
sudo /opt/aoj-command-os/scripts/install_linux.sh

# Start
/opt/aoj-command-os/assets/aoj_launcher.sh
```

**Install Location:** `/opt/aoj-command-os/`  
**System User:** `aoj-os`  
**Menu:** Applications → Utilities → AOJ Command OS

---

## Launch Methods

### Method 1: Application Menu

Ubuntu/Debian/Fedora: Applications → Utilities → AOJ Command OS

### Method 2: Command Line

```bash
# From anywhere if installed via .deb/.rpm
/opt/aoj-command-os/assets/aoj_launcher.sh

# OR if using portable tar.gz
cd ~/aoj-command-os
bash assets/aoj_launcher.sh
```

### Method 3: Desktop Shortcut

Creates automatically with .deb/.rpm installation.

For portable: Create `~/.desktop/aoj-command-os.desktop`
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=AOJ Command OS
Comment=Tactical Server and Frontend
Exec=/path/to/aoj-command-os/assets/aoj_launcher.sh
Icon=aoj-icon
Categories=Utility;Server;
Terminal=false
```

### Method 4: Systemd Service (Optional Auto-Start)

For .deb/.rpm installations:
```bash
# Enable auto-start (runs on boot)
sudo systemctl enable aoj-command-os
sudo systemctl start aoj-command-os

# View status
sudo systemctl status aoj-command-os

# Stop
sudo systemctl stop aoj-command-os

# Logs
sudo journalctl -u aoj-command-os -f
```

---

## Version Management

### Bumping to a New Version

1. **Update VERSION.txt** at project root:
   ```bash
   echo "1.0.2" > VERSION.txt
   ```

2. **Rebuild installer**:
   ```bash
   bash installer/build_linux.sh --all
   ```

   Outputs:
   ```
   dist/installer/AOJ_CommandOS_v1.0.2_x64.tar.gz
   dist/installer/aoj-command-os_1.0.2_amd64.deb
   dist/installer/aoj-command-os-1.0.2-1.x86_64.rpm
   ```

3. **For existing installations (upgrade existing)**:
   
   tar.gz method:
   ```bash
   # Backup first
   cp -r ~/aoj-command-os ~/aoj-command-os.backup
   
   # Extract new version over existing
   tar xzf AOJ_CommandOS_v1.0.2_x64.tar.gz -C ~/aoj-command-os --strip-components=1
   ```
   
   .deb/.rpm method:
   ```bash
   sudo dpkg -i aoj-command-os_1.0.2_amd64.deb  # Automatic upgrade
   # OR
   sudo rpm -U aoj-command-os-1.0.2-1.x86_64.rpm
   ```

---

## Icon & Branding Assets

Place the following in `installer/assets/`:

| File | Size | Purpose |
|------|------|---------|
| `aoj_icon.png` | 256×256px | Application icon (all usages) |
| (optional) | 64×64px | Taskbar icon |
| (optional) | 32×32px | Menu icon |

**Asset Preparation:**

The build script automatically:
- Detects PNG icon at `installer/assets/aoj_icon.png`
- Stages it to `/usr/share/icons/hicolor/256x256/apps/`
- Registers with desktop database

If icon is missing, the launcher still works but won't have visual branding in menus.

---

## Configuration Files

### `/opt/aoj-command-os/` (package installations)

```
/opt/aoj-command-os/
├── backend/                 # FastAPI server
│   ├── app/
│   ├── .venv/              # Python virtual environment
│   ├── requirements.txt
│   └── data/               # User data, uploads, database
├── frontend/               # React + Vite app
│   ├── src/
│   ├── dist/               # Built output
│   └── node_modules/
├── scripts/
│   ├── install_linux.sh    # Dependency setup
│   ├── start_backend.sh
│   ├── start_frontend.sh
│   └── start_aoj_linux.sh
├── assets/
│   ├── aoj_launcher.sh     # Application launcher
│   └── aoj_icon.png
├── docs/
├── VERSION                 # Version string
└── README.md
```

### `/etc/systemd/system/aoj-command-os.service`

Optional systemd service for auto-startup. Edit with:
```bash
sudo systemctl edit aoj-command-os
```

Common customizations:
- `User=` : Change system user
- `ExecStart=` : Modify startup command
- `Restart=` : Adjust restart policy

---

## Uninstallation

### tar.gz (Portable)

```bash
# Simply delete the directory
rm -rf ~/aoj-command-os
```

### Ubuntu/Debian (.deb)

```bash
sudo dpkg -r aoj-command-os

# Also remove system user
sudo userdel -r aoj-os
```

### Red Hat/Fedora (.rpm)

```bash
sudo rpm -e aoj-command-os

# Also remove system user
sudo userdel -r aoj-os
```

---

## Troubleshooting

### "Python 3.11+ not found"

**Ubuntu/Debian:**
```bash
sudo apt-get install python3.11 python3.11-venv
```

**Red Hat/Fedora:**
```bash
sudo dnf install python3 python3-devel
```

### "Node.js 18+ not found"

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install nodejs
```

**Red Hat/Fedora:**
```bash
sudo dnf install nodejs npm
```

### Frontend stuck on "Building"

The first launch compiles the React frontend. This takes 30-60 seconds. Monitor:
```bash
tail -f /opt/aoj-command-os/frontend/build.log
```

### Port 8000 or 4173 already in use

Check what's using the ports:
```bash
sudo lsof -i :8000
sudo lsof -i :4173
```

Kill the process or modify `scripts/start_backend.sh` and `scripts/start_frontend.sh` to use different ports.

### Permission denied errors

For package installations:
```bash
sudo chown -R aoj-os:aoj-os /opt/aoj-command-os
sudo chmod -R u+w /opt/aoj-command-os
```

For portable installations:
```bash
chmod -R u+w ~/aoj-command-os
```

### .deb installation requires fpm gem

Install build tools:
```bash
sudo apt-get install ruby ruby-dev build-essential
gem install fpm
```

Then rebuild:
```bash
bash installer/build_linux.sh --deb
```

---

## Distribution & Release Workflow

### For Users: Installation

**Simple one-liner installation (from releases page):**

```bash
# Ubuntu/Debian
wget https://github.com/bravo-nineteen/AOJ-Server/releases/download/v1.0.1/aoj-command-os_1.0.1_amd64.deb
sudo dpkg -i aoj-command-os_1.0.1_amd64.deb
/opt/aoj-command-os/assets/aoj_launcher.sh

# OR Red Hat/Fedora
wget https://github.com/bravo-nineteen/AOJ-Server/releases/download/v1.0.1/aoj-command-os-1.0.1-1.x86_64.rpm
sudo rpm -i aoj-command-os-1.0.1-1.x86_64.rpm
/opt/aoj-command-os/assets/aoj_launcher.sh

# OR Portable (any Linux)
wget https://github.com/bravo-nineteen/AOJ-Server/releases/download/v1.0.1/AOJ_CommandOS_v1.0.1_x64.tar.gz
mkdir -p ~/aoj-command-os
tar xzf AOJ_CommandOS_v1.0.1_x64.tar.gz -C ~/aoj-command-os --strip-components=1
cd ~/aoj-command-os
bash scripts/install_linux.sh
bash assets/aoj_launcher.sh
```

### For Developers: Building Release

```bash
# Build all formats
bash installer/build_linux.sh --all

# Output ready for GitHub Releases
ls -lh dist/installer/aoj-command-os_*.deb
ls -lh dist/installer/aoj-command-os-*.rpm
ls -lh dist/installer/AOJ_CommandOS_v*.tar.gz

# Upload to GitHub Releases:
# 1. Create release for v1.0.1
# 2. Attach all three files
# 3. Include installation instructions from above
```

---

## Next Steps

1. **Provide PNG icon**: Place `aoj_icon.png` (256×256px) in `installer/assets/`
2. **Build installers**: Run `bash installer/build_linux.sh --all` from project root
3. **Test each format**: Try .tar.gz, .deb, and .rpm on representative systems
4. **Release**: Upload to GitHub Releases or your distribution platform

---

## Support & Links

- **GitHub Repository**: https://github.com/bravo-nineteen/AOJ-Server
- **Issue Tracker**: https://github.com/bravo-nineteen/AOJ-Server/issues
- **Documentation**: https://github.com/bravo-nineteen/AOJ-Server/blob/main/README.md
