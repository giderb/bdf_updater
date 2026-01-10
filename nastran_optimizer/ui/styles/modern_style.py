"""
Modern UI Style and Theme for SOL200 Optimizer.

Provides a consistent, professional look with:
- Dark/Light theme support
- Smooth rounded corners
- Consistent color palette
- Accessibility considerations
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ColorPalette:
    """Color palette for theming."""
    # Primary colors
    primary: str = "#2196F3"        # Blue
    primary_light: str = "#64B5F6"
    primary_dark: str = "#1976D2"

    # Accent colors
    accent: str = "#FF9800"         # Orange
    accent_light: str = "#FFB74D"

    # Status colors
    success: str = "#4CAF50"
    warning: str = "#FFC107"
    error: str = "#F44336"
    info: str = "#2196F3"

    # Background colors
    background: str = "#FAFAFA"
    surface: str = "#FFFFFF"
    surface_variant: str = "#F5F5F5"

    # Text colors
    text_primary: str = "#212121"
    text_secondary: str = "#757575"
    text_disabled: str = "#BDBDBD"
    text_on_primary: str = "#FFFFFF"

    # Border colors
    border: str = "#E0E0E0"
    border_focus: str = "#2196F3"

    # Shadow
    shadow: str = "rgba(0, 0, 0, 0.1)"


@dataclass
class DarkPalette(ColorPalette):
    """Dark theme color palette."""
    primary: str = "#90CAF9"
    primary_light: str = "#BBDEFB"
    primary_dark: str = "#42A5F5"

    accent: str = "#FFB74D"

    background: str = "#121212"
    surface: str = "#1E1E1E"
    surface_variant: str = "#2D2D2D"

    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0B0B0"
    text_disabled: str = "#666666"
    text_on_primary: str = "#000000"

    border: str = "#333333"
    border_focus: str = "#90CAF9"

    shadow: str = "rgba(0, 0, 0, 0.3)"


class ModernStyle:
    """
    Modern style generator for PyQt6 widgets.

    Creates consistent, professional styling for all UI components.
    """

    def __init__(self, dark_mode: bool = False):
        """Initialize with color palette."""
        self.palette = DarkPalette() if dark_mode else ColorPalette()
        self.dark_mode = dark_mode

    def get_stylesheet(self) -> str:
        """Generate complete application stylesheet."""
        p = self.palette
        return f"""
/* === Global Styles === */
QWidget {{
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    color: {p.text_primary};
    background-color: {p.background};
}}

/* === Main Window === */
QMainWindow {{
    background-color: {p.background};
}}

QMainWindow::separator {{
    background-color: {p.border};
    width: 1px;
    height: 1px;
}}

/* === Menu Bar === */
QMenuBar {{
    background-color: {p.surface};
    border-bottom: 1px solid {p.border};
    padding: 4px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {p.primary};
    color: {p.text_on_primary};
}}

QMenu {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {p.primary_light};
}}

/* === Tool Bar === */
QToolBar {{
    background-color: {p.surface};
    border-bottom: 1px solid {p.border};
    padding: 4px;
    spacing: 4px;
}}

QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 8px;
}}

QToolButton:hover {{
    background-color: {p.surface_variant};
}}

QToolButton:pressed {{
    background-color: {p.primary_light};
}}

/* === Push Button === */
QPushButton {{
    background-color: {p.primary};
    color: {p.text_on_primary};
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: 500;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {p.primary_light};
}}

QPushButton:pressed {{
    background-color: {p.primary_dark};
}}

QPushButton:disabled {{
    background-color: {p.text_disabled};
    color: {p.surface};
}}

QPushButton[secondary="true"] {{
    background-color: {p.surface};
    color: {p.primary};
    border: 2px solid {p.primary};
}}

QPushButton[secondary="true"]:hover {{
    background-color: {p.primary_light};
    color: {p.text_on_primary};
}}

QPushButton[accent="true"] {{
    background-color: {p.accent};
}}

QPushButton[accent="true"]:hover {{
    background-color: {p.accent_light};
}}

QPushButton[success="true"] {{
    background-color: {p.success};
}}

QPushButton[danger="true"] {{
    background-color: {p.error};
}}

/* === Line Edit === */
QLineEdit {{
    background-color: {p.surface};
    border: 2px solid {p.border};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {p.primary_light};
}}

QLineEdit:focus {{
    border-color: {p.border_focus};
}}

QLineEdit:disabled {{
    background-color: {p.surface_variant};
    color: {p.text_disabled};
}}

/* === Spin Box === */
QSpinBox, QDoubleSpinBox {{
    background-color: {p.surface};
    border: 2px solid {p.border};
    border-radius: 6px;
    padding: 8px 12px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {p.border_focus};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border: none;
    width: 20px;
}}

