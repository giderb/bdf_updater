"""
GUI tests for the BDF Property Updater application.

Tests cover:
- Window initialization
- File selection widgets
- BDF loading and display
- CSV loading
- Preview functionality
- Update application
- Reset functionality

Uses pytest-qt for Qt testing.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Skip all tests in this module if PyQt5 is not available
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog
    from PyQt5.QtCore import Qt
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not installed")


@pytest.fixture
def app():
    """Create QApplication for tests."""
    if not PYQT_AVAILABLE:
        pytest.skip("PyQt5 not installed")
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def main_window(app):
    """Create main window for testing."""
    from bdf_updater_gui import BDFUpdaterMainWindow
    window = BDFUpdaterMainWindow()
    yield window
    window.close()


class TestMainWindowInit:
    """Tests for main window initialization."""

    def test_window_title(self, main_window):
        """Test that window has correct title."""
        assert "BDF" in main_window.windowTitle()
        assert "Updater" in main_window.windowTitle()

    def test_window_minimum_size(self, main_window):
        """Test that window has minimum size set."""
        assert main_window.minimumWidth() >= 800
        assert main_window.minimumHeight() >= 500

    def test_processor_initialized(self, main_window):
        """Test that BDF processor is initialized."""
        assert main_window.processor is not None

    def test_update_lists_empty(self, main_window):
        """Test that update lists are initially empty."""
        assert len(main_window.shell_updates) == 0
        assert len(main_window.bar_updates) == 0

    def test_buttons_initial_state(self, main_window):
        """Test initial button enabled states."""
        # Preview and Apply should be disabled initially
        assert not main_window.preview_btn.isEnabled()
        assert not main_window.apply_btn.isEnabled()

    def test_write_bdfs_checkbox_default(self, main_window):
        """Test that write_bdfs checkbox is checked by default."""
        assert main_window.write_bdfs_checkbox.isChecked()


class TestFileSelectionWidgets:
    """Tests for file selection widgets."""

    def test_bdf_file_widget_exists(self, main_window):
        """Test that BDF file selection widget exists."""
        assert main_window.bdf_file_widget is not None

    def test_shell_csv_widget_exists(self, main_window):
        """Test that shell CSV selection widget exists."""
        assert main_window.shell_csv_widget is not None

    def test_bar_csv_widget_exists(self, main_window):
        """Test that bar CSV selection widget exists."""
        assert main_window.bar_csv_widget is not None

    def test_file_widget_get_path_empty(self, main_window):
        """Test that get_path returns None when empty."""
        assert main_window.bdf_file_widget.get_path() is None

    def test_file_widget_set_path(self, main_window):
        """Test setting path programmatically."""
        test_path = "/test/path/file.bdf"
        main_window.bdf_file_widget.set_path(test_path)
        assert main_window.bdf_file_widget.get_path() == test_path

    def test_file_widget_clear(self, main_window):
        """Test clearing the path."""
        main_window.bdf_file_widget.set_path("/test/path/file.bdf")
        main_window.bdf_file_widget.clear()
        assert main_window.bdf_file_widget.get_path() is None


class TestBDFLoading:
    """Tests for BDF file loading functionality."""

    def test_load_bdf_no_file_selected(self, main_window, qtbot):
        """Test loading when no file is selected shows warning."""
        with patch.object(QMessageBox, 'warning') as mock_warning:
            main_window.load_bdf()
            mock_warning.assert_called_once()

    def test_load_bdf_valid_file(self, main_window, sample_bdf_path, qtbot):
        """Test loading a valid BDF file."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        # Check that properties are loaded
        assert main_window.processor.bdf is not None
        assert main_window.shell_table.rowCount() > 0

    def test_load_bdf_displays_shell_properties(self, main_window, sample_bdf_path, qtbot):
        """Test that shell properties are displayed in table."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        # sample.bdf has 3 PSHELL properties
        assert main_window.shell_table.rowCount() == 3

    def test_load_bdf_displays_bar_properties(self, main_window, sample_bdf_path, qtbot):
        """Test that bar properties are displayed in table."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        # sample.bdf has 3 PBARL properties
        assert main_window.bar_table.rowCount() == 3

    def test_load_bdf_updates_status_bar(self, main_window, sample_bdf_path, qtbot):
        """Test that status bar is updated after loading."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        status_message = main_window.statusBar.currentMessage()
        assert "sample.bdf" in status_message or "Loaded" in status_message

    def test_load_bdf_nonexistent_file(self, main_window, qtbot):
        """Test loading a nonexistent file shows error."""
        main_window.bdf_file_widget.set_path("/nonexistent/file.bdf")

        with patch.object(QMessageBox, 'critical') as mock_critical:
            main_window.load_bdf()
            mock_critical.assert_called_once()


class TestCSVLoading:
    """Tests for CSV file loading functionality."""

    def test_load_csv_shell_only(self, main_window, sample_shell_csv_path, qtbot):
        """Test loading only shell CSV."""
        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.load_csv_files()

        assert len(main_window.shell_updates) == 3
        assert len(main_window.bar_updates) == 0

    def test_load_csv_bar_only(self, main_window, sample_bar_csv_path, qtbot):
        """Test loading only bar CSV."""
        main_window.bar_csv_widget.set_path(str(sample_bar_csv_path))
        main_window.load_csv_files()

        assert len(main_window.shell_updates) == 0
        assert len(main_window.bar_updates) == 3

    def test_load_csv_both(self, main_window, sample_shell_csv_path, sample_bar_csv_path, qtbot):
        """Test loading both shell and bar CSV."""
        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.bar_csv_widget.set_path(str(sample_bar_csv_path))
        main_window.load_csv_files()

        assert len(main_window.shell_updates) == 3
        assert len(main_window.bar_updates) == 3

    def test_load_csv_updates_button_state(self, main_window, sample_bdf_path,
                                           sample_shell_csv_path, qtbot):
        """Test that buttons are enabled after loading BDF and CSV."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.load_csv_files()

        assert main_window.preview_btn.isEnabled()
        assert main_window.apply_btn.isEnabled()

    def test_load_csv_invalid_file(self, main_window, test_data_dir, qtbot):
        """Test loading invalid CSV shows warning."""
        main_window.shell_csv_widget.set_path(str(test_data_dir / "invalid_shell.csv"))

        with patch.object(QMessageBox, 'warning') as mock_warning:
            main_window.load_csv_files()
            mock_warning.assert_called()


