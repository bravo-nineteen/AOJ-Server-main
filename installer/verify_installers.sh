#!/usr/bin/env bash
# =============================================================================
# AOJ Command OS — Verify Installer Configuration
# =============================================================================
# This script checks that both Windows and Linux installer systems are
# properly configured and ready for building.
#
# Usage: bash installer/verify_installers.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   AOJ Command OS — Installer Configuration Verification        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
  local file="$1"
  local description="$2"
  if [[ -f "$file" ]]; then
    echo -e "  ${GREEN}✓${NC} $description"
    return 0
  else
    echo -e "  ${RED}✗${NC} $description (missing: $file)"
    return 1
  fi
}

check_executable() {
  local file="$1"
  local description="$2"
  if [[ -x "$file" ]]; then
    echo -e "  ${GREEN}✓${NC} $description (executable)"
    return 0
  elif [[ -f "$file" ]]; then
    echo -e "  ${YELLOW}!${NC} $description (exists but not executable)"
    return 1
  else
    echo -e "  ${RED}✗${NC} $description (missing: $file)"
    return 1
  fi
}

# ============ Check VERSION.txt (shared source)
echo "📋 Version Management:"
if check_file "${PROJECT_ROOT}/VERSION.txt" "VERSION.txt (single source of truth)"; then
  VERSION=$(head -1 "${PROJECT_ROOT}/VERSION.txt" | tr -d '[:space:]')
  echo "     → Version: $VERSION"
else
  VERSION="unknown"
fi
echo ""

# ============ Windows Installer
echo "🪟 Windows Installer Files:"
WINDOWS_OK=0

check_file "${SCRIPT_DIR}/aoj_installer.iss" "Inno Setup script (aoj_installer.iss)" && ((WINDOWS_OK++)) || true
check_executable "${SCRIPT_DIR}/build_installer.ps1" "Build script (build_installer.ps1)" && ((WINDOWS_OK++)) || true
check_file "${SCRIPT_DIR}/after_install.txt" "Post-install info (after_install.txt)" && ((WINDOWS_OK++)) || true

echo ""

# ============ Linux Installer
echo "🐧 Linux Installer Files:"
LINUX_OK=0

check_executable "${SCRIPT_DIR}/build_linux.sh" "Build script (build_linux.sh)" && ((LINUX_OK++)) || true
check_executable "${SCRIPT_DIR}/assets/aoj_launcher.sh" "Launcher script (aoj_launcher.sh)" && ((LINUX_OK++)) || true

echo ""

# ============ Documentation
echo "📚 Documentation:"
DOC_OK=0

check_file "${SCRIPT_DIR}/README.md" "Overview (README.md)" && ((DOC_OK++)) || true
check_file "${SCRIPT_DIR}/INSTALLER_SETUP.md" "Windows guide (INSTALLER_SETUP.md)" && ((DOC_OK++)) || true
check_file "${SCRIPT_DIR}/LINUX_INSTALLER_SETUP.md" "Linux guide (LINUX_INSTALLER_SETUP.md)" && ((DOC_OK++)) || true
check_file "${SCRIPT_DIR}/assets/README.md" "Asset guide (assets/README.md)" && ((DOC_OK++)) || true

echo ""

# ============ Asset Files (optional but recommended)
echo "🎨 Branding Assets (optional):"
ASSETS_FOUND=0

if [[ -f "${SCRIPT_DIR}/assets/aoj_icon.ico" ]]; then
  echo -e "  ${GREEN}✓${NC} Windows icon (aoj_icon.ico)"
  ((ASSETS_FOUND++))
else
  echo -e "  ${YELLOW}○${NC} Windows icon (aoj_icon.ico) — optional, improves UI"
fi

if [[ -f "${SCRIPT_DIR}/assets/aoj_icon.png" ]]; then
  echo -e "  ${GREEN}✓${NC} Linux icon (aoj_icon.png)"
  ((ASSETS_FOUND++))
else
  echo -e "  ${YELLOW}○${NC} Linux icon (aoj_icon.png) — optional, improves UI"
fi

if [[ -f "${SCRIPT_DIR}/assets/aoj_logo.bmp" ]]; then
  echo -e "  ${GREEN}✓${NC} Windows wizard image (aoj_logo.bmp)"
  ((ASSETS_FOUND++))
else
  echo -e "  ${YELLOW}○${NC} Windows wizard image (aoj_logo.bmp) — optional"
fi

echo ""

# ============ Build tools availability (checks)
echo "🔧 Build Tool Availability:"

if command -v iscc.exe &>/dev/null 2>&1 || command -v iscc &>/dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Inno Setup compiler (iscc) available"
else
  echo -e "  ${YELLOW}○${NC} Inno Setup compiler (iscc) not available (build on Windows required)"
fi

if command -v powershell &>/dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} PowerShell available (Windows build script)"
else
  echo -e "  ${YELLOW}○${NC} PowerShell not available (Windows build requires Windows/PowerShell)"
fi

if command -v bash &>/dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Bash available (Linux build script)"
else
  echo -e "  ${RED}✗${NC} Bash not available (required for Linux build)"
fi

if command -v fpm &>/dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} fpm available (for .deb/.rpm packages)"
else
  echo -e "  ${YELLOW}○${NC} fpm not available (optional, install with: gem install fpm)"
fi

echo ""

# ============ Summary
echo "════════════════════════════════════════════════════════════════"

TOTAL_OK=$((WINDOWS_OK + LINUX_OK + DOC_OK))
TOTAL_EXPECTED=$((3 + 2 + 4))

if [[ $TOTAL_OK -eq $TOTAL_EXPECTED ]]; then
  echo -e "✅ ${GREEN}All systems ready to build!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Place assets in installer/assets/ (optional but recommended)"
  echo "  2. Build Windows installer:"
  echo "     powershell -ExecutionPolicy Bypass -File installer\\build_installer.ps1"
  echo "  3. Build Linux installers:"
  echo "     bash installer/build_linux.sh --all"
  echo ""
  echo "Documentation:"
  echo "  - Windows: installer/INSTALLER_SETUP.md"
  echo "  - Linux:   installer/LINUX_INSTALLER_SETUP.md"
  echo "  - Overview: installer/README.md"
else
  echo -e "⚠️  ${YELLOW}Some files are missing.${NC}"
  echo "Visit installer/README.md for setup instructions."
fi

echo "════════════════════════════════════════════════════════════════"
