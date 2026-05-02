# AOJ Command OS - Release packager (Windows)
# Creates a distributable zip archive of the project suitable for download and install.
# Excludes runtime artifacts: .venv, node_modules, __pycache__, dist, *.db, backups.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\package_release_windows.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\package_release_windows.ps1 -Version "1.2.0"
#
# Output: aoj-command-os-1.0.0-windows.zip in the project root (or parent directory).

param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ArchiveName = "aoj-command-os-$Version-windows.zip"
$OutputPath = Join-Path $ProjectRoot $ArchiveName

Write-Host "[AOJ] Packaging release v$Version..."
Write-Host "[AOJ] Project root: $ProjectRoot"
Write-Host "[AOJ] Output: $OutputPath"

# Remove existing archive if present
if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
    Write-Host "[AOJ] Removed existing archive."
}

# Build list of files to include, excluding runtime-generated directories and files
$Excludes = @(
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "*.pyc",
    "dist",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "backups"
)

# Collect all files that should be included
$FilesToInclude = Get-ChildItem -Path $ProjectRoot -Recurse -File | Where-Object {
    $RelPath = $_.FullName.Substring($ProjectRoot.Length + 1)
    $Parts = $RelPath -split '\\'
    $Excluded = $false
    foreach ($Part in $Parts) {
        foreach ($Pattern in $Excludes) {
            if ($Part -like $Pattern) {
                $Excluded = $true
                break
            }
        }
        if ($Excluded) { break }
    }
    -not $Excluded
}

Write-Host "[AOJ] Files to include: $($FilesToInclude.Count)"

# Create the zip using .NET ZipFile
Add-Type -AssemblyName System.IO.Compression.FileSystem

$ZipStream = [System.IO.Compression.ZipFile]::Open($OutputPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($File in $FilesToInclude) {
        $RelPath = $File.FullName.Substring($ProjectRoot.Length + 1)
        $EntryName = "aoj-command-os\" + $RelPath
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($ZipStream, $File.FullName, $EntryName, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally {
    $ZipStream.Dispose()
}

$SizeMB = [math]::Round((Get-Item $OutputPath).Length / 1MB, 2)
Write-Host ""
Write-Host "[AOJ] Release package created: $ArchiveName ($SizeMB MB)"
Write-Host "[AOJ] Recipients can install with:"
Write-Host "      Expand-Archive .\$ArchiveName -DestinationPath ."
Write-Host "      powershell -ExecutionPolicy Bypass -File .\aoj-command-os\scripts\install_windows.ps1"
