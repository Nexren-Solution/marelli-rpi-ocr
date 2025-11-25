' run_ss1.vbs - Launch send_screenshot.bat for Region 1 (hidden)
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c C:\tools\send_screenshot.bat 1", 0, False