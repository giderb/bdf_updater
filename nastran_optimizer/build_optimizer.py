#!/usr/bin/env python3
"""
Build script for SOL200 Optimizer standalone executable.

This script:
1. Generates platform-specific icons (if not present)
2. Runs PyInstaller to create the executable
3. Handles cleanup and post-processing

Usage:
    python build_optimizer.py [--clean] [--skip-icons] [--debug]

Options:
    --clean      Remove previous build artifacts before building
    --skip-icons Skip icon generation (use existing icons)
    --debug      Build with debug console visible
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def clean_build(base_dir: Path):
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")

    dirs_to_remove = [
        base_dir / 'build',
        base_dir / 'dist',
    ]

    for d in dirs_to_remove:
        if d.exists():
            print(f"  Removing {d}")
            shutil.rmtree(d)

    # Remove .spec backup files
    for spec_backup in base_dir.glob('*.spec.bak'):
        spec_backup.unlink()


def generate_icons(base_dir: Path, root_dir: Path):
    """Generate platform-specific icons."""
    print("Generating icons...")

    # Check if icon.svg exists in root
    svg_path = root_dir / 'icon.svg'

    if not svg_path.exists():
        print(f"  Warning: {svg_path} not found, using default icon")
        return False

    # Run the icon build script from root
    build_icon = root_dir / 'build_icon.py'
    if build_icon.exists():
        try:
            subprocess.run([sys.executable, str(build_icon)], check=True)
            print("  Icons generated successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  Warning: Icon generation failed: {e}")
            return False
    else:
        print(f"  Warning: Icon build script not found")
        return False


def build_executable(base_dir: Path, debug: bool = False):
    """Build the executable using PyInstaller."""
    print("\nBuilding SOL200 Optimizer executable...")

    spec_file = base_dir / 'sol200_optimizer.spec'

    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}")
        return False

    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
    ]

    if debug:
        # Modify spec to enable console
        print("  Debug mode: Console will be visible")

    cmd.append(str(spec_file))

    print(f"  Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, cwd=str(base_dir))
        print("  Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Build failed: {e}")
        return False


def post_process(base_dir: Path):
    """Post-process the build output."""
    print("\nPost-processing...")

    dist_dir = base_dir / 'dist'

    if not dist_dir.exists():
        print("  Warning: dist directory not found")
        return

    # Find the output executable
    if sys.platform == 'win32':
        exe_name = 'SOL200_Optimizer.exe'
    elif sys.platform == 'darwin':
        exe_name = 'SOL200 Optimizer.app'
    else:
        exe_name = 'SOL200_Optimizer'

    output_path = dist_dir / exe_name

    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024) if output_path.is_file() else 0
        print(f"  Output: {output_path}")
        if size_mb > 0:
            print(f"  Size: {size_mb:.1f} MB")
    else:
        print(f"  Warning: Expected output not found: {output_path}")


def main():
    """Main build function."""
    parser = argparse.ArgumentParser(
        description='Build SOL200 Optimizer standalone executable'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Remove previous build artifacts before building'
    )
    parser.add_argument(
        '--skip-icons',
        action='store_true',
        help='Skip icon generation'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Build with debug console visible'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("SOL200 Optimizer - Build Script")
    print("=" * 60)

    base_dir = Path(__file__).parent
    root_dir = base_dir.parent

    print(f"\nBase directory: {base_dir}")
    print(f"Root directory: {root_dir}")

    # Check dependencies
    print("\nChecking dependencies...")
    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("  Error: PyInstaller not installed")
        print("  Run: pip install pyinstaller")
        sys.exit(1)

    try:
        import PyQt6
        print(f"  PyQt6: Found")
    except ImportError:
        print("  Error: PyQt6 not installed")
        sys.exit(1)

    try:
        import pyNastran
        print(f"  pyNastran: {pyNastran.__version__}")
    except ImportError:
        print("  Warning: pyNastran not installed")

    # Clean if requested
    if args.clean:
        clean_build(base_dir)

    # Generate icons
    if not args.skip_icons:
        generate_icons(base_dir, root_dir)

    # Build
    success = build_executable(base_dir, debug=args.debug)

    if success:
        post_process(base_dir)
        print("\n" + "=" * 60)
        print("Build completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Build failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
