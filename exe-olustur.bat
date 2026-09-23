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
rem Smart App Control imzasiz her exe'yi engeller — "Run anyway" bile yok.
rem Bu durumda derleme saglam olabilir, sadece bu makinede calistirilamiyor.
rem Ikisini ayirmazsak betik saglam bir derlemeye "shipleme" diyor.
set "SAC="
for /f "tokens=3" %%i in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy" /v VerifiedAndReputablePolicyState 2^>nul ^| find "VerifiedAndReputablePolicyState"') do set "SAC=%%i"
if "%SAC%"=="0x1" goto :sac
echo.
echo [ERROR] The exe was built but --selftest failed. Do not ship it.
if "%~1"=="" pause
exit /b 1

:sac
echo.
echo [BLOCKED] Smart App Control is ON, so Windows refuses to run any unsigned
echo exe on this machine - including this one. The build itself was NOT tested.
echo.
echo   - To use MetinKap here, run it from source: baslat.bat
echo   - To test the exe, use a machine with Smart App Control off
echo.
echo Turning Smart App Control off is one-way: Windows cannot switch it back on
echo without a reinstall. Do not do it just for this.
if "%~1"=="" pause
exit /b 2
