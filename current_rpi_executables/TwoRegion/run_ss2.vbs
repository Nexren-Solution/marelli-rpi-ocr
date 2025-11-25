' run_ss2.vbs - Launch send_screenshot.bat for Region 2 (hidden)
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c C:\tools\send_screenshot.bat 2", 0, False