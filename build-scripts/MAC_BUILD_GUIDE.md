# Building DarkSoul RPG for macOS from WSL

This guide explains how to create macOS builds when working in WSL (Windows Subsystem for Linux).

## The Challenge

PyInstaller cannot directly cross-compile from Linux/WSL to macOS. You need to build macOS applications on an actual Mac.

## Solution: Transfer Package Method

We've created a helper script that prepares everything you need, so you can easily build on a Mac.

## Step-by-Step Instructions

### 1. Prepare the Build Package in WSL

```bash
cd build-scripts
./prepare_mac_build.sh
```

This creates:
- A `mac_build_package` folder with all necessary files
- A compressed archive: `DarkSoul_RPG_MacBuild_YYYYMMDD.tar.gz`

### 2. Transfer to Mac

Choose one of these methods:

#### Method A: Direct File Transfer
Copy the archive to Mac using:
- USB drive
- Network share
- Cloud storage (Google Drive, Dropbox, etc.)
- Email (if small enough)
- AirDrop (if on the same network)

#### Method B: From Windows Explorer
1. Open Windows Explorer
2. Navigate to: `\\wsl.localhost\<distro-name>\home\jay\Game-Dev\last-ver\DarkSoul_RPG\build-scripts\`
3. Copy `DarkSoul_RPG_MacBuild_YYYYMMDD.tar.gz` to your Desktop or USB drive
4. Transfer to Mac

#### Method C: Copy to Windows First
```bash
# Copy to Windows Desktop
cp DarkSoul_RPG_MacBuild_*.tar.gz /mnt/c/Users/$USER/Desktop/
```
Then transfer to Mac from Windows.

### 3. Build on Mac

On your Mac:

```bash
# Extract the archive (if using compressed version)
tar -xzf DarkSoul_RPG_MacBuild_YYYYMMDD.tar.gz

# Navigate to build scripts
cd mac_build_package/build-scripts

# Run the build
./BUILD_ON_MAC.sh
```

The script will:
1. Check for Python 3
2. Install dependencies
3. Build the .app bundle
4. Create `dist/DarkSoul_RPG.app`

### 4. Test and Distribute

After building:

```bash
# Test the app
open dist/DarkSoul_RPG.app

# Optional: Create a DMG for distribution
cd dist
hdiutil create -volname "DarkSoul RPG" \
  -srcfolder DarkSoul_RPG.app \
  -ov -format UDZO \
  DarkSoul_RPG.dmg
```

## Troubleshooting

### "Permission denied" when running script
```bash
chmod +x BUILD_ON_MAC.sh
```

### "Python not found"
Install Python 3:
- From [python.org](https://www.python.org/downloads/)
- Or with Homebrew: `brew install python3`

### Dependencies fail to install
Try installing as user:
```bash
pip3 install --user -r requirements.txt
```

### Need to rebuild
```bash
cd build-scripts
rm -rf build dist
./BUILD_ON_MAC.sh
```

## What Gets Packaged

The preparation script includes:
- All game assets (sprites, sounds, etc.)
- All source code
- Configuration files
- Build scripts optimized for Mac
- Requirements file
- Complete build instructions

## Alternative: Build on Mac Directly

If you have access to a Mac regularly, you can:

1. Clone the repository on the Mac
2. Run the native build script:
   ```bash
   cd build-scripts
   ./build_mac.sh
   ```

## Files Created

After running `prepare_mac_build.sh`:

```
build-scripts/
├── mac_build_package/          # Complete project package
│   ├── assets/                 # Game assets
│   ├── src/                    # Source code
│   ├── config/                 # Configuration
│   ├── build-scripts/          # Build scripts
│   │   ├── BUILD_ON_MAC.sh    # Main build script
│   │   ├── build_mac.sh       # Alternative script
│   │   └── DarkSoul_RPG.spec  # PyInstaller spec
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   └── BUILD_README.txt       # Instructions
└── DarkSoul_RPG_MacBuild_YYYYMMDD.tar.gz  # Compressed archive
```

## Tips

- **Keep it updated**: Run `prepare_mac_build.sh` again whenever you make changes
- **Test early**: If possible, test on Mac early in development to catch platform-specific issues
- **Automate**: Consider setting up CI/CD with GitHub Actions for automatic Mac builds
- **Documentation**: The BUILD_README.txt in the package has condensed instructions for Mac users

## CI/CD Alternative (Advanced)

For automatic builds without a Mac:
1. Use GitHub Actions with `macos-latest` runner
2. Configure workflow to build on every release
3. Artifacts will be automatically available

Example `.github/workflows/build-mac.yml`:
```yaml
name: Build macOS
on: [push, release]
jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Build
        run: |
          cd build-scripts
          ./build_mac.sh
      - name: Upload artifact
        uses: actions/upload-artifact@v2
        with:
          name: DarkSoul_RPG-macOS
          path: build-scripts/dist/DarkSoul_RPG.app
```

## Summary

The `prepare_mac_build.sh` script makes it easy to create macOS builds from WSL by:
1. Packaging everything needed
2. Creating clear build instructions
3. Preparing scripts that work on Mac
4. Generating an easy-to-transfer archive

This workflow allows you to develop on Windows/WSL while still supporting macOS users!
