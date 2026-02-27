"""Main application window – toolbar, menus, docks, coordination."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter, QColor, QActionGroup
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QFileDialog,
    QMessageBox, QStatusBar, QToolButton, QWidget,
    QLabel, QDialog, QVBoxLayout, QTextEdit, QTabWidget,
    QScrollArea, QFrame,
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
        self.setMinimumSize(900, 700)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_tutorial_tab(), "Tutorial")
        tabs.addTab(self._create_dsl_tab(), "DSL Reference")
        tabs.addTab(self._create_shortcuts_tab(), "Shortcuts")

        layout.addWidget(tabs)

    def _create_tutorial_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)

        sections = [
            ("Getting Started", self._tutorial_getting_started()),
            ("Creating Nodes", self._tutorial_nodes()),
            ("Creating Edges", self._tutorial_edges()),
            ("Selecting & Editing", self._tutorial_editing()),
            ("Navigation", self._tutorial_navigation()),
            ("Graph Properties", self._tutorial_properties()),
            ("Running Algorithms", self._tutorial_algorithms()),
            ("Saving & Exporting", self._tutorial_export()),
        ]

        for title, html in sections:
            label = QLabel()
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText(f"<h2>{title}</h2>{html}")
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)

        layout.addStretch()
        scroll.setWidget(content)
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(scroll)
        return widget

    def _tutorial_getting_started(self) -> str:
        return """\
<p>Welcome to Graph Suite! This tutorial will guide you through the basics.</p>

<h3>The Interface</h3>
<ul>
  <li><b>Canvas (center)</b> — Where you create and edit your graph</li>
  <li><b>Toolbar (top)</b> — Quick access to tools and commands</li>
  <li><b>Adjacency Matrix (right)</b> — Edit graph structure as a matrix</li>
  <li><b>Algorithms (right)</b> — Run graph algorithms</li>
  <li><b>Script Console (bottom)</b> — Write and execute DSL scripts</li>
</ul>

<h3>Your First Graph</h3>
<ol>
  <li>Click the <b>"Add Node"</b> button (or press <b>N</b>)</li>
  <li>Click anywhere on the canvas to place a node</li>
  <li>Click <b>"Add Edge"</b> (or press <b>E</b>)</li>
  <li>Click two nodes to connect them</li>
</ol>"""

    def _tutorial_nodes(self) -> str:
        return """\
<h3>Add a Node</h3>
<ol>
  <li>Select the <b>"Add Node"</b> tool from toolbar (or press <b>N</b>)</li>
  <li>Click on the canvas where you want the node</li>
  <li>Nodes are auto-named (v1, v2, ...) or use context menu to name</li>
</ol>

<h3>Name a Node</h3>
<ul>
  <li><b>Double-click</b> the node to rename it</li>
  <li>Or right-click → "Rename…"</li>
</ul>

<h3>Color a Node</h3>
<ul>
  <li>Right-click the node → "Change Color…"</li>
  <li>Pick a color from the dialog</li>
</ul>

<h3>Move a Node</h3>
<ul>
  <li>Select mode (<b>S</b>)</li>
  <li>Click and drag the node</li>
  <li>Drag multiple: Ctrl+click to select, then drag</li>
</ul>"""

    def _tutorial_edges(self) -> str:
        return """\
<h3>Add an Edge</h3>
<ol>
  <li>Select <b>"Add Edge"</b> tool (or press <b>E</b>)</li>
  <li>Click the source node</li>
  <li>Click the target node</li>
</ol>

<h3>Set Edge Weight</h3>
<ul>
  <li>Enable weighted mode: toggle "Weighted" in toolbar</li>
  <li>Double-click the edge to edit weight</li>
  <li>Or edit directly in the Adjacency Matrix</li>
</ul>

<h3>Directed vs Undirected</h3>
<ul>
  <li><b>Directed</b>: Edges have direction (arrow)</li>
  <li><b>Undirected</b>: Edges go both ways (no arrow)</li>
  <li>Toggle with the "Directed" button or Graph menu</li>
</ul>

<h3>Bidirectional Edges</h3>
<p>Create two opposite edges between same nodes, or use DSL: <code>edge A &lt;-&gt; B</code></p>"""

    def _tutorial_editing(self) -> str:
        return """\
<h3>Select Items</h3>
<ul>
  <li>Click a node to select it</li>
  <li>Ctrl+click to add to selection</li>
  <li>Click empty space to deselect</li>
</ul>

<h3>Delete Items</h3>
<ul>
  <li>Select <b>"Delete"</b> tool (or press <b>D</b>)</li>
  <li>Click the node or edge to remove</li>
  <li>Or select and press <b>Delete</b> key</li>
