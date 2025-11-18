#!/bin/bash
# Build script for Linux
# Run this on a Linux machine to create the Linux executable

echo "========================================"
echo "Building DarkSoul RPG for Linux"
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
echo "Building executable..."
pyinstaller --clean --distpath ./dist --workpath ./build DarkSoul_RPG.spec

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
echo "To run the game:"
echo "cd build-scripts/dist/DarkSoul_RPG/"
echo "./DarkSoul_RPG"
echo ""
