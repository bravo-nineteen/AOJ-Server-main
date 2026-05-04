# AOJ Command OS – Release Checklist

Use this checklist before creating a distributable archive of the project.

---

## Pre-Release

- [ ] All unit and integration tests pass (if applicable)
- [ ] `GET /api/health` returns `{"status":"ok","database":"connected"}`
- [ ] Frontend builds without errors: `npm run build` in `frontend/`
- [ ] `frontend/dist/` exists and contains `index.html`
- [ ] Backend starts in production mode with no import errors
- [ ] WebSocket connects and receives `system.online` event
- [ ] Mission Control: create mission, start, timer counts down
- [ ] Schedule: create item, mark complete
- [ ] Results: create result, winner displayed in Results Board
- [ ] Prop Network: arm/disarm command, status updates
- [ ] System Logs: entries appear, clear works
- [ ] System Monitor: status shows online, metrics visible
- [ ] AI Assistant: mock response returned, blocked actions rejected
- [ ] Update Center: version displayed, backup creates a file in `backend/backups/`

## Version Bump

- [ ] Update `version` in `backend/app/main.py` FastAPI constructor
- [ ] Update `version` in `frontend/package.json`
- [ ] Update `VERSION` in this checklist header below:

**Current release version: 1.0.0**

## Package

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_release_windows.ps1 -Version "1.0.0"
```

Output: `aoj-command-os-1.0.0-windows.zip`

### Windows Code Signing (recommended)

- [ ] Use an OV or EV code-signing certificate issued to your legal publisher name
- [ ] Set signing environment variables in the current shell:

```powershell
$env:AOJ_SIGN_CERT_PATH = "C:\certs\aoj_codesign.pfx"
$env:AOJ_SIGN_CERT_PASSWORD = "<pfx-password>"
$env:AOJ_SIGN_TIMESTAMP_URL = "http://timestamp.digicert.com"
# Optional if signtool.exe is not on PATH:
# $env:AOJ_SIGNTOOL_PATH = "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
```

- [ ] Build and sign installer EXE:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build_installer.ps1 -Sign
```

- [ ] Build and sign desktop EXE (if distributing standalone desktop binary):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_desktop_exe.ps1 -Sign
```

- [ ] Verify signatures manually from PowerShell (optional defense in depth):

```powershell
Get-AuthenticodeSignature .\dist\installer\AOJ_Command_OS_Setup_1.0.0.exe
Get-AuthenticodeSignature .\dist\desktop\AOJ_Command_OS_Desktop.exe
```

- [ ] Confirm signature status is `Valid` and publisher matches release notes
- [ ] Publish the same filename/version repeatedly to build SmartScreen reputation over time

### Linux / Raspberry Pi

```bash
chmod +x ./scripts/package_release_linux.sh
./scripts/package_release_linux.sh 1.0.0
```

Output: `aoj-command-os-1.0.0-linux.tar.gz`

## Archive Contents Verification

After creating the archive, spot-check it before distributing:

- [ ] `aoj-command-os/README.md` is present
- [ ] `aoj-command-os/backend/requirements.txt` is present
- [ ] `aoj-command-os/backend/app/main.py` is present
- [ ] `aoj-command-os/frontend/package.json` is present
- [ ] `aoj-command-os/scripts/install_windows.ps1` is present
- [ ] `aoj-command-os/scripts/install_linux.sh` is present
- [ ] No `.venv/` directory included
- [ ] No `node_modules/` directory included
- [ ] No `frontend/dist/` directory included (recipients build it themselves)
- [ ] No `*.db` database files included (clean install produces a fresh db)
- [ ] No `backend/backups/` included

## Post-Package

- [ ] Test a clean install from the archive on a separate machine or clean directory:
  - Extract, run installer script, run production launcher, confirm UI loads at port 8000
- [ ] Tag the Git commit: `git tag v1.0.0`
- [ ] Upload archive to release storage / GitHub Releases

## Install Instructions for Recipients

### Windows

```powershell
Expand-Archive .\aoj-command-os-1.0.0-windows.zip -DestinationPath .
powershell -ExecutionPolicy Bypass -File .\aoj-command-os\scripts\install_windows.ps1
powershell -ExecutionPolicy Bypass -File .\aoj-command-os\scripts\start_production_windows.ps1
```

Access: http://MACHINE_IP:8000

### Linux / Raspberry Pi

```bash
tar -xzf aoj-command-os-1.0.0-linux.tar.gz
chmod +x ./aoj-command-os/scripts/*.sh
./aoj-command-os/scripts/install_linux.sh
./aoj-command-os/scripts/start_production.sh
```

Access: http://MACHINE_IP:8000
