@echo off
title DualAudio Sync - Python Dependencies Setup
chcp 65001 >nul
color 0a

echo ========================================================
echo    Installing Python dependencies for DualAudio Sync...
echo ========================================================
echo.

python -m pip install --upgrade pip
pip install -r "%~dp0..\requirements.txt"

echo.
echo ========================================================
echo    Dependencies installed successfully!
echo    You can now launch the app via: scripts\start.bat
echo ========================================================
echo.
pause