class TestPreviewFunctionality:
    """Tests for preview changes functionality."""

    def test_preview_no_bdf_loaded(self, main_window, qtbot):
        """Test preview without loading BDF shows warning."""
        with patch.object(QMessageBox, 'warning') as mock_warning:
            main_window.preview_changes()
            mock_warning.assert_called_once()

    def test_preview_populates_shell_table(self, main_window, sample_bdf_path,
                                           sample_shell_csv_path, qtbot):
        """Test that preview populates shell preview table."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.load_csv_files()

        main_window.preview_changes()

        assert main_window.shell_preview_table.rowCount() == 3

    def test_preview_populates_bar_table(self, main_window, sample_bdf_path,
                                         sample_bar_csv_path, qtbot):
        """Test that preview populates bar preview table."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        main_window.bar_csv_widget.set_path(str(sample_bar_csv_path))
        main_window.load_csv_files()

        main_window.preview_changes()

        assert main_window.bar_preview_table.rowCount() == 3

    def test_preview_switches_to_preview_tab(self, main_window, sample_bdf_path,
                                              sample_shell_csv_path, qtbot):
        """Test that preview switches to preview tab."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.load_csv_files()

        main_window.preview_changes()

        assert main_window.tabs.currentIndex() == 1


class TestResetFunctionality:
    """Tests for reset functionality."""

    def test_reset_clears_processor(self, main_window, sample_bdf_path, qtbot):
        """Test that reset clears the processor."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            main_window.reset_all()

        assert main_window.processor.bdf is None

    def test_reset_clears_updates(self, main_window, sample_shell_csv_path, qtbot):
        """Test that reset clears update lists."""
        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.load_csv_files()

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            main_window.reset_all()

        assert len(main_window.shell_updates) == 0
        assert len(main_window.bar_updates) == 0

    def test_reset_clears_tables(self, main_window, sample_bdf_path, qtbot):
        """Test that reset clears property tables."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            main_window.reset_all()

        assert main_window.shell_table.rowCount() == 0
        assert main_window.bar_table.rowCount() == 0

    def test_reset_clears_file_paths(self, main_window, sample_bdf_path, qtbot):
        """Test that reset clears file path widgets."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            main_window.reset_all()

        assert main_window.bdf_file_widget.get_path() is None

    def test_reset_cancelled(self, main_window, sample_bdf_path, qtbot):
        """Test that reset can be cancelled."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            main_window.reset_all()

        # BDF should still be loaded
        assert main_window.processor.bdf is not None


class TestLogFunctionality:
    """Tests for log display functionality."""

    def test_log_adds_message(self, main_window, qtbot):
        """Test that log() adds message to log widget."""
        main_window.log("Test message")
        log_content = main_window.log_text.toPlainText()
        assert "Test message" in log_content

    def test_log_info_level(self, main_window, qtbot):
        """Test log with info level."""
        main_window.log("Info message", "info")
        log_html = main_window.log_text.toHtml()
        assert "Info message" in log_html

    def test_log_error_level(self, main_window, qtbot):
        """Test log with error level."""
        main_window.log("Error message", "error")
        log_html = main_window.log_text.toHtml()
        assert "Error message" in log_html
        assert "red" in log_html

    def test_log_success_level(self, main_window, qtbot):
        """Test log with success level."""
        main_window.log("Success message", "success")
        log_html = main_window.log_text.toHtml()
        assert "Success message" in log_html
        assert "green" in log_html


class TestPropertyTables:
    """Tests for property table widgets."""

    def test_shell_table_has_correct_columns(self, main_window):
        """Test that shell table has correct column headers."""
        headers = []
        for i in range(main_window.shell_table.columnCount()):
            headers.append(main_window.shell_table.horizontalHeaderItem(i).text())

        assert "Property ID" in headers
        assert "Thickness" in headers

    def test_bar_table_has_correct_columns(self, main_window):
        """Test that bar table has correct column headers."""
        headers = []
        for i in range(main_window.bar_table.columnCount()):
            headers.append(main_window.bar_table.horizontalHeaderItem(i).text())

        assert "Property ID" in headers
        assert "Bar Type" in headers
        assert "Dimensions" in headers

    def test_table_clear_data(self, main_window, sample_bdf_path, qtbot):
        """Test that table can be cleared."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        initial_rows = main_window.shell_table.rowCount()
        assert initial_rows > 0

        main_window.shell_table.clear_data()
        assert main_window.shell_table.rowCount() == 0


class TestUpdateButtonStates:
    """Tests for button state management."""

    def test_buttons_disabled_no_bdf(self, main_window):
        """Test buttons disabled when no BDF loaded."""
        main_window.update_button_states()
        assert not main_window.preview_btn.isEnabled()
        assert not main_window.apply_btn.isEnabled()

    def test_buttons_disabled_no_updates(self, main_window, sample_bdf_path, qtbot):
        """Test buttons disabled when BDF loaded but no updates."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        main_window.update_button_states()
        assert not main_window.preview_btn.isEnabled()
        assert not main_window.apply_btn.isEnabled()

    def test_buttons_enabled_with_updates(self, main_window, sample_bdf_path,
                                          sample_shell_csv_path, qtbot):
        """Test buttons enabled when BDF and updates loaded."""
        main_window.bdf_file_widget.set_path(str(sample_bdf_path))
        main_window.load_bdf()

        main_window.shell_csv_widget.set_path(str(sample_shell_csv_path))
        main_window.load_csv_files()

        assert main_window.preview_btn.isEnabled()
        assert main_window.apply_btn.isEnabled()
