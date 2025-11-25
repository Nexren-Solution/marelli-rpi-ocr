@echo off
REM ===============================================
REM  Capture and Send Screenshot to Raspberry Pi (Region-aware)
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

:: --- Generate safe timestamp (YYYY-MM-DD_HH-MM-SS) ---
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
:: Fix space-padding in hour
if "%hh:~0,1%"==" " set "hh=0%hh:~1,1%"

:: Combine all parts
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
