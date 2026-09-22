@echo off
chcp 65001 >nul
setlocal
title MetinKap setup

set "VENV=%USERPROFILE%\venvs\metinkap"

echo.
echo  MetinKap setup
echo  --------------
echo  Virtualenv: %VENV%
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install it from python.org/downloads and retry.
    pause
    exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
    echo  Creating the virtualenv...
    py -3 -m venv "%VENV%" || (echo  [ERROR] Could not create the virtualenv. & pause & exit /b 1)
)

echo  Installing packages...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%VENV%\Scripts\python.exe" -m pip install --quiet ^
    pillow pystray ^
    winrt-Windows.Media.Ocr ^
    winrt-Windows.Graphics.Imaging ^
    winrt-Windows.Storage ^
    winrt-Windows.Storage.Streams ^
    winrt-Windows.Globalization ^
    winrt-Windows.Foundation ^
    winrt-Windows.Foundation.Collections
if errorlevel 1 (
    echo  [ERROR] Package installation failed.
    pause
    exit /b 1
)

echo.
echo  Checking the OCR engine...
"%VENV%\Scripts\python.exe" -c "from winrt.windows.media.ocr import OcrEngine; ls=[l.language_tag for l in OcrEngine.available_recognizer_languages]; print('   installed OCR languages: ' + (', '.join(ls) if ls else 'NONE - add one from the Languages tab'))"
if errorlevel 1 (
    echo  [ERROR] The Windows OCR engine could not be reached.
    pause
    exit /b 1
)

echo.
echo  Setup complete. Starting MetinKap...
echo  Shortcut: Ctrl+Shift+Space   ·   Settings: double-click the tray icon
start "" "%VENV%\Scripts\pythonw.exe" "%~dp0metinkap.py"
echo.
pause
