@echo off
chcp 65001 >nul
setlocal
set "VENV=%USERPROFILE%\venvs\metinkap"
if not exist "%VENV%\Scripts\python.exe" (
    echo Run kurulum.bat first.
    pause
    exit /b 1
)

"%VENV%\Scripts\python.exe" "%~dp0tests\calistir.py" %*
set "KOD=%errorlevel%"

rem Cift tiklayarak acildiginda pencere hemen kapanmasin diye bekliyoruz.
rem Argumanla cagrildiysa (ornegin --hizli, ya da bir betikten) beklemiyoruz.
if "%~1"=="" pause
exit /b %KOD%