</ul>

<h3>Undo/Redo</h3>
<ul>
  <li><b>Ctrl+Z</b> — Undo last action</li>
  <li><b>Ctrl+Y</b> — Redo undone action</li>
  <li>Undo history shown in status bar</li>
</ul>"""

    def _tutorial_navigation(self) -> str:
        return """\
<h3>Pan the View</h3>
<ul>
  <li><b>Click-drag on empty space</b> to pan</li>
  <li><b>Middle mouse drag</b> to pan (any mode)</li>
</ul>

<h3>Zoom</h3>
<ul>
  <li><b>Mouse wheel</b> — Zoom in/out</li>
  <li><b>Zoom + / -</b> buttons in toolbar</li>
  <li><b>Ctrl++ / Ctrl+-</b> keyboard shortcuts</li>
</ul>

<h3>Fit View</h3>
<ul>
  <li>Press <b>F</b> to fit all nodes on screen</li>
  <li>Or click "Fit" in toolbar</li>
</ul>"""

    def _tutorial_properties(self) -> str:
        return """\
<h3>Toggle Graph Type</h3>
<ul>
  <li><b>Directed/Undirected</b>: Toolbar toggle or Graph menu</li>
  <li><b>Weighted/Unweighted</b>: Toolbar toggle or Graph menu</li>
</ul>

<h3>Matrix Editor</h3>
<ul>
  <li><b>Adjacency Matrix</b>: Edit edge weights directly</li>
  <li><b>Incidence Matrix</b>: View node-edge relationships</li>
  <li>Click "+ Node" to add nodes from matrix</li>
  <li>Click "Apply Matrix" to rebuild from edits</li>
</ul>"""

    def _tutorial_algorithms(self) -> str:
        return """\
<h3>Run an Algorithm</h3>
<ol>
  <li>Open the "Algorithms" panel (right dock)</li>
  <li>Select an algorithm from dropdown</li>
  <li>Enter required parameters (source/target nodes)</li>
  <li>Click "Run"</li>
</ol>

<h3>Available Algorithms</h3>
<ul>
  <li><b>BFS/DFS Traversal</b> — Explore graph order</li>
  <li><b>Dijkstra/Bellman-Ford</b> — Shortest path</li>
  <li><b>MST</b> — Minimum spanning tree (undirected)</li>
  <li><b>Topological Sort</b> — Ordering (directed acyclic)</li>
  <li><b>Components</b> — Connected components</li>
  <li><b>SCC</b> — Strongly connected components</li>
  <li><b>Cycle Detection</b> — Find cycles</li>
  <li><b>Centrality</b> — Node importance</li>
</ul>

<h3>Results</h3>
<ul>
  <li>Output appears in the Results box</li>
  <li>Highlighted nodes/edges shown on canvas</li>
  <li>Click "Clear Highlight" to remove</li>
</ul>"""

    def _tutorial_export(self) -> str:
        return """\
<h3>Save Graph</h3>
<ul>
  <li><b>File → Save</b> (Ctrl+S)</li>
  <li><b>File → Save As…</b> (Ctrl+Shift+S)</li>
  <li>Format: JSON (.graph.json)</li>
</ul>

<h3>Export as Image</h3>
<ul>
  <li><b>File → Export PNG…</b></li>
  <li>Choose location and filename</li>
  <li>Current canvas view is exported</li>
</ul>

<h3>Load Graph</h3>
<ul>
  <li><b>File → Open…</b> (Ctrl+O)</li>
  <li>Select a .graph.json file</li>
</ul>"""

    def _create_dsl_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)

        sections = [
            ("Introduction", self._dsl_intro()),
            ("Comments & Settings", self._dsl_settings()),
            ("Node Commands", self._dsl_nodes()),
            ("Edge Commands", self._dsl_edges()),
            ("Algorithm Commands", self._dsl_algorithms()),
            ("Layout Commands", self._dsl_layout()),
            ("Example Scripts", self._dsl_examples()),
        ]

        for title, html in sections:
            label = QLabel()
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText(f"<h2>{title}</h2>{html}")
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)

        layout.addStretch()
        scroll.setWidget(content)
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(scroll)
        return widget

    def _dsl_intro(self) -> str:
        return """\
<p>The DSL (Domain Specific Language) lets you script graph operations.
Write scripts in the Console panel at the bottom and click "Run Script".</p>

<h3>Why Use DSL?</h3>
<ul>
  <li>Create complex graphs quickly</li>
  <li>Reproduce graphs exactly</li>
  <li>Automate repetitive tasks</li>
  <li>Share graph definitions</li>
