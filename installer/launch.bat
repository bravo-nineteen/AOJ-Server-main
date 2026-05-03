@echo off
REM AOJ Command OS — launcher
REM This file is called by launch.vbs (which hides the console window).
REM You can also double-click this .bat to launch with a visible console.

SET SCRIPT_DIR=%~dp0
SET VENV_PYTHON=%SCRIPT_DIR%backend\.venv\Scripts\python.exe
SET DESKTOP_LAUNCHER=%SCRIPT_DIR%backend\desktop_launcher.py

IF NOT EXIST "%VENV_PYTHON%" (
    echo [AOJ] Setup has not been completed yet.
    echo [AOJ] Please re-run the installer or run: scripts\install_windows.ps1
    pause
    exit /b 1
)

IF NOT EXIST "%SCRIPT_DIR%frontend\dist\index.html" (
    echo [AOJ] Frontend build missing.
    echo [AOJ] Please re-run the installer or run: scripts\install_windows.ps1
    pause
    exit /b 1
)

IF NOT EXIST "%DESKTOP_LAUNCHER%" (
    echo [AOJ] Desktop launcher missing.
    echo [AOJ] Please update AOJ and re-run scripts\install_windows.ps1
    pause
    exit /b 1
)

echo [AOJ] Starting AOJ Command OS desktop app...
echo [AOJ] A native AOJ window will open (no browser required).
echo [AOJ] Close that window to stop AOJ if it launched the backend.

cd /d "%SCRIPT_DIR%backend"
"%VENV_PYTHON%" "%DESKTOP_LAUNCHER%"
