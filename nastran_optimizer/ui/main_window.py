#!/usr/bin/env python3
"""
Main Window for SOL200 Optimizer.

Provides the primary user interface for setting up and running
MSC Nastran SOL200 optimization with frequency response objectives.

Features:
- Guided workflow with step-by-step panels
- Real-time validation and feedback
- Interactive property selection
- Results visualization
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFileDialog, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QTextEdit, QProgressBar, QSplitter, QFrame,
    QTabWidget, QScrollArea, QCheckBox, QStatusBar, QToolBar,
    QMenu, QMenuBar, QDialog, QFormLayout, QDialogButtonBox,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QPalette

from ..core import (
    OptimizationModel, BDFManager, DesignVariable, DesignVariableLink,
    DesignResponse, DesignConstraint, ObjectiveFunction, ObjectiveType,
    PropertyType, PropertyField, ResponseType, ModelValidator
)
from .styles.modern_style import ModernStyle


class WorkflowStep:
    """Enumeration of workflow steps."""
    MODEL = 0
    DESIGN_VARIABLES = 1
    RESPONSES = 2
    CONSTRAINTS = 3
    OBJECTIVE = 4
    VALIDATE = 5
    RUN = 6
    RESULTS = 7


class StepIndicator(QFrame):
    """Visual indicator for workflow progress."""

    def __init__(self, steps: List[str], parent=None):
        super().__init__(parent)
        self.steps = steps
        self.current_step = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)

        self.step_widgets = []

        for i, step_name in enumerate(self.steps):
            step_widget = QFrame()
            step_layout = QVBoxLayout(step_widget)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Step number circle
            circle = QLabel(str(i + 1))
            circle.setFixedSize(32, 32)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setProperty("step_circle", True)
            circle.setStyleSheet("""
                QLabel[step_circle="true"] {
                    background-color: #E0E0E0;
                    border-radius: 16px;
                    font-weight: bold;
                }
            """)

            # Step name
            name = QLabel(step_name)
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet("font-size: 11px; color: #757575;")

            step_layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)

            self.step_widgets.append((step_widget, circle, name))
            layout.addWidget(step_widget)

            # Add connector line (except for last)
            if i < len(self.steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet("background-color: #E0E0E0;")
                layout.addWidget(line, 1)

        self._update_appearance()

    def set_current_step(self, step: int):
        """Set the current workflow step."""
        self.current_step = step
        self._update_appearance()

    def _update_appearance(self):
        """Update visual appearance based on current step."""
        for i, (widget, circle, name) in enumerate(self.step_widgets):
            if i < self.current_step:
                # Completed
                circle.setStyleSheet("""
                    QLabel {
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 16px;
                        font-weight: bold;
                    }
                """)
                name.setStyleSheet("font-size: 11px; color: #4CAF50; font-weight: bold;")
            elif i == self.current_step:
                # Current
                circle.setStyleSheet("""
                    QLabel {
                        background-color: #2196F3;
                        color: white;
                        border-radius: 16px;
                        font-weight: bold;
                    }
                """)
                name.setStyleSheet("font-size: 11px; color: #2196F3; font-weight: bold;")
            else:
                # Future
                circle.setStyleSheet("""
                    QLabel {
                        background-color: #E0E0E0;
                        color: #757575;
                        border-radius: 16px;
                        font-weight: bold;
                    }
                """)
                name.setStyleSheet("font-size: 11px; color: #757575;")


class ModelPanel(QFrame):
    """Panel for loading and viewing the BDF model."""

    model_loaded = pyqtSignal(str)

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("1. Load Nastran Model")
        header.setProperty("heading", True)
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Load your MSC Nastran BDF file. The model should contain the structural "
            "elements and properties that will be optimized."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # File selection
        file_group = QGroupBox("BDF File")
        file_layout = QHBoxLayout(file_group)

        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select a BDF file...")
        self.file_path.setReadOnly(True)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)

        file_layout.addWidget(self.file_path, 1)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_group)

        # Model summary
        summary_group = QGroupBox("Model Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.summary_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setMaximumHeight(200)

        summary_layout.addWidget(self.summary_table)
        layout.addWidget(summary_group)

        # Properties preview
        props_group = QGroupBox("Designable Properties")
        props_layout = QVBoxLayout(props_group)

        self.props_tree = QTreeWidget()
        self.props_tree.setHeaderLabels(["Property", "Type", "Elements", "Current Value"])
        self.props_tree.setAlternatingRowColors(True)

        props_layout.addWidget(self.props_tree)
        layout.addWidget(props_group, 1)

    def _browse_file(self):
        """Open file browser for BDF selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Nastran BDF File",
            "",
            "BDF Files (*.bdf *.dat *.nas);;All Files (*)"
        )

        if file_path:
            self._load_model(file_path)

    def _load_model(self, file_path: str):
        """Load the selected BDF file."""
        try:
            summary = self.opt_model.load_bdf(file_path)
            self.file_path.setText(file_path)
            self._update_summary(summary)
            self._update_properties()
            self.model_loaded.emit(file_path)
        except Exception as e:
            QMessageBox.critical(
                self, "Load Error",
                f"Failed to load BDF file:\n{str(e)}"
            )

    def _update_summary(self, summary):
        """Update the model summary table."""
        data = [
            ("File", Path(summary.filename).name),
            ("Nodes", str(summary.num_nodes)),
            ("Elements", str(summary.num_elements)),
            ("Properties", str(summary.num_properties)),
            ("Materials", str(summary.num_materials)),
            ("Has SPC", "Yes" if summary.has_spc else "No"),
            ("Has Loads", "Yes" if summary.has_loads else "No"),
            ("Has Freq Cards", "Yes" if summary.has_frequency_cards else "No"),
        ]

        self.summary_table.setRowCount(len(data))
        for row, (prop, value) in enumerate(data):
            self.summary_table.setItem(row, 0, QTableWidgetItem(prop))
            self.summary_table.setItem(row, 1, QTableWidgetItem(value))

    def _update_properties(self):
        """Update the properties tree."""
        self.props_tree.clear()

        designable = self.opt_model.bdf_manager.get_designable_properties()

        for prop in designable:
            item = QTreeWidgetItem([
                f"PID {prop['id']}",
                prop['type'],
                str(prop['element_count']),
                ""
            ])

            for field in prop['fields']:
                value_str = f"{field['current_value']:.6g}" if field['current_value'] else "N/A"
                child = QTreeWidgetItem([
                    field['name'],
                    field['description'],
                    "",
                    value_str
                ])
                item.addChild(child)

            self.props_tree.addTopLevelItem(item)

        self.props_tree.expandAll()


