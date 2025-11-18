#!/bin/bash
# Verify that all assets are included in the build

echo "========================================="
echo "  DarkSoul RPG - Build Verification"
echo "========================================="
echo ""

# Check if dist folder exists
if [ ! -d "dist/DarkSoul_RPG" ]; then
    echo "❌ ERROR: dist/DarkSoul_RPG not found!"
    echo "   Please build the game first with ./build_linux.sh"
    exit 1
fi

echo "✅ Build folder exists: dist/DarkSoul_RPG"
echo ""

# Check executable
if [ -f "dist/DarkSoul_RPG/DarkSoul_RPG" ]; then
    echo "✅ Executable found: DarkSoul_RPG"
    ls -lh dist/DarkSoul_RPG/DarkSoul_RPG
else
    echo "❌ ERROR: Executable not found!"
    exit 1
fi
echo ""

# Check _internal folder
if [ -d "dist/DarkSoul_RPG/_internal" ]; then
    echo "✅ Internal folder exists: _internal"
else
    echo "❌ ERROR: _internal folder not found!"
    exit 1
fi
echo ""

# Check assets
echo "Checking ASSETS folder..."
if [ -d "dist/DarkSoul_RPG/_internal/assets" ]; then
    ASSET_SIZE=$(du -sh dist/DarkSoul_RPG/_internal/assets | cut -f1)
    ASSET_COUNT=$(find dist/DarkSoul_RPG/_internal/assets -type f | wc -l)
    echo "✅ Assets folder found!"
    echo "   Size: $ASSET_SIZE"
    echo "   Files: $ASSET_COUNT"
    
    # Check major asset folders
    echo ""
    echo "   Asset subfolders:"
    for folder in Player enemy consumable tiles monster background armament; do
        if [ -d "dist/DarkSoul_RPG/_internal/assets/$folder" ]; then
            count=$(find "dist/DarkSoul_RPG/_internal/assets/$folder" -type f 2>/dev/null | wc -l)
            echo "   ✅ $folder ($count files)"
        else
            echo "   ⚠️  $folder (not found)"
        fi
    done
else
    echo "❌ ERROR: Assets folder not found!"
    exit 1
fi
echo ""

# Check config
echo "Checking CONFIG files..."
if [ -d "dist/DarkSoul_RPG/_internal/config" ]; then
    CONFIG_SIZE=$(du -sh dist/DarkSoul_RPG/_internal/config | cut -f1)
    CONFIG_COUNT=$(find dist/DarkSoul_RPG/_internal/config -type f | wc -l)
    echo "✅ Config folder found!"
    echo "   Size: $CONFIG_SIZE"
    echo "   Files: $CONFIG_COUNT"
else
    echo "❌ ERROR: Config folder not found!"
    exit 1
fi

if [ -f "dist/DarkSoul_RPG/_internal/config.py" ]; then
    echo "✅ config.py found!"
else
    echo "❌ ERROR: config.py not found!"
    exit 1
fi
echo ""

# Check src
echo "Checking SOURCE code..."
if [ -d "dist/DarkSoul_RPG/_internal/src" ]; then
    SRC_SIZE=$(du -sh dist/DarkSoul_RPG/_internal/src | cut -f1)
    SRC_COUNT=$(find dist/DarkSoul_RPG/_internal/src -type f -name "*.pyc" | wc -l)
    echo "✅ Source folder found!"
    echo "   Size: $SRC_SIZE"
    echo "   Compiled files: $SRC_COUNT"
else
    echo "❌ ERROR: Source folder not found!"
    exit 1
fi
echo ""

# Check total size
echo "Build Statistics:"
TOTAL_SIZE=$(du -sh dist/DarkSoul_RPG | cut -f1)
TOTAL_FILES=$(find dist/DarkSoul_RPG -type f | wc -l)
echo "   Total size: $TOTAL_SIZE"
echo "   Total files: $TOTAL_FILES"
echo ""

# Check distribution packages if they exist
echo "========================================="
echo "  Checking Distribution Packages"
echo "========================================="
echo ""

if [ -d "distributions" ]; then
    echo "Distribution folder exists!"
    echo ""
    
    # Check Linux package
    if [ -f "distributions/DarkSoul_RPG_v"*"_Linux.tar.gz" ]; then
        LINUX_PKG=$(ls distributions/DarkSoul_RPG_v*_Linux.tar.gz 2>/dev/null | head -1)
        LINUX_SIZE=$(du -sh "$LINUX_PKG" | cut -f1)
        echo "✅ Linux package found!"
        echo "   File: $(basename "$LINUX_PKG")"
        echo "   Size: $LINUX_SIZE"
        
        # Verify assets in Linux package
        echo "   Verifying assets in package..."
        ASSET_FILES=$(tar -tzf "$LINUX_PKG" | grep "assets/" | wc -l)
        if [ "$ASSET_FILES" -gt 100 ]; then
            echo "   ✅ Assets included: $ASSET_FILES files"
        else
            echo "   ⚠️  Warning: Only $ASSET_FILES asset files found"
        fi
    else
        echo "⚠️  Linux package not found"
        echo "   Run: ./create_distribution.sh"
    fi
    echo ""
    
    # Check Windows package
    if [ -f "distributions/DarkSoul_RPG_v"*"_Windows.zip" ]; then
        WIN_PKG=$(ls distributions/DarkSoul_RPG_v*_Windows.zip 2>/dev/null | head -1)
        WIN_SIZE=$(du -sh "$WIN_PKG" | cut -f1)
        echo "✅ Windows package found!"
        echo "   File: $(basename "$WIN_PKG")"
        echo "   Size: $WIN_SIZE"
        
        # Verify assets in Windows package
        echo "   Verifying assets in package..."
        ASSET_FILES=$(unzip -l "$WIN_PKG" | grep "assets/" | wc -l)
        if [ "$ASSET_FILES" -gt 100 ]; then
            echo "   ✅ Assets included: $ASSET_FILES files"
        else
            echo "   ⚠️  Warning: Only $ASSET_FILES asset files found"
        fi
    else
        echo "⚠️  Windows package not found"
        echo "   Run: ./create_windows_distribution.sh"
    fi
else
    echo "⚠️  Distribution folder not found"
    echo "   Run: ./create_distribution.sh"
fi

echo ""
echo "========================================="
echo "  Verification Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "✅ Executable: Ready"
echo "✅ Assets: $ASSET_SIZE ($ASSET_COUNT files)"
echo "✅ Config: Included"
echo "✅ Source: Included"
echo "✅ Total: $TOTAL_SIZE"
echo ""
echo "🎮 Your game is ready to run!"
echo ""
echo "To test on Linux:"
echo "   cd dist/DarkSoul_RPG"
echo "   ./DarkSoul_RPG"
echo ""
