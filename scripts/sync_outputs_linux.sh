#!/usr/bin/env bash
# Build split sync outputs for Linux:
# 1) Main Server (python package + linux executable when possible)
# 2) Team Terminals (source package + linux executable when possible)

set -euo pipefail

VERSION="${1:-$(date +%Y.%m.%d-%H%M)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$PROJECT_ROOT/outputs/$VERSION/linux"

mkdir -p "$OUT_DIR"

echo "[SYNC] Creating Linux sync outputs (version: $VERSION)"
echo "[SYNC] Output directory: $OUT_DIR"

MAIN_PY_ARCHIVE="$OUT_DIR/main-server-python-$VERSION-linux.tar.gz"
TEAM_PY_ARCHIVE="$OUT_DIR/team-terminals-python-$VERSION-linux.tar.gz"

# Main server python package (project without Team-Terminals-main)
tar -czf "$MAIN_PY_ARCHIVE" \
  -C "$PROJECT_ROOT" \
  --exclude=".git" \
  --exclude="outputs" \
  --exclude="Team-Terminals-main" \
  --exclude="backend/.venv" \
  --exclude="frontend/node_modules" \
  --exclude="**/__pycache__" \
  --exclude="*.pyc" \
  --exclude="backend/*.db" \
  .

# Team Terminals source package (Flutter project only)
tar -czf "$TEAM_PY_ARCHIVE" \
  -C "$PROJECT_ROOT" \
  --exclude="Team-Terminals-main/.dart_tool" \
  --exclude="Team-Terminals-main/build" \
  --exclude="Team-Terminals-main/.git" \
  --exclude="Team-Terminals-main/.idea" \
  --exclude="Team-Terminals-main/android/.gradle" \
  Team-Terminals-main

# Main server Linux executable (PyInstaller onefile)
MAIN_EXE_SKIP="$OUT_DIR/main-server-exe-linux-SKIPPED.txt"
if [[ -x "$PROJECT_ROOT/backend/.venv/bin/python" && -d "$PROJECT_ROOT/frontend/dist" ]]; then
  echo "[SYNC] Building main server Linux executable..."
  PY="$PROJECT_ROOT/backend/.venv/bin/python"
  "$PY" -m pip install --upgrade pyinstaller >/dev/null
  "$PY" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --name AOJ_Command_OS_Desktop_Linux \
    --distpath "$OUT_DIR" \
    --workpath "$PROJECT_ROOT/backend/.pyinstaller-work" \
    --specpath "$PROJECT_ROOT/backend/.pyinstaller-spec" \
    --add-data "$PROJECT_ROOT/frontend/dist:frontend/dist" \
    "$PROJECT_ROOT/backend/desktop_launcher.py" >/dev/null
  rm -f "$MAIN_EXE_SKIP"
else
  {
    echo "Skipped main server Linux executable build."
    echo "Requirements: backend/.venv/bin/python and frontend/dist"
  } > "$MAIN_EXE_SKIP"
fi

# Team Terminals Linux executable (Flutter)
TEAM_EXE_SKIP="$OUT_DIR/team-terminals-exe-linux-SKIPPED.txt"
if command -v flutter >/dev/null 2>&1 && [[ -d "$PROJECT_ROOT/Team-Terminals-main/linux" ]]; then
  echo "[SYNC] Building Team Terminals Linux executable..."
  pushd "$PROJECT_ROOT/Team-Terminals-main" >/dev/null
  flutter pub get >/dev/null
  flutter build linux --release >/dev/null
  popd >/dev/null

  TEAM_BUNDLE_DIR="$PROJECT_ROOT/Team-Terminals-main/build/linux/x64/release/bundle"
  if [[ -d "$TEAM_BUNDLE_DIR" ]]; then
    cp -r "$TEAM_BUNDLE_DIR" "$OUT_DIR/team-terminals-exe-linux"
    rm -f "$TEAM_EXE_SKIP"
  else
    {
      echo "Skipped Team Terminals Linux executable copy."
      echo "Flutter build completed but bundle path not found: $TEAM_BUNDLE_DIR"
    } > "$TEAM_EXE_SKIP"
  fi
else
  {
    echo "Skipped Team Terminals Linux executable build."
    echo "Requirements: flutter CLI and Team-Terminals-main/linux platform folder"
  } > "$TEAM_EXE_SKIP"
fi

echo "[SYNC] Done. Generated files:"
ls -1 "$OUT_DIR"
