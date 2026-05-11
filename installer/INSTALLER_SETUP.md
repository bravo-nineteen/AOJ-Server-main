# AOJ Command OS Windows Installer - Setup & Configuration

💾 **Also available:** [Linux Installer Guide](LINUX_INSTALLER_SETUP.md) (Ubuntu, Debian, CentOS, Fedora) | [Cross-Platform Overview](README.md)

## Recent Improvements (v1.0.1)

### ✅ Complete Features Added

1. **Desktop Icon Placement**
   - Desktop shortcut automatically created during installation
   - Icon uses Airsoft Online Japan branding (from `installer/assets/aoj_icon.ico`)
   - Enabled by default (no user interaction needed)
   - Can be customized via `[Tasks]` section if needed

2. **Automatic Upgrade Support**
   - Installing a new version over an existing installation automatically overwrites it
   - Previous installation safely cleaned up
   - Preserves user settings and data directories (backend database, uploaded files)
   - GUID-based upgrade tracking: `{6F3A1D2B-84CE-4B7E-9031-F2C84A6D5E90}`

3. **Version Management**
   - Version tracked in `VERSION.txt` (single source of truth)
   - Version definitions in `installer/aoj_installer.iss`:
     ```iss
     #define AppVersion   "1.0.1"
     #define AppVersionMajor      1
     #define AppVersionMinor      0
     #define AppVersionRevision   1
     ```
   - Output filename includes version: `AOJ_CommandOS_Setup_v1.0.1_x64.exe`
   - Version displayed in:
     - Installer title: "AOJ Command OS v1.0.1"
     - Start Menu shortcuts
     - Desktop shortcut properties
     - Windows Control Panel (Apps & Features)

4. **Logo Branding**
   - Application icon (`aoj_icon.ico`) used throughout UI:
     - Installer wizard title bar
     - Desktop shortcuts
     - Start Menu items
     - Application taskbar (when running)
     - Uninstaller
   - Optional wizard image (`aoj_logo.bmp` 480x360px) displayed during installation
   - Airsoft Online Japan branding on all installer pages

5. **Installer Enhancements**
   - Modern Inno Setup UI (WizardStyle=modern)
   - Clean application group organization
   - Documentation shortcut in Start Menu
   - Support URL linking to GitHub issues
   - Updates URL linking to releases page
   - Improved error messages and post-install information

## Build Instructions

### Prerequisites

