@echo off
setlocal enabledelayedexpansion

:: ===================================================
::  WATCH FOR FLAG FILES FROM RASPBERRY PI
:: ===================================================
set SHARE=\\192.168.1.151\incoming
set VBSPATH=C:\tools\run_ss_hidden_v1.vbs
set LOGFILE=C:\tools\flag_watcher.log

echo ================================================ >> "%LOGFILE%"
echo [%DATE% %TIME%] Flag Watcher started. >> "%LOGFILE%"
echo Watching folder: %SHARE% >> "%LOGFILE%"
echo ================================================ >> "%LOGFILE%"

:loop
for %%F in ("%SHARE%\capture_*.flag") do (
    echo [INFO] Flag detected: %%~nxF >> "%LOGFILE%"
    echo Trigger from Pi detected at %DATE% %TIME%
    
    :: Run your hidden screenshot capture
    cscript //nologo "%VBSPATH%"
    
    :: Wait a moment for screenshot + transfer
    timeout /t 3 >nul

    :: Delete flag to signal completion
    del "%%F" >nul 2>&1
    echo [DONE] Flag %%~nxF processed and removed. >> "%LOGFILE%"
)

timeout /t 2 >nul
goto loop
