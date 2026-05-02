@echo off
REM AOJ Command OS — launcher
REM This file is called by launch.vbs (which hides the console window).
REM You can also double-click this .bat to launch with a visible console.

SET SCRIPT_DIR=%~dp0
SET VENV_PYTHON=%SCRIPT_DIR%backend\.venv\Scripts\python.exe

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

echo [AOJ] Starting AOJ Command OS...
echo [AOJ] Open http://localhost:8000 in your browser.
echo [AOJ] Close this window to stop the server.

REM Open the browser after a short delay (start is non-blocking)
start "" /B cmd /C "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM Start the server (blocking — keeps this window open)
cd /d "%SCRIPT_DIR%backend"
"%VENV_PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
