@echo off
echo ================================================
echo   WATCHER LAUNCHER
echo   This will keep restarting the watcher
echo   Press Ctrl+C to stop completely
echo ================================================
echo.

:restart_loop
call C:\tools\unified_watcher.bat
if errorlevel 1 (
    echo.
    echo [Launcher] Watcher exited, restarting in 1 second...
    ping 127.0.0.1 -n 2 >nul
    goto restart_loop
)
echo [Launcher] Watcher stopped normally.
pause