Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Start both AOJ Command OS services in separate PowerShell windows on Windows.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendScript = Join-Path $ScriptDir 'start_backend_windows.ps1'
$FrontendScript = Join-Path $ScriptDir 'start_frontend_windows.ps1'

Start-Process powershell.exe -ArgumentList @(
    '-ExecutionPolicy', 'Bypass',
    '-NoExit',
    '-File', $BackendScript
)

Start-Process powershell.exe -ArgumentList @(
    '-ExecutionPolicy', 'Bypass',
    '-NoExit',
    '-File', $FrontendScript
)

Write-Host '[AOJ] Backend:  http://127.0.0.1:8000'
Write-Host '[AOJ] Frontend: http://127.0.0.1:4173'
