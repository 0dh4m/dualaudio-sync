@echo off
title Install VB-CABLE Driver (Silent PC Speakers)
cls
echo ========================================================
echo    Installing VB-Audio Virtual Cable Driver...
echo ========================================================
echo.
echo This tool lets your laptop speakers stay COMPLETELY SILENT
echo while streaming sound ONLY to Sonos and Citytek in sync!
echo.
echo Click "Yes" on the Windows Administrator prompt,
echo then click "Install Driver" in the window that appears.
echo.
powershell -Command "Start-Process '%~dp0vbcable\VBCABLE_Setup_x64.exe' -Verb RunAs"
pause
