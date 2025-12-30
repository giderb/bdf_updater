#!/usr/bin/env python3
"""
Build script to generate platform-specific icon files from SVG.

Generates:
- icon.ico (Windows) - multi-resolution ICO file
- icon.icns (macOS) - Apple icon format
- icon.png (Linux/general) - PNG format

Requires: Pillow, cairosvg (optional, for better SVG rendering)
"""

import os
import sys
from pathlib import Path

# Try to import required libraries
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cairosvg
    HAS_CAIROSVG = True
except (ImportError, OSError):
    HAS_CAIROSVG = False


def svg_to_png_cairosvg(svg_path: Path, png_path: Path, size: int) -> bool:
    """Convert SVG to PNG using cairosvg (high quality)."""
    if not HAS_CAIROSVG:
        return False
    try:
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            output_width=size,
            output_height=size
        )
        return True
    except Exception as e:
        print(f"cairosvg conversion failed: {e}")
        return False


def svg_to_png_pyqt(svg_path: Path, png_path: Path, size: int) -> bool:
    """Convert SVG to PNG using PyQt5 (fallback)."""
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QByteArray, Qt
        from PyQt5.QtGui import QPixmap, QPainter
        from PyQt5.QtSvg import QSvgRenderer

        # Initialize QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # Read SVG content
        with open(svg_path, 'rb') as f:
            svg_data = f.read()

        # Render to pixmap
        renderer = QSvgRenderer(QByteArray(svg_data))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)  # Transparent

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        # Save as PNG
        pixmap.save(str(png_path), "PNG")
        return True

    except Exception as e:
        print(f"PyQt5 conversion failed: {e}")
        return False


def create_png_icons(svg_path: Path, output_dir: Path) -> dict:
    """Create PNG icons at various sizes."""
    sizes = [16, 24, 32, 48, 64, 128, 256, 512]
    png_files = {}

    output_dir.mkdir(parents=True, exist_ok=True)

    for size in sizes:
        png_path = output_dir / f"icon_{size}.png"

        # Try cairosvg first (better quality), then PyQt5
        if svg_to_png_cairosvg(svg_path, png_path, size):
            png_files[size] = png_path
            print(f"  Created {png_path.name} ({size}x{size}) using cairosvg")
        elif svg_to_png_pyqt(svg_path, png_path, size):
            png_files[size] = png_path
            print(f"  Created {png_path.name} ({size}x{size}) using PyQt5")
        else:
            print(f"  Failed to create {size}x{size} PNG")

    return png_files


def create_ico_file(png_files: dict, ico_path: Path) -> bool:
    """Create Windows ICO file from PNG files."""
    if not HAS_PIL:
        print("Pillow not installed, cannot create ICO file")
        return False

    # ICO supports these sizes
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in ico_sizes:
        if size in png_files:
            img = Image.open(png_files[size])
            # Ensure RGBA mode
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            images.append(img)

    if not images:
        print("No images available for ICO creation")
        return False

    try:
        # Save as ICO with multiple sizes
        images[0].save(
            str(ico_path),
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        print(f"  Created {ico_path.name}")
        return True
    except Exception as e:
        print(f"Failed to create ICO: {e}")
        return False


def create_icns_file(png_files: dict, icns_path: Path) -> bool:
    """Create macOS ICNS file from PNG files."""
    if not HAS_PIL:
        print("Pillow not installed, cannot create ICNS file")
        return False

    # ICNS needs specific sizes
    required_sizes = [16, 32, 64, 128, 256, 512]
    images = []

    for size in required_sizes:
        if size in png_files:
            img = Image.open(png_files[size])
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            images.append(img)

    if not images:
        print("No images available for ICNS creation")
        return False

    try:
        # macOS ICNS format
        images[0].save(
            str(icns_path),
            format='ICNS',
            append_images=images[1:]
        )
        print(f"  Created {icns_path.name}")
        return True
    except Exception as e:
        print(f"Failed to create ICNS: {e}")
        # ICNS format may not be supported on all Pillow versions
        return False


def create_main_png(png_files: dict, png_path: Path) -> bool:
    """Copy the 256x256 PNG as the main icon."""
    if 256 in png_files:
        import shutil
        shutil.copy(png_files[256], png_path)
        print(f"  Created {png_path.name}")
        return True
    return False


def main():
    """Main build function."""
    print("=" * 60)
    print("BDF Property Updater - Icon Build Script")
    print("=" * 60)

    # Paths
    script_dir = Path(__file__).parent
    svg_path = script_dir / "icon.svg"
    build_dir = script_dir / "build" / "icons"

    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        sys.exit(1)

    print(f"\nSource: {svg_path}")
    print(f"Output: {build_dir}\n")

    # Check dependencies
    print("Checking dependencies:")
    print(f"  Pillow: {'installed' if HAS_PIL else 'NOT INSTALLED'}")
    print(f"  cairosvg: {'installed' if HAS_CAIROSVG else 'not installed (optional)'}")
    print()

    # Create PNG icons at various sizes
    print("Creating PNG icons...")
    png_files = create_png_icons(svg_path, build_dir)

    if not png_files:
        print("Error: Failed to create any PNG icons")
        sys.exit(1)

    print()

    # Create platform-specific icons
    print("Creating platform-specific icons...")

    # Windows ICO
    ico_path = script_dir / "icon.ico"
    create_ico_file(png_files, ico_path)

    # macOS ICNS (may fail if Pillow doesn't support it)
    icns_path = script_dir / "icon.icns"
    create_icns_file(png_files, icns_path)

    # Main PNG for Linux/general use
    png_path = script_dir / "icon.png"
    create_main_png(png_files, png_path)

    print()
    print("=" * 60)
    print("Icon build complete!")
    print("=" * 60)

    # Summary
    print("\nGenerated files:")
    for f in [ico_path, icns_path, png_path]:
        if f.exists():
            print(f"  ✓ {f.name}")
        else:
            print(f"  ✗ {f.name} (not created)")


if __name__ == "__main__":
    main()
