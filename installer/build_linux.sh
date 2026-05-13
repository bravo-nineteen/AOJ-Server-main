#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# AOJ Command OS — Build Linux installer package
# =============================================================================
# Usage (from the project root):
#   bash installer/build_linux.sh
#   bash installer/build_linux.sh --deb           (Debian/Ubuntu .deb package)
#   bash installer/build_linux.sh --rpm           (Red Hat/Fedora .rpm package)
#   bash installer/build_linux.sh --tar           (Portable tar.gz archive)
#   bash installer/build_linux.sh --all           (All formats)
#
# Prerequisites:
#   - Linux/macOS with bash 4+
#   - git configured
#   - For .deb: fpm (https://fpm.readthedocs.io/en/latest/installation.html)
#   - For .rpm: fpm
#   - For .tar: tar, gzip (standard on most systems)
#
# Output:
#   - dist/installer/AOJ_CommandOS_v${VERSION}_x64.tar.gz
#   - dist/installer/aoj-command-os_${VERSION}_amd64.deb           (if --deb)
#   - dist/installer/aoj-command-os-${VERSION}-1.x86_64.rpm        (if --rpm)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALLER_DIR="${SCRIPT_DIR}"
DIST_DIR="${PROJECT_ROOT}/dist/installer"

# Parse arguments
BUILD_TAR=0
BUILD_DEB=0
BUILD_RPM=0
if [[ $# -eq 0 ]]; then
  BUILD_TAR=1  # Default to tar.gz
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --tar)  BUILD_TAR=1 ;;
      --deb)  BUILD_DEB=1 ;;
      --rpm)  BUILD_RPM=1 ;;
      --all)  BUILD_TAR=1; BUILD_DEB=1; BUILD_RPM=1 ;;
      *)      echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
  done
fi

# Read version from VERSION.txt
VERSION_FILE="${PROJECT_ROOT}/VERSION.txt"
CURRENT_VERSION='1.0.1'
if [[ -f "$VERSION_FILE" ]]; then
  CURRENT_VERSION=$(head -1 "$VERSION_FILE" | tr -d '[:space:]')
fi

echo "=========================================="
echo "AOJ Command OS Linux Installer Builder"
echo "=========================================="
echo "Version: $CURRENT_VERSION"
echo "Project Root: $PROJECT_ROOT"

# Create build directory
BUILD_DIR="${DIST_DIR}/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "[*] Preparing installation files..."

# Create package structure: /opt/aoj-command-os/
STAGE_DIR="${BUILD_DIR}/opt/aoj-command-os"
mkdir -p "$STAGE_DIR"

# Copy backend
echo "[*] Copying backend..."
cp -r "${PROJECT_ROOT}/backend" "$STAGE_DIR/backend"
rm -rf "$STAGE_DIR/backend/.venv" "$STAGE_DIR/backend/__pycache__"

# Copy frontend
echo "[*] Copying frontend..."
cp -r "${PROJECT_ROOT}/frontend" "$STAGE_DIR/frontend"
rm -rf "$STAGE_DIR/frontend/node_modules" "$STAGE_DIR/frontend/dist"

# Copy scripts
echo "[*] Copying scripts..."
mkdir -p "$STAGE_DIR/scripts"
cp "${PROJECT_ROOT}/scripts/install_linux.sh" "$STAGE_DIR/scripts/"
cp "${PROJECT_ROOT}/scripts/start_backend.sh" "$STAGE_DIR/scripts/"
cp "${PROJECT_ROOT}/scripts/start_frontend.sh" "$STAGE_DIR/scripts/"
cp "${PROJECT_ROOT}/scripts/start_aoj_linux.sh" "$STAGE_DIR/scripts/"

# Copy docs
echo "[*] Copying documentation..."
mkdir -p "$STAGE_DIR/docs"
cp "${PROJECT_ROOT}/README.md" "$STAGE_DIR/"
cp -r "${PROJECT_ROOT}/docs" "$STAGE_DIR/" 2>/dev/null || true

# Copy installer assets
echo "[*] Copying installer assets..."
mkdir -p "$STAGE_DIR/assets"
if [[ -f "${INSTALLER_DIR}/assets/aoj_icon.png" ]]; then
  cp "${INSTALLER_DIR}/assets/aoj_icon.png" "$STAGE_DIR/assets/"
fi
if [[ -f "${INSTALLER_DIR}/assets/aoj_launcher.sh" ]]; then
  cp "${INSTALLER_DIR}/assets/aoj_launcher.sh" "$STAGE_DIR/assets/"
fi

# Create version file in staged install
echo "$CURRENT_VERSION" > "$STAGE_DIR/VERSION"

# Create desktop integration files
echo "[*] Creating desktop integration files..."

# Create .desktop file
DESKTOP_FILE="${BUILD_DIR}/usr/share/applications/aoj-command-os.desktop"
mkdir -p "${BUILD_DIR}/usr/share/applications"
cat > "$DESKTOP_FILE" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=AOJ Command OS
Comment=Airsoft Online Japan Tactical Server and Frontend
Exec=/opt/aoj-command-os/assets/aoj_launcher.sh
Icon=aoj-icon
Categories=Utility;Server;
Terminal=false
StartupNotify=true
EOF

# Create icon symlink location
ICON_DIR="${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"

# Create systemd service file (optional auto-start)
SYSTEMD_SERVICE="${BUILD_DIR}/etc/systemd/system/aoj-command-os.service"
mkdir -p "$(dirname "$SYSTEMD_SERVICE")"
cat > "$SYSTEMD_SERVICE" << 'EOF'
[Unit]
Description=AOJ Command OS - Tactical Server and Frontend
After=network.target

