@echo off
REM ===============================================
REM  Capture and Send Screenshot to Raspberry Pi
REM  Author: Uday Gupta
REM ===============================================

:: Path to NirCmd executable
set "NIRPATH=C:\tools\nircmd.exe"

:: Get safe date/time parts (replace : and spaces)
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do (
    set yyyy=%%d
    set mm=%%b
    set dd=%%c
)
for /f "tokens=1-3 delims=:." %%a in ("%time%") do (
    set hh=%%a
    set nn=%%b
    set ss=%%c
)
:: Remove leading spaces and pad hour with zero if needed
if "%hh:~0,1%"==" " set hh=0%hh:~1,1%

:: Combine into safe filename
set "FILENAME=snap_%yyyy%-%mm%-%dd%_%hh%-%nn%-%ss%.png"

:: Local file path (save screenshot here)
set "LOCALPATH=C:\tools\%FILENAME%"

:: Network destination (Raspberry Pi share)
set "NETWORKPATH=\\192.168.1.151\incoming\%FILENAME%"

echo ===============================================
echo [INFO] Capturing screenshot...
"%NIRPATH%" savescreenshot "%LOCALPATH%"

if exist "%LOCALPATH%" (
    echo [INFO] Screenshot saved at: %LOCALPATH%
) else (
    echo [ERROR] Failed to capture screenshot. Exiting...
    pause
    exit /b
)

echo [INFO] Transferring file to Raspberry Pi...
copy "%LOCALPATH%" "%NETWORKPATH%" /Y >nul

if %ERRORLEVEL%==0 (
    echo [SUCCESS] Screenshot copied successfully to Raspberry Pi.
) else (
    echo [ERROR] File copy failed. Check network access or permissions.
)

echo [DONE] Operation complete.
echo ===============================================
pause
