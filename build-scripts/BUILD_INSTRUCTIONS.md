# DarkSoul RPG - Build Instructions

This guide explains how to build executable files for DarkSoul RPG on Windows, Linux, and macOS.

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Quick Start

### Windows

1. Open Command Prompt in the project directory
2. Run the build script:
   ```cmd
   build_windows.bat
   ```
3. The executable will be in `dist/DarkSoul_RPG/`
4. To run the game, double-click `DarkSoul_RPG.exe`

### Linux

1. Open a terminal in the project directory
2. Run the build script:
   ```bash
   ./build_linux.sh
   ```
3. The executable will be in `dist/DarkSoul_RPG/`
4. To run the game:
   ```bash
   cd dist/DarkSoul_RPG/
   ./DarkSoul_RPG
   ```

### macOS

#### Building on macOS:
1. Open Terminal in the project directory
2. Run the build script:
   ```bash
   cd build-scripts
   ./build_mac.sh
   ```
3. The application bundle will be at `dist/DarkSoul_RPG.app`
4. To run the game:
   ```bash
   open dist/DarkSoul_RPG.app
   ```
   Or drag the .app to your Applications folder

#### Building from WSL/Linux for macOS:
Since PyInstaller cannot cross-compile to macOS, use this helper script:
1. In WSL, navigate to build-scripts:
   ```bash
   cd build-scripts
   ./prepare_mac_build.sh
   ```
2. This creates a `mac_build_package` folder and archive
3. Transfer the package to a Mac (via USB, network, cloud, etc.)
4. On the Mac, open Terminal and run:
   ```bash
   cd /path/to/mac_build_package/build-scripts
   ./BUILD_ON_MAC.sh
   ```

## Manual Build (All Platforms)

If you prefer to build manually or customize the build:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build the executable:
   ```bash
   pyinstaller --clean DarkSoul_RPG.spec
   ```

3. The output will be in the `dist/` folder

## Distribution

### Windows
- Compress the `dist/DarkSoul_RPG/` folder into a ZIP file
- Users can extract and run `DarkSoul_RPG.exe`

### Linux
- Create a tar.gz archive:
  ```bash
  cd dist
  tar -czf DarkSoul_RPG_linux.tar.gz DarkSoul_RPG/
  ```
- Users can extract and run the executable

### macOS
- The `DarkSoul_RPG.app` can be distributed as-is
- Consider creating a DMG file for easier distribution:
  ```bash
  hdiutil create -volname "DarkSoul RPG" -srcfolder dist/DarkSoul_RPG.app -ov -format UDZO DarkSoul_RPG.dmg
  ```

## Customization

### Adding an Icon

1. Create or obtain icon files:
   - Windows: `.ico` file
   - macOS: `.icns` file
   - Linux: `.png` file (recommended 256x256 or higher)

2. Edit `DarkSoul_RPG.spec` and update the `icon` parameter in both the `EXE` and `BUNDLE` sections:
   ```python
   icon='path/to/your/icon.ico'  # or .icns for macOS
   ```

### Console Window

By default, the console window is hidden. To show it (useful for debugging):

Edit `DarkSoul_RPG.spec` and change:
```python
console=False,
```
to:
```python
console=True,
```

## Troubleshooting

### "Module not found" errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that all source files are in the correct locations

### Missing assets in executable
- Verify that the `assets/`, `config/`, and `src/` folders are in the project root
- Check the `datas` section in `DarkSoul_RPG.spec` to ensure all necessary files are included

### Executable is too large
- Consider using UPX compression (enabled by default)
- Remove unused dependencies from the build

### Game won't start
- Try running the build script with `console=True` to see error messages
- Verify that all required files are in the `dist/` folder
- Check that Python version matches (build on the same Python version users will have)

## Build Sizes (Approximate)

- Windows: ~50-100 MB
- Linux: ~50-100 MB  
- macOS: ~50-100 MB

Actual sizes may vary depending on included assets and dependencies.

## Cross-Platform Building

**Important:** You must build on each target platform:
- Build Windows executables on Windows (or from WSL using `build_windows_from_wsl.sh`)
- Build Linux executables on Linux
- Build macOS applications on macOS (or prepare a package from WSL using `prepare_mac_build.sh`)

PyInstaller does not support true cross-platform building. However, we provide helper scripts:

### Building from WSL (Windows Subsystem for Linux):
- **For Windows:** Use `build_windows_from_wsl.sh` (builds Windows .exe from WSL)
- **For macOS:** Use `prepare_mac_build.sh` (creates a transfer package for building on Mac)
- **For Linux:** Use `build_linux.sh` (native build)

The `prepare_mac_build.sh` script packages your project with all necessary files and build scripts, ready to transfer to a Mac for final building.

## Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [Pygame Documentation](https://www.pygame.org/docs/)

## Support

If you encounter issues during the build process:
1. Check the error messages in the console
2. Verify all prerequisites are installed
3. Try rebuilding with `--clean` flag
4. Check PyInstaller's compatibility with your Python version
