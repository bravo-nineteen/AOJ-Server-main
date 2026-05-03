Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# AOJ Command OS Windows installer.
#
# This script creates the backend virtual environment, installs Python
# dependencies, installs frontend dependencies, and builds the frontend.
# It does not install Windows services or modify machine-wide settings.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'frontend'
$VenvDir = Join-Path $BackendDir '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'

function Get-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return 'py'
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return 'python'
    }
    throw 'Python 3 was not found. Install Python 3 and rerun this script.'
}

function Get-NpmCommand {
    if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
        return 'npm.cmd'
    }
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        return 'npm'
    }
    throw 'npm was not found. Install Node.js and rerun this script.'
}

$PythonLauncher = Get-PythonLauncher
$NpmCommand = Get-NpmCommand

if (-not (Test-Path $VenvDir)) {
    if ($PythonLauncher -eq 'py') {
        & py -3 -m venv $VenvDir
    }
    else {
        & python -m venv $VenvDir
    }
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $BackendDir 'requirements.txt')

Push-Location $FrontendDir
try {
    & $NpmCommand install
    & $NpmCommand run build
}
finally {
    Pop-Location
}

Write-Host '[AOJ] Windows installation complete.'
Write-Host "[AOJ] Desktop start (no browser): $ProjectRoot\scripts\start_desktop_windows.ps1"
Write-Host "[AOJ] Backend start: $ProjectRoot\scripts\start_backend_windows.ps1"
Write-Host "[AOJ] Frontend start: $ProjectRoot\scripts\start_frontend_windows.ps1"
