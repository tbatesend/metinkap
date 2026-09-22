@echo off
set "VENV=%USERPROFILE%\venvs\metinkap"
if not exist "%VENV%\Scripts\pythonw.exe" (
    echo Run kurulum.bat first.
    pause
    exit /b 1
)
start "" "%VENV%\Scripts\pythonw.exe" "%~dp0metinkap.py"
