@echo off
title DualAudio Sync (Sonos and Citytek)
chcp 65001 >nul
cls

echo ========================================================
echo    Starting DualAudio Sync (Sonos + Citytek)
echo ========================================================
echo.

cd /d "%~dp0backend"

echo [1/2] Opening Web Dashboard in browser...
start "" http://localhost:5050

echo [2/2] Starting Audio Sync Server...
echo.
python app.py

pause
