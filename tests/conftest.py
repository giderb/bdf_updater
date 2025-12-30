"""
Pytest configuration and fixtures for BDF Property Updater tests.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bdf_processor import BDFProcessor


@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return Path(__file__).parent.parent / "test_data"


@pytest.fixture
def sample_bdf_path(test_data_dir):
    """Return the path to the sample BDF file."""
    return test_data_dir / "sample.bdf"


@pytest.fixture
def sample_shell_csv_path(test_data_dir):
    """Return the path to the sample shell CSV file."""
    return test_data_dir / "shell_updates.csv"


@pytest.fixture
def sample_bar_csv_path(test_data_dir):
    """Return the path to the sample bar CSV file."""
    return test_data_dir / "bar_updates.csv"


@pytest.fixture
def main_with_include_path(test_data_dir):
    """Return the path to the main BDF with INCLUDE."""
    return test_data_dir / "main_with_include.bdf"


@pytest.fixture
def temp_dir():
    """Create and return a temporary directory, cleaned up after test."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_bdf_copy(sample_bdf_path, temp_dir):
    """Create a copy of the sample BDF in a temp directory."""
    dest = temp_dir / "test_sample.bdf"
    shutil.copy(sample_bdf_path, dest)
    return dest


@pytest.fixture
def temp_include_copy(test_data_dir, temp_dir):
    """Create copies of the INCLUDE test files in a temp directory."""
    main_src = test_data_dir / "main_with_include.bdf"
    props_src = test_data_dir / "properties.bdf"

    main_dest = temp_dir / "main_with_include.bdf"
    props_dest = temp_dir / "properties.bdf"

    shutil.copy(main_src, main_dest)
    shutil.copy(props_src, props_dest)

    return main_dest


@pytest.fixture
def processor():
    """Return a fresh BDFProcessor instance."""
    return BDFProcessor()


@pytest.fixture
def loaded_processor(processor, sample_bdf_path):
    """Return a BDFProcessor with sample.bdf loaded."""
    processor.load_bdf(sample_bdf_path)
    return processor


@pytest.fixture
def temp_shell_csv(temp_dir):
    """Create a temporary shell CSV file."""
    csv_path = temp_dir / "shell_test.csv"
    with open(csv_path, 'w') as f:
        f.write("property_id,thickness\n")
        f.write("101,0.007\n")
        f.write("102,0.014\n")
    return csv_path


@pytest.fixture
def temp_bar_csv(temp_dir):
    """Create a temporary bar CSV file."""
    csv_path = temp_dir / "bar_test.csv"
    with open(csv_path, 'w') as f:
        f.write("property_id,height,width\n")
        f.write("201,0.12,0.06\n")
        f.write("202,0.08,0.04\n")
    return csv_path


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for GUI tests."""
    # Import here to avoid issues if PyQt5 is not installed
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    except ImportError:
        pytest.skip("PyQt5 not installed")


@pytest.fixture
def main_window(qapp):
    """Create the main window for GUI tests."""
    try:
        from bdf_updater_gui import BDFUpdaterMainWindow
        window = BDFUpdaterMainWindow()
        yield window
        window.close()
    except ImportError:
        pytest.skip("GUI module not available")
