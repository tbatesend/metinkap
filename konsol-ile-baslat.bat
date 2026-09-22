@echo off
chcp 65001 >nul
set "VENV=%USERPROFILE%\venvs\metinkap"
"%VENV%\Scripts\python.exe" "%~dp0metinkap.py"
pause
