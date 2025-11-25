@echo off
setlocal enabledelayedexpansion

REM ===============================================
REM  Windows Watcher Script for OCR Trigger
REM  Monitors shared folder for capture.flag
REM  Launches run_ss_hidden.vbs silently
REM ===============================================

set "SHARED_FOLDER=\\10.129.143.40\incoming"
set "VBS_SCRIPT=C:\tools\run_ss_hidden.vbs"

echo [WATCHER] Starting... Monitoring %SHARED_FOLDER% for capture_*.flag
echo [WATCHER] Press Ctrl+C to stop.

:loop
    REM Check for any capture flag
    set FLAG_FOUND=
    for %%f in ("%SHARED_FOLDER%\capture_*.flag") do (
        set FLAG_FOUND=%%f
        goto :trigger_capture
    )

    REM No flag found → wait and loop
    timeout /t 2 /nobreak >nul
    goto :loop

:trigger_capture
    echo [WATCHER] Flag detected: !FLAG_FOUND!
    echo [WATCHER] Launching hidden screenshot capture...

    REM Call the VBScript (which runs send_screenshot.bat invisibly)
    cscript //nologo "%VBS_SCRIPT%"

    REM Wait a moment for the batch to complete (optional safety)
    timeout /t 1 >nul

    REM Delete the flag (only if it still exists)
    if exist "!FLAG_FOUND!" (
        del "!FLAG_FOUND!" >nul
        echo [WATCHER] Flag deleted.
    ) else (
        echo [WATCHER] Flag already deleted by script or another process.
    )

    goto :loop