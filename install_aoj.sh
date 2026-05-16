#!/bin/bash
# AOJ Quick Install Wrapper
# This script can be double-clicked or run from terminal

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure scripts are executable
chmod +x scripts/quick-install.sh

# Run the installer
./scripts/quick-install.sh

# Keep terminal open on exit
read -p "Press Enter to close..."
