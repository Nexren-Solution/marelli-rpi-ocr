@echo off
setlocal

set SHARE=\\192.168.1.151\incoming
set VBSPATH=C:\tools\run_ss_hidden_v1.vbs
set LOGFILE=C:\tools\flag_watcher.log

echo [%DATE% %TIME%] Watcher started. >> "%LOGFILE%"

:loop
rem --- Map network path using pushd ---
pushd "%SHARE%" >nul 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] Share not reachable. >> "%LOGFILE%"
    call :sleep 5
    goto loop
)

rem --- Process any flag files ---
for %%F in (capture_*.flag) do (
    echo [%DATE% %TIME%] Found %%F >> "%LOGFILE%"
    cscript //nologo "%VBSPATH%"
    call :sleep 3
    del "%%F" >nul 2>&1
    echo [%DATE% %TIME%] Deleted %%F >> "%LOGFILE%"
)

popd >nul
call :sleep 2
goto loop

:: -------------------------------
:: Sleep subroutine using ping
:: -------------------------------
:sleep
set /a n=%1+1
ping -n %n% 127.0.0.1 >nul
goto :eof
