Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Build a single-file AOJ desktop executable for Windows.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot 'backend'
$VenvPython = Join-Path $BackendDir '.venv\Scripts\python.exe'
$FrontendDist = Join-Path $ProjectRoot 'frontend\dist'
$Launcher = Join-Path $BackendDir 'desktop_launcher.py'
$OutDir = Join-Path $ProjectRoot 'dist\desktop'

if (-not (Test-Path $VenvPython)) {
    throw 'Backend virtual environment not found. Run scripts\install_windows.ps1 first.'
}

if (-not (Test-Path $FrontendDist)) {
    throw 'Frontend build not found. Run scripts\install_windows.ps1 first.'
}

if (-not (Test-Path $Launcher)) {
    throw 'Desktop launcher not found: backend\desktop_launcher.py'
}

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

& $VenvPython -m pip install --upgrade pyinstaller

Push-Location $ProjectRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean --onefile --windowed --name AOJ_Command_OS_Desktop --distpath $OutDir --add-data "frontend/dist;frontend/dist" backend/desktop_launcher.py
}
finally {
    Pop-Location
}

Write-Host "[AOJ] Desktop executable built at: $OutDir" -ForegroundColor Green
