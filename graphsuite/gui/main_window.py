"""Main application window – toolbar, menus, docks, coordination."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter, QColor, QActionGroup
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QFileDialog,
    QMessageBox, QStatusBar, QToolButton, QWidget,
    QLabel, QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QTabWidget,
    QScrollArea, QFrame, QPushButton,
)

from graphsuite.core.graph import Graph, GraphEvent
from graphsuite.gui.canvas import GraphCanvas, CanvasMode
from graphsuite.gui.matrix_editor import MatrixEditor
from graphsuite.gui.algorithm_panel import AlgorithmPanel
from graphsuite.gui.style import Colors, STYLESHEET
from graphsuite.dsl.engine import DSLConsole


class MainWindow(QMainWindow):
    """Graph Suite main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Graph Suite")
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        # Core model
        self.graph = Graph()

        # Widgets
        self.canvas = GraphCanvas(self.graph)
        self.matrix_editor = MatrixEditor(self.graph)
        self.algo_panel = AlgorithmPanel(self.graph)
        self.dsl_console = DSLConsole(self.graph)

        # Wire cross-component signals
        self.algo_panel.set_canvas(self.canvas)
        self.dsl_console.highlight_request.connect(self.canvas.set_highlight)
        self.dsl_console.clear_highlight.connect(self.canvas.clear_highlight)
        self.dsl_console.fit_request.connect(self.canvas.fit_view)

        # Central widget
        self.setCentralWidget(self.canvas)

        # Build UI
        self._build_menu_bar()
        self._build_toolbar()
        self._build_docks()
        self._build_status_bar()

        # Listen to graph for status updates
        self.graph.add_listener(self._on_graph_event)

        self._current_file: str | None = None
        self._update_status()

    # ── Menu bar ──────────────────────────────────────────────────────────

    def _build_menu_bar(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        file_menu.addAction(
            self._action("&New", "Ctrl+N", self._file_new))
        file_menu.addAction(
            self._action("&Open…", "Ctrl+O", self._file_open))
        file_menu.addAction(
            self._action("&Save", "Ctrl+S", self._file_save))
        file_menu.addAction(
            self._action("Save &As…", "Ctrl+Shift+S", self._file_save_as))
        file_menu.addSeparator()
        file_menu.addAction(
            self._action("Export &PNG…", "", self._export_png))
        file_menu.addSeparator()
        file_menu.addAction(
            self._action("&Quit", "Ctrl+Q", self.close))

        # Edit
        edit_menu = mb.addMenu("&Edit")
        edit_menu.addAction(
            self._action("&Undo", "Ctrl+Z", self.graph.undo))
        edit_menu.addAction(
            self._action("&Redo", "Ctrl+Y", self.graph.redo))
        edit_menu.addSeparator()
        edit_menu.addAction(
            self._action("Clear &Graph", "", self._clear_graph))

        # Graph
        graph_menu = mb.addMenu("&Graph")
        self._act_directed = QAction("&Directed", self, checkable=True)
        self._act_directed.setChecked(self.graph.directed)
        self._act_directed.toggled.connect(self._toggle_directed)
        graph_menu.addAction(self._act_directed)

        self._act_weighted = QAction("&Weighted", self, checkable=True)
        self._act_weighted.setChecked(self.graph.weighted)
        self._act_weighted.toggled.connect(self._toggle_weighted)
        graph_menu.addAction(self._act_weighted)

        graph_menu.addSeparator()
        graph_menu.addAction(
            self._action("Circle Layout", "", self._layout_circle))
        graph_menu.addAction(
            self._action("Spring Layout", "", self._layout_spring))
        graph_menu.addAction(
            self._action("Fit View", "F",
                         self.canvas.fit_view))

        # View
        self._view_menu = mb.addMenu("&View")
        self._dock_actions: list[QAction] = []  # filled in _build_docks

        # Help
        help_menu = mb.addMenu("&Help")
        help_menu.addAction(
            self._action("&About", "", self._about))
        help_menu.addAction(
            self._action("DSL &Reference", "", self._dsl_help))

    def _action(self, text: str, shortcut: str,
                slot: object) -> QAction:
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        return act

    # ── Toolbar ───────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        # Mode buttons (exclusive)
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        modes = [
            ("Select", CanvasMode.SELECT, "S"),
            ("Add Node", CanvasMode.ADD_NODE, "N"),
            ("Add Edge", CanvasMode.ADD_EDGE, "E"),
            ("Delete", CanvasMode.DELETE, "D"),
        ]
        for label, mode, key in modes:
            act = QAction(label, self, checkable=True)
            act.setShortcut(QKeySequence(key))
            act.setToolTip(f"{label} ({key})")
            act.triggered.connect(lambda checked, m=mode: self._set_mode(m))
            mode_group.addAction(act)
            tb.addAction(act)
            if mode == CanvasMode.SELECT:
                act.setChecked(True)

        tb.addSeparator()

        # Directed toggle
        self._tb_directed = QAction("Directed", self, checkable=True)
        self._tb_directed.setChecked(self.graph.directed)
        self._tb_directed.setToolTip("Toggle directed/undirected")
        self._tb_directed.toggled.connect(self._toggle_directed)
        tb.addAction(self._tb_directed)

        # Weighted toggle
        self._tb_weighted = QAction("Weighted", self, checkable=True)
        self._tb_weighted.setChecked(self.graph.weighted)
        self._tb_weighted.setToolTip("Toggle weighted/unweighted")
        self._tb_weighted.toggled.connect(self._toggle_weighted)
        tb.addAction(self._tb_weighted)

        tb.addSeparator()

        # Layout buttons
        act_circle = QAction("Circle", self)
        act_circle.setToolTip("Circle layout")
        act_circle.triggered.connect(self._layout_circle)
        tb.addAction(act_circle)

        act_spring = QAction("Spring", self)
        act_spring.setToolTip("Spring layout")
        act_spring.triggered.connect(self._layout_spring)
        tb.addAction(act_spring)

        act_fit = QAction("Fit", self)
        act_fit.setToolTip("Fit all nodes in view")
        act_fit.triggered.connect(self.canvas.fit_view)
        tb.addAction(act_fit)

        tb.addSeparator()

        # Zoom controls
        act_zoom_in = QAction("Zoom +", self)
        act_zoom_in.setToolTip("Zoom in (Ctrl++))")
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(self._zoom_in)
        tb.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom -", self)
        act_zoom_out.setToolTip("Zoom out (Ctrl+-))")
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self._zoom_out)
        tb.addAction(act_zoom_out)

        tb.addSeparator()

        # Clear everything
        act_clear = QAction("Clear All", self)
        act_clear.setToolTip("Clear entire graph")
        act_clear.triggered.connect(self._clear_graph)
        tb.addAction(act_clear)

        tb.addSeparator()

        # Undo / Redo
        act_undo = QAction("Undo", self)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo.triggered.connect(self.graph.undo)
        tb.addAction(act_undo)

        act_redo = QAction("Redo", self)
        act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        act_redo.triggered.connect(self.graph.redo)
        tb.addAction(act_redo)

    def _set_mode(self, mode: CanvasMode) -> None:
        self.canvas.mode = mode

    # ── Dock widgets ──────────────────────────────────────────────────────

    def _build_docks(self) -> None:
        # Matrix editor – right
        matrix_dock = QDockWidget("Matrixes", self)
        matrix_dock.setWidget(self.matrix_editor)
        matrix_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, matrix_dock)

        # Algorithm panel – right (tabbed with matrix)
        algo_dock = QDockWidget("Algorithms", self)
        algo_dock.setWidget(self.algo_panel)
        algo_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, algo_dock)
        self.tabifyDockWidget(matrix_dock, algo_dock)
        matrix_dock.raise_()

        # DSL console – bottom
        dsl_dock = QDockWidget("Script Console", self)
        dsl_dock.setWidget(self.dsl_console)
        dsl_dock.setMinimumHeight(150)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dsl_dock)

        # Add toggle actions to View menu
        self._view_menu.addAction(matrix_dock.toggleViewAction())
        self._view_menu.addAction(algo_dock.toggleViewAction())
        self._view_menu.addAction(dsl_dock.toggleViewAction())

    # ── Status bar ────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel()
        self._status.addPermanentWidget(self._status_label)

    def _update_status(self) -> None:
        n = len(self.graph.nodes)
        e = len(self.graph.edges)
        d = "Directed" if self.graph.directed else "Undirected"
        w = "Weighted" if self.graph.weighted else "Unweighted"
        fname = Path(self._current_file).name if self._current_file else "Untitled"
        self._status_label.setText(
            f"  {fname}  |  {d} · {w}  |  "
            f"Nodes: {n}  Edges: {e}  |  "
            f"Undo: {len(self.graph._undo_stack)}  "
            f"Redo: {len(self.graph._redo_stack)}  ")

    # ── Graph event listener ──────────────────────────────────────────────

    def _on_graph_event(self, event: GraphEvent, data: dict) -> None:
        self._update_status()
        # sync toggle buttons
        if event in (GraphEvent.DIRECTED_CHANGED, GraphEvent.UNDO_REDO,
                     GraphEvent.GRAPH_REBUILT):
            self._tb_directed.blockSignals(True)
            self._tb_directed.setChecked(self.graph.directed)
            self._tb_directed.blockSignals(False)
            self._act_directed.blockSignals(True)
            self._act_directed.setChecked(self.graph.directed)
            self._act_directed.blockSignals(False)
        if event in (GraphEvent.WEIGHTED_CHANGED, GraphEvent.UNDO_REDO,
                     GraphEvent.GRAPH_REBUILT):
            self._tb_weighted.blockSignals(True)
            self._tb_weighted.setChecked(self.graph.weighted)
            self._tb_weighted.blockSignals(False)
            self._act_weighted.blockSignals(True)
            self._act_weighted.setChecked(self.graph.weighted)
            self._act_weighted.blockSignals(False)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _toggle_directed(self, checked: bool) -> None:
        self.graph.directed = checked

    def _toggle_weighted(self, checked: bool) -> None:
        self.graph.weighted = checked

    def _layout_circle(self) -> None:
        w, h = self.canvas.width(), self.canvas.height()
        self.graph.layout_circle(cx=w / 2, cy=h / 2,
                                 radius=min(w, h) * 0.35)
        self.canvas.fit_view()

    def _layout_spring(self) -> None:
        self.graph.layout_spring(
            width=self.canvas.width(), height=self.canvas.height())
        self.canvas.fit_view()

    def _zoom_in(self) -> None:
        self.canvas._zoom = min(5.0, self.canvas._zoom * 1.2)
        self.canvas.update()

    def _zoom_out(self) -> None:
        self.canvas._zoom = max(0.1, self.canvas._zoom / 1.2)
        self.canvas.update()

    def _clear_graph(self) -> None:
        if len(self.graph.nodes) == 0:
            return
        reply = QMessageBox.question(
            self, "Clear Graph",
            "Are you sure you want to clear the entire graph?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.graph.clear()

    # ── File operations ───────────────────────────────────────────────────

    def _file_new(self) -> None:
        self.graph.clear(record_undo=False)
        self.graph._undo_stack.clear()
        self.graph._redo_stack.clear()
        self._current_file = None
        self._update_status()

    def _file_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Graph", "",
            "Graph JSON (*.graph.json *.json);;All Files (*)")
        if path:
            try:
                with open(path, "r") as f:
                    self.graph.from_json(f.read())
                self._current_file = path
                self._update_status()
                self.canvas.fit_view()
            except Exception as e:
                QMessageBox.critical(self, "Open Error", str(e))

    def _file_save(self) -> None:
        if self._current_file:
            self._save_to(self._current_file)
        else:
            self._file_save_as()

    def _file_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Graph", "untitled.graph.json",
            "Graph JSON (*.graph.json *.json);;All Files (*)")
        if path:
            self._save_to(path)
            self._current_file = path
            self._update_status()

    def _save_to(self, path: str) -> None:
        try:
            with open(path, "w") as f:
                f.write(self.graph.to_json())
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PNG", "graph.png",
            "PNG Image (*.png);;All Files (*)")
        if path:
            pixmap = self.canvas.grab()
            pixmap.save(path, "PNG")
            self._status.showMessage(f"Exported to {path}", 3000)

    # ── Help ──────────────────────────────────────────────────────────────

    def _about(self) -> None:
        QMessageBox.about(
            self, "About Graph Suite",
            "<h2>Graph Suite</h2>"
            "<p>A professional 2D graph editor and analysis tool.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Interactive canvas with drag, zoom & pan</li>"
            "<li>Adjacency matrix editor</li>"
            "<li>Graph algorithms (BFS, DFS, Dijkstra, MST, …)</li>"
            "<li>Built-in scripting DSL</li>"
            "<li>Directed & undirected, weighted & unweighted</li>"
            "<li>Undo/redo, save/load, PNG export</li>"
            "</ul>")

    def _dsl_help(self) -> None:
        """Show comprehensive help dialog with Tutorial and DSL Reference."""
        dialog = HelpDialog(self)
        dialog.exec()


