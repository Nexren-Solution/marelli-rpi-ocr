@echo off
REM ===============================================
REM  Capture and Send Screenshot to Raspberry Pi (Locale-safe)
REM  Usage: send_screenshot.bat 1   OR   send_screenshot.bat 2
REM ===============================================

if "%~1"=="" (
    echo ERROR: Missing region argument (1 or 2).
    exit /b 1
)
set "REGION=%~1"

if not "%REGION%"=="1" if not "%REGION%"=="2" (
    echo ERROR: Region must be 1 or 2.
    exit /b 1
)

:: Path to NirCmd executable
set "NIRPATH=C:\tools\nircmd.exe"

:: --- Get timestamp in a locale-independent format ---
for /f %%a in ('wmic os get localdatetime ^| find "."') do set datetime=%%a
set "yyyy=%datetime:~0,4%"
set "mm=%datetime:~4,2%"
set "dd=%datetime:~6,2%"
set "hh=%datetime:~8,2%"
set "nn=%datetime:~10,2%"
set "ss=%datetime:~12,2%"

:: Safe formatted filename
set "FILENAME=snap%REGION%_%yyyy%-%mm%-%dd%_%hh%-%nn%-%ss%.png"

:: Local file path
set "LOCALPATH=C:\tools\%FILENAME%"

:: Network destination (Raspberry Pi share)
set "NETWORKPATH=\\192.168.1.151\incoming\%FILENAME%"

echo ===============================================
echo [INFO] Capturing screenshot for Region %REGION%...
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
