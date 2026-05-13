# AOJ Command OS Installer Assets

## Logo & Branding

The Airsoft Online Japan official logo should be placed in this directory for use in the Windows installer.

### Required Files

1. **aoj_icon.ico** (already present)
   - Application icon for taskbar, desktop shortcuts, and window title
   - Size: 32x32px (or multi-resolution ICO format recommended: 16x16, 32x32, 48x48, 256x256)
   - Used in Start Menu, Desktop shortcuts, and installer wizard

2. **aoj_logo.bmp** (recommended for complete branding)
   - Wizard/installer branding image displayed during installation
   - Optimal size: 480x360px (Inno Setup wizard standard)
   - Format: BMP (best compatibility), PNG or JPG (auto-converted)
   - Appears on left side of installation wizard pages

### Setup Instructions

1. Export the Airsoft Online Japan logo as:
   - **Icon version** → save as `aoj_icon.ico` 
   - **Wizard image** → resize to 480x360px, save as `aoj_logo.bmp`

2. Place files in this directory (`installer/assets/`)

3. Rebuild installer:
   ```powershell
   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
   ```

### Installer Features

✅ **Desktop Icon**: Automatically created during installation  
✅ **Version Numbers**: Displays version in all shortcuts and dialogs  
✅ **Upgrade Support**: New version automatically overwrites previous installation  
✅ **Logo Branding**: Custom icon and wizard image throughout installer UI  
✅ **Clean Uninstall**: Previous versions safely removed on upgrade  
✅ **Optional Code Signing**: Authenticode signing reduces SmartScreen warnings  

### Version Management

The installer version is tracked in three places:

- `VERSION.txt` - Single source of truth for version number (in project root)
- `installer/aoj_installer.iss` - Inno Setup script version definitions
- Build output filename: `AOJ_CommandOS_Setup_v{version}_x64.exe`

**To bump version:**

1. Edit `VERSION.txt` with new version (e.g., `1.0.2`)
2. In `installer/aoj_installer.iss`, update:
   ```iss
   #define AppVersion   "1.0.2"
   #define AppVersionRevision   2
   ```
3. Rebuild: `powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1`

### Icon Export Guide

**From Microsoft Office or similar programs:**

1. Right-click logo image → Export as PNG or PNG transparency
2. Use free online ICO converter (icoconvert, etc.)
3. Upload PNG, select multi-resolution (16, 32, 48, 256px)
4. Download as `.ico` file
5. Save as `aoj_icon.ico` in this directory

**From image editors (Photoshop, GIMP, etc.):**

1. Create 256x256px image with transparency
2. File → Export As → Select `.ico` format
3. Choose multi-resolution option if available
4. Save as `aoj_icon.ico`

**Wizard Image (480x360px BMP):**

1. Resize logo to 480x360px in Photoshop/GIMP
2. File → Export As → Save as `aoj_logo.bmp`
3. Ensure format is BMP (24-bit or 32-bit preferred)
4. Place in this directory

### Design Recommendations

- **Color Scheme**: Tactical/Military (align with Airsoft Online Japan brand colors)
- **Contrast**: Ensure logo is visible against both light and dark backgrounds
- **Simplicity**: Icon should be recognizable at small sizes (16x16px)
- **Transparency**: Use transparent PNG before converting to ICO for best results
- **Branding**: Include Airsoft Online Japan name/callsign for user recognition


