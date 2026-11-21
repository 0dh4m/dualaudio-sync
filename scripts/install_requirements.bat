@echo off
title DualAudio Sync - تثبيت المتطلبات
chcp 65001 >nul
color 0a

echo ========================================================
echo    📦 تثبيت مكتبات بايثون لتطبيق DualAudio Sync
echo ========================================================
echo.

python -m pip install --upgrade pip
pip install soco flask sounddevice numpy soundfile pyaudiowpatch mutagen imageio-ffmpeg

echo.
echo ========================================================
echo    ✅ تم تثبيت جميع المكتبات بنجاح!
echo    يمكنك الآن تشغيل التطبيق عبر: Start_Sync_App.bat
echo ========================================================
echo.
pause
