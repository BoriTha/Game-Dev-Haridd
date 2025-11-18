#!/bin/bash
# Create Windows ZIP distribution package from WSL/Linux

echo "========================================"
echo "Creating Windows Distribution Package"
echo "========================================"

# Check if dist folder exists
if [ ! -d "dist/DarkSoul_RPG" ]; then
    echo "Error: dist/DarkSoul_RPG not found. Please build the game first."
    exit 1
fi

# Get current date for version
VERSION=$(date +%Y%m%d)

echo ""
echo "Version: $VERSION"
echo ""

# Create distributions directory
mkdir -p distributions

# Create ZIP for Windows
echo "Creating Windows ZIP archive..."
cd dist
zip -r "../distributions/DarkSoul_RPG_v${VERSION}_Windows.zip" DarkSoul_RPG/
cd ..

echo ""
echo "========================================"
echo "Windows distribution package created!"
echo "========================================"
echo "Location: build-scripts/distributions/DarkSoul_RPG_v${VERSION}_Windows.zip"
ls -lh distributions/DarkSoul_RPG_v${VERSION}_Windows.zip
echo ""
echo "This ZIP file can be:"
echo "  - Shared with Windows users"
echo "  - Accessed from Windows at:"
echo "    \\\\wsl.localhost\\kali-linux\\home\\jay\\Game-Dev\\last-ver\\DarkSoul_RPG\\build-scripts\\distributions\\"
echo ""