class DesignVariablePanel(QFrame):
    """Panel for defining design variables."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("2. Define Design Variables")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Select which property values should be optimized. Each design variable "
            "needs bounds that define the allowed range of values."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Splitter for properties and variables
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Available properties
        props_frame = QFrame()
        props_layout = QVBoxLayout(props_frame)
        props_layout.setContentsMargins(0, 0, 0, 0)

        props_label = QLabel("Available Properties")
        props_label.setStyleSheet("font-weight: bold;")
        props_layout.addWidget(props_label)

        self.available_props = QTreeWidget()
        self.available_props.setHeaderLabels(["Property", "Field", "Current"])
        self.available_props.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        props_layout.addWidget(self.available_props)

        add_btn = QPushButton("Add as Design Variable →")
        add_btn.clicked.connect(self._add_design_variable)
        props_layout.addWidget(add_btn)

        splitter.addWidget(props_frame)

        # Right: Design variables
        dv_frame = QFrame()
        dv_layout = QVBoxLayout(dv_frame)
        dv_layout.setContentsMargins(0, 0, 0, 0)

        dv_label = QLabel("Design Variables")
        dv_label.setStyleSheet("font-weight: bold;")
        dv_layout.addWidget(dv_label)

        self.dv_table = QTableWidget()
        self.dv_table.setColumnCount(6)
        self.dv_table.setHorizontalHeaderLabels([
            "Label", "Property", "Field", "Initial", "Lower", "Upper"
        ])
        self.dv_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        dv_layout.addWidget(self.dv_table)

        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit Bounds")
        edit_btn.clicked.connect(self._edit_bounds)
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("danger", True)
        remove_btn.clicked.connect(self._remove_design_variable)

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        dv_layout.addLayout(btn_layout)

        splitter.addWidget(dv_frame)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter, 1)

    def refresh(self):
        """Refresh the available properties list."""
        self.available_props.clear()

        if not self.opt_model.bdf_manager.is_loaded:
            return

        designable = self.opt_model.bdf_manager.get_designable_properties()

        for prop in designable:
            prop_item = QTreeWidgetItem([
                f"PID {prop['id']} ({prop['type']})",
                "",
                ""
            ])
            prop_item.setData(0, Qt.ItemDataRole.UserRole, prop)

            for field in prop['fields']:
                value_str = f"{field['current_value']:.6g}" if field['current_value'] else "N/A"
                field_item = QTreeWidgetItem([
                    "",
                    field['name'],
                    value_str
                ])
                field_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'property': prop,
                    'field': field
                })
                prop_item.addChild(field_item)

            self.available_props.addTopLevelItem(prop_item)

        self.available_props.expandAll()
        self._refresh_dv_table()

    def _add_design_variable(self):
        """Add selected properties as design variables."""
        selected = self.available_props.selectedItems()

        for item in selected:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and 'field' in data:
                prop = data['property']
                field = data['field']

                # Create design variable with default bounds
                initial = field['current_value'] or 0.001
                lower = initial * 0.5
                upper = initial * 2.0

                label = f"{prop['type'][:2]}{prop['id']}"[:8]

                dv = self.opt_model.add_design_variable(
                    label=label,
                    initial_value=initial,
                    lower_bound=lower,
                    upper_bound=upper,
                    description=f"{prop['type']} {prop['id']} {field['name']}",
                )

                # Link to property
                prop_type = PropertyType[prop['type']]
                field_enum = self._get_field_enum(prop['type'], field['name'])

                if field_enum:
                    self.opt_model.link_variable_to_property(
                        design_variable=dv,
                        property_type=prop_type,
                        property_id=prop['id'],
                        field=field_enum,
                    )

        self._refresh_dv_table()

    def _get_field_enum(self, prop_type: str, field_name: str) -> Optional[PropertyField]:
        """Get PropertyField enum for a field name."""
        mapping = {
            ('PSHELL', 'T'): PropertyField.PSHELL_T,
            ('PBAR', 'A'): PropertyField.PBAR_A,
            ('PBAR', 'I1'): PropertyField.PBAR_I1,
            ('PBAR', 'I2'): PropertyField.PBAR_I2,
            ('PBAR', 'J'): PropertyField.PBAR_J,
            ('PBARL', 'DIM1'): PropertyField.PBARL_DIM1,
            ('PBARL', 'DIM2'): PropertyField.PBARL_DIM2,
            ('PROD', 'A'): PropertyField.PROD_A,
            ('PROD', 'J'): PropertyField.PROD_J,
        }
        return mapping.get((prop_type, field_name))

    def _refresh_dv_table(self):
        """Refresh the design variables table."""
        self.dv_table.setRowCount(len(self.opt_model.design_variables))

        for row, (dv_id, dv) in enumerate(self.opt_model.design_variables.items()):
            self.dv_table.setItem(row, 0, QTableWidgetItem(dv.label))
            self.dv_table.setItem(row, 1, QTableWidgetItem(str(dv_id)))
            self.dv_table.setItem(row, 2, QTableWidgetItem(dv.description))
            self.dv_table.setItem(row, 3, QTableWidgetItem(f"{dv.initial_value:.6g}"))
            self.dv_table.setItem(row, 4, QTableWidgetItem(f"{dv.lower_bound:.6g}"))
            self.dv_table.setItem(row, 5, QTableWidgetItem(f"{dv.upper_bound:.6g}"))

    def _edit_bounds(self):
        """Edit bounds for selected design variable."""
        row = self.dv_table.currentRow()
        if row < 0:
            return

        dv_id = int(self.dv_table.item(row, 1).text())
        dv = self.opt_model.design_variables.get(dv_id)

        if dv:
            dialog = BoundsDialog(dv, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                dv.lower_bound = dialog.lower_spin.value()
                dv.upper_bound = dialog.upper_spin.value()
                dv.initial_value = dialog.initial_spin.value()
                self._refresh_dv_table()

    def _remove_design_variable(self):
        """Remove selected design variable."""
        row = self.dv_table.currentRow()
        if row < 0:
            return

        dv_id = int(self.dv_table.item(row, 1).text())
        if dv_id in self.opt_model.design_variables:
            del self.opt_model.design_variables[dv_id]
            self._refresh_dv_table()


class BoundsDialog(QDialog):
    """Dialog for editing design variable bounds."""

    def __init__(self, dv: DesignVariable, parent=None):
        super().__init__(parent)
        self.dv = dv
        self.setWindowTitle(f"Edit Bounds - {dv.label}")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.lower_spin = QDoubleSpinBox()
        self.lower_spin.setRange(0, 1e10)
        self.lower_spin.setDecimals(6)
        self.lower_spin.setValue(self.dv.lower_bound)

        self.upper_spin = QDoubleSpinBox()
        self.upper_spin.setRange(0, 1e10)
        self.upper_spin.setDecimals(6)
        self.upper_spin.setValue(self.dv.upper_bound)

        self.initial_spin = QDoubleSpinBox()
        self.initial_spin.setRange(0, 1e10)
        self.initial_spin.setDecimals(6)
        self.initial_spin.setValue(self.dv.initial_value)

        layout.addRow("Lower Bound:", self.lower_spin)
        layout.addRow("Upper Bound:", self.upper_spin)
        layout.addRow("Initial Value:", self.initial_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class ResponsePanel(QFrame):
    """Panel for defining design responses."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("3. Define Design Responses")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Design responses are the output quantities that will be used in "
            "constraints or objectives. For SOL111, these are typically frequency "
            "response accelerations or displacements."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Quick setup buttons
        quick_group = QGroupBox("Quick Setup Templates")
        quick_layout = QHBoxLayout(quick_group)

        accel_btn = QPushButton("Add Acceleration Response")
        accel_btn.setProperty("accent", True)
        accel_btn.clicked.connect(lambda: self._show_response_dialog(ResponseType.FRACCL))
        quick_layout.addWidget(accel_btn)

        disp_btn = QPushButton("Add Displacement Response")
        disp_btn.clicked.connect(lambda: self._show_response_dialog(ResponseType.FRDISP))
        quick_layout.addWidget(disp_btn)

        weight_btn = QPushButton("Add Weight Response")
        weight_btn.clicked.connect(lambda: self._show_response_dialog(ResponseType.WEIGHT))
        quick_layout.addWidget(weight_btn)

        layout.addWidget(quick_group)

        # Responses table
        resp_group = QGroupBox("Defined Responses")
        resp_layout = QVBoxLayout(resp_group)

        self.resp_table = QTableWidget()
        self.resp_table.setColumnCount(6)
        self.resp_table.setHorizontalHeaderLabels([
            "ID", "Label", "Type", "Description", "Region", "Component"
        ])
        self.resp_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.resp_table.setAlternatingRowColors(True)
        resp_layout.addWidget(self.resp_table)

        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_response)
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("danger", True)
        remove_btn.clicked.connect(self._remove_response)

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        resp_layout.addLayout(btn_layout)

        layout.addWidget(resp_group, 1)

        # RMS Setup Section
        rms_group = QGroupBox("RMS Response Setup (for multiple frequency points)")
        rms_layout = QVBoxLayout(rms_group)

        rms_desc = QLabel(
            "Create an RMS (Root Mean Square) response combining multiple frequency points. "
            "This is typical for broadband vibration optimization."
        )
        rms_desc.setWordWrap(True)
        rms_layout.addWidget(rms_desc)

        rms_btn = QPushButton("Setup RMS Acceleration Response...")
        rms_btn.setProperty("accent", True)
        rms_btn.clicked.connect(self._setup_rms_response)
        rms_layout.addWidget(rms_btn)

        layout.addWidget(rms_group)

    def refresh(self):
        """Refresh the responses table."""
        self.resp_table.setRowCount(len(self.opt_model.responses))

        for row, (resp_id, resp) in enumerate(self.opt_model.responses.items()):
            self.resp_table.setItem(row, 0, QTableWidgetItem(str(resp_id)))
            self.resp_table.setItem(row, 1, QTableWidgetItem(resp.label))
            self.resp_table.setItem(row, 2, QTableWidgetItem(resp.response_type.name))
            self.resp_table.setItem(row, 3, QTableWidgetItem(resp.description))
            self.resp_table.setItem(row, 4, QTableWidgetItem(str(resp.region or "")))
            self.resp_table.setItem(row, 5, QTableWidgetItem(str(resp.component or "")))

    def _show_response_dialog(self, resp_type: ResponseType):
        """Show dialog to add a new response."""
        dialog = ResponseDialog(self.opt_model, resp_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_response(self):
        """Edit selected response."""
        row = self.resp_table.currentRow()
        if row < 0:
            return
        resp_id = int(self.resp_table.item(row, 0).text())
        resp = self.opt_model.responses.get(resp_id)
        if resp:
            dialog = ResponseDialog(self.opt_model, resp.response_type, self, resp)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh()

    def _remove_response(self):
        """Remove selected response."""
        row = self.resp_table.currentRow()
        if row < 0:
            return
        resp_id = int(self.resp_table.item(row, 0).text())
        if resp_id in self.opt_model.responses:
            del self.opt_model.responses[resp_id]
            self.refresh()

    def _setup_rms_response(self):
        """Setup RMS response combining multiple points."""
        dialog = RMSSetupDialog(self.opt_model, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()


class ResponseDialog(QDialog):
    """Dialog for adding/editing a design response."""

    def __init__(self, opt_model: OptimizationModel, resp_type: ResponseType,
                 parent=None, existing: DesignResponse = None):
        super().__init__(parent)
        self.opt_model = opt_model
        self.resp_type = resp_type
        self.existing = existing
        self.setWindowTitle("Add Response" if not existing else "Edit Response")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.label_edit = QLineEdit()
        self.label_edit.setMaxLength(8)
        self.label_edit.setPlaceholderText("e.g., ACCL1")
        layout.addRow("Label (max 8 chars):", self.label_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Description of response")
        layout.addRow("Description:", self.desc_edit)

        # Type-specific fields
        if self.resp_type in (ResponseType.FRACCL, ResponseType.FRDISP):
            self.node_spin = QSpinBox()
            self.node_spin.setRange(1, 99999999)
            layout.addRow("Node ID:", self.node_spin)

            self.comp_combo = QComboBox()
            self.comp_combo.addItems(["1 (X)", "2 (Y)", "3 (Z)", "4 (RX)", "5 (RY)", "6 (RZ)"])
            layout.addRow("Component:", self.comp_combo)

            self.freq_spin = QDoubleSpinBox()
            self.freq_spin.setRange(0.001, 10000)
            self.freq_spin.setDecimals(3)
            self.freq_spin.setValue(100.0)
            layout.addRow("Frequency (Hz):", self.freq_spin)

        if self.existing:
            self.label_edit.setText(self.existing.label)
            self.desc_edit.setText(self.existing.description)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        """Validate and accept."""
        label = self.label_edit.text().strip()
        if not label:
            QMessageBox.warning(self, "Validation", "Label is required")
            return

        if self.existing:
            self.existing.label = label
            self.existing.description = self.desc_edit.text()
        else:
            resp = DesignResponse(
                label=label,
                response_type=self.resp_type,
                description=self.desc_edit.text(),
            )
            if self.resp_type in (ResponseType.FRACCL, ResponseType.FRDISP):
                resp.region = self.node_spin.value()
                resp.component = self.comp_combo.currentIndex() + 1
                resp.atta = self.freq_spin.value()
            self.opt_model.add_response(resp)

        self.accept()


class RMSSetupDialog(QDialog):
    """Dialog for setting up RMS response."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self.setWindowTitle("RMS Acceleration Response Setup")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        desc = QLabel(
            "This will create individual DRESP1 cards for each frequency point "
            "and a DRESP2 card that computes the RMS value."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()

        self.label_edit = QLineEdit("RMSACC")
        form.addRow("RMS Response Label:", self.label_edit)

        self.node_spin = QSpinBox()
        self.node_spin.setRange(1, 99999999)
        form.addRow("Node ID:", self.node_spin)

        self.comp_combo = QComboBox()
        self.comp_combo.addItems(["3 (Z - Vertical)"])
        form.addRow("Component:", self.comp_combo)

        layout.addLayout(form)

        # Frequency range
        freq_group = QGroupBox("Frequency Range")
        freq_layout = QFormLayout(freq_group)

        self.freq_min = QDoubleSpinBox()
        self.freq_min.setRange(0.1, 10000)
        self.freq_min.setValue(20.0)
        freq_layout.addRow("Min Frequency (Hz):", self.freq_min)

        self.freq_max = QDoubleSpinBox()
        self.freq_max.setRange(0.1, 10000)
        self.freq_max.setValue(2000.0)
        freq_layout.addRow("Max Frequency (Hz):", self.freq_max)

        self.num_points = QSpinBox()
        self.num_points.setRange(3, 100)
        self.num_points.setValue(10)
        freq_layout.addRow("Number of Points:", self.num_points)

        layout.addWidget(freq_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        """Create the RMS response setup."""
        import numpy as np

        label = self.label_edit.text().strip()[:8]
        node_id = self.node_spin.value()
        component = 3  # Z direction

        freq_min = self.freq_min.value()
        freq_max = self.freq_max.value()
        num_points = self.num_points.value()

        # Create logarithmically spaced frequency points
        frequencies = np.logspace(np.log10(freq_min), np.log10(freq_max), num_points)

        # Create DRESP1 for each frequency point
        dresp1_ids = []
        for i, freq in enumerate(frequencies):
            resp = DesignResponse(
                label=f"A{i+1:03d}",
                response_type=ResponseType.FRACCL,
                description=f"Accel at {freq:.1f} Hz",
                region=node_id,
                component=component,
                atta=freq,
            )
            resp_id = self.opt_model.add_response(resp)
            dresp1_ids.append(resp_id)

        # Create DRESP2 for RMS
        rms_resp = DesignResponse(
            label=label,
            response_type=ResponseType.DRESP2,
            description=f"RMS Acceleration {freq_min:.0f}-{freq_max:.0f} Hz",
            dresp1_refs=dresp1_ids,
        )
        self.opt_model.add_response(rms_resp)

        self.accept()


class ConstraintPanel(QFrame):
    """Panel for defining design constraints."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("4. Define Design Constraints")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Design constraints limit the response values during optimization. "
            "Common constraints include maximum stress, minimum thickness, "
            "and maximum weight."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Add constraint button
        add_btn = QPushButton("+ Add Constraint")
        add_btn.setProperty("accent", True)
        add_btn.clicked.connect(self._show_constraint_dialog)
        layout.addWidget(add_btn)

        # Constraints table
        const_group = QGroupBox("Defined Constraints")
        const_layout = QVBoxLayout(const_group)

        self.const_table = QTableWidget()
        self.const_table.setColumnCount(6)
        self.const_table.setHorizontalHeaderLabels([
            "ID", "Response", "Lower Bound", "Upper Bound", "Type", "Status"
        ])
        self.const_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.const_table.setAlternatingRowColors(True)
        const_layout.addWidget(self.const_table)

        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_constraint)
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("danger", True)
        remove_btn.clicked.connect(self._remove_constraint)

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        const_layout.addLayout(btn_layout)

        layout.addWidget(const_group, 1)

        # Tips
        tips_group = QGroupBox("Common Constraint Patterns")
        tips_layout = QVBoxLayout(tips_group)

        tips = QLabel(
            "• Weight constraint: Limit total structural weight\n"
            "• Thickness constraint: Ensure minimum gauge requirements\n"
            "• Stress constraint: Keep stresses below allowable limits\n"
            "• Frequency constraint: Avoid resonance frequencies"
        )
        tips.setStyleSheet("color: #616161;")
        tips_layout.addWidget(tips)
        layout.addWidget(tips_group)

    def refresh(self):
        """Refresh the constraints table."""
        self.const_table.setRowCount(len(self.opt_model.constraints))

        for row, (const_id, const) in enumerate(self.opt_model.constraints.items()):
            self.const_table.setItem(row, 0, QTableWidgetItem(str(const_id)))

            # Get response label
            resp_label = ""
            if const.response_id in self.opt_model.responses:
                resp_label = self.opt_model.responses[const.response_id].label
            self.const_table.setItem(row, 1, QTableWidgetItem(resp_label))

            lower = f"{const.lower_bound:.6g}" if const.lower_bound is not None else "-"
            upper = f"{const.upper_bound:.6g}" if const.upper_bound is not None else "-"
            self.const_table.setItem(row, 2, QTableWidgetItem(lower))
            self.const_table.setItem(row, 3, QTableWidgetItem(upper))

            # Constraint type
            if const.lower_bound is not None and const.upper_bound is not None:
                ctype = "Range"
            elif const.lower_bound is not None:
                ctype = "Lower"
            else:
                ctype = "Upper"
            self.const_table.setItem(row, 4, QTableWidgetItem(ctype))

            # Status
            status_item = QTableWidgetItem("Pending")
            status_item.setForeground(QColor("#757575"))
            self.const_table.setItem(row, 5, status_item)

    def _show_constraint_dialog(self):
        """Show dialog to add a new constraint."""
        dialog = ConstraintDialog(self.opt_model, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_constraint(self):
        """Edit selected constraint."""
        row = self.const_table.currentRow()
        if row < 0:
            return
        const_id = int(self.const_table.item(row, 0).text())
        const = self.opt_model.constraints.get(const_id)
        if const:
            dialog = ConstraintDialog(self.opt_model, self, const)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh()

    def _remove_constraint(self):
        """Remove selected constraint."""
        row = self.const_table.currentRow()
        if row < 0:
            return
        const_id = int(self.const_table.item(row, 0).text())
        if const_id in self.opt_model.constraints:
            del self.opt_model.constraints[const_id]
            self.refresh()


class ConstraintDialog(QDialog):
    """Dialog for adding/editing a design constraint."""

    def __init__(self, opt_model: OptimizationModel, parent=None,
                 existing: DesignConstraint = None):
        super().__init__(parent)
        self.opt_model = opt_model
        self.existing = existing
        self.setWindowTitle("Add Constraint" if not existing else "Edit Constraint")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        # Response selection
        self.resp_combo = QComboBox()
        for resp_id, resp in self.opt_model.responses.items():
            self.resp_combo.addItem(f"{resp.label} (ID: {resp_id})", resp_id)
        layout.addRow("Response:", self.resp_combo)

        # Bounds
        self.lower_check = QCheckBox("Lower bound")
        self.lower_spin = QDoubleSpinBox()
        self.lower_spin.setRange(-1e20, 1e20)
        self.lower_spin.setDecimals(6)
        self.lower_spin.setEnabled(False)
        self.lower_check.toggled.connect(self.lower_spin.setEnabled)

        lower_layout = QHBoxLayout()
        lower_layout.addWidget(self.lower_check)
        lower_layout.addWidget(self.lower_spin, 1)
        layout.addRow("", lower_layout)

        self.upper_check = QCheckBox("Upper bound")
        self.upper_spin = QDoubleSpinBox()
        self.upper_spin.setRange(-1e20, 1e20)
        self.upper_spin.setDecimals(6)
        self.upper_spin.setEnabled(False)
        self.upper_check.toggled.connect(self.upper_spin.setEnabled)

        upper_layout = QHBoxLayout()
        upper_layout.addWidget(self.upper_check)
        upper_layout.addWidget(self.upper_spin, 1)
        layout.addRow("", upper_layout)

        if self.existing:
            # Find response in combo
            for i in range(self.resp_combo.count()):
                if self.resp_combo.itemData(i) == self.existing.response_id:
                    self.resp_combo.setCurrentIndex(i)
                    break
            if self.existing.lower_bound is not None:
                self.lower_check.setChecked(True)
                self.lower_spin.setValue(self.existing.lower_bound)
            if self.existing.upper_bound is not None:
                self.upper_check.setChecked(True)
                self.upper_spin.setValue(self.existing.upper_bound)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        """Validate and accept."""
        if not self.lower_check.isChecked() and not self.upper_check.isChecked():
            QMessageBox.warning(self, "Validation", "At least one bound is required")
            return

        resp_id = self.resp_combo.currentData()
        lower = self.lower_spin.value() if self.lower_check.isChecked() else None
        upper = self.upper_spin.value() if self.upper_check.isChecked() else None

        if self.existing:
            self.existing.response_id = resp_id
            self.existing.lower_bound = lower
            self.existing.upper_bound = upper
        else:
            const = DesignConstraint(
                response_id=resp_id,
                lower_bound=lower,
                upper_bound=upper,
            )
            self.opt_model.add_constraint(const)

        self.accept()


class ObjectivePanel(QFrame):
    """Panel for defining the optimization objective."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("5. Define Objective Function")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Define the objective function to minimize or maximize. For vibration "
            "optimization, this is typically minimizing RMS acceleration."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Objective type
        type_group = QGroupBox("Objective Type")
        type_layout = QVBoxLayout(type_group)

        self.minimize_radio = QCheckBox("Minimize (reduce response)")
        self.minimize_radio.setChecked(True)
        self.maximize_radio = QCheckBox("Maximize (increase response)")

        # Make them mutually exclusive
        self.minimize_radio.toggled.connect(
            lambda checked: self.maximize_radio.setChecked(not checked) if checked else None
        )
        self.maximize_radio.toggled.connect(
            lambda checked: self.minimize_radio.setChecked(not checked) if checked else None
        )

        type_layout.addWidget(self.minimize_radio)
        type_layout.addWidget(self.maximize_radio)
        layout.addWidget(type_group)

        # Response selection
        resp_group = QGroupBox("Select Response for Objective")
        resp_layout = QVBoxLayout(resp_group)

        self.response_list = QListWidget()
        self.response_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        resp_layout.addWidget(self.response_list)

        set_obj_btn = QPushButton("Set as Objective")
        set_obj_btn.setProperty("accent", True)
        set_obj_btn.clicked.connect(self._set_objective)
        resp_layout.addWidget(set_obj_btn)

        layout.addWidget(resp_group)

        # Current objective display
        current_group = QGroupBox("Current Objective")
        current_layout = QVBoxLayout(current_group)

        self.current_obj_label = QLabel("No objective set")
        self.current_obj_label.setStyleSheet("font-size: 14px; padding: 10px;")
        current_layout.addWidget(self.current_obj_label)

        layout.addWidget(current_group)

        # Equation builder for custom objectives
        eq_group = QGroupBox("Custom Equation (Advanced)")
        eq_layout = QVBoxLayout(eq_group)

        eq_desc = QLabel("Define a custom equation combining multiple responses:")
        eq_layout.addWidget(eq_desc)

        self.equation_edit = QLineEdit()
        self.equation_edit.setPlaceholderText("e.g., RMS(R1, R2, R3) = SQRT((R1**2 + R2**2 + R3**2) / 3)")
        eq_layout.addWidget(self.equation_edit)

        validate_btn = QPushButton("Validate Equation")
        validate_btn.clicked.connect(self._validate_equation)
        eq_layout.addWidget(validate_btn)

        layout.addWidget(eq_group)
        layout.addStretch()

    def refresh(self):
        """Refresh the response list."""
        self.response_list.clear()

        for resp_id, resp in self.opt_model.responses.items():
            item = QListWidgetItem(f"{resp.label} (ID: {resp_id}) - {resp.description}")
            item.setData(Qt.ItemDataRole.UserRole, resp_id)
            self.response_list.addItem(item)

        # Update current objective display
        if self.opt_model.objective:
            obj = self.opt_model.objective
            direction = "Minimize" if obj.objective_type == ObjectiveType.MINIMIZE else "Maximize"
            resp = self.opt_model.responses.get(obj.response_id)
            resp_label = resp.label if resp else f"ID {obj.response_id}"
            self.current_obj_label.setText(f"{direction}: {resp_label}")
            self.current_obj_label.setStyleSheet(
                "font-size: 14px; padding: 10px; background-color: #E3F2FD; border-radius: 4px;"
            )
        else:
            self.current_obj_label.setText("No objective set")
            self.current_obj_label.setStyleSheet("font-size: 14px; padding: 10px;")

    def _set_objective(self):
        """Set the selected response as the objective."""
        current_item = self.response_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selection Required", "Please select a response")
            return

        resp_id = current_item.data(Qt.ItemDataRole.UserRole)
        obj_type = ObjectiveType.MINIMIZE if self.minimize_radio.isChecked() else ObjectiveType.MAXIMIZE

        self.opt_model.objective = ObjectiveFunction(
            response_id=resp_id,
            objective_type=obj_type,
        )
        self.refresh()

    def _validate_equation(self):
        """Validate the custom equation."""
        equation = self.equation_edit.text().strip()
        if not equation:
            return

        try:
            parsed = self.opt_model.equation_parser.parse(equation)
            QMessageBox.information(
                self, "Valid Equation",
                f"Equation '{parsed.name}' is valid!\n\n"
                f"Arguments: {', '.join(parsed.arguments)}\n"
                f"Functions used: {', '.join(parsed.functions_used) or 'None'}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Invalid Equation", str(e))


class ValidatePanel(QFrame):
    """Panel for validating the optimization model."""

    validation_complete = pyqtSignal(bool)

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self.validator = ModelValidator()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("6. Validate Model")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Comprehensive validation ensures your optimization model is correctly "
            "configured and ready for execution. All checks must pass before running."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Validation button
        validate_btn = QPushButton("Run Validation Checks")
        validate_btn.setProperty("accent", True)
        validate_btn.clicked.connect(self._run_validation)
        layout.addWidget(validate_btn)

        # Summary
        summary_group = QGroupBox("Validation Summary")
        summary_layout = QHBoxLayout(summary_group)

        self.errors_label = QLabel("Errors: -")
        self.errors_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.warnings_label = QLabel("Warnings: -")
        self.warnings_label.setStyleSheet("font-size: 16px;")
        self.passed_label = QLabel("Passed: -")
        self.passed_label.setStyleSheet("font-size: 16px; color: #4CAF50;")

        summary_layout.addWidget(self.errors_label)
        summary_layout.addWidget(self.warnings_label)
        summary_layout.addWidget(self.passed_label)
        summary_layout.addStretch()

        layout.addWidget(summary_group)

        # Results table
        results_group = QGroupBox("Validation Results")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Category", "Check", "Status", "Message"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group, 1)

        # Status indicator
        self.status_frame = QFrame()
        status_layout = QHBoxLayout(self.status_frame)

        self.status_icon = QLabel()
        self.status_text = QLabel("Run validation to check model")
        self.status_text.setStyleSheet("font-size: 14px;")

        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_text, 1)
        layout.addWidget(self.status_frame)

    def refresh(self):
        """Clear previous validation results."""
        self.results_table.setRowCount(0)
        self.errors_label.setText("Errors: -")
        self.warnings_label.setText("Warnings: -")
        self.passed_label.setText("Passed: -")
        self.status_text.setText("Run validation to check model")

    def _run_validation(self):
        """Run all validation checks."""
        results = self.validator.validate(self.opt_model)

        # Count by severity
        errors = sum(1 for r in results if r.severity == "ERROR")
        warnings = sum(1 for r in results if r.severity == "WARNING")
        passed = sum(1 for r in results if r.severity == "PASS")

        self.errors_label.setText(f"Errors: {errors}")
        self.errors_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {'#F44336' if errors > 0 else '#4CAF50'};"
        )

        self.warnings_label.setText(f"Warnings: {warnings}")
        self.warnings_label.setStyleSheet(
            f"font-size: 16px; color: {'#FF9800' if warnings > 0 else '#757575'};"
        )

        self.passed_label.setText(f"Passed: {passed}")

        # Populate table
        self.results_table.setRowCount(len(results))

        for row, result in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(result.category))
            self.results_table.setItem(row, 1, QTableWidgetItem(result.check_name))

            status_item = QTableWidgetItem(result.severity)
            if result.severity == "ERROR":
                status_item.setForeground(QColor("#F44336"))
            elif result.severity == "WARNING":
                status_item.setForeground(QColor("#FF9800"))
            else:
                status_item.setForeground(QColor("#4CAF50"))
            self.results_table.setItem(row, 2, status_item)

            self.results_table.setItem(row, 3, QTableWidgetItem(result.message))

        # Update status
        if errors > 0:
            self.status_text.setText("Model has errors - please fix before running")
            self.status_text.setStyleSheet("font-size: 14px; color: #F44336; font-weight: bold;")
            self.validation_complete.emit(False)
        elif warnings > 0:
            self.status_text.setText("Model validated with warnings - review before running")
            self.status_text.setStyleSheet("font-size: 14px; color: #FF9800;")
            self.validation_complete.emit(True)
        else:
            self.status_text.setText("Model validated successfully - ready to run!")
            self.status_text.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")
            self.validation_complete.emit(True)


class RunPanel(QFrame):
    """Panel for running Nastran optimization."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self.runner = None
        self.run_thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("7. Run Optimization")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "Configure and execute the MSC Nastran SOL200 optimization. "
            "Ensure Nastran is installed and accessible."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Nastran settings
        nastran_group = QGroupBox("Nastran Settings")
        nastran_layout = QFormLayout(nastran_group)

        self.nastran_path = QLineEdit()
        self.nastran_path.setPlaceholderText("Auto-detect or specify path...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_nastran)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.nastran_path, 1)
        path_layout.addWidget(browse_btn)
        nastran_layout.addRow("Nastran Executable:", path_layout)

        self.memory_combo = QComboBox()
        self.memory_combo.addItems(["2gb", "4gb", "8gb", "16gb", "32gb"])
        self.memory_combo.setCurrentText("4gb")
        nastran_layout.addRow("Memory:", self.memory_combo)

        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 64)
        self.parallel_spin.setValue(4)
        nastran_layout.addRow("Parallel CPUs:", self.parallel_spin)

        layout.addWidget(nastran_group)

        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Same as BDF file location")
        output_layout.addRow("Output Directory:", self.output_dir)

        self.export_btn = QPushButton("Export SOL200 BDF Only")
        self.export_btn.clicked.connect(self._export_bdf)
        output_layout.addRow("", self.export_btn)

        layout.addWidget(output_group)

        # Run controls
        run_group = QGroupBox("Execution")
        run_layout = QVBoxLayout(run_group)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Start Optimization")
        self.run_btn.setProperty("accent", True)
        self.run_btn.clicked.connect(self._start_run)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("danger", True)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_run)

        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        run_layout.addLayout(btn_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        run_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to run optimization")
        run_layout.addWidget(self.status_label)

        layout.addWidget(run_group)

        # Log output
        log_group = QGroupBox("Execution Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group, 1)

    def _browse_nastran(self):
        """Browse for Nastran executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Nastran Executable", "",
            "Executable Files (*.exe nastran*);;All Files (*)"
        )
        if file_path:
            self.nastran_path.setText(file_path)

    def _export_bdf(self):
        """Export SOL200 BDF without running."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save SOL200 BDF", "",
            "BDF Files (*.bdf);;All Files (*)"
        )
        if file_path:
            try:
                self.opt_model.export_sol200_bdf(file_path)
                self._log(f"SOL200 BDF exported to: {file_path}")
                QMessageBox.information(self, "Export Complete",
                                       f"SOL200 BDF saved to:\n{file_path}")
            except Exception as e:
                self._log(f"Export failed: {e}")
                QMessageBox.critical(self, "Export Failed", str(e))

    def _start_run(self):
        """Start the optimization run."""
        from ..core.nastran_runner import NastranRunner, NastranStatus

        # Get Nastran path
        nastran_path = self.nastran_path.text().strip() or None

        self.runner = NastranRunner(nastran_path)

        if not self.runner.is_nastran_available():
            QMessageBox.critical(
                self, "Nastran Not Found",
                "Could not find MSC Nastran executable.\n\n"
                "Please specify the path to nastran.exe or nastran."
            )
            return

        # Disable controls
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        # Export BDF first
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.bdf', delete=False) as f:
            temp_bdf = f.name

        try:
            self.opt_model.export_sol200_bdf(temp_bdf)
            self._log(f"SOL200 BDF written to: {temp_bdf}")
        except Exception as e:
            self._log(f"Failed to generate BDF: {e}")
            self.run_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            return

        # Set up callbacks
        self.runner.on_progress = self._on_progress
        self.runner.on_complete = self._on_complete

        # Start in thread
        self.run_thread = NastranRunThread(
            self.runner, temp_bdf,
            memory=self.memory_combo.currentText(),
            parallel=self.parallel_spin.value()
        )
        self.run_thread.progress.connect(self._update_progress)
        self.run_thread.finished.connect(self._on_run_finished)
        self.run_thread.start()

        self._log("Starting Nastran SOL200 optimization...")
        self.progress_bar.setFormat("Running...")
        self.progress_bar.setRange(0, 0)  # Indeterminate

    def _cancel_run(self):
        """Cancel the running optimization."""
        if self.runner:
            self.runner.cancel()
            self._log("Cancellation requested...")

    def _on_progress(self, cycle: int, message: str):
        """Handle progress updates."""
        self._log(f"Design Cycle {cycle}: {message}")

    def _update_progress(self, message: str):
        """Update progress display."""
        self.status_label.setText(message)

    def _on_complete(self, result):
        """Handle completion."""
        pass  # Handled by _on_run_finished

    def _on_run_finished(self, result):
        """Handle run completion."""
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setRange(0, 100)

        if result.success:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Complete!")
            self._log(f"\nOptimization completed successfully!")
            self._log(f"  Design cycles: {len(result.cycles)}")
            if result.improvement:
                self._log(f"  Improvement: {result.improvement:.2f}%")
            self._log(f"  Wall time: {result.wall_time:.1f} seconds")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Failed")
            self._log(f"\nOptimization failed: {result.error_message}")

        # Store result
        self.opt_model.last_result = result

    def _log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)


class NastranRunThread(QThread):
    """Thread for running Nastran."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, runner, bdf_path: str, memory: str, parallel: int):
        super().__init__()
        self.runner = runner
        self.bdf_path = bdf_path
        self.memory = memory
        self.parallel = parallel

    def run(self):
        """Run Nastran in background."""
        result = self.runner.run(
            self.bdf_path,
            memory=self.memory,
            parallel=self.parallel,
        )
        self.finished.emit(result)


class ResultsPanel(QFrame):
    """Panel for viewing optimization results."""

    def __init__(self, opt_model: OptimizationModel, parent=None):
        super().__init__(parent)
        self.opt_model = opt_model
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("8. Results")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)

        desc = QLabel(
            "View and export the optimization results. Compare initial and final designs."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #757575; margin-bottom: 16px;")
        layout.addWidget(desc)

        # Summary
        summary_group = QGroupBox("Optimization Summary")
        summary_layout = QFormLayout(summary_group)

        self.status_label = QLabel("-")
        summary_layout.addRow("Status:", self.status_label)

        self.cycles_label = QLabel("-")
        summary_layout.addRow("Design Cycles:", self.cycles_label)

        self.initial_obj_label = QLabel("-")
        summary_layout.addRow("Initial Objective:", self.initial_obj_label)

        self.final_obj_label = QLabel("-")
        summary_layout.addRow("Final Objective:", self.final_obj_label)

        self.improvement_label = QLabel("-")
        summary_layout.addRow("Improvement:", self.improvement_label)

        self.time_label = QLabel("-")
        summary_layout.addRow("Execution Time:", self.time_label)

        layout.addWidget(summary_group)

        # Tabs for detailed results
        tabs = QTabWidget()

        # Convergence history tab
        conv_widget = QWidget()
        conv_layout = QVBoxLayout(conv_widget)

        self.conv_table = QTableWidget()
        self.conv_table.setColumnCount(4)
        self.conv_table.setHorizontalHeaderLabels([
            "Cycle", "Objective", "Max Constraint", "Feasible"
        ])
        self.conv_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        conv_layout.addWidget(self.conv_table)
        tabs.addTab(conv_widget, "Convergence History")

        # Design variables tab
        dv_widget = QWidget()
        dv_layout = QVBoxLayout(dv_widget)

        self.dv_table = QTableWidget()
        self.dv_table.setColumnCount(4)
        self.dv_table.setHorizontalHeaderLabels([
            "Variable", "Initial", "Final", "Change %"
        ])
        self.dv_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        dv_layout.addWidget(self.dv_table)
        tabs.addTab(dv_widget, "Design Variables")

        # Constraints tab
        const_widget = QWidget()
        const_layout = QVBoxLayout(const_widget)

        self.const_table = QTableWidget()
        self.const_table.setColumnCount(5)
        self.const_table.setHorizontalHeaderLabels([
            "Constraint", "Lower", "Value", "Upper", "Status"
        ])
        self.const_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        const_layout.addWidget(self.const_table)
        tabs.addTab(const_widget, "Constraints")

        layout.addWidget(tabs, 1)

        # Export buttons
        export_group = QGroupBox("Export Results")
        export_layout = QHBoxLayout(export_group)

        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        export_layout.addWidget(export_csv_btn)

        export_bdf_btn = QPushButton("Export Final BDF")
        export_bdf_btn.clicked.connect(self._export_final_bdf)
        export_layout.addWidget(export_bdf_btn)

        export_report_btn = QPushButton("Generate Report")
        export_report_btn.clicked.connect(self._generate_report)
        export_layout.addWidget(export_report_btn)

        export_layout.addStretch()
        layout.addWidget(export_group)

    def refresh(self):
        """Refresh results display."""
        result = getattr(self.opt_model, 'last_result', None)

        if not result:
            self.status_label.setText("No results available")
            return

        # Update summary
        self.status_label.setText("Success" if result.success else "Failed")
        self.status_label.setStyleSheet(
            f"color: {'#4CAF50' if result.success else '#F44336'}; font-weight: bold;"
        )

        self.cycles_label.setText(str(len(result.cycles)))

        if result.initial_objective is not None:
            self.initial_obj_label.setText(f"{result.initial_objective:.6g}")
        if result.final_objective is not None:
            self.final_obj_label.setText(f"{result.final_objective:.6g}")
        if result.improvement is not None:
            self.improvement_label.setText(f"{result.improvement:.2f}%")
            self.improvement_label.setStyleSheet(
                f"color: {'#4CAF50' if result.improvement > 0 else '#F44336'}; font-weight: bold;"
            )

        self.time_label.setText(f"{result.wall_time:.1f} seconds")

        # Update convergence table
        self.conv_table.setRowCount(len(result.cycles))
        for row, cycle in enumerate(result.cycles):
            self.conv_table.setItem(row, 0, QTableWidgetItem(str(cycle.cycle_number)))
            self.conv_table.setItem(row, 1, QTableWidgetItem(f"{cycle.objective_value:.6g}"))
            self.conv_table.setItem(row, 2, QTableWidgetItem(f"{cycle.max_constraint_violation:.6g}"))

            feasible_item = QTableWidgetItem("Yes" if cycle.is_feasible else "No")
            feasible_item.setForeground(
                QColor("#4CAF50" if cycle.is_feasible else "#F44336")
            )
            self.conv_table.setItem(row, 3, feasible_item)

        # Update design variables table
        self.dv_table.setRowCount(len(result.final_design))
        for row, (dv_id, final_value) in enumerate(result.final_design.items()):
            dv = self.opt_model.design_variables.get(dv_id)
            label = dv.label if dv else f"DV{dv_id}"
            initial = dv.initial_value if dv else 0

            self.dv_table.setItem(row, 0, QTableWidgetItem(label))
            self.dv_table.setItem(row, 1, QTableWidgetItem(f"{initial:.6g}"))
            self.dv_table.setItem(row, 2, QTableWidgetItem(f"{final_value:.6g}"))

            if initial != 0:
                change = (final_value - initial) / initial * 100
                change_item = QTableWidgetItem(f"{change:+.2f}%")
                change_item.setForeground(
                    QColor("#4CAF50" if change < 0 else "#FF9800")
                )
                self.dv_table.setItem(row, 3, change_item)

    def _export_csv(self):
        """Export results to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results CSV", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            result = getattr(self.opt_model, 'last_result', None)
            if result:
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Cycle', 'Objective', 'Max Constraint', 'Feasible'])
                    for cycle in result.cycles:
                        writer.writerow([
                            cycle.cycle_number,
                            cycle.objective_value,
                            cycle.max_constraint_violation,
                            cycle.is_feasible
                        ])
                QMessageBox.information(self, "Export Complete",
                                       f"Results exported to:\n{file_path}")

    def _export_final_bdf(self):
        """Export final optimized BDF."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Final BDF", "",
            "BDF Files (*.bdf);;All Files (*)"
        )
        if file_path:
            try:
                self.opt_model.export_final_bdf(file_path)
                QMessageBox.information(self, "Export Complete",
                                       f"Final BDF exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))

    def _generate_report(self):
        """Generate optimization report."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "",
            "HTML Files (*.html);;All Files (*)"
        )
        if file_path:
            try:
                self._write_html_report(file_path)
                QMessageBox.information(self, "Report Generated",
                                       f"Report saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Report Failed", str(e))

    def _write_html_report(self, path: str):
        """Write HTML optimization report."""
        result = getattr(self.opt_model, 'last_result', None)
        if not result:
            raise ValueError("No results to report")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SOL200 Optimization Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2196F3; }}
        h2 {{ color: #424242; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #2196F3; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
        .failed {{ color: #F44336; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>SOL200 Optimization Report</h1>
    <p>Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Summary</h2>
    <table>
        <tr><th>Property</th><th>Value</th></tr>
        <tr><td>Status</td><td class="{'success' if result.success else 'failed'}">
            {'Success' if result.success else 'Failed'}</td></tr>
        <tr><td>Design Cycles</td><td>{len(result.cycles)}</td></tr>
        <tr><td>Initial Objective</td><td>{result.initial_objective:.6g if result.initial_objective else 'N/A'}</td></tr>
        <tr><td>Final Objective</td><td>{result.final_objective:.6g if result.final_objective else 'N/A'}</td></tr>
        <tr><td>Improvement</td><td>{result.improvement:.2f}% if result.improvement else 'N/A'}</td></tr>
        <tr><td>Execution Time</td><td>{result.wall_time:.1f} seconds</td></tr>
    </table>

    <h2>Convergence History</h2>
    <table>
        <tr><th>Cycle</th><th>Objective</th><th>Max Constraint</th><th>Feasible</th></tr>
        {''.join(f'<tr><td>{c.cycle_number}</td><td>{c.objective_value:.6g}</td><td>{c.max_constraint_violation:.6g}</td><td>{"Yes" if c.is_feasible else "No"}</td></tr>' for c in result.cycles)}
    </table>
</body>
</html>"""

        with open(path, 'w') as f:
            f.write(html)


class SOL200OptimizerWindow(QMainWindow):
    """
    Main window for SOL200 Optimizer.

    Provides a guided workflow for setting up and running
    structural optimization with frequency response objectives.
    """

    def __init__(self):
        super().__init__()
        self.opt_model = OptimizationModel("SOL200 Optimization")
        self.current_step = WorkflowStep.MODEL
        self.style = ModernStyle(dark_mode=False)

        self._setup_ui()
        self._apply_style()
        self._connect_signals()

        self.setWindowTitle("SOL200 Optimizer - MSC Nastran Structural Optimization")
        self.setMinimumSize(1200, 800)
        self.showMaximized()

    def _setup_ui(self):
        """Set up the main UI."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Step indicator
        self.step_indicator = StepIndicator([
            "Model", "Design Vars", "Responses", "Constraints",
            "Objective", "Validate", "Run", "Results"
        ])
        self.step_indicator.setFixedHeight(80)
        main_layout.addWidget(self.step_indicator)

        # Content area
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(16, 16, 16, 16)

        # Stacked widget for panels
        self.stack = QStackedWidget()

        # Create panels
        self.model_panel = ModelPanel(self.opt_model)
        self.dv_panel = DesignVariablePanel(self.opt_model)
        self.response_panel = ResponsePanel(self.opt_model)
        self.constraint_panel = ConstraintPanel(self.opt_model)
        self.objective_panel = ObjectivePanel(self.opt_model)
        self.validate_panel = ValidatePanel(self.opt_model)
        self.run_panel = RunPanel(self.opt_model)
        self.results_panel = ResultsPanel(self.opt_model)

        self.stack.addWidget(self.model_panel)
        self.stack.addWidget(self.dv_panel)
        self.stack.addWidget(self.response_panel)
        self.stack.addWidget(self.constraint_panel)
        self.stack.addWidget(self.objective_panel)
        self.stack.addWidget(self.validate_panel)
        self.stack.addWidget(self.run_panel)
        self.stack.addWidget(self.results_panel)

        content_layout.addWidget(self.stack, 1)

        main_layout.addWidget(content_frame, 1)

        # Navigation bar
        nav_frame = QFrame()
        nav_frame.setStyleSheet("background-color: #F5F5F5; border-top: 1px solid #E0E0E0;")
        nav_layout = QHBoxLayout(nav_frame)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setProperty("secondary", True)
        self.back_btn.clicked.connect(self._go_back)

        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self._go_next)

        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)

        main_layout.addWidget(nav_frame)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Load a BDF file to begin")

        # Menu bar
        self._setup_menu()

    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)

        save_action = QAction("&Save Project", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction("&Export SOL200 BDF...", self)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        dark_mode = QAction("&Dark Mode", self)
        dark_mode.setCheckable(True)
        dark_mode.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(dark_mode)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _apply_style(self):
        """Apply the modern stylesheet."""
        self.setStyleSheet(self.style.get_stylesheet())

    def _connect_signals(self):
        """Connect signals between panels."""
        self.model_panel.model_loaded.connect(self._on_model_loaded)

    def _on_model_loaded(self, path: str):
        """Handle model loaded event."""
        self.status_bar.showMessage(f"Model loaded: {Path(path).name}")
        self.dv_panel.refresh()

    def _go_back(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self._update_step()

    def _go_next(self):
        """Go to next step."""
        if self.current_step < WorkflowStep.RESULTS:
            self.current_step += 1
            self._update_step()

    def _update_step(self):
        """Update UI for current step."""
        self.step_indicator.set_current_step(self.current_step)
        self.stack.setCurrentIndex(self.current_step)

        self.back_btn.setEnabled(self.current_step > 0)
        self.next_btn.setEnabled(self.current_step < WorkflowStep.RESULTS)

        # Refresh panels when navigating
        if self.current_step == WorkflowStep.DESIGN_VARIABLES:
            self.dv_panel.refresh()
        elif self.current_step == WorkflowStep.RESPONSES:
            self.response_panel.refresh()
        elif self.current_step == WorkflowStep.CONSTRAINTS:
            self.constraint_panel.refresh()
        elif self.current_step == WorkflowStep.OBJECTIVE:
            self.objective_panel.refresh()
        elif self.current_step == WorkflowStep.VALIDATE:
            self.validate_panel.refresh()
        elif self.current_step == WorkflowStep.RESULTS:
            self.results_panel.refresh()

    def _toggle_dark_mode(self, enabled: bool):
        """Toggle dark mode."""
        self.style = ModernStyle(dark_mode=enabled)
        self._apply_style()

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About SOL200 Optimizer",
            "<h2>SOL200 Optimizer</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A modern tool for MSC Nastran structural optimization.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Design variable management (PSHELL, PBAR, PBARL, PROD)</li>"
            "<li>Frequency response optimization (SOL111)</li>"
            "<li>RMS acceleration objectives</li>"
            "<li>Comprehensive validation</li>"
            "</ul>"
        )


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("SOL200 Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Aerospace Tools")

    window = SOL200OptimizerWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
