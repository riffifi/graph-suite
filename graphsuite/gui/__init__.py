"""Graphical user interface components.

This module contains all Qt-based UI components for the Graph Suite application:

- MainWindow: Main application window
- GraphCanvas: Interactive graph visualization widget
- MatrixEditor: Adjacency and incidence matrix editors
- AlgorithmPanel: Graph algorithm execution panel
- Style: Color palette and application stylesheet
"""

from graphsuite.gui.style import Colors, STYLESHEET

__all__ = [
    "Colors",
    "STYLESHEET",
]
