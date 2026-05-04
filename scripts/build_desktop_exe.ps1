Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Build a single-file AOJ desktop executable for Windows.

param(
    [switch]$Sign,
    [string]$CertificatePath = $env:AOJ_SIGN_CERT_PATH,
    [string]$CertificatePassword = $env:AOJ_SIGN_CERT_PASSWORD,
    [string]$TimestampUrl = $(if ($env:AOJ_SIGN_TIMESTAMP_URL) { $env:AOJ_SIGN_TIMESTAMP_URL } else { 'http://timestamp.digicert.com' }),
    [string]$SignToolPath = $env:AOJ_SIGNTOOL_PATH,
    [string]$ProductUrl = $(if ($env:AOJ_PRODUCT_URL) { $env:AOJ_PRODUCT_URL } else { 'https://github.com/YOUR_ORG/AOJ-Server' })
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot 'backend'
$VenvPython = Join-Path $BackendDir '.venv\Scripts\python.exe'
$FrontendDist = Join-Path $ProjectRoot 'frontend\dist'
$Launcher = Join-Path $BackendDir 'desktop_launcher.py'
$OutDir = Join-Path $ProjectRoot 'dist\desktop'
$DesktopExe = Join-Path $OutDir 'AOJ_Command_OS_Desktop.exe'

function Find-SignTool {
    param([string]$PreferredPath)

    if ($PreferredPath -and (Test-Path $PreferredPath)) {
        return $PreferredPath
    }

    $fromPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $kitRoots = @(
        'C:\Program Files (x86)\Windows Kits\10\bin',
        'C:\Program Files\Windows Kits\10\bin'
    )

    foreach ($root in $kitRoots) {
        if (-not (Test-Path $root)) {
            continue
        }

        $candidate = Get-ChildItem -Path $root -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1

        if ($candidate) {
            return $candidate.FullName
        }
    }

    return $null
}

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

if ($Sign) {
    if (-not (Test-Path $DesktopExe)) {
        throw "Desktop executable not found: $DesktopExe"
    }
    if (-not $CertificatePath) {
        throw 'Signing requested but no certificate path was provided. Set AOJ_SIGN_CERT_PATH or pass -CertificatePath.'
    }
    if (-not (Test-Path $CertificatePath)) {
        throw "Signing certificate not found: $CertificatePath"
    }
    if (-not $CertificatePassword) {
        throw 'Signing requested but no certificate password was provided. Set AOJ_SIGN_CERT_PASSWORD or pass -CertificatePassword.'
    }

    $resolvedSignTool = Find-SignTool -PreferredPath $SignToolPath
    if (-not $resolvedSignTool) {
        throw 'Signing requested but signtool.exe was not found. Install Windows SDK Signing Tools or set AOJ_SIGNTOOL_PATH.'
    }

    Write-Host "[AOJ] Signing desktop executable..." -ForegroundColor Cyan
    & $resolvedSignTool sign /fd SHA256 /td SHA256 /tr $TimestampUrl /f $CertificatePath /p $CertificatePassword /d 'AOJ Command OS Desktop (Airsoft Online Japan)' /du $ProductUrl $DesktopExe
    if ($LASTEXITCODE -ne 0) {
        throw "signtool sign failed (exit code $LASTEXITCODE)."
    }

    Write-Host "[AOJ] Verifying desktop executable signature..." -ForegroundColor Cyan
    & $resolvedSignTool verify /pa /v $DesktopExe
    if ($LASTEXITCODE -ne 0) {
        throw "signtool verify failed (exit code $LASTEXITCODE)."
    }

    Write-Host "[AOJ] Desktop executable is signed and verified." -ForegroundColor Green
}
