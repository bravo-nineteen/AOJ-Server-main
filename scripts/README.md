# Scripts

Automation scripts for setup, deployment, backups, and maintenance.

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
