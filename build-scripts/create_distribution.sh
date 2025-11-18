#!/bin/bash
# Create distribution packages after building

echo "========================================"
echo "Creating Distribution Packages"
echo "========================================"

# Check if dist folder exists
if [ ! -d "dist/DarkSoul_RPG" ]; then
    echo "Error: dist/DarkSoul_RPG not found. Please build the game first."
    exit 1
fi

# Get current date for version
VERSION=$(date +%Y%m%d)
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')

echo ""
echo "Platform detected: $PLATFORM"
echo "Version: $VERSION"
echo ""

# Create distributions directory
mkdir -p distributions

if [ "$PLATFORM" == "darwin" ]; then
    # macOS - create DMG
    echo "Creating macOS DMG..."
    if [ -d "dist/DarkSoul_RPG.app" ]; then
        hdiutil create -volname "DarkSoul RPG" \
            -srcfolder dist/DarkSoul_RPG.app \
            -ov -format UDZO \
            "distributions/DarkSoul_RPG_v${VERSION}_macOS.dmg"
        echo "Created: distributions/DarkSoul_RPG_v${VERSION}_macOS.dmg"
    else
        echo "Warning: DarkSoul_RPG.app not found. Creating tar.gz instead..."
        cd dist
        tar -czf "../distributions/DarkSoul_RPG_v${VERSION}_macOS.tar.gz" DarkSoul_RPG/
        cd ..
        echo "Created: distributions/DarkSoul_RPG_v${VERSION}_macOS.tar.gz"
    fi
    
elif [ "$PLATFORM" == "linux" ]; then
    # Linux - create tar.gz
    echo "Creating Linux tar.gz..."
    cd dist
    tar -czf "../distributions/DarkSoul_RPG_v${VERSION}_Linux.tar.gz" DarkSoul_RPG/
    cd ..
    echo "Created: distributions/DarkSoul_RPG_v${VERSION}_Linux.tar.gz"
    
else
    # Generic Unix - create tar.gz
    echo "Creating tar.gz..."
    cd dist
    tar -czf "../distributions/DarkSoul_RPG_v${VERSION}_${PLATFORM}.tar.gz" DarkSoul_RPG/
    cd ..
    echo "Created: distributions/DarkSoul_RPG_v${VERSION}_${PLATFORM}.tar.gz"
fi

echo ""
echo "========================================"
echo "Distribution package created!"
echo "========================================"
echo "Location: build-scripts/distributions/"
ls -lh distributions/
echo ""
