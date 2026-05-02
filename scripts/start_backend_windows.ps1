Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Start the AOJ Command OS backend on Windows.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot 'backend'
$VenvPython = Join-Path $BackendDir '.venv\Scripts\python.exe'

if (-not (Test-Path $VenvPython)) {
    throw 'Backend virtual environment not found. Run scripts\install_windows.ps1 first.'
}

Push-Location $BackendDir
try {
    & $VenvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000
}
finally {
    Pop-Location
}
