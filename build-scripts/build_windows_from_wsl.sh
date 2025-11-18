#!/bin/bash
# Build Windows executable from WSL/Linux
# This creates a Windows .exe that can run on Windows

echo "========================================"
echo "Building DarkSoul RPG for Windows (from WSL)"
echo "========================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r ../requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

echo ""
echo "Building Windows executable..."
pyinstaller --clean --onedir \
    --distpath ./dist \
    --workpath ./build \
    --name DarkSoul_RPG \
    --add-data "../assets:assets" \
    --add-data "../config:config" \
    --add-data "../src:src" \
    --add-data "../config.py:." \
    --noconsole \
    ../main.py

if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo "Executable location: build-scripts/dist/DarkSoul_RPG/"
echo ""
echo "To access from Windows Explorer:"
echo "\\\\wsl.localhost\\kali-linux\\home\\jay\\Game-Dev\\last-ver\\DarkSoul_RPG\\build-scripts\\dist\\DarkSoul_RPG"
echo ""
echo "Or copy to Windows:"
echo "cp -r dist/DarkSoul_RPG /mnt/c/Users/\$USER/Desktop/"
echo ""