- **Inno Setup 6.x** (free download: https://jrsoftware.org/isdl.php)
- **Windows 10/11** with PowerShell 5.0+
- Python 3.11+ and Node.js 18+ installed (verified during setup)

### Quick Build

```powershell
# From project root directory
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
```

Output: `dist/installer/AOJ_CommandOS_Setup_v1.0.1_x64.exe`

### With Code Signing (Optional)

```powershell
# Set environment variables first
$env:AOJ_SIGN_CERT_PATH = "C:\path\to\certificate.pfx"
$env:AOJ_SIGN_CERT_PASSWORD = "your-password"
$env:AOJ_SIGNTOOL_PATH = "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
$env:AOJ_PRODUCT_URL = "https://github.com/bravo-nineteen/AOJ-Server"

# Then build with signing
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1 -Sign
```

## Version Bumping

To release a new version:

1. **Edit `VERSION.txt`:**
   ```
   1.0.2
   ```

2. **Update `installer/aoj_installer.iss`:**
   ```iss
   #define AppVersion       "1.0.2"
   #define AppVersionMinor   0
   #define AppVersionRevision 2
   #define AppVersionBuild    0
   ```

3. **Update `installer/after_install.txt`:**
   - Update version number in first line
   - Add release notes under "New in this version:"

4. **Rebuild:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
   ```

## Logo/Branding Setup

### Step 1: Prepare the Airsoft Online Japan Logo

See `installer/assets/README.md` for detailed export instructions.

**Required files:**
- `aoj_icon.ico` - Multi-resolution icon (16x16, 32x32, 48x48, 256x256px)
- `aoj_logo.bmp` - Wizard image (480x360px) - *optional but recommended*

### Step 2: Place Assets

```
installer/
  assets/
    aoj_icon.ico        ← Application icon (required)
    aoj_logo.bmp        ← Wizard splash image (optional)
    README.md           ← Asset documentation
```

### Step 3: Rebuild Installer

The build script will warn if assets are missing but will still create a working installer with default branding.

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
```

## Installation Behavior

### First Installation

1. User runs `AOJ_CommandOS_Setup_v1.0.1_x64.exe`
2. Inno Setup wizard displays with Airsoft Online Japan branding
3. User selects installation location (default: `C:\Program Files\AOJ Command OS`)
4. Desktop icon creation offered (checked by default)
5. Optional: Startup launcher selection
6. Python/Node.js dependencies installed
7. Frontend build occurs (2-5 minutes)
8. Setup completes, desktop icon visible immediately

### Upgrade (Version 1.0.1 → 1.0.2)

1. User runs new `AOJ_CommandOS_Setup_v1.0.2_x64.exe`
2. Inno Setup detects existing installation via GUID
3. User prompted to upgrade the existing installation
4. Previous version gracefully stopped (Python/Node processes terminated)
5. New files extracted, overwriting old ones
6. Desktop icon updated to new version
7. Database and user data preserved
8. Upgrade completes automatically

### Uninstallation

1. User runs uninstaller
2. Python and Node processes gracefully terminated
3. Installation directory removed (except configured data directories)
4. Start Menu shortcuts removed
5. Desktop icon removed
6. Registry entries cleaned
7. Optional: Remove database backups if user selects

## Configuration Files

### `installer/aoj_installer.iss`

Inno Setup script defining:
- Version information
- File inclusions/exclusions
- Icon and splash image paths
- Installation directories
- Shortcuts (Start Menu, Desktop, Startup)
- Pre/post-install tasks
- Uninstall cleanup

**Key sections:**
- `[Setup]` - Configuration, versioning, UI
- `[Files]` - Source → Destination mappings
- `[Icons]` - Shortcut definitions
- `[Tasks]` - Optional user choices
- `[Run]` - Post-install scripts
- `[Code]` - Pre-install checks (Python, Node.js)

### `installer/build_installer.ps1`

PowerShell build automation script:
- Locates Inno Setup compiler (`iscc.exe`)
- Reads version from `VERSION.txt`
- Verifies logo assets
- Cleans old builds
- Optionally signs with Authenticode certificate
- Outputs final EXE to `dist/installer/`

### `VERSION.txt`

Simple version file (project root):
```
1.0.1
```

Used by build script to:
- Populate `AppVersion` in Inno Setup
- Name output file: `AOJ_CommandOS_Setup_v{VERSION}_x64.exe`
- Track version history

## Troubleshooting

### "Inno Setup compiler (iscc.exe) was not found"

**Solution:** Install Inno Setup 6 from https://jrsoftware.org/isdl.php

### "Python 3.11+ not found" during installation

**Solution:** User must install Python before running AOJ installer
- Download from https://python.org/downloads
- Check "Add Python to PATH" during installation

### "Node.js 18+ not found" during installation

**Solution:** User must install Node.js before running AOJ installer
- Download from https://nodejs.org
- LTS version recommended

### Desktop icon not appearing after install

**Possible causes:**
- User unchecked "Create a desktop shortcut" during setup
- Windows Explorer not refreshed (press F5)
- Desktop folder corrupted

**Solution:**
- Reinstall and ensure checkbox is selected
- Manually create shortcut: Right-click `launch.vbs` → Send to → Desktop

### "WARNING: aoj_icon.ico not found" during build

**Solution:** Place icon at `installer/assets/aoj_icon.ico`
- Installer still works but uses default Windows icon
- See `installer/assets/README.md` for icon creation guide

## Distribution

### Release Workflow

1. **Prepare release:**
   - Update VERSION.txt
   - Update aoj_installer.iss
   - Commit to git
   - Create GitHub release tag

2. **Build installer:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1 -Sign
   ```

3. **Verify output:**
   - File: `dist/installer/AOJ_CommandOS_Setup_vX.X.X_x64.exe`
   - Size: ~200-500MB depending on dependencies

4. **Upload to GitHub:**
   - Add to release notes
   - Include installer version and changes

5. **Announce to users:**
   - Version available for download
   - Desktop icon automatically configured
   - Automatic upgrade if previously installed

## Support & Documentation

- **Installation Guide:** `README.md` (project root)
- **Installer Assets:** `installer/assets/README.md`
- **Build Script:** `installer/build_installer.ps1` (inline documentation)
- **Inno Setup Documentation:** https://jrsoftware.org/isinfo.php
- **GitHub Issues:** https://github.com/bravo-nineteen/AOJ-Server/issues

