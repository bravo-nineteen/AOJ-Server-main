# AOJ Command OS - Production launcher (Windows)
# Serves the built React frontend AND the API from a single uvicorn process.
# Access the UI and API at http://MACHINE_IP:8000
#
# Prerequisites: run install_windows.ps1 first, then build the frontend:
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start_production_windows.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$VenvPython = Join-Path $ProjectRoot "backend\.venv\Scripts\python.exe"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDist = Join-Path $ProjectRoot "frontend\dist"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[AOJ] ERROR: Virtual environment not found at $VenvPython"
    Write-Host "[AOJ] Run install_windows.ps1 first."
    exit 1
}

if (-not (Test-Path $FrontendDist)) {
    Write-Host "[AOJ] ERROR: Frontend build not found at $FrontendDist"
    Write-Host "[AOJ] Run install_windows.ps1 first (it runs the frontend build)."
    exit 1
}

Write-Host "[AOJ] Starting production server on port 8000 (LAN-accessible)..."
Write-Host "[AOJ] UI + API: http://0.0.0.0:8000"
Write-Host "[AOJ] Press Ctrl+C to stop."
Write-Host ""

Set-Location $BackendDir
& $VenvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000
