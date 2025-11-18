#!/bin/bash
# Prepare a build package for macOS that can be transferred to a Mac
# This creates a clean package with build scripts and instructions

echo "========================================"
echo "Preparing macOS Build Package"
echo "========================================"
echo ""

# Create package directory
PACKAGE_DIR="./mac_build_package"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

echo "Copying project files..."

# Copy all necessary files to package directory
cp -r ../assets "$PACKAGE_DIR/"
cp -r ../config "$PACKAGE_DIR/"
cp -r ../src "$PACKAGE_DIR/"
cp ../config.py "$PACKAGE_DIR/"
cp ../main.py "$PACKAGE_DIR/"
cp ../requirements.txt "$PACKAGE_DIR/"
cp ../README.md "$PACKAGE_DIR/" 2>/dev/null || true

# Copy build scripts
mkdir -p "$PACKAGE_DIR/build-scripts"
cp DarkSoul_RPG.spec "$PACKAGE_DIR/build-scripts/"
cp build_mac.sh "$PACKAGE_DIR/build-scripts/"

# Create a setup script for Mac
cat > "$PACKAGE_DIR/build-scripts/BUILD_ON_MAC.sh" << 'EOF'
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
EOF

chmod +x "$PACKAGE_DIR/build-scripts/BUILD_ON_MAC.sh"
chmod +x "$PACKAGE_DIR/build-scripts/build_mac.sh"

# Create README for Mac users
cat > "$PACKAGE_DIR/BUILD_README.txt" << 'EOF'
DarkSoul RPG - macOS Build Instructions
========================================

This package contains everything needed to build DarkSoul RPG on macOS.

REQUIREMENTS:
-------------
- macOS 10.13 or later
- Python 3.7 or higher
- pip (Python package installer)

QUICK START:
------------
1. Open Terminal
2. Navigate to this folder:
   cd /path/to/mac_build_package

3. Run the build script:
   cd build-scripts
   ./BUILD_ON_MAC.sh

4. The app will be created in: build-scripts/dist/DarkSoul_RPG.app

INSTALLATION:
-------------
After building, you can:
- Double-click DarkSoul_RPG.app to run
- Copy it to /Applications
- Create a DMG for distribution

TROUBLESHOOTING:
----------------
If you get "Permission denied":
  chmod +x build-scripts/BUILD_ON_MAC.sh

If you get "Python not found":
  Install Python from https://www.python.org/downloads/
  Or use Homebrew: brew install python3

If you get "pip not found":
  python3 -m ensurepip --upgrade

If build fails with dependencies:
  pip3 install --user -r requirements.txt

CREATING A DMG:
---------------
To create a distributable DMG file:
  cd build-scripts/dist
  hdiutil create -volname "DarkSoul RPG" \
    -srcfolder DarkSoul_RPG.app \
    -ov -format UDZO \
    DarkSoul_RPG.dmg

SUPPORT:
--------
For issues, check the main README.md file or build logs.
EOF

# Create archive
echo ""
echo "Creating archive..."
cd ..
ARCHIVE_NAME="DarkSoul_RPG_MacBuild_$(date +%Y%m%d).tar.gz"
tar -czf "$ARCHIVE_NAME" -C build-scripts mac_build_package

if [ $? -ne 0 ]; then
    echo "Warning: Failed to create archive, but package folder is ready"
else
    echo "Archive created: $ARCHIVE_NAME"
fi

echo ""
echo "========================================"
echo "Package preparation complete!"
echo "========================================"
echo ""
echo "Package location: build-scripts/mac_build_package/"
echo "Archive: $ARCHIVE_NAME"
echo ""
echo "To transfer to Mac:"
echo "  1. Copy the entire 'mac_build_package' folder to a Mac"
echo "     OR copy the archive: $ARCHIVE_NAME"
echo ""
echo "  2. On the Mac, open Terminal and run:"
echo "     cd /path/to/mac_build_package/build-scripts"
echo "     ./BUILD_ON_MAC.sh"
echo ""
echo "To access from Windows Explorer:"
echo "  \\\\wsl.localhost\\$(grep '^ID=' /etc/os-release | cut -d= -f2)\\$HOME/Game-Dev/last-ver/DarkSoul_RPG/build-scripts/"
echo ""
echo "Or copy to Windows Desktop:"
echo "  cp $ARCHIVE_NAME /mnt/c/Users/\$USER/Desktop/"
echo ""
