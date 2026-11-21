@echo off
title DualAudio Sync Engine
cd /d "%~dp0\.."

echo ========================================================
echo        DualAudio Sync - Real-Time Multi-Room Audio
echo ========================================================
echo.

python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [INFO] Starting DualAudio Web Application...
start http://localhost:5000
python app.py

pause
