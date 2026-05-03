Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Start AOJ Command OS in a native desktop window (no external browser needed).

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot 'backend'
$VenvPython = Join-Path $BackendDir '.venv\Scripts\python.exe'
$Launcher = Join-Path $BackendDir 'desktop_launcher.py'

if (-not (Test-Path $VenvPython)) {
    throw 'Backend virtual environment not found. Run scripts\install_windows.ps1 first.'
}

if (-not (Test-Path $Launcher)) {
    throw 'Desktop launcher not found: backend\desktop_launcher.py'
}

Push-Location $BackendDir
try {
    & $VenvPython $Launcher
}
finally {
    Pop-Location
}
