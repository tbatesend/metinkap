@echo off
chcp 65001 >nul
setlocal
set "VENV=%USERPROFILE%\venvs\metinkap"
if not exist "%VENV%\Scripts\python.exe" (
    echo Run kurulum.bat first.
    pause
    exit /b 1
)

echo Installing PyInstaller if missing...
"%VENV%\Scripts\python.exe" -m pip install --quiet pyinstaller || goto :hata

echo Building MetinKap.exe...
rem --collect-submodules/--collect-binaries winrt sart: winrt paketleri
rem derlenmis uzantilar ve dinamik import kullaniyor, PyInstaller kendiliginden
rem bulamiyor. foundation.collections de ayrica belirtilmeli.
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --clean ^
    --name MetinKap --onefile --windowed ^
    --icon "%~dp0docs\metinkap.ico" ^
    --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" ^
    --collect-submodules winrt --collect-binaries winrt ^
    --hidden-import winrt.windows.foundation.collections ^
    "%~dp0metinkap.py" || goto :hata

echo.
echo Verifying the build...
"%~dp0dist\MetinKap.exe" --selftest || goto :dogrulama

echo.
echo Done: %~dp0dist\MetinKap.exe
if "%~1"=="" pause
exit /b 0

:hata
echo.
echo [ERROR] Build failed.
if "%~1"=="" pause
exit /b 1

:dogrulama
echo.
echo [ERROR] The exe was built but --selftest failed. Do not ship it.
if "%~1"=="" pause
exit /b 1
