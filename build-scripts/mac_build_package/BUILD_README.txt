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
