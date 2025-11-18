@echo off
REM Build script for Windows
REM Run this on a Windows machine to create the Windows executable

echo ========================================
echo Building DarkSoul RPG for Windows
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r ..\requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Building executable...
pyinstaller --clean --distpath .\dist --workpath .\build DarkSoul_RPG.spec

if errorlevel 1 (
    echo Error: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo Executable location: build-scripts\dist\DarkSoul_RPG\
echo.
pause