/* === Combo Box === */
QComboBox {{
    background-color: {p.surface};
    border: 2px solid {p.border};
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 100px;
}}

QComboBox:focus {{
    border-color: {p.border_focus};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 6px;
    selection-background-color: {p.primary_light};
}}

/* === Group Box === */
QGroupBox {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    background-color: {p.surface};
    color: {p.primary};
}}

/* === Tab Widget === */
QTabWidget::pane {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {p.surface_variant};
    border: 1px solid {p.border};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 10px 20px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {p.surface};
    border-bottom: 2px solid {p.primary};
}}

QTabBar::tab:hover:!selected {{
    background-color: {p.primary_light};
}}

/* === Table Widget === */
QTableWidget, QTableView {{
    background-color: {p.surface};
    alternate-background-color: {p.surface_variant};
    border: 1px solid {p.border};
    border-radius: 8px;
    gridline-color: {p.border};
}}

QTableWidget::item, QTableView::item {{
    padding: 8px;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {p.primary_light};
}}

QHeaderView::section {{
    background-color: {p.surface_variant};
    border: none;
    border-bottom: 2px solid {p.border};
    padding: 10px;
    font-weight: 600;
}}

/* === Tree Widget === */
QTreeWidget, QTreeView {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
}}

QTreeWidget::item, QTreeView::item {{
    padding: 6px;
    border-radius: 4px;
}}

QTreeWidget::item:selected, QTreeView::item:selected {{
    background-color: {p.primary_light};
}}

/* === Scroll Bar === */
QScrollBar:vertical {{
    background-color: {p.surface};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {p.text_disabled};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {p.text_secondary};
}}

QScrollBar:horizontal {{
    background-color: {p.surface};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {p.text_disabled};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
    width: 0;
}}

/* === Progress Bar === */
QProgressBar {{
    background-color: {p.surface_variant};
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {p.primary};
    border-radius: 6px;
}}

/* === Slider === */
QSlider::groove:horizontal {{
    background-color: {p.surface_variant};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {p.primary};
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {p.primary_light};
}}

/* === Check Box === */
QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {p.border};
    border-radius: 4px;
    background-color: {p.surface};
}}

QCheckBox::indicator:checked {{
    background-color: {p.primary};
    border-color: {p.primary};
}}

QCheckBox::indicator:hover {{
    border-color: {p.primary};
}}

/* === Radio Button === */
QRadioButton {{
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {p.border};
    border-radius: 10px;
    background-color: {p.surface};
}}

QRadioButton::indicator:checked {{
    background-color: {p.primary};
    border-color: {p.primary};
}}

/* === Text Edit === */
QTextEdit, QPlainTextEdit {{
    background-color: {p.surface};
    border: 2px solid {p.border};
    border-radius: 6px;
    padding: 8px;
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {p.border_focus};
}}

/* === Label === */
QLabel {{
    color: {p.text_primary};
}}

QLabel[heading="true"] {{
    font-size: 18px;
    font-weight: 600;
    color: {p.primary};
}}

QLabel[subheading="true"] {{
    font-size: 14px;
    color: {p.text_secondary};
}}

QLabel[error="true"] {{
    color: {p.error};
}}

QLabel[success="true"] {{
    color: {p.success};
}}

/* === Status Bar === */
QStatusBar {{
    background-color: {p.surface};
    border-top: 1px solid {p.border};
}}

QStatusBar::item {{
    border: none;
}}

/* === Splitter === */
QSplitter::handle {{
    background-color: {p.border};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* === Dock Widget === */
QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}

QDockWidget::title {{
    background-color: {p.surface_variant};
    padding: 8px;
    font-weight: 600;
}}

/* === Tool Tip === */
QToolTip {{
    background-color: {p.surface};
    color: {p.text_primary};
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 8px;
}}

/* === Frame === */
QFrame[card="true"] {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 12px;
    padding: 16px;
}}

/* === Wizard styling === */
QWizard {{
    background-color: {p.background};
}}

QWizardPage {{
    background-color: {p.background};
}}
"""

    def get_icon_color(self) -> str:
        """Get appropriate icon color for current theme."""
        return self.palette.text_primary if not self.dark_mode else "#FFFFFF"


def get_status_style(status: str) -> Dict[str, str]:
    """Get styling for different status types."""
    styles = {
        'success': {'color': '#4CAF50', 'bg': '#E8F5E9'},
        'warning': {'color': '#FFC107', 'bg': '#FFF8E1'},
        'error': {'color': '#F44336', 'bg': '#FFEBEE'},
        'info': {'color': '#2196F3', 'bg': '#E3F2FD'},
    }
    return styles.get(status, styles['info'])
