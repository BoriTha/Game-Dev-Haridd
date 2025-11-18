#!/bin/bash
# Build macOS application from WSL using Docker
# This script uses a Docker container with macOS build tools to create a macOS .app bundle

echo "========================================"
echo "Building DarkSoul RPG for macOS (from WSL)"
echo "========================================"
echo ""
echo "Note: Building macOS apps from Linux/WSL has limitations."
echo "This script will attempt to use Docker with OSXCross."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo ""
    echo "To build for macOS from WSL, you have two options:"
    echo ""
    echo "Option 1: Install Docker and OSXCross (Advanced)"
    echo "  1. Install Docker Desktop for Windows (with WSL2 backend)"
    echo "  2. Run this script again"
    echo ""
    echo "Option 2: Transfer to a Mac (Recommended)"
    echo "  1. Copy the entire project to a Mac"
    echo "  2. Run: cd build-scripts && ./build_mac.sh"
    echo ""
    echo "Option 3: Create a portable build package"
    echo "  Run: ./prepare_mac_build.sh"
    echo "  This creates a package you can transfer to a Mac for building"
    echo ""
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is installed but not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "Docker detected. Checking for OSXCross image..."
echo ""

# Check if we have an OSXCross image
if ! docker images | grep -q "osxcross"; then
    echo "OSXCross Docker image not found."
    echo ""
    echo "Building macOS apps from Linux requires Apple's SDK and special tools."
    echo "Due to licensing restrictions, we cannot distribute the macOS SDK."
    echo ""
    echo "Recommended approach:"
    echo "  1. Copy project to a Mac"
    echo "  2. Run: cd build-scripts && ./build_mac.sh"
    echo ""
    echo "Alternative: Use prepare_mac_build.sh to create a transfer package"
    exit 1
fi

echo "Building with OSXCross..."
echo ""

# Create output directory
mkdir -p ./dist_mac

# Build using Docker with OSXCross
docker run --rm \
    -v "$(pwd)/../:/project" \
    -w /project/build-scripts \
    osxcross \
    bash -c "
        pip3 install -r ../requirements.txt && \
        pyinstaller --clean --distpath ./dist_mac --workpath ./build_mac DarkSoul_RPG.spec
    "

if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo "Application location: build-scripts/dist_mac/DarkSoul_RPG.app"
echo ""
echo "To transfer to Mac:"
echo "1. Copy the .app bundle to a Mac"
echo "2. Open Terminal and run: xattr -cr DarkSoul_RPG.app"
echo "3. Run the application"
echo ""
