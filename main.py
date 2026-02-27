#!/usr/bin/env python3
"""Graph Suite – Main entry point."""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from graphsuite.gui.main_window import MainWindow
from graphsuite.gui.style import STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Graph Suite")
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
