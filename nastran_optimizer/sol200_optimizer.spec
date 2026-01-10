# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SOL200 Optimizer.

Generates a single executable with embedded icon and all dependencies.

Usage:
    pyinstaller sol200_optimizer.spec

Or use the build script:
    python build_optimizer.py
"""

import sys
import os
from pathlib import Path

# Get the directory containing this spec file
SPEC_DIR = Path(SPECPATH)
ROOT_DIR = SPEC_DIR.parent

# Determine the icon file based on platform
if sys.platform == 'win32':
    ICON_FILE = ROOT_DIR / 'icon.ico'
elif sys.platform == 'darwin':
    ICON_FILE = ROOT_DIR / 'icon.icns'
else:
    ICON_FILE = ROOT_DIR / 'icon.png'

# Use icon.ico as fallback if platform-specific doesn't exist
if not ICON_FILE.exists():
    ICON_FILE = ROOT_DIR / 'icon.ico'
    if not ICON_FILE.exists():
        ICON_FILE = None

# Analysis: collect all dependencies
a = Analysis(
    [str(SPEC_DIR / 'ui' / 'main_window.py')],
    pathex=[str(SPEC_DIR), str(ROOT_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyQt6 modules
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'PyQt6.sip',
        # pyNastran modules
        'pyNastran',
        'pyNastran.bdf',
        'pyNastran.bdf.bdf',
        'pyNastran.bdf.cards',
        'pyNastran.utils',
        # Sympy for equation parsing
        'sympy',
        'sympy.core',
        'sympy.parsing',
        # Standard library
        'csv',
        'dataclasses',
        'pathlib',
        'typing',
        'json',
        'tempfile',
        # Numpy (used by pyNastran and calculations)
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.lib',
        'numpy.lib.format',
        # Local modules
        'nastran_optimizer',
        'nastran_optimizer.core',
        'nastran_optimizer.core.design_variable',
        'nastran_optimizer.core.response',
        'nastran_optimizer.core.constraint',
        'nastran_optimizer.core.objective',
        'nastran_optimizer.core.equation_parser',
        'nastran_optimizer.core.bdf_manager',
        'nastran_optimizer.core.optimization_model',
        'nastran_optimizer.core.validator',
        'nastran_optimizer.core.nastran_runner',
        'nastran_optimizer.ui',
        'nastran_optimizer.ui.main_window',
        'nastran_optimizer.ui.styles',
        'nastran_optimizer.ui.styles.modern_style',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'PIL',
        'cairosvg',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove unnecessary pyNastran data files to reduce size
a.datas = [d for d in a.datas if not d[0].startswith('pyNastran/bdf/test')]

# PYZ: Create the Python archive
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# EXE: Create the executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SOL200_Optimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI application)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE) if ICON_FILE and ICON_FILE.exists() else None,
)

# For macOS: Create .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='SOL200 Optimizer.app',
        icon=str(ICON_FILE) if ICON_FILE and ICON_FILE.exists() else None,
        bundle_identifier='com.aerospace.sol200optimizer',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'CFBundleName': 'SOL200 Optimizer',
            'CFBundleDisplayName': 'SOL200 Optimizer',
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'BDF File',
                    'CFBundleTypeExtensions': ['bdf', 'dat', 'nas'],
                    'CFBundleTypeRole': 'Editor',
                },
                {
                    'CFBundleTypeName': 'Optimization Project',
                    'CFBundleTypeExtensions': ['sol200', 'json'],
                    'CFBundleTypeRole': 'Editor',
                },
            ],
        },
    )
