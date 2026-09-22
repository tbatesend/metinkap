@echo off
chcp 65001 >nul
setlocal
set "VENV=%USERPROFILE%\venvs\metinkap"
if not exist "%VENV%\Scripts\python.exe" (
    echo Run kurulum.bat first.
    goto :son
)
"%VENV%\Scripts\python.exe" "%~dp0tests\calistir.py" %*

:son
rem Cift tiklayarak acildiysa pencere hemen kapanmasin; komut satirindan
rem cagrildiysa bekletme (otomasyonu kilitler).
echo %cmdcmdline% | "%SystemRoot%\System32ind.exe" /i "%~nx0" >nul && pause
exit /b %errorlevel%
