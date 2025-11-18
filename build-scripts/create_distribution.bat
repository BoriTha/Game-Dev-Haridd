@echo off
REM Create distribution packages for Windows

echo ========================================
echo Creating Distribution Package for Windows
echo ========================================

REM Check if dist folder exists
if not exist "dist\DarkSoul_RPG\" (
    echo Error: dist\DarkSoul_RPG not found. Please build the game first.
    pause
    exit /b 1
)

REM Get current date for version (YYYYMMDD format)
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
set VERSION=%mydate%

echo.
echo Version: %VERSION%
echo.

REM Create distributions directory
if not exist "distributions" mkdir distributions

REM Create ZIP archive (requires PowerShell)
echo Creating Windows ZIP archive...
powershell -Command "Compress-Archive -Path 'dist\DarkSoul_RPG\*' -DestinationPath 'distributions\DarkSoul_RPG_v%VERSION%_Windows.zip' -Force"

if errorlevel 1 (
    echo Error: Failed to create ZIP archive
    echo.
    echo Alternative: Manually zip the dist\DarkSoul_RPG folder
    pause
    exit /b 1
)

echo.
echo ========================================
echo Distribution package created!
echo ========================================
echo Location: build-scripts\distributions\
dir distributions\DarkSoul_RPG*.zip
echo.
pause
