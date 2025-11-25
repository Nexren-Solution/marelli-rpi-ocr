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
    ping 127.0.0.1 -n 4 >nul   :: ~3 sec delay
    exit /b 1
)

copy "%LOCALPATH%" "%NETWORKPATH%" /Y >nul
if errorlevel 1 (
    ping 127.0.0.1 -n 4 >nul   :: ~3 sec delay
    exit /b 1
)

ping 127.0.0.1 -n 2 >nul       :: ~1 sec delay