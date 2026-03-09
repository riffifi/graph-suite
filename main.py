#!/usr/bin/env python3
"""Graph Suite – Main entry point.

A professional desktop application for creating, editing, and analyzing graphs.
Supports directed/undirected graphs, weighted edges, parallel edges, and
bidirectional edges with an interactive canvas and DSL scripting.

Usage:
    python main.py

Or install and run:
    pip install -e .
    graph-suite
"""

from __future__ import annotations

import sys
import os

# Force dark mode on macOS before importing Qt
if sys.platform == "darwin":
    os.environ["QT_MAC_FORCE_DARK_MODE"] = "1"

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from graphsuite.gui.main_window import MainWindow
from graphsuite.gui.style import STYLESHEET, Colors


def setup_dark_palette() -> QPalette:
    """Create and return a dark color palette for the application."""
    palette = QPalette()
    
    # Base colors
    palette.setColor(QPalette.Window, QColor(Colors.BG_DARK))
    palette.setColor(QPalette.WindowText, QColor(Colors.TEXT))
    palette.setColor(QPalette.Base, QColor(Colors.BG_INPUT))
    palette.setColor(QPalette.AlternateBase, QColor(Colors.BG_MID))
    palette.setColor(QPalette.ToolTipBase, QColor(Colors.BG_DARK))
    palette.setColor(QPalette.ToolTipText, QColor(Colors.TEXT))
    palette.setColor(QPalette.Text, QColor(Colors.TEXT))
    
    # Button colors
    palette.setColor(QPalette.Button, QColor(Colors.BG_SURFACE))
    palette.setColor(QPalette.ButtonText, QColor(Colors.TEXT))
    
    # Highlight colors
    palette.setColor(QPalette.Highlight, QColor(Colors.PRIMARY))
    palette.setColor(QPalette.HighlightedText, QColor(Colors.TEXT_BRIGHT))
    
    # Link colors
    palette.setColor(QPalette.Link, QColor(Colors.SECONDARY))
    palette.setColor(QPalette.LinkVisited, QColor(Colors.PRIMARY_HOVER))
    
    # Disabled colors
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(Colors.TEXT_DIM))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(Colors.TEXT_DIM))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(Colors.TEXT_DIM))
    
    return palette


def main() -> int:
    """Main entry point for Graph Suite application.

    Returns:
        Exit code from QApplication execution.
    """
    # Force dark mode on Windows (if applicable)
    if sys.platform == "win32":
        try:
            # Try to set dark mode for Windows 10+
            from PySide6.QtWinExtras import QtWin
            if QtWin.isCompositionEnabled():
                QtWin.setCurrentProcessExplicitAppUserModelID("GraphSuite.GraphSuite.1.0")
        except ImportError:
            pass
    
    # Enable High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Set dark mode attribute before creating QApplication
    if hasattr(Qt, 'ApplicationAttribute'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)

    app = QApplication(sys.argv)
    app.setApplicationName("Graph Suite")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Graph Suite")
    app.setStyle("Fusion")
    
    # Apply dark palette
    app.setPalette(setup_dark_palette())

    # Apply custom stylesheet (overrides any system theme)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
