"""Main application window – toolbar, menus, docks, coordination."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter, QColor, QActionGroup
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QFileDialog,
    QMessageBox, QStatusBar, QToolButton, QWidget,
    QLabel,
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
        matrix_dock = QDockWidget("Adjacency Matrix", self)
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
        QMessageBox.information(
            self, "DSL Reference",
            "<h3>Graph DSL Commands</h3>"
            "<pre>"
            "set directed true|false\n"
            "set weighted true|false\n\n"
            "node &lt;name&gt; [at &lt;x&gt; &lt;y&gt;]\n"
            "edge &lt;src&gt; -&gt; &lt;tgt&gt; [weight &lt;w&gt;]\n"
            "edge &lt;src&gt; -- &lt;tgt&gt; [weight &lt;w&gt;]\n\n"
            "delete node &lt;name&gt;\n"
            "delete edge &lt;src&gt; &lt;tgt&gt;\n"
            "rename &lt;old&gt; &lt;new&gt;\n"
            "color &lt;node&gt; #rrggbb\n\n"
            "run bfs|dfs from &lt;src&gt;\n"
            "run dijkstra from &lt;src&gt; to &lt;tgt&gt;\n"
            "run bellman from &lt;src&gt; to &lt;tgt&gt;\n"
            "run mst | topo | components | scc\n"
            "run cycle | info\n\n"
            "layout circle | spring\n"
            "clear\n"
            "fit\n"
            "</pre>"
            "<p><i># comments start with hash</i></p>")
