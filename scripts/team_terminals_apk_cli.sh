#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/Team-Terminals-main"
FLUTTER_BIN="${FLUTTER_BIN:-flutter}"

usage() {
  cat <<'EOF'
Team-Terminals APK CLI

Usage:
  ./scripts/team_terminals_apk_cli.sh <command> [options]

Commands:
  build    Build APK and export it under outputs/
  clean    Run flutter clean in Team-Terminals-main
  doctor   Run flutter doctor -v
  locate   List generated APK files

Build options:
  --debug              Build debug APK (default: release)
  --release            Build release APK
  --split-per-abi      Build split APKs per ABI
  --target-platform P  Forwarded to flutter build apk --target-platform
  --flutter-bin PATH   Flutter executable to use
  --output-dir PATH    Destination directory for copied APK(s)
  --no-copy            Do not copy APK(s) to outputs/
  -h, --help           Show this help

Examples:
  ./scripts/team_terminals_apk_cli.sh build --release
  ./scripts/team_terminals_apk_cli.sh build --split-per-abi
  FLUTTER_BIN=/opt/flutter/bin/flutter ./scripts/team_terminals_apk_cli.sh build
EOF
}

require_flutter() {
  if ! command -v "$FLUTTER_BIN" >/dev/null 2>&1; then
    echo "Error: Flutter executable not found: $FLUTTER_BIN" >&2
    exit 1
  fi
}

resolve_version() {
  local version_line
  version_line="$(grep -E '^version:' "$APP_DIR/pubspec.yaml" | head -n1 || true)"
  if [[ -z "$version_line" ]]; then
    echo "unknown"
    return
  fi

  local version_raw
  version_raw="${version_line#version:}"
  version_raw="$(echo "$version_raw" | tr -d '[:space:]')"
  echo "$version_raw"
}

command_build() {
  local build_mode="release"
  local split_per_abi="false"
  local target_platform=""
  local copy_outputs="true"
  local output_dir=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --debug)
        build_mode="debug"
        ;;
      --release)
        build_mode="release"
        ;;
      --split-per-abi)
        split_per_abi="true"
        ;;
      --target-platform)
        shift
        target_platform="${1:-}"
        if [[ -z "$target_platform" ]]; then
          echo "Error: --target-platform requires a value" >&2
          exit 1
        fi
        ;;
      --flutter-bin)
        shift
        FLUTTER_BIN="${1:-}"
        if [[ -z "$FLUTTER_BIN" ]]; then
          echo "Error: --flutter-bin requires a value" >&2
          exit 1
        fi
        ;;
      --output-dir)
        shift
        output_dir="${1:-}"
        if [[ -z "$output_dir" ]]; then
          echo "Error: --output-dir requires a value" >&2
          exit 1
        fi
        ;;
      --no-copy)
        copy_outputs="false"
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Error: Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
    shift
  done

  require_flutter

  if [[ ! -d "$APP_DIR" ]]; then
    echo "Error: Team-Terminals app folder not found: $APP_DIR" >&2
    exit 1
  fi

  pushd "$APP_DIR" >/dev/null
  "$FLUTTER_BIN" pub get

  local -a build_args
  build_args=(build apk "--$build_mode")
  if [[ "$split_per_abi" == "true" ]]; then
    build_args+=(--split-per-abi)
  fi
  if [[ -n "$target_platform" ]]; then
    build_args+=(--target-platform "$target_platform")
  fi

  "$FLUTTER_BIN" "${build_args[@]}"

  local apk_dir="$APP_DIR/build/app/outputs/flutter-apk"
  mapfile -t apks < <(find "$apk_dir" -maxdepth 1 -type f -name "*.apk" | sort)
  popd >/dev/null

  if [[ "${#apks[@]}" -eq 0 ]]; then
    echo "Error: No APK files were generated in $apk_dir" >&2
    exit 1
  fi

  echo "Build complete. Generated APK(s):"
  printf '  %s\n' "${apks[@]}"

  if [[ "$copy_outputs" == "false" ]]; then
    return
  fi

  local stamp version destination
  stamp="$(date +%Y%m%d_%H%M%S)"
  version="$(resolve_version)"

  if [[ -n "$output_dir" ]]; then
    destination="$output_dir"
  else
    destination="$ROOT_DIR/outputs/team-terminals-apk/${version}_${stamp}"
  fi

  mkdir -p "$destination"
  cp "${apks[@]}" "$destination/"

  echo
  echo "Copied APK(s) to: $destination"
}

command_clean() {
  require_flutter
  pushd "$APP_DIR" >/dev/null
  "$FLUTTER_BIN" clean
  popd >/dev/null
}

command_doctor() {
  require_flutter
  "$FLUTTER_BIN" doctor -v
}

command_locate() {
  local apk_dir="$APP_DIR/build/app/outputs/flutter-apk"
  if [[ ! -d "$apk_dir" ]]; then
    echo "No build output directory yet: $apk_dir"
    return
  fi

  local found
  found="$(find "$apk_dir" -maxdepth 1 -type f -name '*.apk' | sort || true)"
  if [[ -z "$found" ]]; then
    echo "No APKs found in: $apk_dir"
    return
  fi

  echo "$found"
}

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 1
  fi

  local cmd="$1"
  shift

  case "$cmd" in
    build)
      command_build "$@"
      ;;
    clean)
      command_clean
      ;;
    doctor)
      command_doctor
      ;;
    locate)
      command_locate
      ;;
    -h|--help|help)
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
