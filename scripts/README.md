# Scripts

Automation scripts for setup, deployment, backups, and maintenance.

## Raspberry Pi 5 + Ollama

```bash
chmod +x ./scripts/install_pi.sh ./scripts/setup_pi_ollama.sh ./scripts/start_production.sh
./scripts/install_pi.sh
./scripts/setup_pi_ollama.sh
./scripts/start_production.sh
```

Notes:
- `setup_pi_ollama.sh` installs Ollama service and pulls `qwen2.5:0.5b` by default.
- `start_production.sh` now defaults to `OLLAMA_STRICT=true` and Pi LoRa SPI settings when running on Raspberry Pi hardware.

## Sync Output Builders

Use these scripts to generate separate deliverables for:

- Main Server
- Team Terminals

for Linux and Windows in one run.

### Linux

```bash
chmod +x ./scripts/sync_outputs_linux.sh
./scripts/sync_outputs_linux.sh
./scripts/sync_outputs_linux.sh 1.0.0
```

Output path:

- `outputs/<version>/linux/`

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync_outputs_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\sync_outputs_windows.ps1 -Version "1.0.0"
```

Output path:

- `outputs\<version>\windows\`

## Team-Terminals APK CLI

Build Android APKs for the Flutter Team-Terminals app from repo root.

```bash
chmod +x ./scripts/team_terminals_apk_cli.sh
./scripts/team_terminals_apk_cli.sh build --release
```

Useful commands:

```bash
./scripts/team_terminals_apk_cli.sh build --debug
./scripts/team_terminals_apk_cli.sh build --split-per-abi
./scripts/team_terminals_apk_cli.sh locate
./scripts/team_terminals_apk_cli.sh clean
./scripts/team_terminals_apk_cli.sh doctor
```

Optional flags for `build`:

- `--flutter-bin <path>` to use a specific Flutter binary
- `--target-platform <value>` forwarded to Flutter build
- `--output-dir <path>` to control where APKs are copied
- `--no-copy` to skip output copy step
