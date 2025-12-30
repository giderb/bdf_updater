#!/usr/bin/env python3
"""
Build script to create a standalone executable for BDF Property Updater.

This script:
1. Generates platform-specific icons (ICO, ICNS, PNG)
2. Runs PyInstaller to create a single executable
3. Copies the executable to the dist folder

Usage:
    python build_exe.py [options]

Options:
    --skip-icons    Skip icon generation (use existing icons)
    --clean         Clean build directories before building
    --debug         Build with debug console enabled
    --onedir        Build as one-directory instead of one-file

Requirements:
    pip install pyinstaller pillow cairosvg

Note: cairosvg is optional but provides better SVG rendering quality.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform_info() -> dict:
    """Get platform-specific information."""
    system = platform.system().lower()

    if system == 'windows':
        return {
            'name': 'Windows',
            'icon_ext': '.ico',
            'exe_ext': '.exe',
            'icon_file': 'icon.ico',
        }
    elif system == 'darwin':
        return {
            'name': 'macOS',
            'icon_ext': '.icns',
            'exe_ext': '.app',
            'icon_file': 'icon.icns',
        }
    else:
        return {
            'name': 'Linux',
            'icon_ext': '.png',
            'exe_ext': '',
            'icon_file': 'icon.png',
        }


def check_requirements() -> bool:
    """Check if required packages are installed."""
    print("Checking requirements...")

    missing = []

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  ✗ PyInstaller NOT INSTALLED")
        missing.append("pyinstaller")

    # Check Pillow (for icon generation)
    try:
        import PIL
        print(f"  ✓ Pillow {PIL.__version__}")
    except ImportError:
        print("  ✗ Pillow NOT INSTALLED (required for icon generation)")
        missing.append("pillow")

    # Check cairosvg (optional)
    try:
        import cairosvg
        print(f"  ✓ cairosvg (optional, better SVG quality)")
    except ImportError:
        print("  ○ cairosvg not installed (optional)")

    # Check PyQt5
    try:
        from PyQt5.QtCore import QT_VERSION_STR
        print(f"  ✓ PyQt5 {QT_VERSION_STR}")
    except ImportError:
        print("  ✗ PyQt5 NOT INSTALLED")
        missing.append("PyQt5")

    # Check pyNastran
    try:
        import pyNastran
        print(f"  ✓ pyNastran {pyNastran.__version__}")
    except ImportError:
        print("  ✗ pyNastran NOT INSTALLED")
        missing.append("pyNastran")

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False

    return True


def build_icons(script_dir: Path, force: bool = False) -> bool:
    """Build platform-specific icons."""
    platform_info = get_platform_info()
    icon_file = script_dir / platform_info['icon_file']

    if icon_file.exists() and not force:
        print(f"  Icon already exists: {icon_file.name}")
        return True

    print("Building icons...")
    build_icon_script = script_dir / "build_icon.py"

    if not build_icon_script.exists():
        print(f"  Error: build_icon.py not found")
        return False

    result = subprocess.run(
        [sys.executable, str(build_icon_script)],
        cwd=str(script_dir),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  Icon build failed:")
        print(result.stderr)
        return False

    print(result.stdout)
    return icon_file.exists()


def clean_build_dirs(script_dir: Path):
    """Clean build and dist directories."""
    print("Cleaning build directories...")

    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.pyc', '*.pyo']

    for dir_name in dirs_to_clean:
        dir_path = script_dir / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed {dir_name}/")

    # Clean __pycache__ in subdirectories
    for pycache in script_dir.rglob('__pycache__'):
        shutil.rmtree(pycache)


def run_pyinstaller(script_dir: Path, debug: bool = False, onedir: bool = False) -> bool:
    """Run PyInstaller to create the executable."""
    print("\nRunning PyInstaller...")

    spec_file = script_dir / "bdf_updater.spec"

    if not spec_file.exists():
        print(f"  Error: Spec file not found: {spec_file}")
        return False

    # Build command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
    ]

    if debug:
        cmd.append('--debug=all')

    cmd.append(str(spec_file))

    print(f"  Command: {' '.join(cmd)}")
    print()

    # Run PyInstaller
    result = subprocess.run(
        cmd,
        cwd=str(script_dir),
    )

    return result.returncode == 0


def get_output_info(script_dir: Path) -> dict:
    """Get information about the built executable."""
    platform_info = get_platform_info()
    dist_dir = script_dir / 'dist'

    exe_name = 'BDF_Property_Updater' + platform_info['exe_ext']
    exe_path = dist_dir / exe_name

    # For macOS app bundle
    if platform_info['name'] == 'macOS':
        app_path = dist_dir / 'BDF Property Updater.app'
        if app_path.exists():
            return {
                'path': app_path,
                'size': sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()),
                'type': 'app bundle'
            }

    if exe_path.exists():
        return {
            'path': exe_path,
            'size': exe_path.stat().st_size,
            'type': 'executable'
        }

    return None


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main():
    """Main build function."""
    parser = argparse.ArgumentParser(
        description='Build standalone executable for BDF Property Updater'
    )
    parser.add_argument(
        '--skip-icons', action='store_true',
        help='Skip icon generation'
    )
    parser.add_argument(
        '--clean', action='store_true',
        help='Clean build directories before building'
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Build with debug console enabled'
    )
    parser.add_argument(
        '--onedir', action='store_true',
        help='Build as one-directory instead of one-file'
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()

    print("=" * 60)
    print("BDF Property Updater - Executable Build Script")
    print("=" * 60)
    print()

    platform_info = get_platform_info()
    print(f"Platform: {platform_info['name']}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    # Check requirements
    if not check_requirements():
        print("\nBuild aborted: Missing requirements")
        sys.exit(1)

    print()

    # Clean if requested
    if args.clean:
        clean_build_dirs(script_dir)
        print()

    # Build icons
    if not args.skip_icons:
        if not build_icons(script_dir):
            print("\nWarning: Icon build failed, continuing without custom icon")
        print()

    # Run PyInstaller
    if not run_pyinstaller(script_dir, args.debug, args.onedir):
        print("\nBuild FAILED!")
        sys.exit(1)

    # Report results
    print()
    print("=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)

    output = get_output_info(script_dir)
    if output:
        print(f"\nOutput: {output['path']}")
        print(f"Type: {output['type']}")
        print(f"Size: {format_size(output['size'])}")
    else:
        print("\nWarning: Could not find output executable")

    print()
    print("To run the application:")
    if platform_info['name'] == 'Windows':
        print(f"  dist\\BDF_Property_Updater.exe")
    elif platform_info['name'] == 'macOS':
        print(f"  open 'dist/BDF Property Updater.app'")
    else:
        print(f"  ./dist/BDF_Property_Updater")


if __name__ == "__main__":
    main()