</ul>"""

    def _dsl_settings(self) -> str:
        return """\
<h3>Comments</h3>
<pre># Lines starting with # are ignored</pre>

<h3>Graph Mode</h3>
<pre>set directed true    # Directed edges (default)
set directed false   # Undirected edges
set weighted true    # Enable weights
set weighted false   # Disable weights (default)</pre>"""

    def _dsl_nodes(self) -> str:
        return """\
<h3>Add Node</h3>
<pre>node A              # Auto position
node B at 100 200   # Specific coordinates</pre>

<h3>Delete Node</h3>
<pre>delete node A</pre>

<h3>Rename Node</h3>
<pre>rename old new</pre>

<h3>Set Color</h3>
<pre>color A #ff5500    # Hex color code</pre>"""

    def _dsl_edges(self) -> str:
        return """\
<h3>Add Directed Edge</h3>
<pre>edge A -> B              # Basic directed
edge A -> B weight 5     # With weight</pre>

<h3>Add Undirected Edge</h3>
<pre>edge A -- B              # Undirected</pre>

<h3>Add Bidirectional Edges</h3>
<pre>edge A <-> B             # Both directions at once</pre>

<h3>Delete Edge</h3>
<pre>delete edge A B</pre>"""

    def _dsl_algorithms(self) -> str:
        return """\
<h3>Traversal</h3>
<pre>run bfs from A       # Breadth-first search
run dfs from A       # Depth-first search</pre>

<h3>Shortest Path</h3>
<pre>run dijkstra from A to B
run bellman from A to B</pre>

<h3>Structural Analysis</h3>
<pre>run mst              # Minimum spanning tree
run topo             # Topological sort
run components       # Connected components
run scc              # Strongly connected components
run cycle            # Find cycles
run centrality       # Degree centrality
run info             # Graph statistics</pre>"""

    def _dsl_layout(self) -> str:
        return """\
<h3>Apply Layout</h3>
<pre>layout circle        # Circular arrangement
layout spring        # Force-directed</pre>

<h3>View & Clear</h3>
<pre>fit                  # Fit view to nodes
clear                # Remove everything</pre>"""

    def _dsl_examples(self) -> str:
        return """\
<h3>Simple Path Graph</h3>
<pre>set directed true
node A at 100 200
node B at 250 200
node C at 400 200
edge A -> B
edge B -> C</pre>

<h3>Weighted Cycle</h3>
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

<h3>Complete Script</h3>
<pre># Create and analyze a graph
set directed false
set weighted true

# Nodes in a pentagon
node A at 200 100
node B at 350 200
node C at 300 350
node D at 100 350
node E at 50 200

# Edges with weights
edge A -- B weight 4
edge B -- C weight 2
edge C -- D weight 3
edge D -- E weight 1
edge E -- A weight 5

# Run algorithms
run mst
run bfs from A</pre>"""

    def _create_shortcuts_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)

        shortcuts = """\
<h2>Keyboard Shortcuts</h2>

<h3>Modes</h3>
<table cellpadding="8">
  <tr><td><b>S</b></td><td>Select mode</td></tr>
  <tr><td><b>N</b></td><td>Add node mode</td></tr>
  <tr><td><b>E</b></td><td>Add edge mode</td></tr>
  <tr><td><b>D</b></td><td>Delete mode</td></tr>
</table>

<h3>View</h3>
<table cellpadding="8">
  <tr><td><b>F</b></td><td>Fit view</td></tr>
  <tr><td><b>Ctrl++</b></td><td>Zoom in</td></tr>
  <tr><td><b>Ctrl+-</b></td><td>Zoom out</td></tr>
  <tr><td><b>Mouse wheel</b></td><td>Zoom in/out</td></tr>
  <tr><td><b>Middle drag</b></td><td>Pan view</td></tr>
</table>

<h3>Edit</h3>
<table cellpadding="8">
  <tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
  <tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
  <tr><td><b>Delete</b></td><td>Delete selected</td></tr>
  <tr><td><b>Ctrl+click</b></td><td>Add to selection</td></tr>
</table>

<h3>File</h3>
<table cellpadding="8">
  <tr><td><b>Ctrl+N</b></td><td>New graph</td></tr>
  <tr><td><b>Ctrl+O</b></td><td>Open graph</td></tr>
  <tr><td><b>Ctrl+S</b></td><td>Save graph</td></tr>
  <tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>
</table>
"""
        label = QLabel(shortcuts)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)
        layout.addStretch()

        scroll.setWidget(content)
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(scroll)
        return widget
