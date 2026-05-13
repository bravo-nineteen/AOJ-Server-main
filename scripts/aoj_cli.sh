#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"

usage() {
  cat <<'EOF'
AOJ Repository CLI

Usage:
  ./scripts/aoj_cli.sh <command> [args]

Commands:
  terminals-apk   Build/manage Team-Terminals APK artifacts
  tt-apk          Alias for terminals-apk
  help            Show this help

Examples:
  ./scripts/aoj_cli.sh terminals-apk build --release
  ./scripts/aoj_cli.sh terminals-apk build --split-per-abi
  ./scripts/aoj_cli.sh tt-apk locate
EOF
}

run_terminals_apk() {
  local script="$SCRIPTS_DIR/team_terminals_apk_cli.sh"
  if [[ ! -f "$script" ]]; then
    echo "Error: Missing script: $script" >&2
    exit 1
  fi
  if [[ ! -x "$script" ]]; then
    chmod +x "$script"
  fi

  "$script" "$@"
}

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 1
  fi

  local cmd="$1"
  shift || true

  case "$cmd" in
    terminals-apk|tt-apk)
      run_terminals_apk "$@"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      echo "Error: Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
