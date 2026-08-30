@echo off
title Academic Summary Bot (Auto-Restart)
cd /d D:\summary_msi\scripts
echo ========================================
echo   Academic Summary Bot (Auto-Restart)
echo ========================================
echo.
echo Bot akan otomatis restart jika crash.
echo Tekan Ctrl+C untuk berhenti.
echo.
python auto_restart.py
pause
