# =============================================================================
# AOJ Command OS — build the Windows EXE installer
# =============================================================================
# Usage (from the project root):
#   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
#
# Prerequisites:
#   Inno Setup 6.x must be installed.
#   Download free from: https://jrsoftware.org/isdl.php
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

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

# Create output directory
$OutputDir = Join-Path $ProjectRoot 'dist\installer'
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# Build
$IssFile = Join-Path $PSScriptRoot 'aoj_installer.iss'
Write-Host ""
Write-Host "Building installer..." -ForegroundColor Cyan
Write-Host "  Script : $IssFile"
Write-Host "  Output : $OutputDir"
Write-Host ""

& $Iscc $IssFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Installer built successfully." -ForegroundColor Green
    $exe = Get-ChildItem -Path $OutputDir -Filter '*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($exe) {
        Write-Host "Output: $($exe.FullName)" -ForegroundColor Green
        Write-Host "Size  : $([math]::Round($exe.Length / 1MB, 1)) MB"
    }
} else {
    Write-Host ""
    Write-Host "Installer build failed (exit code $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}
