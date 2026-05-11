# AOJ Command OS Installation Guide

Complete installation & deployment system for **Airsoft Online Japan Tactical Server and Frontend**.

Supported platforms:
- 🪟 **Windows 10/11** (64-bit) — Inno Setup installer
- 🐧 **Linux** (Ubuntu, Debian, CentOS, Fedora) — tar.gz, .deb, .rpm
- 🍎 **macOS** (partial) — Portable installation

---

## Quick Start

### Windows

1. **Download** the latest `AOJ_CommandOS_Setup_v*.exe` from [Releases](https://github.com/bravo-nineteen/AOJ-Server/releases)
2. **Run** the installer
3. **Choose** desktop icon and auto-launch options
4. **Done!** Application starts immediately

**Full details:** [INSTALLER_SETUP.md](INSTALLER_SETUP.md)

### Linux (Ubuntu/Debian)

```bash
# One-liner installation
wget https://github.com/bravo-nineteen/AOJ-Server/releases/download/v1.0.1/aoj-command-os_1.0.1_amd64.deb
sudo dpkg -i aoj-command-os_1.0.1_amd64.deb
sudo /opt/aoj-command-os/scripts/install_linux.sh
/opt/aoj-command-os/assets/aoj_launcher.sh
```

### Linux (Red Hat/CentOS/Fedora)

```bash
# One-liner installation
wget https://github.com/bravo-nineteen/AOJ-Server/releases/download/v1.0.1/aoj-command-os-1.0.1-1.x86_64.rpm
sudo rpm -i aoj-command-os-1.0.1-1.x86_64.rpm
sudo /opt/aoj-command-os/scripts/install_linux.sh
/opt/aoj-command-os/assets/aoj_launcher.sh
```

### Linux (Portable)

```bash
# Works on any Linux/macOS system
mkdir -p ~/aoj-command-os
tar xzf AOJ_CommandOS_v1.0.1_x64.tar.gz -C ~/aoj-command-os --strip-components=1
cd ~/aoj-command-os
bash scripts/install_linux.sh
bash assets/aoj_launcher.sh
```

**Full details:** [LINUX_INSTALLER_SETUP.md](LINUX_INSTALLER_SETUP.md)

---

## For Developers

### Build Windows Installer

From project root:
```bash
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
```

Output: `dist/installer/AOJ_CommandOS_Setup_v1.0.1_x64.exe`

### Build Linux Installers

```bash
# Single format (tar.gz default)
bash installer/build_linux.sh

# All formats (tar.gz + .deb + .rpm)
bash installer/build_linux.sh --all

# Specific format
bash installer/build_linux.sh --deb      # Ubuntu/Debian
bash installer/build_linux.sh --rpm      # Red Hat/Fedora
```

Output:
```
dist/installer/AOJ_CommandOS_v1.0.1_x64.tar.gz
dist/installer/aoj-command-os_1.0.1_amd64.deb
dist/installer/aoj-command-os-1.0.1-1.x86_64.rpm
```

### Configuration Files

| File | Purpose |
|------|---------|
| [aoj_installer.iss](aoj_installer.iss) | Windows Inno Setup script |
| [build_installer.ps1](build_installer.ps1) | Windows build automation (PowerShell) |
| [build_linux.sh](build_linux.sh) | Linux build automation (Bash) |
| [assets/aoj_launcher.sh](assets/aoj_launcher.sh) | Linux application launcher |
| [VERSION.txt](../VERSION.txt) | Single version source (used by all builders) |
| [INSTALLER_SETUP.md](INSTALLER_SETUP.md) | Windows detailed guide |
| [LINUX_INSTALLER_SETUP.md](LINUX_INSTALLER_SETUP.md) | Linux detailed guide |

### Version Bumping Workflow

To release version 1.0.2:

1. **Update VERSION.txt** (project root):
   ```bash
   echo "1.0.2" > VERSION.txt
   ```

2. **Update Windows installer callout** (optional, for release notes):
   ```bash
   # Edit installer/after_install.txt
   # Update version reference and changelog
   ```

3. **Build all installers**:
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
   
   # Linux (Bash)
   bash installer/build_linux.sh --all
   ```

4. **Verify outputs**:
   ```
   dist/installer/AOJ_CommandOS_Setup_v1.0.2_x64.exe
   dist/installer/AOJ_CommandOS_v1.0.2_x64.tar.gz
   dist/installer/aoj-command-os_1.0.2_amd64.deb
   dist/installer/aoj-command-os-1.0.2-1.x86_64.rpm
   ```

5. **Release to GitHub**:
   - Create release tag: `v1.0.2`
   - Attach all four installer files
   - Add release notes

---

## Feature Comparison

| Feature | Windows | Linux (deb) | Linux (rpm) | Linux (tar) |
|---------|---------|------------|------------|------------|
| Desktop icon | ✅ Yes | ✅ Yes | ✅ Yes | Manual |
| Auto-start option | ✅ Yes | ✅ Systemd | ✅ Systemd | Manual |
| Version in filename | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Auto-upgrade | ✅ Yes | ✅ Yes | ✅ Yes | Manual |
| Branding (logo) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| System user isolation | - | ✅ Yes | ✅ Yes | Manual |
| Package dependencies | ✅ Auto | ✅ Declared | ✅ Declared | Manual |
| Portability | Single OS | Ubuntu/Debian | Red Hat/CentOS | Universal |

---

## Asset Preparation

To enable full branding on all platforms:

1. **Prepare PNG icon** (256×256px):
   - Airsoft Online Japan tactical logo
   - PNG format with transparency
   - Place in `installer/assets/aoj_icon.png`

2. **Optional: Prepare BMP logo** (480×360px):
   - For Windows wizard pages
   - Already configured in `aoj_installer.iss`
   - Place in `installer/assets/aoj_logo.bmp`

3. **Rebuild installers**:
   ```bash
   # Windows
   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
   
   # Linux
   bash installer/build_linux.sh --all
   ```

See [assets/README.md](assets/README.md) for detailed asset guidelines.

---

## Troubleshooting

### Windows Issues

**"Inno Setup not found"**  
Install from: https://jrsoftware.org/isdl.php

**"Python/Node.js not found during install"**  
The installer requires Python 3.11+ and Node.js 18+. They'll be installed automatically if missing (with apt-get on Linux systems).

### Linux Issues

**"dpkg: error processing"**  
Usually means dependencies missing. Run:
```bash
sudo apt-get install -y python3.11 python3-venv nodejs npm
```

**".deb/.rpm build failed"**  
Install fpm:
```bash
gem install fpm
# OR
sudo apt-get install ruby ruby-dev && gem install fpm
```

**Port 8000/4173 already in use**  
Edit `scripts/start_backend.sh` and `scripts/start_frontend.sh` to use different ports.

### Both Platforms

**"First launch takes too long"**  
- Backend initializes database (few seconds)
- Frontend compiles React (30-60 seconds first time)
- Subsequent launches are instant

**Application doesn't start**  
Check logs:
- Windows: Look in Program Files directory  
- Linux: Run `bash /opt/aoj-command-os/scripts/install_linux.sh` for dependency check

---

## Support

- **Issues**: https://github.com/bravo-nineteen/AOJ-Server/issues
- **Releases**: https://github.com/bravo-nineteen/AOJ-Server/releases
- **Documentation**: https://github.com/bravo-nineteen/AOJ-Server/blob/main/README.md

---

## License

See [LICENSE](../LICENSE) in project root.

Version: 1.0.1  
Last Updated: 2026-05-11
