#!/usr/bin/env python3
"""
BDF Property Updater GUI

A standalone PyQt5 application for updating Nastran BDF shell and bar properties.

Features:
- Load BDF files with INCLUDE support
- Update PSHELL thickness from CSV
- Update PBARL (rectangular section) dimensions from CSV
- Preview changes before applying
- Save with write_bdfs() for INCLUDE support
"""

import sys
import os
from pathlib import Path
from typing import Optional, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QTextEdit, QMessageBox, QCheckBox, QSplitter, QStatusBar,
    QProgressBar, QFrame, QStyle
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from icon_resources import get_app_icon
from bdf_processor import (
    BDFProcessor, ShellPropertyUpdate, BarPropertyUpdate,
    PropertyUpdateResult, CSVParseError, BDFProcessorError
)


class UpdateWorker(QThread):
    """Worker thread for applying updates to avoid GUI freezing."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, processor: BDFProcessor,
                 shell_updates: Optional[List[ShellPropertyUpdate]] = None,
                 bar_updates: Optional[List[BarPropertyUpdate]] = None,
                 output_path: Optional[str] = None,
                 use_write_bdfs: bool = True):
        super().__init__()
        self.processor = processor
        self.shell_updates = shell_updates or []
        self.bar_updates = bar_updates or []
        self.output_path = output_path
        self.use_write_bdfs = use_write_bdfs

    def run(self):
        try:
            total_updates = len(self.shell_updates) + len(self.bar_updates)
            current = 0

            # Apply shell updates
            for update in self.shell_updates:
                self.processor.update_shell_property(update)
                current += 1
                self.progress.emit(
                    int(current / total_updates * 80),
                    f"Updated PSHELL {update.property_id}"
                )

            # Apply bar updates
            for update in self.bar_updates:
                self.processor.update_bar_property(update)
                current += 1
                self.progress.emit(
                    int(current / total_updates * 80),
                    f"Updated PBARL {update.property_id}"
                )

            # Save the file
            self.progress.emit(90, "Saving BDF file...")
            self.processor.save_bdf(self.output_path, self.use_write_bdfs)
            self.progress.emit(100, "Complete!")

            summary = self.processor.get_update_summary()
            self.finished.emit(
                True,
                f"Successfully updated {summary['successful']} properties. "
                f"Failed: {summary['failed']}"
            )

        except Exception as e:
            self.finished.emit(False, str(e))


class FileSelectionWidget(QFrame):
    """Widget for file selection with path display."""

    def __init__(self, label: str, file_filter: str, parent=None):
        super().__init__(parent)
        self.file_filter = file_filter
        self.setup_ui(label)

    def setup_ui(self, label: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label)
        self.label.setMinimumWidth(120)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No file selected")

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear)

        layout.addWidget(self.label)
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(self.browse_btn)
        layout.addWidget(self.clear_btn)

    def browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.label.text()}", "", self.file_filter
        )
        if file_path:
            self.path_edit.setText(file_path)

    def clear(self):
        self.path_edit.clear()

    def get_path(self) -> Optional[str]:
        path = self.path_edit.text().strip()
        return path if path else None

    def set_path(self, path: str):
        self.path_edit.setText(path)


class PropertyTableWidget(QTableWidget):
    """Table widget for displaying properties."""

    def __init__(self, columns: List[str], parent=None):
        super().__init__(parent)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def clear_data(self):
        self.setRowCount(0)

    def add_row(self, values: List[str], color: Optional[QColor] = None):
        row = self.rowCount()
        self.insertRow(row)
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if color:
                item.setBackground(color)
            self.setItem(row, col, item)


class BDFUpdaterMainWindow(QMainWindow):
    """Main window for the BDF Property Updater application."""

    def __init__(self):
        super().__init__()
        self.processor = BDFProcessor()
        self.shell_updates: List[ShellPropertyUpdate] = []
        self.bar_updates: List[BarPropertyUpdate] = []
        self.worker: Optional[UpdateWorker] = None

        self.setup_ui()
        self.setWindowTitle("Nastran BDF Property Updater")
        self.setMinimumSize(1000, 700)

    def setup_ui(self):
        """Set up the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)

        self.bdf_file_widget = FileSelectionWidget(
            "BDF File:", "BDF Files (*.bdf *.dat *.nas);;All Files (*)"
        )
        self.shell_csv_widget = FileSelectionWidget(
            "Shell CSV:", "CSV Files (*.csv);;All Files (*)"
        )
        self.bar_csv_widget = FileSelectionWidget(
            "Bar CSV:", "CSV Files (*.csv);;All Files (*)"
        )

        file_layout.addWidget(self.bdf_file_widget)
        file_layout.addWidget(self.shell_csv_widget)
        file_layout.addWidget(self.bar_csv_widget)

        # Load button
        load_btn_layout = QHBoxLayout()
        self.load_bdf_btn = QPushButton("Load BDF")
        self.load_bdf_btn.clicked.connect(self.load_bdf)
        self.load_csv_btn = QPushButton("Load CSV Files")
        self.load_csv_btn.clicked.connect(self.load_csv_files)
        load_btn_layout.addStretch()
        load_btn_layout.addWidget(self.load_bdf_btn)
        load_btn_layout.addWidget(self.load_csv_btn)
        file_layout.addLayout(load_btn_layout)

        main_layout.addWidget(file_group)

        # Create splitter for properties and preview
        splitter = QSplitter(Qt.Vertical)

        # Properties tabs
        self.tabs = QTabWidget()

        # Current properties tab
        current_props_widget = QWidget()
        current_props_layout = QVBoxLayout(current_props_widget)

        # Shell properties table
        shell_group = QGroupBox("Current PSHELL Properties")
        shell_layout = QVBoxLayout(shell_group)
        self.shell_table = PropertyTableWidget(
            ["Property ID", "Thickness", "Material ID", "NSM"]
        )
        shell_layout.addWidget(self.shell_table)
        current_props_layout.addWidget(shell_group)

        # Bar properties table
        bar_group = QGroupBox("Current PBARL Properties")
        bar_layout = QVBoxLayout(bar_group)
        self.bar_table = PropertyTableWidget(
            ["Property ID", "Bar Type", "Dimensions", "Material ID", "Group"]
        )
        bar_layout.addWidget(self.bar_table)
        current_props_layout.addWidget(bar_group)

        self.tabs.addTab(current_props_widget, "Current Properties")

        # Preview tab
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Shell updates preview
        shell_preview_group = QGroupBox("Shell Property Updates Preview")
        shell_preview_layout = QVBoxLayout(shell_preview_group)
        self.shell_preview_table = PropertyTableWidget(
            ["Property ID", "Current Thickness", "New Thickness", "Change", "Status"]
        )
        shell_preview_layout.addWidget(self.shell_preview_table)
        preview_layout.addWidget(shell_preview_group)

        # Bar updates preview
        bar_preview_group = QGroupBox("Bar Property Updates Preview")
        bar_preview_layout = QVBoxLayout(bar_preview_group)
        self.bar_preview_table = PropertyTableWidget(
            ["Property ID", "Current (W×H)", "New (W×H)", "Status"]
        )
        bar_preview_layout.addWidget(self.bar_preview_table)
        preview_layout.addWidget(bar_preview_group)

        self.tabs.addTab(preview_widget, "Preview Changes")

        splitter.addWidget(self.tabs)

        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        self.log_text.setFont(font)
        log_layout.addWidget(self.log_text)

        splitter.addWidget(log_group)
        main_layout.addWidget(splitter, 1)

        # Bottom controls
        bottom_layout = QHBoxLayout()

        self.write_bdfs_checkbox = QCheckBox("Use write_bdfs() (preserves INCLUDE structure)")
        self.write_bdfs_checkbox.setChecked(True)
        bottom_layout.addWidget(self.write_bdfs_checkbox)

        bottom_layout.addStretch()

        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self.preview_changes)
        self.preview_btn.setEnabled(False)

        self.apply_btn = QPushButton("Apply && Save")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 16px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_all)

        bottom_layout.addWidget(self.preview_btn)
        bottom_layout.addWidget(self.apply_btn)
        bottom_layout.addWidget(self.reset_btn)

        main_layout.addLayout(bottom_layout)

        # Status bar with progress
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)

        self.statusBar.showMessage("Ready")

    def log(self, message: str, level: str = "info"):
        """Add a message to the log."""
        color_map = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        color = color_map.get(level, "black")
        self.log_text.append(f'<span style="color: {color};">{message}</span>')
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def load_bdf(self):
        """Load the BDF file."""
        bdf_path = self.bdf_file_widget.get_path()
        if not bdf_path:
            QMessageBox.warning(self, "Warning", "Please select a BDF file first.")
            return

        try:
            self.log(f"Loading BDF file: {bdf_path}")
            self.processor.load_bdf(bdf_path)
            self.log("BDF file loaded successfully.", "success")

            # Display current properties
            self.display_shell_properties()
            self.display_bar_properties()

            self.statusBar.showMessage(f"Loaded: {Path(bdf_path).name}")
            self.update_button_states()

        except BDFProcessorError as e:
            self.log(f"Error loading BDF: {e}", "error")
            QMessageBox.critical(self, "Error", str(e))

    def display_shell_properties(self):
        """Display current shell properties in the table."""
        self.shell_table.clear_data()
        shell_props = self.processor.get_shell_properties()

        for pid, props in sorted(shell_props.items()):
            self.shell_table.add_row([
                str(pid),
                f"{props['thickness']:.6g}",
                str(props['material_id']),
                f"{props['nsm']:.6g}"
            ])

        self.log(f"Found {len(shell_props)} PSHELL properties")

    def display_bar_properties(self):
        """Display current bar properties in the table."""
        self.bar_table.clear_data()
        bar_props = self.processor.get_bar_properties()

        for pid, props in sorted(bar_props.items()):
            dims_str = "×".join(f"{d:.6g}" for d in props['dimensions'])
            self.bar_table.add_row([
                str(pid),
                props['bar_type'],
                dims_str,
                str(props['material_id']),
                props['group']
            ])

        self.log(f"Found {len(bar_props)} PBARL properties")

    def load_csv_files(self):
        """Load and parse CSV files."""
        self.shell_updates = []
        self.bar_updates = []

        # Load shell CSV
        shell_csv_path = self.shell_csv_widget.get_path()
        if shell_csv_path:
            try:
                self.log(f"Loading shell CSV: {shell_csv_path}")
                self.shell_updates = BDFProcessor.parse_shell_csv(shell_csv_path)
                self.log(f"Loaded {len(self.shell_updates)} shell property updates", "success")
            except CSVParseError as e:
                self.log(f"Error parsing shell CSV: {e}", "error")
                QMessageBox.warning(self, "CSV Parse Error", str(e))

        # Load bar CSV
        bar_csv_path = self.bar_csv_widget.get_path()
        if bar_csv_path:
            try:
                self.log(f"Loading bar CSV: {bar_csv_path}")
                self.bar_updates = BDFProcessor.parse_bar_csv(bar_csv_path)
                self.log(f"Loaded {len(self.bar_updates)} bar property updates", "success")
            except CSVParseError as e:
                self.log(f"Error parsing bar CSV: {e}", "error")
                QMessageBox.warning(self, "CSV Parse Error", str(e))

        if not self.shell_updates and not self.bar_updates:
            QMessageBox.information(
                self, "Info",
                "No property updates loaded. Please check your CSV files."
            )

        self.update_button_states()

    def preview_changes(self):
        """Preview changes without applying them."""
        if self.processor.bdf is None:
            QMessageBox.warning(self, "Warning", "Please load a BDF file first.")
            return

        self.shell_preview_table.clear_data()
        self.bar_preview_table.clear_data()

        try:
            previews = self.processor.preview_changes(
                self.shell_updates,
                self.bar_updates
            )

            for preview in previews:
                if preview['property_type'] == 'PSHELL':
                    if preview['status'] == 'valid':
                        change = preview['change']
                        change_str = f"{'+' if change >= 0 else ''}{change:.6g}"
                        self.shell_preview_table.add_row([
                            str(preview['property_id']),
                            f"{preview['current_thickness']:.6g}",
                            f"{preview['new_thickness']:.6g}",
                            change_str,
                            "OK"
                        ], QColor(200, 255, 200))
                    else:
                        self.shell_preview_table.add_row([
                            str(preview['property_id']),
                            "-",
                            "-",
                            "-",
                            preview.get('error', 'Error')
                        ], QColor(255, 200, 200))

                elif preview['property_type'] == 'PBARL':
                    if preview['status'] == 'valid':
                        curr_w = preview.get('current_width', 0) or 0
                        curr_h = preview.get('current_height', 0) or 0
                        self.bar_preview_table.add_row([
                            str(preview['property_id']),
                            f"{curr_w:.6g}×{curr_h:.6g}",
                            f"{preview['new_width']:.6g}×{preview['new_height']:.6g}",
                            "OK"
                        ], QColor(200, 255, 200))
                    else:
                        self.bar_preview_table.add_row([
                            str(preview['property_id']),
                            "-",
                            "-",
                            preview.get('error', 'Error')
                        ], QColor(255, 200, 200))

            self.tabs.setCurrentIndex(1)  # Switch to preview tab
            self.log("Preview generated successfully", "success")

        except Exception as e:
            self.log(f"Error generating preview: {e}", "error")
            QMessageBox.critical(self, "Error", str(e))

    def apply_changes(self):
        """Apply changes and save the BDF file."""
        if self.processor.bdf is None:
            QMessageBox.warning(self, "Warning", "Please load a BDF file first.")
            return

        if not self.shell_updates and not self.bar_updates:
            QMessageBox.warning(self, "Warning", "No updates to apply.")
            return

        # Ask for output file
        default_path = str(self.processor.bdf_path)
        base, ext = os.path.splitext(default_path)
        suggested_path = f"{base}_updated{ext}"

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Updated BDF",
            suggested_path,
            "BDF Files (*.bdf *.dat *.nas);;All Files (*)"
        )

        if not output_path:
            return

        # Confirm overwrite if same file
        if output_path == default_path:
            reply = QMessageBox.question(
                self, "Confirm Overwrite",
                "This will overwrite the original file. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Disable buttons during processing
        self.apply_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Clear previous results
        self.processor.clear_results()

        # Start worker thread
        self.worker = UpdateWorker(
            self.processor,
            self.shell_updates,
            self.bar_updates,
            output_path,
            self.write_bdfs_checkbox.isChecked()
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, value: int, message: str):
        """Handle progress updates from worker thread."""
        self.progress_bar.setValue(value)
        self.statusBar.showMessage(message)
        self.log(message)

    def on_finished(self, success: bool, message: str):
        """Handle completion of worker thread."""
        self.progress_bar.setVisible(False)
        self.update_button_states()

        if success:
            self.log(message, "success")
            self.statusBar.showMessage("Update complete!")

            # Show summary
            summary = self.processor.get_update_summary()
            summary_msg = (
                f"Update Complete!\n\n"
                f"Total updates: {summary['total_updates']}\n"
                f"Successful: {summary['successful']}\n"
                f"Failed: {summary['failed']}\n\n"
                f"Shell updates: {summary['shell_updates']['successful']}/"
                f"{summary['shell_updates']['total']}\n"
                f"Bar updates: {summary['bar_updates']['successful']}/"
                f"{summary['bar_updates']['total']}"
            )

            if summary['failed'] > 0:
                summary_msg += "\n\nFailed updates:\n"
                for detail in summary['failed_details']:
                    summary_msg += f"  - {detail['type']} {detail['property_id']}: {detail['error']}\n"

            QMessageBox.information(self, "Update Complete", summary_msg)

        else:
            self.log(f"Error: {message}", "error")
            self.statusBar.showMessage("Update failed!")
            QMessageBox.critical(self, "Error", f"Update failed: {message}")

    def update_button_states(self):
        """Update button enabled states based on current state."""
        has_bdf = self.processor.bdf is not None
        has_updates = bool(self.shell_updates or self.bar_updates)

        self.preview_btn.setEnabled(has_bdf and has_updates)
        self.apply_btn.setEnabled(has_bdf and has_updates)

    def reset_all(self):
        """Reset all state."""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "This will clear all loaded data. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.processor = BDFProcessor()
        self.shell_updates = []
        self.bar_updates = []

        self.bdf_file_widget.clear()
        self.shell_csv_widget.clear()
        self.bar_csv_widget.clear()

        self.shell_table.clear_data()
        self.bar_table.clear_data()
        self.shell_preview_table.clear_data()
        self.bar_preview_table.clear_data()

        self.log_text.clear()
        self.log("Application reset")

        self.update_button_states()
        self.statusBar.showMessage("Ready")


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Set application metadata
    app.setApplicationName("BDF Property Updater")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BDF Tools")

    # Set application icon (appears in taskbar and window decorations)
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)

    # Create and show main window
    window = BDFUpdaterMainWindow()
    window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
