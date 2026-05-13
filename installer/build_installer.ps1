# =============================================================================
# AOJ Command OS — build the Windows EXE installer
# =============================================================================
# Usage (from the project root):
#   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
#   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1 -Sign
#
# Prerequisites:
#   Inno Setup 6.x must be installed.
#   Download free from: https://jrsoftware.org/isdl.php
#
# Optional signing configuration (recommended for SmartScreen reputation):
#   $env:AOJ_SIGN_CERT_PATH = "C:\certs\aoj_codesign.pfx"
#   $env:AOJ_SIGN_CERT_PASSWORD = "<pfx-password>"
#   $env:AOJ_SIGN_TIMESTAMP_URL = "http://timestamp.digicert.com"
#   $env:AOJ_SIGNTOOL_PATH = "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
#   $env:AOJ_PRODUCT_URL = "https://github.com/YOUR_ORG/AOJ-Server"
# =============================================================================

param(
    [switch]$Sign,
    [string]$CertificatePath = $env:AOJ_SIGN_CERT_PATH,
    [string]$CertificatePassword = $env:AOJ_SIGN_CERT_PASSWORD,
    [string]$TimestampUrl = $(if ($env:AOJ_SIGN_TIMESTAMP_URL) { $env:AOJ_SIGN_TIMESTAMP_URL } else { 'http://timestamp.digicert.com' }),
    [string]$SignToolPath = $env:AOJ_SIGNTOOL_PATH,
    [string]$ProductUrl = $(if ($env:AOJ_PRODUCT_URL) { $env:AOJ_PRODUCT_URL } else { 'https://github.com/bravo-nineteen/AOJ-Server' })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Version tracking file (can be updated to bump installer version)
$VersionFile = Join-Path (Split-Path -Parent $PSScriptRoot) 'VERSION.txt'
$CurrentVersion = '1.0.1'
if (Test-Path $VersionFile) {
    $ReadVersion = Get-Content $VersionFile -Raw | Select-String -Pattern '\d+\.\d+\.\d+' -AllMatches | ForEach-Object { $_.Matches[0].Value }
    if ($ReadVersion) { $CurrentVersion = $ReadVersion }
}
Write-Host "Building AOJ Command OS Installer Version $CurrentVersion" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Locate iscc.exe (Inno Setup compiler)
$IsccCandidates = @(
    'C:\Program Files (x86)\Inno Setup 6\iscc.exe',
    'C:\Program Files\Inno Setup 6\iscc.exe',
    'C:\Program Files (x86)\Inno Setup 5\iscc.exe',
    'C:\Program Files\Inno Setup 5\iscc.exe'
)

$Iscc = $null
foreach ($candidate in $IsccCandidates) {
    if (Test-Path $candidate) {
        $Iscc = $candidate
        break
    }
}

if (-not $Iscc) {
    # Try PATH
    $fromPath = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($fromPath) {
        $Iscc = $fromPath.Source
    }
}

if (-not $Iscc) {
    Write-Host ""
    Write-Host "ERROR: Inno Setup compiler (iscc.exe) was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Download and install Inno Setup 6 (free) from:"
    Write-Host "  https://jrsoftware.org/isdl.php"
    Write-Host ""
    Write-Host "Then re-run this script."
    exit 1
}

Write-Host "Found Inno Setup at: $Iscc" -ForegroundColor Cyan

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

# Create output directory
$OutputDir = Join-Path $ProjectRoot 'dist\installer'
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# Verify and warn about logo assets
$AssetDir = Join-Path $PSScriptRoot 'assets'
$LogoFile = Join-Path $AssetDir 'aoj_logo.bmp'
$IconFile = Join-Path $AssetDir 'aoj_icon.ico'

if (-not (Test-Path $IconFile)) {
    Write-Host "WARNING: aoj_icon.ico not found at $IconFile" -ForegroundColor Yellow
    Write-Host "  Installer will use default icon. Place your logo icon file for branding." -ForegroundColor Yellow
}

if (-not (Test-Path $LogoFile)) {
    Write-Host "NOTE: aoj_logo.bmp not found at $LogoFile" -ForegroundColor Yellow
    Write-Host "  Wizard will not display custom branding. Place a 480x360px BMP file for wizard image." -ForegroundColor Yellow
}

# Clean old installers before building new version
Write-Host "Cleaning previous builds..." -ForegroundColor Gray
Get-ChildItem -Path $OutputDir -Filter 'AOJ_CommandOS_Setup_*.exe' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# Build
$IssFile = Join-Path $PSScriptRoot 'aoj_installer.iss'
Write-Host ""
Write-Host "Building installer..." -ForegroundColor Cyan
Write-Host "  Version : $CurrentVersion"
Write-Host "  Script  : $IssFile"
Write-Host "  Output  : $OutputDir"
Write-Host ""

& $Iscc $IssFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Installer built successfully." -ForegroundColor Green
    $exe = Get-ChildItem -Path $OutputDir -Filter '*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($exe) {
        Write-Host "Output: $($exe.FullName)" -ForegroundColor Green
        Write-Host "Size  : $([math]::Round($exe.Length / 1MB, 1)) MB"

        if ($Sign) {
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

            Write-Host "" 
            Write-Host "Signing installer with Authenticode..." -ForegroundColor Cyan
            Write-Host "SignTool : $resolvedSignTool"
            Write-Host "Timestamp: $TimestampUrl"

            & $resolvedSignTool sign /fd SHA256 /td SHA256 /tr $TimestampUrl /f $CertificatePath /p $CertificatePassword /d 'AOJ Command OS Installer (Airsoft Online Japan)' /du $ProductUrl $exe.FullName
            if ($LASTEXITCODE -ne 0) {
                throw "signtool sign failed (exit code $LASTEXITCODE)."
            }

            Write-Host "Verifying signature..." -ForegroundColor Cyan
            & $resolvedSignTool verify /pa /v $exe.FullName
            if ($LASTEXITCODE -ne 0) {
                throw "signtool verify failed (exit code $LASTEXITCODE)."
            }

            Write-Host "Installer is signed and verified." -ForegroundColor Green
        } else {
            Write-Host "" 
            Write-Host "WARNING: Installer is currently unsigned. SmartScreen warnings are expected on other machines." -ForegroundColor Yellow
            Write-Host "Re-run with -Sign after configuring AOJ_SIGN_CERT_PATH and AOJ_SIGN_CERT_PASSWORD to reduce warnings." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host ""
    Write-Host "Installer build failed (exit code $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}
