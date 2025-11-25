@echo off
if "%~1"=="" exit /b 1
set "REGION=%~1"
if not "%REGION%"=="1" if not "%REGION%"=="2" exit /b 1

set "NIRPATH=C:\tools\nircmd.exe"
set "FILENAME=snap%REGION%_current.png"
set "LOCALPATH=C:\tools\%FILENAME%"
set "NETWORKPATH=\\192.168.1.151\incoming\%FILENAME%"

"%NIRPATH%" savescreenshot "%LOCALPATH%"
if not exist "%LOCALPATH%" (
    timeout /t 3 >nul
    exit /b 1
)

copy "%LOCALPATH%" "%NETWORKPATH%" /Y >nul
if errorlevel 1 (
    timeout /t 3 >nul
    exit /b 1
)

timeout /t 1 >nul