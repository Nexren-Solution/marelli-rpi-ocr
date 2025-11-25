@echo off
REM ===============================================
REM  Capture and Send Screenshot to Raspberry Pi
REM  Author: Uday Gupta
REM ===============================================

:: Path to NirCmd executable
set NIRPATH=C:\tools\nircmd.exe

:: Generate timestamped filename (YYYY-MM-DD_HH-MM-SS)
set FILENAME=snap_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%-%TIME:~6,2%.png
set FILENAME=%FILENAME: =0%

:: Local temp file path
set LOCALPATH=%TEMP%\%FILENAME%

:: Network destination (Raspberry Pi share)
set NETWORKPATH=\\192.168.1.151\incoming\%FILENAME%

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
