# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for BDF Property Updater.

Generates a single executable with embedded icon and all dependencies.

Usage:
    pyinstaller bdf_updater.spec

Or use the build script:
    python build_exe.py
"""

import sys
import os
from pathlib import Path

# Get the directory containing this spec file
SPEC_DIR = Path(SPECPATH)

# Determine the icon file based on platform
if sys.platform == 'win32':
    ICON_FILE = SPEC_DIR / 'icon.ico'
elif sys.platform == 'darwin':
    ICON_FILE = SPEC_DIR / 'icon.icns'
else:
    ICON_FILE = SPEC_DIR / 'icon.png'

# Use icon.ico as fallback if platform-specific doesn't exist
if not ICON_FILE.exists():
    ICON_FILE = SPEC_DIR / 'icon.ico'
    if not ICON_FILE.exists():
        ICON_FILE = None

# Analysis: collect all dependencies
a = Analysis(
    ['bdf_updater_gui.py'],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=[
        # Include test data for verification (optional, remove for smaller exe)
        # ('test_data', 'test_data'),
    ],
    hiddenimports=[
        # PyQt5 modules
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtSvg',
        'PyQt5.sip',
        # pyNastran modules
        'pyNastran',
        'pyNastran.bdf',
        'pyNastran.bdf.bdf',
        'pyNastran.bdf.cards',
        'pyNastran.utils',
        # Standard library
        'csv',
        'dataclasses',
        'pathlib',
        'typing',
        # Numpy (used by pyNastran)
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.lib',
        'numpy.lib.format',
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
        'PIL',  # Not needed at runtime (only for icon building)
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
    name='BDF_Property_Updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression if available
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
        name='BDF Property Updater.app',
        icon=str(ICON_FILE) if ICON_FILE and ICON_FILE.exists() else None,
        bundle_identifier='com.bdftools.propertyupdater',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'CFBundleName': 'BDF Property Updater',
            'CFBundleDisplayName': 'BDF Property Updater',
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'BDF File',
                    'CFBundleTypeExtensions': ['bdf', 'dat', 'nas'],
                    'CFBundleTypeRole': 'Editor',
                },
                {
                    'CFBundleTypeName': 'CSV File',
                    'CFBundleTypeExtensions': ['csv'],
                    'CFBundleTypeRole': 'Editor',
                },
            ],
        },
    )
