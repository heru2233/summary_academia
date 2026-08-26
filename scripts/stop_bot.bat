@echo off
echo Stopping Academic Summary Bot...
taskkill /IM python.exe /F 2>nul
if %errorlevel% equ 0 (
    echo Bot stopped.
) else (
    echo Bot not running.
)
pause
