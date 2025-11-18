#!/bin/bash
# Build DarkSoul RPG on macOS
# Run this script on a Mac to create the .app bundle

echo "========================================"
echo "Building DarkSoul RPG for macOS"
echo "========================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo ""
    echo "Please install Python 3:"
    echo "  brew install python3"
    echo ""
    echo "Or download from: https://www.python.org/downloads/"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    exit 1
fi

echo "Python version: $(python3 --version)"
echo ""

# Install dependencies
echo "Installing dependencies..."
cd ..
pip3 install --upgrade pip
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Failed to install dependencies"
    echo "Try: pip3 install --user -r requirements.txt"
    exit 1
fi

# Install PyInstaller if not installed
if ! pip3 show pyinstaller &> /dev/null; then
    echo ""
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

echo ""
echo "Building application..."
cd build-scripts

# Clean previous builds
rm -rf build dist

# Build the application
pyinstaller --clean \
    --distpath ./dist \
    --workpath ./build \
    DarkSoul_RPG.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo ""
echo "Application location: build-scripts/dist/DarkSoul_RPG.app"
echo ""
echo "To test the game:"
echo "  open dist/DarkSoul_RPG.app"
echo ""
echo "To install:"
echo "  1. Copy dist/DarkSoul_RPG.app to /Applications"
echo "  2. Or drag it to your Applications folder"
echo ""
echo "To create a DMG (optional):"
echo "  cd dist"
echo '  hdiutil create -volname "DarkSoul RPG" -srcfolder DarkSoul_RPG.app -ov -format UDZO DarkSoul_RPG.dmg'
echo ""
