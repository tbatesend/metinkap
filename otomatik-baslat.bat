@echo off
chcp 65001 >nul
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK=%STARTUP%\MetinKap.lnk"

if exist "%LNK%" (
    del "%LNK%"
    echo  Autostart DISABLED.
    pause
    exit /b 0
)

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%');" ^
  "$s.TargetPath='%USERPROFILE%\venvs\metinkap\Scripts\pythonw.exe';" ^
  "$s.Arguments='\"%~dp0metinkap.py\"';" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "$s.Description='MetinKap - grab text from screen';" ^
  "$s.Save()"

echo  Autostart ENABLED. MetinKap will start with Windows.
echo  Run this file again to turn it off. Settings does the same thing.
pause
