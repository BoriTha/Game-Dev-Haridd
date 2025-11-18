# Build Scripts and Documentation

This folder contains all build-related scripts and documentation for DarkSoul RPG.

## Build Scripts

### Platform-Specific Builds
- **`build_linux.sh`** - Build script for Linux
- **`build_mac.sh`** - Build script for macOS
- **`build_windows.bat`** - Build script for Windows (native)
- **`build_windows_from_wsl.sh`** - Build script for Windows from WSL

### Distribution Scripts
- **`create_distribution.sh`** - Create distribution packages (Linux/Mac)
- **`create_distribution.bat`** - Create distribution packages (Windows native)
- **`create_windows_distribution.sh`** - Create Windows distribution from WSL

### Utility Scripts
- **`verify_build.sh`** - Verify build integrity and test executable
- **`fix_asset_paths.py`** - Fix asset paths for PyInstaller compatibility
- **`fix_remaining_assets.py`** - Additional asset path fixes

## Documentation

- **`BUILD_INSTRUCTIONS.md`** - Detailed instructions for building the game
- **`DISTRIBUTION_SUMMARY.txt`** - Summary of distribution process and outputs
- **`FINAL_BUILD_SUMMARY.txt`** - Final build summary and notes
- **`COMMIT_MESSAGE_v0.7.txt`** - Release notes for version 0.7

## Build Specification

- **`DarkSoul_RPG.spec`** - PyInstaller spec file for building executables

## Output Directories

All build outputs are organized within this folder:

- **`dist/`** - Contains the built executable (created by build scripts)
- **`build/`** - PyInstaller temporary build files (auto-generated)
- **`distributions/`** - Distribution packages (ZIP, tar.gz, DMG) created by distribution scripts

## Usage

**IMPORTANT:** All build scripts must be run from within the `build-scripts` directory.

```bash
# Navigate to build-scripts folder first
cd build-scripts

# Then run the appropriate build script
./build_linux.sh      # Linux
./build_mac.sh        # macOS
build_windows.bat     # Windows (run from Command Prompt)
./build_windows_from_wsl.sh  # Windows from WSL
```

The build output will be in `build-scripts/dist/DarkSoul_RPG/`

After building, create distribution packages:
```bash
./create_distribution.sh      # Linux/Mac
create_distribution.bat        # Windows
```

Distribution packages will be in `build-scripts/distributions/`

For more detailed instructions, see `BUILD_INSTRUCTIONS.md` or `QUICK_START.md`.
