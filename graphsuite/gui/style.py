"""Dark theme and colour palette for Graph Suite."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

class Colors:
    BG_DARK = "#1e1e2e"
    BG_MID = "#252536"
    BG_SURFACE = "#2a2a3c"
    BG_HOVER = "#35354a"
    BG_INPUT = "#1a1a28"
    BORDER = "#3a3a50"

    TEXT = "#e0e0e0"
    TEXT_DIM = "#8888a0"
    TEXT_BRIGHT = "#ffffff"

    PRIMARY = "#7c4dff"
    PRIMARY_HOVER = "#9e7cff"
    SECONDARY = "#4fc3f7"

    NODE_DEFAULT = "#4fc3f7"
    NODE_SELECTED = "#ff6f00"
    NODE_HOVER = "#80d8ff"
    NODE_LABEL = "#1e1e2e"

    EDGE_DEFAULT = "#90a4ae"
    EDGE_SELECTED = "#ff6f00"
    EDGE_HIGHLIGHT = "#66bb6a"
    EDGE_WEIGHT = "#cfd8dc"

    CANVAS_BG = "#1a1a28"
    CANVAS_GRID = "#252536"

    SUCCESS = "#66bb6a"
    WARNING = "#ffa726"
    ERROR = "#ef5350"

    ALGO_HIGHLIGHT = "#66bb6a"


# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------

STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT};
}}

QMenuBar {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 2px;
}}
QMenuBar::item:selected {{
    background-color: {Colors.BG_HOVER};
    border-radius: 4px;
}}

QMenu {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item:selected {{
    background-color: {Colors.PRIMARY};
    border-radius: 4px;
}}
QMenu::separator {{
    height: 1px;
    background-color: {Colors.BORDER};
    margin: 4px 8px;
}}

QToolBar {{
    background-color: {Colors.BG_MID};
    border-bottom: 1px solid {Colors.BORDER};
    spacing: 4px;
    padding: 3px 6px;
}}

QToolButton {{
    background-color: transparent;
    color: {Colors.TEXT};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: 500;
}}
QToolButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER};
}}
QToolButton:checked {{
    background-color: {Colors.PRIMARY};
    color: {Colors.TEXT_BRIGHT};
    border-color: {Colors.PRIMARY};
}}

QPushButton {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 5px;
    padding: 5px 14px;
    min-height: 22px;
}}
QPushButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.PRIMARY};
}}
QPushButton:pressed {{
    background-color: {Colors.PRIMARY};
}}

QComboBox {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 5px;
    padding: 4px 10px;
    min-height: 22px;
}}
QComboBox:hover {{
    border-color: {Colors.PRIMARY};
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    selection-background-color: {Colors.PRIMARY};
}}

QLabel {{
    color: {Colors.TEXT};
}}

QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.PRIMARY};
}}

QTableWidget {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT};
    gridline-color: {Colors.BORDER};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    selection-background-color: {Colors.PRIMARY};
}}
QTableWidget QHeaderView::section {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    padding: 4px;
    font-weight: bold;
}}

QHeaderView::section {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    padding: 4px;
}}

QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
}}

QDockWidget {{
    color: {Colors.TEXT};
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background-color: {Colors.BG_MID};
    border: 1px solid {Colors.BORDER};
    border-radius: 0px;
    padding: 6px;
    font-weight: bold;
}}

QStatusBar {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT_DIM};
    border-top: 1px solid {Colors.BORDER};
}}

QScrollBar:vertical {{
    background: {Colors.BG_DARK};
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {Colors.BG_HOVER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {Colors.BG_DARK};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.BG_HOVER};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QSplitter::handle {{
    background-color: {Colors.BORDER};
}}

QCheckBox {{
    color: {Colors.TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {Colors.BORDER};
    border-radius: 3px;
    background-color: {Colors.BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {Colors.PRIMARY};
    border-color: {Colors.PRIMARY};
}}

QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_DARK};
}}
QTabBar::tab {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT_DIM};
    border: 1px solid {Colors.BORDER};
    border-bottom: none;
    padding: 6px 14px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_BRIGHT};
}}
QTabBar::tab:hover:!selected {{
    background-color: {Colors.BG_HOVER};
}}
"""
