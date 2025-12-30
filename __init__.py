"""
BDF Property Updater Package

A PyQt5 application for updating Nastran BDF shell and bar properties.
"""

__version__ = "1.0.0"
__author__ = "BDF Tools"

from .bdf_processor import (
    BDFProcessor,
    ShellPropertyUpdate,
    BarPropertyUpdate,
    PropertyUpdateResult,
    CSVParseError,
    BDFProcessorError
)

__all__ = [
    'BDFProcessor',
    'ShellPropertyUpdate',
    'BarPropertyUpdate',
    'PropertyUpdateResult',
    'CSVParseError',
    'BDFProcessorError'
]