[Service]
Type=simple
User=aoj-os
WorkingDirectory=/opt/aoj-command-os
ExecStart=/opt/aoj-command-os/scripts/start_aoj_linux.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create pre-install script (create user if needed)
PREINST_SCRIPT="${BUILD_DIR}/DEBIAN/preinst"
mkdir -p "${BUILD_DIR}/DEBIAN"
cat > "$PREINST_SCRIPT" << 'EOF'
#!/bin/bash
set -e

# Create aoj-os system user if it doesn't exist
if ! id "aoj-os" &>/dev/null; then
  useradd -r -s /bin/bash -d /opt/aoj-command-os -m aoj-os || true
fi

exit 0
EOF
chmod 755 "$PREINST_SCRIPT"

# Create post-install script
POSTINST_SCRIPT="${BUILD_DIR}/DEBIAN/postinst"
cat > "$POSTINST_SCRIPT" << 'EOF'
#!/bin/bash
set -e

AOJ_DIR="/opt/aoj-command-os"
AOJ_USER="aoj-os"

# Fix permissions
chown -R "$AOJ_USER:$AOJ_USER" "$AOJ_DIR" || true
chmod +x "$AOJ_DIR/scripts"/*.sh || true
chmod +x "$AOJ_DIR/assets"/*.sh || true

# Update desktop database
update-desktop-database /usr/share/applications 2>/dev/null || true

# Optional: Install dependencies (comment out for container deployments)
if command -v apt-get &>/dev/null; then
  echo "Run 'sudo /opt/aoj-command-os/scripts/install_linux.sh' to install dependencies"
fi

echo "AOJ Command OS installed to $AOJ_DIR"
echo "To start: /opt/aoj-command-os/assets/aoj_launcher.sh"

exit 0
EOF
chmod 755 "$POSTINST_SCRIPT"

# Create DEBIAN/control file (metadata)
CONTROL_FILE="${BUILD_DIR}/DEBIAN/control"
cat > "$CONTROL_FILE" << EOF
Package: aoj-command-os
Version: $CURRENT_VERSION
Section: utils
Priority: optional
Maintainer: Airsoft Online Japan <support@example.com>
Homepage: https://github.com/bravo-nineteen/AOJ-Server
Description: Tactical Server and Frontend for Airsoft Online Japan
 AOJ Command OS is a comprehensive tactical server and frontend
 system for Airsoft Online Japan game servers.
 .
 Features:
  - Real-time game management and scoring
  - AI-powered game advisor and announcements
  - LoRa device communication and control
  - Complete REST API and WebSocket support
  - Responsive web-based frontend
Architecture: amd64
Depends: python3 (>= 3.11), python3-venv, nodejs (>= 18), npm, git
EOF

echo "[*] Build staging complete."

# Build tar.gz if requested
if [[ $BUILD_TAR -eq 1 ]]; then
  echo "[*] Building tar.gz package..."
  TAR_FILE="${DIST_DIR}/AOJ_CommandOS_v${CURRENT_VERSION}_x64.tar.gz"
  mkdir -p "$DIST_DIR"
  
  cd "${BUILD_DIR}/opt"
  tar czf "$TAR_FILE" "aoj-command-os/"
  
  echo "✓ Built: $TAR_FILE"
  ls -lh "$TAR_FILE"
fi

# Build .deb if requested
if [[ $BUILD_DEB -eq 1 ]]; then
  if ! command -v fpm &>/dev/null; then
    echo "⚠ fpm not found. Install with: gem install fpm"
    BUILD_DEB=0
  else
    echo "[*] Building .deb package..."
    DEB_FILE="${DIST_DIR}/aoj-command-os_${CURRENT_VERSION}_amd64.deb"
    mkdir -p "$DIST_DIR"
    
    cd "$BUILD_DIR"
    fpm -s dir -t deb \
      -n aoj-command-os \
      -v "$CURRENT_VERSION" \
      -p "$DEB_FILE" \
      --before-install "$PREINST_SCRIPT" \
      --after-install "$POSTINST_SCRIPT" \
      --maintainer "Airsoft Online Japan" \
      --description "AOJ Command OS - Tactical Server and Frontend" \
      --url "https://github.com/bravo-nineteen/AOJ-Server" \
      -C "$BUILD_DIR" \
      opt/ etc/ usr/
    
    echo "✓ Built: $DEB_FILE"
    ls -lh "$DEB_FILE"
  fi
fi

# Build .rpm if requested
if [[ $BUILD_RPM -eq 1 ]]; then
  if ! command -v fpm &>/dev/null; then
    echo "⚠ fpm not found. Install with: gem install fpm"
    BUILD_RPM=0
  else
    echo "[*] Building .rpm package..."
    RPM_FILE="${DIST_DIR}/aoj-command-os-${CURRENT_VERSION}-1.x86_64.rpm"
    mkdir -p "$DIST_DIR"
    
    cd "$BUILD_DIR"
    fpm -s dir -t rpm \
      -n aoj-command-os \
      -v "$CURRENT_VERSION" \
      -p "$RPM_FILE" \
      --maintainer "Airsoft Online Japan" \
      --description "AOJ Command OS - Tactical Server and Frontend" \
      --url "https://github.com/bravo-nineteen/AOJ-Server" \
      -C "$BUILD_DIR" \
      opt/ etc/ usr/
    
    echo "✓ Built: $RPM_FILE"
    ls -lh "$RPM_FILE"
  fi
fi

echo ""
echo "=========================================="
echo "✓ Linux installer build complete!"
echo "=========================================="
echo ""
echo "Installation methods:"
echo "  1. Portable (tar.gz): Extract and run scripts/install_linux.sh"
echo "  2. Ubuntu/Debian:  sudo dpkg -i aoj-command-os_*.deb"
echo "  3. Red Hat/Fedora: sudo rpm -i aoj-command-os-*.rpm"
echo ""
