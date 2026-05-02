Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Serve the built AOJ Command OS frontend on Windows.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDistDir = Join-Path $ProjectRoot 'frontend\dist'
$VenvPython = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
$Port = if ($env:AOJ_FRONTEND_PORT) { [int]$env:AOJ_FRONTEND_PORT } else { 4173 }

if (-not (Test-Path $FrontendDistDir)) {
    throw 'Frontend build directory not found. Run scripts\install_windows.ps1 first.'
}

if (-not (Test-Path $VenvPython)) {
    throw 'Backend virtual environment not found. Run scripts\install_windows.ps1 first.'
}

Push-Location $FrontendDistDir
try {
    & $VenvPython -m http.server $Port --bind 0.0.0.0
}
finally {
    Pop-Location
}
