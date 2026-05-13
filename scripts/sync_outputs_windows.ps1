# Split sync outputs for Windows:
# 1) Main Server (python package + desktop exe)
# 2) Team Terminals (source package + windows exe when possible)

param(
    [string]$Version = (Get-Date -Format "yyyy.MM.dd-HHmm")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$OutDir = Join-Path $ProjectRoot "outputs\$Version\windows"
New-Item -Path $OutDir -ItemType Directory -Force | Out-Null

Write-Host "[SYNC] Creating Windows sync outputs (version: $Version)"
Write-Host "[SYNC] Output directory: $OutDir"

function New-ZipFromFiles {
    param(
        [Parameter(Mandatory = $true)] [string]$ZipPath,
        [Parameter(Mandatory = $true)] [System.Collections.Generic.List[string]]$Files,
        [Parameter(Mandatory = $true)] [string]$Root
    )

    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath -Force
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::Open($ZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($full in $Files) {
            $rel = $full.Substring($Root.Length + 1)
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $zip,
                $full,
                $rel,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
    finally {
        $zip.Dispose()
    }
}

# Main server python package (exclude Team-Terminals-main)
$mainZip = Join-Path $OutDir "main-server-python-$Version-windows.zip"
$mainFiles = New-Object 'System.Collections.Generic.List[string]'
Get-ChildItem -Path $ProjectRoot -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($ProjectRoot.Length + 1)
    if (
        $rel -like ".git*" -or
        $rel -like "outputs*" -or
        $rel -like "Team-Terminals-main*" -or
        $rel -like "backend\.venv*" -or
        $rel -like "frontend\node_modules*" -or
        $rel -like "*__pycache__*" -or
        $rel -like "*.pyc" -or
        $rel -like "backend\*.db" -or
        $rel -like "backend\*.db-shm" -or
        $rel -like "backend\*.db-wal"
    ) {
        return
    }
    $mainFiles.Add($_.FullName)
}
New-ZipFromFiles -ZipPath $mainZip -Files $mainFiles -Root $ProjectRoot

# Team Terminals source package only
$teamZip = Join-Path $OutDir "team-terminals-python-$Version-windows.zip"
$teamFiles = New-Object 'System.Collections.Generic.List[string]'
$teamRoot = Join-Path $ProjectRoot "Team-Terminals-main"
Get-ChildItem -Path $teamRoot -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($teamRoot.Length + 1)
    if (
        $rel -like ".dart_tool*" -or
        $rel -like "build*" -or
        $rel -like ".git*" -or
        $rel -like ".idea*" -or
        $rel -like "android\.gradle*"
    ) {
        return
    }
    $teamFiles.Add($_.FullName)
}
New-ZipFromFiles -ZipPath $teamZip -Files $teamFiles -Root $ProjectRoot

# Main server desktop EXE
$mainExeSkipped = Join-Path $OutDir "main-server-exe-windows-SKIPPED.txt"
try {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "build_desktop_exe.ps1") -Version $Version
    $builtExe = Join-Path $ProjectRoot "dist\desktop\AOJ_Command_OS_Desktop.exe"
    if (Test-Path $builtExe) {
        Copy-Item $builtExe (Join-Path $OutDir "main-server-exe-$Version-windows.exe") -Force
        if (Test-Path $mainExeSkipped) { Remove-Item $mainExeSkipped -Force }
    }
    else {
        "Skipped main server EXE copy. Expected EXE not found: $builtExe" | Set-Content $mainExeSkipped
    }
}
catch {
    "Skipped main server EXE build. Error: $($_.Exception.Message)" | Set-Content $mainExeSkipped
}

# Team Terminals Windows EXE (Flutter)
$teamExeSkipped = Join-Path $OutDir "team-terminals-exe-windows-SKIPPED.txt"
try {
    $flutter = Get-Command flutter -ErrorAction SilentlyContinue
    $teamWindowsFolder = Join-Path $teamRoot "windows"
    if (-not $flutter -or -not (Test-Path $teamWindowsFolder)) {
        "Skipped Team Terminals Windows EXE build. Requirements: flutter CLI and Team-Terminals-main\windows platform folder" | Set-Content $teamExeSkipped
    }
    else {
        Push-Location $teamRoot
        try {
            & flutter pub get | Out-Null
            & flutter build windows --release | Out-Null
        }
        finally {
            Pop-Location
        }

        $builtTeamExe = Join-Path $teamRoot "build\windows\x64\runner\Release\team_terminals.exe"
        if (Test-Path $builtTeamExe) {
            Copy-Item $builtTeamExe (Join-Path $OutDir "team-terminals-exe-$Version-windows.exe") -Force
            if (Test-Path $teamExeSkipped) { Remove-Item $teamExeSkipped -Force }
        }
        else {
            "Skipped Team Terminals Windows EXE copy. Expected EXE not found: $builtTeamExe" | Set-Content $teamExeSkipped
        }
    }
}
catch {
    "Skipped Team Terminals Windows EXE build. Error: $($_.Exception.Message)" | Set-Content $teamExeSkipped
}

Write-Host "[SYNC] Done. Generated files:"
Get-ChildItem -Path $OutDir -File | Select-Object -ExpandProperty Name
