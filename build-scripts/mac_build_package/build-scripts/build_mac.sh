#!/bin/bash
# Build script for macOS
# Run this on a Mac to create the macOS application bundle

echo "========================================"
echo "Building DarkSoul RPG for macOS"
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
echo "Building application bundle..."
pyinstaller --clean --distpath ./dist --workpath ./build DarkSoul_RPG.spec

if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo "Application location: build-scripts/dist/DarkSoul_RPG.app"
echo ""
echo "To run the game:"
echo "open build-scripts/dist/DarkSoul_RPG.app"
echo ""
echo "Or drag the app to your Applications folder"
echo ""
