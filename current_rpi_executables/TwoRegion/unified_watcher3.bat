@echo off
setlocal
set SHARE=\\192.168.1.151\incoming
set VBS1=C:\tools\run_ss1.vbs
set VBS2=C:\tools\run_ss2.vbs
set LOGFILE=C:\tools\unified_watcher.log

echo [%DATE% %TIME%] Unified watcher STARTED. >> "%LOGFILE%"
echo.
echo ================================================
echo   UNIFIED WATCHER - Multi-Region Monitor
echo   Monitoring: capture1_*.flag and capture2_*.flag
echo   Press Ctrl+C to stop
echo ================================================
echo.

:loop
rem --- Map network path using pushd ---
pushd "%SHARE%" >nul 2>&1
if errorlevel 1 (
    echo [%TIME%] ERROR: Share unreachable.
    echo [%DATE% %TIME%] Share unreachable. >> "%LOGFILE%"
    ping 127.0.0.1 -n 6 >nul
    goto loop
)

rem --- Check for capture1_*.flag files ---
set FOUND1=0
for %%F in (capture1_*.flag) do (
    set FOUND1=1
    set FLAGFILE1=%%F
)

rem --- Check for capture2_*.flag files ---
set FOUND2=0
for %%F in (capture2_*.flag) do (
    set FOUND2=1
    set FLAGFILE2=%%F
)

rem --- Unmap BEFORE processing to avoid conflicts ---
popd >nul

rem --- Process Region 1 if found ---
if "%FOUND1%"=="1" (
    echo.
    echo ********************************************
    echo ** REGION 1 TRIGGER DETECTED! **
    echo ** File: %FLAGFILE1%
    echo ** Action: Calling run_ss1.vbs
    echo ********************************************
    echo.
    
    echo [%TIME%] [REGION 1] TRIGGER: %FLAGFILE1%
    echo [%DATE% %TIME%] Region 1: Processing %FLAGFILE1% >> "%LOGFILE%"
    
    rem --- Call VBS from local context ---
    cscript //nologo "%VBS1%"
    
    echo [%TIME%] [REGION 1] VBS completed, waiting for file operations...
    ping 127.0.0.1 -n 4 >nul
    
    rem --- Delete flag file ---
    pushd "%SHARE%" >nul 2>&1
    if not errorlevel 1 (
        del "%FLAGFILE1%" >nul 2>&1
        popd >nul
    )
    
    echo [%TIME%] [REGION 1] Completed and deleted %FLAGFILE1%
    echo [%DATE% %TIME%] Region 1: Deleted %FLAGFILE1% >> "%LOGFILE%"
    echo.
    echo [%TIME%] Restarting watcher in same window...
    echo [%DATE% %TIME%] Watcher restarted after Region 1 trigger. >> "%LOGFILE%"
    ping 127.0.0.1 -n 2 >nul
    
    rem --- TRUE RESTART: Replace current process ---
    start /b "" "%~f0"
    exit
)

rem --- Process Region 2 if found ---
if "%FOUND2%"=="1" (
    echo.
    echo ############################################
    echo ## REGION 2 TRIGGER DETECTED! ##
    echo ## File: %FLAGFILE2%
    echo ## Action: Calling run_ss2.vbs
    echo ############################################
    echo.
    
    echo [%TIME%] [REGION 2] TRIGGER: %FLAGFILE2%
    echo [%DATE% %TIME%] Region 2: Processing %FLAGFILE2% >> "%LOGFILE%"
    
    rem --- Call VBS from local context ---
    cscript //nologo "%VBS2%"
    
    echo [%TIME%] [REGION 2] VBS completed, waiting for file operations...
    ping 127.0.0.1 -n 4 >nul
    
    rem --- Delete flag file ---
    pushd "%SHARE%" >nul 2>&1
    if not errorlevel 1 (
        del "%FLAGFILE2%" >nul 2>&1
        popd >nul
    )
    
    echo [%TIME%] [REGION 2] Completed and deleted %FLAGFILE2%
    echo [%DATE% %TIME%] Region 2: Deleted %FLAGFILE2% >> "%LOGFILE%"
    echo.
    echo [%TIME%] Restarting watcher in same window...
    echo [%DATE% %TIME%] Watcher restarted after Region 2 trigger. >> "%LOGFILE%"
    ping 127.0.0.1 -n 2 >nul
    
    rem --- TRUE RESTART: Replace current process ---
    start /b "" "%~f0"
    exit
)

ping 127.0.0.1 -n 3 >nul
goto loop