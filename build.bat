@echo off
echo ============================================
echo   WageSlave System - build do .exe
echo ============================================
echo.

py --version >nul 2>&1
if errorlevel 1 (
    echo CHYBA: Python nenalezen.
    pause
    exit /b 1
)

echo Instaluji zavislosti...
pip install pyinstaller pillow pystray pywin32 resvg-py

echo.
echo Sestavuji WageSlave.exe...
echo.

pyinstaller wageslave.spec --clean --noconfirm

echo.
if exist "dist\WageSlave.exe" (
    echo ============================================
    echo   HOTOVO: dist\WageSlave.exe
    echo ============================================
) else (
    echo CHYBA: Build selhal.
)

pause