class HelpDialog(QDialog):
    """Comprehensive help dialog with Tutorial and DSL Reference sections."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Graph Suite Help")
        self.setMinimumSize(1000, 750)
        self._current_section = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e2e;
            }
            QTabBar::tab {
                background-color: #252536;
                color: #e0e0e0;
                padding: 12px 24px;
                border: none;
                border-right: 1px solid #3a3a50;
            }
            QTabBar::tab:selected {
                background-color: #1e1e2e;
                border-bottom: 2px solid #7c4dff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2a2a3c;
            }
        """)

        self._tabs.addTab(self._create_tutorial_tab(), "Tutorial")
        self._tabs.addTab(self._create_dsl_tab(), "DSL Reference")
        self._tabs.addTab(self._create_shortcuts_tab(), "Shortcuts")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs)

    def _create_tutorial_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize tutorial content list
        self._tutorial_sidebar_content: list[str] = []

        # Left sidebar
        sidebar = self._create_sidebar([
            ("Getting Started", self._tutorial_getting_started()),
            ("Creating Nodes", self._tutorial_nodes()),
            ("Creating Edges", self._tutorial_edges()),
            ("Selecting & Editing", self._tutorial_editing()),
            ("Navigation", self._tutorial_navigation()),
            ("Graph Properties", self._tutorial_properties()),
            ("Running Algorithms", self._tutorial_algorithms()),
            ("Saving & Exporting", self._tutorial_export()),
        ], self._tutorial_sidebar_content)

        # Content area
        self._tutorial_content = QTextEdit()
        self._tutorial_content.setReadOnly(True)
        self._tutorial_content.setHtml(self._tutorial_getting_started())
        self._tutorial_content.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #e0e0e0;
                border: none;
                padding: 20px 30px;
                font-size: 14px;
                line-height: 1.6;
            }
            h2 { color: #7c4dff; font-size: 24px; margin-bottom: 15px; border-bottom: 1px solid #3a3a50; padding-bottom: 10px; }
            h3 { color: #4fc3f7; font-size: 16px; margin-top: 20px; margin-bottom: 10px; }
            p { margin: 10px 0; line-height: 1.7; }
            ul, ol { margin: 10px 0; padding-left: 25px; }
            li { margin: 6px 0; }
            code { background-color: #2a2a3c; padding: 2px 6px; border-radius: 3px; color: #66bb6a; }
            pre { background-color: #252536; padding: 15px; border-radius: 6px; overflow-x: auto; }
        """)

        layout.addWidget(sidebar, 0)
        layout.addWidget(self._tutorial_content, 1)
        return widget

    def _create_dsl_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize DSL content list
        self._dsl_sidebar_content: list[str] = []

        # Left sidebar
        sidebar = self._create_sidebar([
            ("Introduction", self._dsl_intro()),
            ("Comments & Settings", self._dsl_settings()),
            ("Node Commands", self._dsl_nodes()),
            ("Edge Commands", self._dsl_edges()),
            ("Algorithm Commands", self._dsl_algorithms()),
            ("Layout Commands", self._dsl_layout()),
            ("Example Scripts", self._dsl_examples()),
        ], self._dsl_sidebar_content)

        # Content area
        self._dsl_content = QTextEdit()
        self._dsl_content.setReadOnly(True)
        self._dsl_content.setHtml(self._dsl_intro())
        self._dsl_content.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #e0e0e0;
                border: none;
                padding: 20px 30px;
                font-size: 14px;
                line-height: 1.6;
            }
            h2 { color: #7c4dff; font-size: 24px; margin-bottom: 15px; border-bottom: 1px solid #3a3a50; padding-bottom: 10px; }
            h3 { color: #4fc3f7; font-size: 16px; margin-top: 20px; margin-bottom: 10px; }
            p { margin: 10px 0; line-height: 1.7; }
            ul, ol { margin: 10px 0; padding-left: 25px; }
            li { margin: 6px 0; }
            code { background-color: #2a2a3c; padding: 2px 6px; border-radius: 3px; color: #66bb6a; }
            pre { background-color: #252536; padding: 15px; border-radius: 6px; overflow-x: auto; font-family: "JetBrains Mono", "Fira Code", monospace; font-size: 13px; }
        """)

        layout.addWidget(sidebar, 0)
        layout.addWidget(self._dsl_content, 1)
        return widget

    def _create_shortcuts_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize shortcuts content list
        self._shortcuts_sidebar_content: list[str] = []

        # Left sidebar
        shortcuts_data = [
            ("Modes", self._shortcuts_modes()),
            ("View", self._shortcuts_view()),
            ("Edit", self._shortcuts_edit()),
            ("File", self._shortcuts_file()),
        ]
        sidebar = self._create_sidebar(shortcuts_data, self._shortcuts_sidebar_content)

        # Content area
        self._shortcuts_content = QTextEdit()
        self._shortcuts_content.setReadOnly(True)
        self._shortcuts_content.setHtml(self._shortcuts_modes())
        self._shortcuts_content.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #e0e0e0;
                border: none;
                padding: 20px 30px;
                font-size: 14px;
            }
            h2 { color: #7c4dff; font-size: 24px; margin-bottom: 15px; border-bottom: 1px solid #3a3a50; padding-bottom: 10px; }
            h3 { color: #4fc3f7; font-size: 16px; margin-top: 20px; margin-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            td { padding: 10px 15px; border: 1px solid #3a3a50; }
            td:first-child { background-color: #252536; font-weight: bold; color: #4fc3f7; width: 150px; }
            tr:hover { background-color: #2a2a3c; }
        """)

        layout.addWidget(sidebar, 0)
        layout.addWidget(self._shortcuts_content, 1)
        return widget

    def _create_sidebar(self, sections: list[tuple[str, str]], content_list: list) -> QFrame:
        """Create left sidebar with navigation buttons."""
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.NoFrame)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #252536;
                border-right: 1px solid #3a3a50;
            }
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-size: 13px;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: #2a2a3c;
            }
            QPushButton:checked {
                background-color: #2a2a3c;
                border-left-color: #7c4dff;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar_buttons: list[QPushButton] = []
        content_list.clear()

        for i, (title, content) in enumerate(sections):
            btn = QPushButton(f"  {title}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._on_section_clicked(idx))
            layout.addWidget(btn)
            self._sidebar_buttons.append(btn)
            content_list.append(content)

        layout.addStretch()

        # Select first button
        if self._sidebar_buttons:
            self._sidebar_buttons[0].setChecked(True)

        return sidebar

    def _on_section_clicked(self, index: int) -> None:
        """Handle sidebar button click."""
        # Uncheck all other buttons
        for i, btn in enumerate(self._sidebar_buttons):
            if i != index:
                btn.setChecked(False)

        # Update content based on which tab is active
        current_tab = self._tabs.currentIndex()
        
        # Get the correct content list for current tab
        if current_tab == 0:  # Tutorial
            content = self._tutorial_sidebar_content[index]
            self._tutorial_content.setHtml(content)
        elif current_tab == 1:  # DSL
            content = self._dsl_sidebar_content[index]
            self._dsl_content.setHtml(content)
        elif current_tab == 2:  # Shortcuts
            content = self._shortcuts_sidebar_content[index]
            self._shortcuts_content.setHtml(content)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab switch - reset sidebar buttons."""
        # Reset sidebar buttons for new tab
        if hasattr(self, '_sidebar_buttons') and self._sidebar_buttons:
            for btn in self._sidebar_buttons:
                btn.setChecked(False)
            self._sidebar_buttons[0].setChecked(True)
            # Update content to first section
            self._on_section_clicked(0)

    def _tutorial_getting_started(self) -> str:
        return """\
<p>Welcome to <b>Graph Suite</b> — a powerful, intuitive tool for creating, editing, and analyzing graphs. 
This tutorial will guide you through everything you need to know.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; border-left: 4px solid #7c4dff; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #4fc3f7;"> Quick Start</h4>
  <ol style="margin: 10px 0;">
    <li>Press <b>N</b> and click to add nodes</li>
    <li>Press <b>E</b> and click two nodes to connect them</li>
    <li>Press <b>S</b> to select and drag nodes</li>
    <li>Run algorithms from the right panel</li>
  </ol>
</div>

<h3>The Interface</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b> Canvas</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Main workspace for creating and editing graphs</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b> Toolbar</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Quick access to tools, modes, and commands</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b> Matrices</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Edit graph structure as adjacency/incidence matrices</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b> Algorithms</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Run BFS, DFS, Dijkstra, MST, and more</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b> DSL Console</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Write scripts to automate graph creation</td>
  </tr>
</table>

<h3>Essential Shortcuts</h3>
<ul>
  <li><code>S</code> — Select mode</li>
  <li><code>N</code> — Add node mode</li>
  <li><code>E</code> — Add edge mode</li>
  <li><code>D</code> — Delete mode</li>
  <li><code>F</code> — Fit view to graph</li>
  <li><code>Ctrl+Z/Y</code> — Undo/Redo</li>
</ul>"""

    def _tutorial_nodes(self) -> str:
        return """\
<h3>Creating Nodes</h3>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Method 1: Canvas Tool</h4>
  <ol>
    <li>Press <b>N</b> or click "Add Node" in toolbar</li>
    <li>Click anywhere on the canvas</li>
    <li>Node appears with auto-generated name (v1, v2, ...)</li>
  </ol>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Method 2: Matrix Editor</h4>
  <ol>
    <li>Go to the Matrices panel</li>
    <li>Click "+ Node" button</li>
    <li>Enter a name (or accept default)</li>
  </ol>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Method 3: DSL Script</h4>
  <pre>node A at 100 200
node B at 300 200
nodes C D E at 150 300  # Multiple at once</pre>
</div>

<h3>Renaming Nodes</h3>
<ul>
  <li><b>Double-click</b> the node and type a new name</li>
  <li>Or right-click → "Rename…"</li>
  <li>Names can be any alphanumeric string</li>
</ul>

<h3>Coloring Nodes</h3>
<ul>
  <li>Right-click the node → "Change Color…"</li>
  <li>Use the color picker to choose any color</li>
  <li>Colors help visualize node groups or properties</li>
</ul>

<h3>Moving Nodes</h3>
<ul>
  <li>Select mode (<b>S</b>)</li>
  <li>Click and drag to move</li>
  <li><b>Ctrl+click</b> to select multiple, drag to move all</li>
</ul>"""

    def _tutorial_edges(self) -> str:
        return """\
<h3>Creating Edges</h3>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Basic Edge Creation</h4>
  <ol>
    <li>Press <b>E</b> or click "Add Edge" in toolbar</li>
    <li>Click the <b>source</b> node</li>
    <li>Click the <b>target</b> node</li>
    <li>Edge appears with arrow (directed graphs)</li>
  </ol>
</div>

<h3>Edge Types</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>→</b> Directed</td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">One-way connection (default)</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>↔</b> Bidirectional</td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Two-way on single edge (right-click → Make Bidirectional)</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>—</b> Undirected</td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Switch graph to undirected mode</td>
  </tr>
</table>

<h3>Edge Weights</h3>
<ol>
  <li>Enable "Weighted" mode in toolbar</li>
  <li>Double-click edge to edit weight</li>
  <li>Or edit directly in Adjacency Matrix</li>
  <li>Weights affect algorithms (Dijkstra, MST, etc.)</li>
</ol>

<h3>Curved Edges</h3>
<ul>
  <li>Hold <b>Ctrl</b> in Select mode</li>
  <li>Drag the handle at edge midpoint</li>
  <li>Useful for distinguishing parallel edges</li>
</ul>

<h3>Parallel Edges</h3>
<ul>
  <li>Hold <b>Shift</b> while creating edge</li>
  <li>Creates additional edge between same nodes</li>
  <li>Auto-curves for visual distinction</li>
</ul>"""

    def _tutorial_editing(self) -> str:
        return """\
<h3>Selecting Items</h3>
<ul>
  <li><b>Click</b> — Select single node/edge</li>
  <li><b>Ctrl+click</b> — Add to selection</li>
  <li><b>Click empty space</b> — Deselect all</li>
  <li>Selected items show highlight glow</li>
</ul>

<h3>Deleting Items</h3>
<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ef5350;">Method 1: Delete Tool</h4>
  <ol>
    <li>Press <b>D</b> or click "Delete" in toolbar</li>
    <li>Click the item to remove</li>
  </ol>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ef5350;">Method 2: Keyboard</h4>
  <ol>
    <li>Select items in Select mode</li>
    <li>Press <b>Delete</b> or <b>Backspace</b></li>
  </ol>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ef5350;">Method 3: Context Menu</h4>
  <ol>
    <li>Right-click the item</li>
    <li>Select "Delete Node" or "Delete Edge"</li>
  </ol>
</div>

<h3>Undo/Redo</h3>
<ul>
  <li><b>Ctrl+Z</b> — Undo last action</li>
  <li><b>Ctrl+Y</b> — Redo undone action</li>
  <li>Up to 100 actions stored</li>
  <li>Works for all operations (add, delete, move, edit)</li>
</ul>

<h3>Editing Properties</h3>
<ul>
  <li><b>Node color</b>: Right-click → "Change Color…"</li>
  <li><b>Node name</b>: Double-click or right-click → "Rename…"</li>
  <li><b>Edge weight</b>: Double-click (when weighted mode enabled)</li>
  <li><b>Edge curvature</b>: Ctrl+drag handle</li>
  <li><b>Edge direction</b>: Right-click → "Make Bidirectional"</li>
</ul>"""

    def _tutorial_navigation(self) -> str:
        return """\
<h3>Canvas Navigation</h3>
<p>Navigate large graphs efficiently with these navigation tools.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #4fc3f7;"> Panning</h4>
  <ul>
    <li><b>Middle mouse drag</b> — Pan from anywhere (works in any mode)</li>
    <li><b>Left drag on empty space</b> — Pan in Select mode</li>
    <li><b>Arrow keys</b> — Nudge view in small increments</li>
  </ul>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #4fc3f7;"> Zooming</h4>
  <ul>
    <li><b>Mouse wheel</b> — Zoom in/out at cursor position</li>
    <li><b>Ctrl + mouse wheel</b> — Fine-grained zoom control</li>
    <li><b>Toolbar buttons</b> — Click + or - buttons</li>
    <li><b>Ctrl + / Ctrl -</b> — Keyboard zoom shortcuts</li>
  </ul>
</div>

<h3>Fit View</h3>
<ul>
  <li><b>Press F</b> — Automatically fit all nodes on screen</li>
  <li><b>Toolbar → Fit</b> — Click the Fit button</li>
  <li>Resets zoom and pan to show entire graph</li>
  <li>Useful after importing large graphs</li>
</ul>

<h3>Zoom Levels</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>25%</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Overview of very large graphs</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>100%</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Normal working view (default)</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>200%+</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Precision editing of small details</td>
  </tr>
</table>

<h3>Navigation Tips</h3>
<ul>
  <li>Zoom out first to see overall structure</li>
  <li>Use Fit View after layout changes</li>
  <li>Middle-drag is fastest for repositioning</li>
  <li>Current zoom level shown in status bar</li>
</ul>"""

    def _tutorial_properties(self) -> str:
        return """\
<h3>Graph Properties</h3>
<p>Configure fundamental graph characteristics that affect algorithms and visualization.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ab47bc;">Directed vs Undirected</h4>
  <table style="width: 100%; margin-top: 10px;">
    <tr>
      <td style="padding: 10px;"><b>Directed</b></td>
      <td style="padding: 10px;">Edges have direction (A→B ≠ B→A)</td>
    </tr>
    <tr>
      <td style="padding: 10px;"><b>Undirected</b></td>
      <td style="padding: 10px;">Edges go both ways (A—B = B—A)</td>
    </tr>
  </table>
  <p style="margin-top: 10px;"><b>Toggle:</b> Toolbar → "Directed" button or Graph menu</p>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ab47bc;">Weighted vs Unweighted</h4>
  <table style="width: 100%; margin-top: 10px;">
    <tr>
      <td style="padding: 10px;"><b>Weighted</b></td>
      <td style="padding: 10px;">Edges have numeric weights (costs, distances)</td>
    </tr>
    <tr>
      <td style="padding: 10px;"><b>Unweighted</b></td>
      <td style="padding: 10px;">All edges treated equally (weight = 1)</td>
    </tr>
  </table>
  <p style="margin-top: 10px;"><b>Toggle:</b> Toolbar → "Weighted" button or Graph menu</p>
</div>

<h3>Matrix Editor</h3>
<p>Edit graph structure using mathematical representations.</p>

<h4>Adjacency Matrix</h4>
<ul>
  <li><b>Rows/Cols</b> represent nodes</li>
  <li><b>Cell value</b> = edge weight (0 = no edge)</li>
  <li><b>Click cell</b> to edit weight directly</li>
  <li><b>+ Node</b> adds new node to matrix</li>
  <li><b>Apply Matrix</b> rebuilds graph from matrix</li>
</ul>

<h4>Incidence Matrix</h4>
<ul>
  <li><b>Rows</b> = nodes, <b>Columns</b> = edges</li>
  <li><b>1</b> = edge starts at node</li>
  <li><b>-1</b> = edge ends at node (directed)</li>
  <li><b>2</b> = self-loop (undirected)</li>
  <li>Read-only view for reference</li>
</ul>

<h3>Algorithm Panel</h3>
<ul>
  <li><b>Dropdown</b> — Select algorithm</li>
  <li><b>Source/Target</b> — Enter node names</li>
  <li><b>Run</b> — Execute algorithm</li>
  <li><b>Results</b> — View output and highlights</li>
  <li><b>Clear Highlight</b> — Remove canvas highlights</li>
</ul>"""

    def _tutorial_algorithms(self) -> str:
        return """\
<h3>Running Algorithms</h3>
<p>Graph Suite includes powerful algorithms for analysis and visualization.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Step-by-Step</h4>
  <ol>
    <li>Open the <b>Algorithms</b> panel (right dock)</li>
    <li>Select an algorithm from the dropdown</li>
    <li>Enter required parameters (node names)</li>
    <li>Click <b>"Run"</b> button</li>
    <li>View results in output box</li>
    <li>Highlighted elements appear on canvas</li>
  </ol>
</div>

<h3>Algorithm Categories</h3>

<h4> Traversal Algorithms</h4>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>BFS</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Breadth-First Search — level-by-level exploration</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>DFS</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Depth-First Search — path-following exploration</td>
  </tr>
</table>

<h4> Shortest Path Algorithms</h4>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Dijkstra</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Fastest path (non-negative weights)</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Bellman-Ford</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Handles negative weights, detects negative cycles</td>
  </tr>
</table>

<h4> Structural Algorithms</h4>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>MST</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Minimum Spanning Tree (undirected graphs)</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Topological Sort</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Linear ordering (directed acyclic graphs)</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Components</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Connected components identification</td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>SCC</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;">Strongly Connected Components (directed)</td>
  </tr>
</table>

<h3>Understanding Results</h3>
<ul>
  <li><b>Text output</b> — Algorithm results in Results box</li>
  <li><b>Node highlights</b> — Affected nodes glow on canvas</li>
  <li><b>Edge highlights</b> — Path edges highlighted</li>
  <li><b>Clear</b> — Click "Clear Highlight" to reset view</li>
</ul>

<h3>Algorithm Requirements</h3>
<ul>
  <li><b>MST</b> — Requires undirected graph</li>
  <li><b>Topological Sort</b> — Requires directed acyclic graph</li>
  <li><b>Dijkstra</b> — Requires non-negative weights</li>
  <li><b>SCC</b> — Requires directed graph</li>
</ul>"""

    def _tutorial_export(self) -> str:
        return """\
<h3>Saving & Loading</h3>
<p>Preserve your work and share graphs with others.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ffa726;"> Save Graph</h4>
  <ul>
    <li><b>File → Save</b> (Ctrl+S) — Save to current file</li>
    <li><b>File → Save As…</b> (Ctrl+Shift+S) — Choose new location</li>
    <li><b>Format</b> — JSON (.graph.json)</li>
    <li><b>Includes</b> — Nodes, edges, weights, positions, colors</li>
  </ul>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ffa726;"> Open Graph</h4>
  <ul>
    <li><b>File → Open…</b> (Ctrl+O) — Load saved graph</li>
    <li><b>Recent Files</b> — Access recently opened graphs</li>
    <li><b>Auto-recovery</b> — Unsaved work preserved on crash</li>
  </ul>
</div>

<h3>Exporting Images</h3>
<ul>
  <li><b>File → Export PNG…</b> — Save canvas as image</li>
  <li><b>Resolution</b> — Current view resolution</li>
  <li><b>Transparent BG</b> — Option for transparent background</li>
  <li><b>Use case</b> — Presentations, documentation, sharing</li>
</ul>

<h3>DSL Export</h3>
<ul>
  <li><b>DSL Console → "Graph → Script"</b></li>
  <li>Generates DSL code from current graph</li>
  <li>Useful for documentation and reproducibility</li>
  <li>Can be edited and re-run</li>
</ul>

<h3>File Format Details</h3>
<pre style="background-color: #252536; padding: 15px; border-radius: 6px;">
{
  "directed": true,
  "weighted": true,
  "nodes": [
    {"name": "A", "x": 100, "y": 200, "color": "#4fc3f7"}
  ],
  "edges": [
    {"source": "A", "target": "B", "weight": 5}
  ]
}
</pre>

<h3>Best Practices</h3>
<ul>
  <li>Save frequently during editing</li>
  <li>Use descriptive filenames</li>
  <li>Export PNG for presentations</li>
  <li>Keep DSL scripts for reproducibility</li>
  <li>Version control with Git for complex graphs</li>
</ul>"""

    def _dsl_intro(self) -> str:
        return """\
<h3>What is DSL?</h3>
<p>The <b>Domain Specific Language (DSL)</b> is a text-based scripting language for Graph Suite. 
Write scripts to create, modify, and analyze graphs programmatically.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #7c4dff;">
  <h4 style="margin-top: 0; color: #4fc3f7;"> Why Use DSL?</h4>
  <ul>
    <li><b>Speed</b> — Create complex graphs with few lines</li>
    <li><b>Precision</b> — Exact coordinates and weights</li>
    <li><b>Reproducibility</b> — Save and re-run scripts</li>
    <li><b>Automation</b> — Batch operations and algorithms</li>
    <li><b>Sharing</b> — Text files are easy to share</li>
  </ul>
</div>

<h3>Using the DSL Console</h3>
<ol>
  <li>Open the <b>DSL Console</b> panel (bottom dock)</li>
  <li>Type your script in the editor</li>
  <li>Click <b>"Run Script"</b> or press Ctrl+Enter</li>
  <li>View output in the output pane</li>
  <li>Graph appears on canvas with highlights</li>
</ol>

<h3>Console Features</h3>
<ul>
  <li><b>Syntax highlighting</b> — Keywords, numbers, arrows colored</li>
  <li><b>Command hints</b> — Type a command to see syntax</li>
  <li><b>Graph → Script</b> — Export current graph as DSL</li>
  <li><b>Example</b> — Load sample script</li>
</ul>"""

    def _dsl_settings(self) -> str:
        return """\
<h3>Comments</h3>
<p>Comments start with <code>#</code> and are ignored by the interpreter.</p>
<pre># This is a comment
node A at 100 100  # Inline comment</pre>

<h3>Graph Mode Settings</h3>
<p>Configure graph properties before creating nodes and edges.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ab47bc;">Directed vs Undirected</h4>
  <pre>set directed true     # Directed edges (default)
set directed false    # Undirected edges</pre>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #ab47bc;">Weighted vs Unweighted</h4>
  <pre>set weighted true     # Enable edge weights
set weighted false    # Disable weights (default)</pre>
</div>

<h3>Output Control</h3>
<pre>cmdoutput true      # Show command output (default)
cmdoutput false     # Silent mode (only print shows)</pre>"""

    def _dsl_nodes(self) -> str:
        return """\
<h3>Creating Nodes</h3>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Single Node</h4>
  <pre>node A                    # Auto-positioned
node B at 100 200       # Specific coordinates</pre>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Multiple Nodes</h4>
  <pre>nodes A B C D           # Multiple at once
nodes X Y Z at 300 400  # Multiple at same position</pre>
</div>

<h3>Node Operations</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Delete</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>delete node A</code></td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Rename</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>rename old new</code></td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Color</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>color A #ff5500</code></td>
  </tr>
</table>

<h3>Layout Commands</h3>
<pre>grid 3 3              # 3x3 grid of nodes
grid 4 5 spacing 100  # Custom spacing
circle 6              # 6 nodes in circle
circle 8 radius 200   # Custom radius</pre>"""

    def _dsl_edges(self) -> str:
        return """\
<h3>Creating Edges</h3>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Edge Types</h4>
  <pre>edge A -> B             # Directed edge
edge A -- B             # Undirected edge  
edge A <-> B            # Bidirectional edge</pre>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">With Weights</h4>
  <pre>edge A -> B weight 5    # Weighted directed
edge A -- B weight 3    # Weighted undirected</pre>
</div>

<h3>Multiple Edges</h3>
<pre>edges A B C -> D      # Multiple sources to one target
edges A B -> C D      # Multiple to multiple (creates all)</pre>

<h3>Edge Patterns</h3>
<pre>path A B C D          # Chain: A→B→C→D
cycle A B C D         # Cycle: A→B→C→D→A
connect A B C D       # Complete graph (all pairs)</pre>

<h3>Edge Operations</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Delete</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>delete edge A B</code></td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Toggle Bidi</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>toggle A B</code></td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Separate</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>separate A B</code></td>
  </tr>
  <tr>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><b>Curve</b></td>
    <td style="padding: 10px; border: 1px solid #3a3a50;"><code>curve A B 50</code></td>
  </tr>
</table>"""

    def _dsl_algorithms(self) -> str:
        return """\
<h3>Running Algorithms</h3>
<p>Execute graph algorithms directly from DSL scripts.</p>

<h4> Traversal</h4>
<pre>run bfs from A        # Breadth-first search
run dfs from A        # Depth-first search</pre>

<h4> Shortest Path</h4>
<pre>run dijkstra from A to B    # Dijkstra's algorithm
run bellman from A to B     # Bellman-Ford algorithm</pre>

<h4> Structural Analysis</h4>
<pre>run mst               # Minimum spanning tree (undirected)
run topo              # Topological sort (DAG)
run components        # Connected components
run scc               # Strongly connected components
run cycle             # Find cycles
run centrality        # Degree centrality
run info              # Graph statistics</pre>

<h3>Algorithm Output</h3>
<ul>
  <li><b>Text results</b> — Printed to output pane</li>
  <li><b>Node highlights</b> — Affected nodes glow on canvas</li>
  <li><b>Edge highlights</b> — Path edges highlighted</li>
  <li><b>Clear with</b> — Click "Clear Highlight" button</li>
</ul>"""

    def _dsl_layout(self) -> str:
        return """\
<h3>Layout Commands</h3>
<p>Automatically arrange nodes using layout algorithms.</p>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Circle Layout</h4>
  <pre>layout circle         # Arrange nodes in circle</pre>
  <p>Useful for: Cycles, complete graphs, symmetric structures</p>
</div>

<div style="background-color: #252536; padding: 15px; border-radius: 6px; margin: 15px 0;">
  <h4 style="margin-top: 0; color: #66bb6a;">Spring Layout</h4>
  <pre>layout spring         # Force-directed layout</pre>
  <p>Useful for: General graphs, revealing structure</p>
</div>

<h3>View Commands</h3>
<pre>fit                   # Fit view to show all nodes</pre>

<h3>Clear Command</h3>
<pre>clear                 # Remove all nodes and edges</pre>
<p>Useful for starting fresh in a script.</p>"""

    def _dsl_examples(self) -> str:
        return """\
<h3>Example Scripts</h3>
<p>Copy and modify these examples for your own graphs.</p>

<h4> Simple Path Graph</h4>
<pre>set directed true
node A at 100 200
node B at 250 200
node C at 400 200
edge A -> B
edge B -> C</pre>

<h4> Weighted Cycle</h4>
<pre>set weighted true
node 1 at 200 100
node 2 at 350 200
node 3 at 300 350
node 4 at 100 350
node 5 at 50 200
edge 1 -> 2 weight 3
edge 2 -> 3 weight 1
edge 3 -> 4 weight 4
edge 4 -> 5 weight 2
edge 5 -> 1 weight 5</pre>

<h4> Complete Graph K5</h4>
<pre>set directed false
connect A B C D E
layout circle</pre>

<h4> Full Analysis Script</h4>
<pre># Create and analyze a graph
set directed false
set weighted true

# Create nodes in pentagon
circle 5 radius 150

# Connect as cycle
cycle v1 v2 v3 v4 v5 weight 1

# Add chords
edge v1 -- v3 weight 2
edge v2 -- v4 weight 2

# Run analysis
run mst
run bfs from v1
run info</pre>"""

    def _shortcuts_modes(self) -> str:
        return """\
<h3>Tool Modes</h3>
<p>Quick-switch between editing modes using keyboard shortcuts.</p>

<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">S</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Select Mode</b> — Select and move nodes</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">N</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Add Node</b> — Click to place nodes</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">E</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Add Edge</b> — Click two nodes to connect</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">D</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Delete</b> — Click to remove items</td>
  </tr>
</table>

<h3>Mode Tips</h3>
<ul>
  <li>Current mode shown in status bar</li>
  <li>Mode icon displayed on cursor</li>
  <li>Press Esc to cancel current operation</li>
</ul>"""

    def _shortcuts_view(self) -> str:
        return """\
<h3>View Navigation</h3>
<p>Navigate and adjust the canvas view efficiently.</p>

<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">F</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Fit View</b> — Show all nodes</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl +</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Zoom In</b> — Magnify view</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl -</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Zoom Out</b> — Reduce view</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Mouse Wheel</b></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Zoom</b> — Scroll to zoom in/out</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Middle Drag</b></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Pan</b> — Drag to move view</td>
  </tr>
</table>

<h3>Zoom Tips</h3>
<ul>
  <li>Zoom level shown in status bar</li>
  <li>Mouse wheel zooms at cursor position</li>
  <li>Fit View useful after layout changes</li>
</ul>"""

    def _shortcuts_edit(self) -> str:
        return """\
<h3>Editing Shortcuts</h3>
<p>Essential shortcuts for editing operations.</p>

<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+Z</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Undo</b> — Reverse last action</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+Y</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Redo</b> — Restore undone action</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Delete</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Delete</b> — Remove selected items</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+Click</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Multi-select</b> — Add to selection</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Esc</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Cancel</b> — Clear selection/deselect</td>
  </tr>
</table>

<h3>Selection Tips</h3>
<ul>
  <li>Selected nodes show highlight glow</li>
  <li>Drag multiple selected nodes together</li>
  <li>Click empty space to deselect all</li>
</ul>"""

    def _shortcuts_file(self) -> str:
        return """\
<h3>File Operations</h3>
<p>Manage graph files with these shortcuts.</p>

<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+N</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>New Graph</b> — Create blank graph</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+O</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Open</b> — Load saved graph</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+S</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Save</b> — Save to current file</td>
  </tr>
  <tr>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+Shift+S</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Save As</b> — Choose new location</td>
  </tr>
  <tr style="background-color: #252536;">
    <td style="padding: 12px; border: 1px solid #3a3a50;"><code style="font-size: 14px;">Ctrl+Q</code></td>
    <td style="padding: 12px; border: 1px solid #3a3a50;"><b>Quit</b> — Exit application</td>
  </tr>
</table>

<h3>File Tips</h3>
<ul>
  <li>Auto-save on crash recovery</li>
  <li>Recent files in File menu</li>
  <li>Format: JSON (.graph.json)</li>
</ul>"""
