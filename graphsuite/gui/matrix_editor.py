"""Adjacency and Incidence matrix editor – QTableWidget synced with the Graph model."""

from __future__ import annotations

import random
import numpy as np
from PySide6.QtCore import Qt, Signal, QRect, QItemSelectionRange
from PySide6.QtGui import QColor, QAction, QKeySequence, QKeyEvent, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QInputDialog, QAbstractItemView, QTabWidget, QGroupBox,
    QMenu, QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QCheckBox, QMessageBox,
)

from graphsuite.core.graph import Graph, GraphEvent
from graphsuite.gui.style import Colors


class MatrixEditor(QWidget):
    """Editable adjacency and incidence matrix view of the graph."""

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._updating = False  # guard against feedback loops
        self._clipboard: list[list[str]] = []  # Store copied values
        self._clipboard_shape: tuple[int, int] = (0, 0)
        self._highlighted_edges: set[str] = set()  # For path highlighting

        self._build_ui()
        self.graph.add_listener(self._on_graph_event)
        self._refresh()

    # -- UI ----------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Group box for the whole matrix editor
        group = QGroupBox()
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(4, 4, 4, 4)
        group_layout.setSpacing(4)

        # Tab widget for adjacency and incidence matrices
        self._tabs = QTabWidget()
        group_layout.addWidget(self._tabs)

        layout.addWidget(group)

        # === Adjacency Matrix Tab ===
        adj_widget = QWidget()
        adj_layout = QVBoxLayout(adj_widget)
        adj_layout.setContentsMargins(4, 4, 4, 4)
        adj_layout.setSpacing(4)

        # button row for adjacency
        adj_btn_row = QHBoxLayout()
        self._btn_add = QPushButton("+ Node")
        self._btn_add.setToolTip("Add a new node")
        self._btn_add.clicked.connect(self._add_node)

        self._btn_remove = QPushButton("− Node")
        self._btn_remove.setToolTip("Remove selected node (column/row)")
        self._btn_remove.clicked.connect(self._remove_node)

        self._btn_presets = QPushButton("Presets")
        self._btn_presets.setToolTip("Generate common graph structures")
        self._btn_presets.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: {Colors.TEXT_BRIGHT};
                border: 1px solid {Colors.PRIMARY};
                border-radius: 5px;
                padding: 5px 14px;
                min-height: 22px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
                border-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY};
            }}
        """)
        self._btn_presets.clicked.connect(self._show_graph_presets)

        self._btn_apply = QPushButton("Apply Matrix")
        self._btn_apply.setToolTip("Rebuild graph from current matrix values")
        self._btn_apply.clicked.connect(self._apply_matrix)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.setToolTip("Reload matrix from graph")
        self._btn_refresh.clicked.connect(self._refresh)

        adj_btn_row.addWidget(self._btn_add)
        adj_btn_row.addWidget(self._btn_remove)
        adj_btn_row.addWidget(self._btn_presets)
        adj_btn_row.addStretch()
        adj_btn_row.addWidget(self._btn_apply)
        adj_btn_row.addWidget(self._btn_refresh)
        adj_layout.addLayout(adj_btn_row)

        # info and symmetric toggle row
        info_row = QHBoxLayout()
        self._info = QLabel()
        self._info.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 11px;")
        info_row.addWidget(self._info)

        self._symmetric_toggle = QCheckBox("Symmetric Fill")
        self._symmetric_toggle.setToolTip("When enabled, changes to cell (i,j) also apply to (j,i)")
        self._symmetric_toggle.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_DIM};
                font-size: 11px;
                spacing: 4px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {Colors.BORDER};
                border-radius: 3px;
                background-color: {Colors.BG_INPUT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
        """)
        self._symmetric_toggle.stateChanged.connect(self._on_symmetric_toggle)
        info_row.addStretch()
        info_row.addWidget(self._symmetric_toggle)
        adj_layout.addLayout(info_row)

        # adjacency table
        self._adj_table = QTableWidget()
        self._adj_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ContiguousSelection)
        self._adj_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems)
        self._adj_table.setEditTriggers(
            QAbstractItemView.EditTrigger.EditKeyPressed)
        self._adj_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._adj_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._adj_table.cellChanged.connect(self._on_cell_changed)
        self._adj_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._adj_table.customContextMenuRequested.connect(self._show_context_menu)
        self._adj_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._adj_table.itemSelectionChanged.connect(self._on_selection_changed)
        # Enable header context menus via event filter
        self._adj_table.horizontalHeader().setSectionsClickable(True)
        self._adj_table.verticalHeader().setSectionsClickable(True)
        self._adj_table.horizontalHeader().installEventFilter(self)
        self._adj_table.verticalHeader().installEventFilter(self)
        # Install event filter for keyboard shortcuts
        self._adj_table.installEventFilter(self)
        adj_layout.addWidget(self._adj_table)

        # Selection info label
        self._selection_info = QLabel()
        self._selection_info.setStyleSheet(f"color: {Colors.SECONDARY}; font-size: 11px; font-weight: bold;")
        self._selection_info.hide()
        adj_layout.addWidget(self._selection_info)

        self._tabs.addTab(adj_widget, "Adjacency Matrix")

        # === Incidence Matrix Tab ===
        inc_widget = QWidget()
        inc_layout = QVBoxLayout(inc_widget)
        inc_layout.setContentsMargins(4, 4, 4, 4)
        inc_layout.setSpacing(4)

        # button row for incidence
        inc_btn_row = QHBoxLayout()
        self._btn_inc_refresh = QPushButton("Refresh")
        self._btn_inc_refresh.setToolTip("Reload incidence matrix from graph")
        self._btn_inc_refresh.clicked.connect(self._refresh_incidence)
        inc_btn_row.addWidget(self._btn_inc_refresh)
        inc_btn_row.addStretch()
        inc_layout.addLayout(inc_btn_row)

        # info label for incidence
        self._inc_info = QLabel()
        self._inc_info.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 11px;")
        inc_layout.addWidget(self._inc_info)

        # incidence table (read-only)
        self._inc_table = QTableWidget()
        self._inc_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._inc_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._inc_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._inc_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        inc_layout.addWidget(self._inc_table)

        self._tabs.addTab(inc_widget, "Incidence Matrix")

    # -- refresh from model ------------------------------------------------

    def _refresh(self) -> None:
        self._refresh_adjacency()
        self._refresh_incidence()

    def _refresh_adjacency(self) -> None:
        self._updating = True
        try:
            mat, names = self.graph.get_adjacency_matrix()
            n = len(names)

            self._adj_table.setRowCount(n)
            self._adj_table.setColumnCount(n)
            self._adj_table.setHorizontalHeaderLabels(names)
            self._adj_table.setVerticalHeaderLabels(names)

            # Build a lookup for highlighted edges
            highlighted_cells = set()
            for edge_id in self._highlighted_edges:
                edge = self.graph.get_edge_by_id(edge_id)
                if edge:
                    if edge.source in names and edge.target in names:
                        highlighted_cells.add((names.index(edge.source), names.index(edge.target)))
                        if not self.graph.directed:
                            highlighted_cells.add((names.index(edge.target), names.index(edge.source)))

            # Build a lookup for bidirectional edges
            bidi_edges = {}
            for e in self.graph.edges:
                if e.bidirectional:
                    bidi_edges[(e.source, e.target)] = e.weight

            for i in range(n):
                for j in range(n):
                    val = mat[i][j]

                    # Check if there's a bidirectional edge in reverse direction
                    # If so, show its weight in this cell too
                    if val == 0 and self.graph.directed:
                        src, tgt = names[i], names[j]
                        # Check if tgt→src is bidirectional (show in src→tgt cell)
                        if (tgt, src) in bidi_edges:
                            val = bidi_edges[(tgt, src)]

                    item = QTableWidgetItem(
                        f"{val:g}" if val != 0 else "0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Check if this cell should be highlighted
                    is_highlighted = (i, j) in highlighted_cells
                    
                    # colour non-zero cells
                    if is_highlighted:
                        item.setForeground(QColor(Colors.ALGO_HIGHLIGHT))
                        item.setFont(self._get_bold_font())
                    elif val != 0:
                        item.setForeground(QColor(Colors.SECONDARY))
                    else:
                        item.setForeground(QColor(Colors.TEXT_DIM))
                    self._adj_table.setItem(i, j, item)

            dtype = "Directed" if self.graph.directed else "Undirected"
            wtype = "Weighted" if self.graph.weighted else "Unweighted"
            bidi_count = sum(1 for e in self.graph.edges if e.bidirectional)
            bidi_text = f" · {bidi_count} bidirectional" if bidi_count > 0 else ""
            self._info.setText(
                f"{dtype} · {wtype} · {n} nodes · {len(self.graph.edges)} edges{bidi_text}")
        finally:
            self._updating = False

    def _refresh_incidence(self) -> None:
        """Refresh the incidence matrix view.
        
        Incidence matrix: rows = nodes, columns = edges.
        Values: 1 = edge starts at node, -1 = edge ends at node (directed),
                2 = edge is incident to node (undirected self-loop),
                1 = edge incident to node (undirected).
        """
        names = list(self.graph.nodes.keys())
        edges = list(self.graph.edges)
        n_nodes = len(names)
        n_edges = len(edges)

        self._inc_table.setRowCount(n_nodes)
        self._inc_table.setColumnCount(max(1, n_edges))

        # Row labels = node names
        self._inc_table.setVerticalHeaderLabels(names)

        # Column labels = edge names (source-target)
        # Add bidirectional indicator (↔) for bidirectional edges
        edge_labels = []
        for e in edges:
            if self.graph.directed:
                if e.bidirectional:
                    edge_labels.append(f"{e.source}↔{e.target}")
                else:
                    edge_labels.append(f"{e.source}→{e.target}")
            else:
                edge_labels.append(f"{e.source}--{e.target}")
        if not edge_labels:
            edge_labels = ["(no edges)"]
        self._inc_table.setHorizontalHeaderLabels(edge_labels)

        # Build incidence matrix
        node_idx = {name: i for i, name in enumerate(names)}
        for j, edge in enumerate(edges):
            src_idx = node_idx.get(edge.source)
            tgt_idx = node_idx.get(edge.target)

            # Clear column first
            for i in range(n_nodes):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor(Colors.TEXT_DIM))
                self._inc_table.setItem(i, j, item)

            if src_idx is not None and tgt_idx is not None:
                if self.graph.directed:
                    # Directed: 1 at source, -1 at target
                    src_item = QTableWidgetItem("1")
                    src_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    src_item.setForeground(QColor(Colors.PRIMARY))
                    self._inc_table.setItem(src_idx, j, src_item)

                    if edge.source != edge.target:  # not a self-loop
                        tgt_item = QTableWidgetItem("-1")
                        tgt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        tgt_item.setForeground(QColor(Colors.ERROR))
                        self._inc_table.setItem(tgt_idx, j, tgt_item)
                    else:  # self-loop in directed graph
                        src_item = QTableWidgetItem("0")
                        src_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self._inc_table.setItem(src_idx, j, src_item)
                else:
                    # Undirected: 1 at both endpoints
                    if edge.source != edge.target:
                        src_item = QTableWidgetItem("1")
                        src_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        src_item.setForeground(QColor(Colors.PRIMARY))
                        self._inc_table.setItem(src_idx, j, src_item)

                        tgt_item = QTableWidgetItem("1")
                        tgt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        tgt_item.setForeground(QColor(Colors.PRIMARY))
                        self._inc_table.setItem(tgt_idx, j, tgt_item)
                    else:  # self-loop in undirected graph
                        src_item = QTableWidgetItem("2")
                        src_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        src_item.setForeground(QColor(Colors.WARNING))
                        self._inc_table.setItem(src_idx, j, src_item)

        dtype = "Directed" if self.graph.directed else "Undirected"
        self._inc_info.setText(
            f"{dtype} · {n_nodes} nodes × {n_edges} edges")

    # -- graph events ------------------------------------------------------

    def _on_graph_event(self, event: GraphEvent, data: dict) -> None:
        # Any structural change → full refresh
        if event in (GraphEvent.NODE_ADDED, GraphEvent.NODE_REMOVED,
                     GraphEvent.NODE_RENAMED, GraphEvent.EDGE_ADDED,
                     GraphEvent.EDGE_REMOVED, GraphEvent.EDGE_WEIGHT_CHANGED,
                     GraphEvent.GRAPH_CLEARED, GraphEvent.GRAPH_REBUILT,
                     GraphEvent.DIRECTED_CHANGED, GraphEvent.WEIGHTED_CHANGED,
                     GraphEvent.UNDO_REDO):
            self._refresh()

    # -- cell edits --------------------------------------------------------

    def _on_cell_changed(self, row: int, col: int) -> None:
        if self._updating:
            return
        item = self._adj_table.item(row, col)
        if item is None:
            return
        names = self.graph.node_names
        if row >= len(names) or col >= len(names):
            return
        try:
            val = float(item.text())
        except ValueError:
            self._refresh_adjacency()
            return

        src, tgt = names[row], names[col]

        self._updating = True
        try:
            if val == 0:
                # Check if we're clearing a bidirectional edge's mirror cell
                # If so, just make it unidirectional instead of removing
                reverse_edge = self.graph.get_edge(tgt, src)
                if reverse_edge and reverse_edge.bidirectional:
                    self.graph.toggle_edge_bidirectional(tgt, src, reverse_edge.edge_id)
                else:
                    self.graph.remove_edge(src, tgt)
            else:
                existing = self.graph.get_edge(src, tgt)
                if existing is None and not self.graph.directed:
                    existing = self.graph.get_edge(tgt, src)

                if existing:
                    # Edge exists - just update weight
                    self.graph.set_edge_weight(src, tgt, val)
                else:
                    # No edge exists - check if we should create bidirectional
                    if self.graph.directed:
                        # Check if reverse edge exists and is bidirectional
                        reverse_edge = self.graph.get_edge(tgt, src)
                        if reverse_edge and reverse_edge.bidirectional:
                            # Reverse edge is bidirectional - just update its weight
                            self.graph.set_edge_weight(tgt, src, val, reverse_edge.edge_id)
                            self._refresh_adjacency()
                            return
                        elif reverse_edge and not reverse_edge.bidirectional:
                            # Reverse edge exists but not bidirectional - make it bidirectional
                            self.graph.toggle_edge_bidirectional(tgt, src, reverse_edge.edge_id)
                            self.graph.set_edge_weight(tgt, src, val, reverse_edge.edge_id)
                            self._refresh_adjacency()
                            return

                    # Create new edge normally
                    self.graph.add_edge(src, tgt, weight=val)
        finally:
            self._updating = False

        # Handle symmetric fill toggle
        if self._symmetric_toggle.isChecked() and row != col:
            self._apply_symmetric_value(row, col, val)
            # Also update the graph for the symmetric cell
            sym_src, sym_tgt = names[col], names[row]
            if val == 0:
                reverse_edge = self.graph.get_edge(sym_tgt, sym_src)
                if reverse_edge and reverse_edge.bidirectional:
                    self.graph.toggle_edge_bidirectional(sym_tgt, sym_src, reverse_edge.edge_id)
                else:
                    self.graph.remove_edge(sym_src, sym_tgt)
            else:
                existing = self.graph.get_edge(sym_src, sym_tgt)
                if existing:
                    self.graph.set_edge_weight(sym_src, sym_tgt, val)
                else:
                    self.graph.add_edge(sym_src, sym_tgt, weight=val)

        self._refresh_adjacency()

    # -- button handlers ---------------------------------------------------

    def _add_node(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Node", "Node name:")
        if ok and name:
            self.graph.add_node(name=name, x=200, y=200)

    def _remove_node(self) -> None:
        # Get selected cell in adjacency matrix
        # Both row and column headers represent the same node in adjacency matrix
        selected_items = self._adj_table.selectedItems()
        
        if selected_items:
            # Get the row of the first selected item
            item = selected_items[0]
            idx = item.row()
        else:
            # Fallback to current column/row
            col = self._adj_table.currentColumn()
            row = self._adj_table.currentRow()
            idx = col if col >= 0 else row
        
        names = self.graph.node_names
        if 0 <= idx < len(names):
            self.graph.remove_node(names[idx])

    def _apply_matrix(self) -> None:
        """Read the full adjacency table and rebuild the graph."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return
        mat = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                item = self._adj_table.item(i, j)
                if item:
                    try:
                        mat[i][j] = float(item.text())
                    except ValueError:
                        pass
        self.graph.from_adjacency_matrix(mat, names)

    # -- event filter for keyboard shortcuts -------------------------------

    def eventFilter(self, obj, event) -> bool:
        """Handle keyboard shortcuts and header right-clicks."""
        # Handle header right-clicks for context menus
        if obj in (self._adj_table.horizontalHeader(), self._adj_table.verticalHeader()):
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    # Get the logical index at the click position
                    if obj == self._adj_table.horizontalHeader():
                        col = obj.logicalIndexAt(event.position().toPoint())
                        if col >= 0:
                            self._on_column_header_right_click(col)
                            return True
                    else:  # vertical header
                        row = obj.logicalIndexAt(event.position().toPoint())
                        if row >= 0:
                            self._on_row_header_right_click(row)
                            return True

        # Handle keyboard shortcuts for the adjacency table
        if obj is not self._adj_table:
            return super().eventFilter(obj, event)

        if event.type() == event.Type.KeyPress:
            # Ctrl+A: Select all
            if event.matches(QKeySequence.StandardKey.SelectAll):
                self._adj_table.selectAll()
                return True

            # Delete/Backspace: Clear selected cells
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self._clear_selected_cells()
                return True

            # Ctrl+C: Copy
            if event.matches(QKeySequence.StandardKey.Copy):
                self._copy_selection()
                return True

            # Ctrl+V: Paste
            if event.matches(QKeySequence.StandardKey.Paste):
                self._paste_selection()
                return True

        return super().eventFilter(obj, event)

    # -- selection info ----------------------------------------------------

    def _on_selection_changed(self) -> None:
        """Update selection info label when selection changes."""
        range_info = self._get_selected_range()
        if range_info is None:
            self._selection_info.hide()
            return

        min_row, min_col, max_row, max_col = range_info
        selected_count = (max_row - min_row + 1) * (max_col - min_col + 1)

        # Calculate statistics
        values = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                item = self._adj_table.item(row, col)
                if item:
                    try:
                        values.append(float(item.text()))
                    except ValueError:
                        pass

        if values:
            total = sum(values)
            min_val = min(values)
            max_val = max(values)
            avg_val = total / len(values)
            self._selection_info.setText(
                f"Selected: {selected_count} cells | "
                f"Sum: {total:g} | Min: {min_val:g} | Max: {max_val:g} | Avg: {avg_val:.2f}"
            )
            self._selection_info.show()
        else:
            self._selection_info.hide()

    def _on_symmetric_toggle(self, state) -> None:
        """Handle symmetric fill toggle state change."""
        if state == Qt.CheckState.Checked:
            self._info.setText(self._info.text() + " · Symmetric fill ON")
        else:
            # Remove the symmetric fill indicator
            text = self._info.text()
            if " · Symmetric fill ON" in text:
                text = text.replace(" · Symmetric fill ON", "")
                self._info.setText(text)

    # -- copy/paste --------------------------------------------------------

    def _copy_selection(self) -> None:
        """Copy selected cells to clipboard."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        min_row, min_col, max_row, max_col = range_info
        rows = max_row - min_row + 1
        cols = max_col - min_col + 1

        self._clipboard = []
        for row in range(min_row, max_row + 1):
            row_data = []
            for col in range(min_col, max_col + 1):
                item = self._adj_table.item(row, col)
                row_data.append(item.text() if item else "0")
            self._clipboard.append(row_data)

        self._clipboard_shape = (rows, cols)
        self._selection_info.setText(
            f"Copied {rows}×{cols} cells to clipboard"
        )

    def _paste_selection(self) -> None:
        """Paste clipboard to selected cells starting from current cell."""
        if not self._clipboard:
            return

        current_row = self._adj_table.currentRow()
        current_col = self._adj_table.currentColumn()

        if current_row < 0 or current_col < 0:
            return

        paste_rows, paste_cols = self._clipboard_shape
        names = self.graph.node_names

        # Calculate how many cells we'll paste to
        actual_rows = min(paste_rows, len(names) - current_row)
        actual_cols = min(paste_cols, len(names) - current_col)

        if actual_rows <= 0 or actual_cols <= 0:
            return

        self._updating = True
        try:
            for i in range(actual_rows):
                for j in range(actual_cols):
                    if i < len(self._clipboard) and j < len(self._clipboard[i]):
                        val_str = self._clipboard[i][j]
                        try:
                            val = float(val_str)
                        except ValueError:
                            continue

                        row = current_row + i
                        col = current_col + j

                        if row < len(names) and col < len(names):
                            item = self._adj_table.item(row, col)
                            if item:
                                item.setText(f"{val:g}" if val != 0 else "0")
                                if val != 0:
                                    item.setForeground(QColor(Colors.SECONDARY))
                                else:
                                    item.setForeground(QColor(Colors.TEXT_DIM))

                                # Handle symmetric fill
                                if self._symmetric_toggle.isChecked():
                                    self._apply_symmetric_value(row, col, val)

            self._apply_matrix()
        finally:
            self._updating = False

    def _clear_selected_cells(self) -> None:
        """Clear (set to 0) all selected cells."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        min_row, min_col, max_row, max_col = range_info
        names = self.graph.node_names

        self._updating = True
        try:
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    item = self._adj_table.item(row, col)
                    if item:
                        item.setText("0")
                        item.setForeground(QColor(Colors.TEXT_DIM))

                        # Handle symmetric fill
                        if self._symmetric_toggle.isChecked():
                            self._apply_symmetric_value(row, col, 0.0)

            self._apply_matrix()
        finally:
            self._updating = False

    def _apply_symmetric_value(self, row: int, col: int, value: float) -> None:
        """Apply value to symmetric cell (col, row) if within bounds."""
        names = self.graph.node_names
        if row >= len(names) or col >= len(names):
            return

        # Don't apply to diagonal (it's already symmetric)
        if row == col:
            return

        # Apply to the symmetric position
        sym_item = self._adj_table.item(col, row)
        if sym_item:
            sym_item.setText(f"{value:g}" if value != 0 else "0")
            if value != 0:
                sym_item.setForeground(QColor(Colors.SECONDARY))
            else:
                sym_item.setForeground(QColor(Colors.TEXT_DIM))

    # -- range selection and bulk editing ----------------------------------

    def _get_selected_range(self) -> tuple[int, int, int, int] | None:
        """Get the bounding box of selected cells as (min_row, min_col, max_row, max_col)."""
        selected_items = self._adj_table.selectedItems()
        if not selected_items:
            return None
        
        min_row = min(item.row() for item in selected_items)
        max_row = max(item.row() for item in selected_items)
        min_col = min(item.column() for item in selected_items)
        max_col = max(item.column() for item in selected_items)
        
        return (min_row, min_col, max_row, max_col)

    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """Handle double-click to edit all selected cells simultaneously."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        min_row, min_col, max_row, max_col = range_info
        selected_count = (max_row - min_row + 1) * (max_col - min_col + 1)

        if selected_count <= 1:
            # Single cell - start editing mode
            self._adj_table.editItem(item)
            return

        # Get current value from the double-clicked item
        current_val = item.text()

        # Prompt for new value
        new_val_str, ok = QInputDialog.getText(
            self,
            "Fill Selected Cells",
            f"Enter value to fill {selected_count} selected cells:",
            text=current_val
        )

        if ok and new_val_str:
            try:
                new_val = float(new_val_str)
                self._updating = True
                try:
                    for row in range(min_row, max_row + 1):
                        for col in range(min_col, max_col + 1):
                            table_item = self._adj_table.item(row, col)
                            if table_item:
                                table_item.setText(f"{new_val:g}" if new_val != 0 else "0")
                                if new_val != 0:
                                    table_item.setForeground(QColor(Colors.SECONDARY))
                                else:
                                    table_item.setForeground(QColor(Colors.TEXT_DIM))

                    # Apply the changes to the graph
                    self._apply_matrix()
                finally:
                    self._updating = False
            except ValueError:
                pass  # Invalid input, ignore

    def _show_context_menu(self, pos) -> None:
        """Show context menu with fill options."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        menu = QMenu(self)

        # Fill Patterns submenu
        patterns_menu = menu.addMenu("Fill Patterns")

        identity_action = QAction("Identity Matrix", self)
        identity_action.setToolTip("Set diagonal to 1, all others to 0")
        identity_action.triggered.connect(self._fill_identity)
        patterns_menu.addAction(identity_action)

        diagonal_action = QAction("Diagonal (Custom Value)...", self)
        diagonal_action.setToolTip("Set diagonal to a custom value")
        diagonal_action.triggered.connect(self._fill_diagonal)
        patterns_menu.addAction(diagonal_action)

        upper_triangle_action = QAction("Upper Triangle", self)
        upper_triangle_action.setToolTip("Fill upper triangle with 1s")
        upper_triangle_action.triggered.connect(lambda: self._fill_triangle(upper=True))
        patterns_menu.addAction(upper_triangle_action)

        lower_triangle_action = QAction("Lower Triangle", self)
        lower_triangle_action.setToolTip("Fill lower triangle with 1s")
        lower_triangle_action.triggered.connect(lambda: self._fill_triangle(upper=False))
        patterns_menu.addAction(lower_triangle_action)

        complete_action = QAction("Complete Graph", self)
        complete_action.setToolTip("Fill all cells with 1s except diagonal")
        complete_action.triggered.connect(self._fill_complete)
        patterns_menu.addAction(complete_action)

        random_symmetric_action = QAction("Random Symmetric", self)
        random_symmetric_action.setToolTip("Generate random symmetric matrix (for undirected graphs)")
        random_symmetric_action.triggered.connect(self._fill_random_symmetric)
        patterns_menu.addAction(random_symmetric_action)

        menu.addSeparator()

        # Fill with Random Numbers submenu
        random_menu = menu.addMenu("Fill with Random Numbers")

        # Action 1: Fill with random numbers (uniform distribution)
        fill_random_action = QAction("Fill with Random Values", self)
        fill_random_action.setToolTip("Fill selected cells with random numbers in a specified range")
        fill_random_action.triggered.connect(lambda: self._fill_with_random(probability_of_zero=0.0))
        random_menu.addAction(fill_random_action)

        # Action 2: Fill with random numbers with probability of zero
        fill_random_zero_action = QAction("Fill with Random Values (Sparse)", self)
        fill_random_zero_action.setToolTip("Fill selected cells with random values, with a chance of zero")
        fill_random_zero_action.triggered.connect(lambda: self._fill_with_random_dialog())
        random_menu.addAction(fill_random_zero_action)

        menu.addSeparator()

        # Quick fill actions
        fill_zero_action = QAction("Fill with Zeros", self)
        fill_zero_action.setToolTip("Set all selected cells to 0")
        fill_zero_action.triggered.connect(lambda: self._fill_selected_cells(0.0))
        menu.addAction(fill_zero_action)

        fill_one_action = QAction("Fill with Ones", self)
        fill_one_action.setToolTip("Set all selected cells to 1")
        fill_one_action.triggered.connect(lambda: self._fill_selected_cells(1.0))
        menu.addAction(fill_one_action)

        menu.addSeparator()

        # Bulk operations submenu
        bulk_menu = menu.addMenu("Bulk Operations")

        multiply_action = QAction("Multiply Selected...", self)
        multiply_action.setToolTip("Multiply all selected cells by a value")
        multiply_action.triggered.connect(self._bulk_multiply)
        bulk_menu.addAction(multiply_action)

        add_action = QAction("Add to Selected...", self)
        add_action.setToolTip("Add a value to all selected cells")
        add_action.triggered.connect(self._bulk_add)
        bulk_menu.addAction(add_action)

        negate_action = QAction("Negate Selected", self)
        negate_action.setToolTip("Negate all selected values")
        negate_action.triggered.connect(self._bulk_negate)
        bulk_menu.addAction(negate_action)

        menu.addSeparator()

        # Copy/Paste actions
        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._copy_selection)
        menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self._paste_selection)
        menu.addAction(paste_action)

        menu.exec_(self._adj_table.viewport().mapToGlobal(pos))

    def _fill_with_random_dialog(self) -> None:
        """Show dialog to configure random fill with probability of zero."""
        dialog = RandomFillDialog(self, include_probability=True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_val = dialog.min_spin.value()
            max_val = dialog.max_spin.value()
            prob_zero = dialog.prob_spin.value() / 100.0  # Convert to 0-1 range
            integer_only = dialog.integer_check.isChecked()
            self._fill_with_random(min_val, max_val, prob_zero, integer_only)

    def _fill_with_random(self, min_val: float = 0.0, max_val: float = 10.0, 
                          probability_of_zero: float = 0.0,
                          integer_only: bool = False) -> None:
        """Fill selected cells with random numbers."""
        range_info = self._get_selected_range()
        if range_info is None:
            return
        
        min_row, min_col, max_row, max_col = range_info
        
        # If probability_of_zero is 0 and no custom range provided, show simple dialog
        if probability_of_zero == 0.0 and min_val == 0.0 and max_val == 10.0:
            dialog = RandomFillDialog(self, include_probability=False)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                min_val = dialog.min_spin.value()
                max_val = dialog.max_spin.value()
                integer_only = dialog.integer_check.isChecked()
            else:
                return
        
        self._updating = True
        try:
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    # Determine if this cell should be zero
                    if probability_of_zero > 0 and random.random() < probability_of_zero:
                        val = 0.0
                    else:
                        if integer_only:
                            val = float(random.randint(int(min_val), int(max_val)))
                        else:
                            val = random.uniform(min_val, max_val)

                    table_item = self._adj_table.item(row, col)
                    if table_item:
                        table_item.setText(f"{val:g}" if val != 0 else "0")
                        if val != 0:
                            table_item.setForeground(QColor(Colors.SECONDARY))
                        else:
                            table_item.setForeground(QColor(Colors.TEXT_DIM))

            # Apply the changes to the graph
            self._apply_matrix()
        finally:
            self._updating = False

    def _fill_selected_cells(self, value: float) -> None:
        """Fill all selected cells with a specific value."""
        range_info = self._get_selected_range()
        if range_info is None:
            return
        
        min_row, min_col, max_row, max_col = range_info
        
        self._updating = True
        try:
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    table_item = self._adj_table.item(row, col)
                    if table_item:
                        table_item.setText(f"{value:g}" if value != 0 else "0")
                        if value != 0:
                            table_item.setForeground(QColor(Colors.SECONDARY))
                        else:
                            table_item.setForeground(QColor(Colors.TEXT_DIM))
            
            # Apply the changes to the graph
            self._apply_matrix()
        finally:
            self._updating = False

    # -- bulk operations ---------------------------------------------------

    def _bulk_multiply(self) -> None:
        """Multiply all selected cells by a value."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        factor, ok = QInputDialog.getDouble(
            self, "Multiply Selected", "Multiply all selected cells by:",
            2.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return

        min_row, min_col, max_row, max_col = range_info

        self._updating = True
        try:
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    item = self._adj_table.item(row, col)
                    if item:
                        try:
                            val = float(item.text()) * factor
                            item.setText(f"{val:g}" if val != 0 else "0")
                            if val != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                            else:
                                item.setForeground(QColor(Colors.TEXT_DIM))
                        except ValueError:
                            pass

            self._apply_matrix()
        finally:
            self._updating = False

    def _bulk_add(self) -> None:
        """Add a value to all selected cells."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        addend, ok = QInputDialog.getDouble(
            self, "Add to Selected", "Add this value to all selected cells:",
            1.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return

        min_row, min_col, max_row, max_col = range_info

        self._updating = True
        try:
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    item = self._adj_table.item(row, col)
                    if item:
                        try:
                            val = float(item.text()) + addend
                            item.setText(f"{val:g}" if val != 0 else "0")
                            if val != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                            else:
                                item.setForeground(QColor(Colors.TEXT_DIM))
                        except ValueError:
                            pass

            self._apply_matrix()
        finally:
            self._updating = False

    def _bulk_negate(self) -> None:
        """Negate all selected values."""
        range_info = self._get_selected_range()
        if range_info is None:
            return

        min_row, min_col, max_row, max_col = range_info

        self._updating = True
        try:
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    item = self._adj_table.item(row, col)
                    if item:
                        try:
                            val = -float(item.text())
                            item.setText(f"{val:g}" if val != 0 else "0")
                            if val != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                            else:
                                item.setForeground(QColor(Colors.TEXT_DIM))
                        except ValueError:
                            pass

            self._apply_matrix()
        finally:
            self._updating = False

    # -- fill patterns -----------------------------------------------------

    def _fill_identity(self) -> None:
        """Fill matrix with identity pattern (1s on diagonal, 0s elsewhere)."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return

        self._updating = True
        try:
            for i in range(n):
                for j in range(n):
                    val = 1.0 if i == j else 0.0
                    item = self._adj_table.item(i, j)
                    if item:
                        item.setText(f"{val:g}" if val != 0 else "0")
                        if val != 0:
                            item.setForeground(QColor(Colors.SECONDARY))
                        else:
                            item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _fill_diagonal(self) -> None:
        """Fill diagonal with a custom value."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return

        value, ok = QInputDialog.getDouble(
            self, "Diagonal Value", "Enter value for diagonal cells:",
            1.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return

        self._updating = True
        try:
            for i in range(n):
                item = self._adj_table.item(i, i)
                if item:
                    item.setText(f"{value:g}" if value != 0 else "0")
                    if value != 0:
                        item.setForeground(QColor(Colors.SECONDARY))
                    else:
                        item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _fill_triangle(self, upper: bool = True) -> None:
        """Fill upper or lower triangle with 1s."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return

        self._updating = True
        try:
            for i in range(n):
                for j in range(n):
                    if upper:
                        val = 1.0 if j > i else 0.0
                    else:
                        val = 1.0 if i > j else 0.0

                    item = self._adj_table.item(i, j)
                    if item:
                        item.setText(f"{val:g}" if val != 0 else "0")
                        if val != 0:
                            item.setForeground(QColor(Colors.SECONDARY))
                        else:
                            item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _fill_complete(self) -> None:
        """Fill all cells with 1s except diagonal (complete graph)."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return

        self._updating = True
        try:
            for i in range(n):
                for j in range(n):
                    val = 1.0 if i != j else 0.0
                    item = self._adj_table.item(i, j)
                    if item:
                        item.setText(f"{val:g}" if val != 0 else "0")
                        if val != 0:
                            item.setForeground(QColor(Colors.SECONDARY))
                        else:
                            item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _fill_random_symmetric(self) -> None:
        """Generate random symmetric matrix for undirected graphs."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return

        # Show dialog for parameters
        dialog = RandomFillDialog(self, include_probability=False)
        dialog.setWindowTitle("Random Symmetric Matrix")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        min_val = dialog.min_spin.value()
        max_val = dialog.max_spin.value()
        integer_only = dialog.integer_check.isChecked()

        self._updating = True
        try:
            for i in range(n):
                for j in range(i, n):  # Only upper triangle including diagonal
                    if i == j:
                        val = 0.0  # Diagonal is always 0
                    else:
                        if integer_only:
                            val = float(random.randint(int(min_val), int(max_val)))
                        else:
                            val = random.uniform(min_val, max_val)

                    # Apply to both (i,j) and (j,i)
                    for r, c in [(i, j), (j, i)]:
                        item = self._adj_table.item(r, c)
                        if item:
                            item.setText(f"{val:g}" if val != 0 else "0")
                            if val != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                            else:
                                item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    # -- row/column header operations --------------------------------------

    def _on_row_header_right_click(self, row: int) -> None:
        """Show context menu for row header."""
        names = self.graph.node_names
        if row >= len(names):
            return

        menu = QMenu(self)

        select_row_action = QAction("Select Row", self)
        select_row_action.setToolTip("Select entire row")
        select_row_action.triggered.connect(lambda: self._select_row(row))
        menu.addAction(select_row_action)

        fill_row_action = QAction("Fill Row with Value...", self)
        fill_row_action.setToolTip("Fill entire row with a value")
        fill_row_action.triggered.connect(lambda: self._fill_row(row))
        menu.addAction(fill_row_action)

        clear_row_action = QAction("Clear Row", self)
        clear_row_action.setToolTip("Set all cells in row to 0")
        clear_row_action.triggered.connect(lambda: self._clear_row(row))
        menu.addAction(clear_row_action)

        menu.exec_(self._adj_table.verticalHeader().viewport().mapToGlobal(
            self._adj_table.verticalHeader().sectionViewportPosition(row)))

    def _on_column_header_right_click(self, col: int) -> None:
        """Show context menu for column header."""
        names = self.graph.node_names
        if col >= len(names):
            return

        menu = QMenu(self)

        select_col_action = QAction("Select Column", self)
        select_col_action.setToolTip("Select entire column")
        select_col_action.triggered.connect(lambda: self._select_column(col))
        menu.addAction(select_col_action)

        fill_col_action = QAction("Fill Column with Value...", self)
        fill_col_action.setToolTip("Fill entire column with a value")
        fill_col_action.triggered.connect(lambda: self._fill_column(col))
        menu.addAction(fill_col_action)

        clear_col_action = QAction("Clear Column", self)
        clear_col_action.setToolTip("Set all cells in column to 0")
        clear_col_action.triggered.connect(lambda: self._clear_column(col))
        menu.addAction(clear_col_action)

        menu.exec_(self._adj_table.horizontalHeader().viewport().mapToGlobal(
            self._adj_table.horizontalHeader().sectionViewportPosition(col)))

    def _select_row(self, row: int) -> None:
        """Select entire row."""
        n = self._adj_table.columnCount()
        if n == 0:
            return
        self._adj_table.clearSelection()
        for col in range(n):
            item = self._adj_table.item(row, col)
            if item:
                item.setSelected(True)

    def _select_column(self, col: int) -> None:
        """Select entire column."""
        n = self._adj_table.rowCount()
        if n == 0:
            return
        self._adj_table.clearSelection()
        for row in range(n):
            item = self._adj_table.item(row, col)
            if item:
                item.setSelected(True)

    def _fill_row(self, row: int) -> None:
        """Fill entire row with a value."""
        value, ok = QInputDialog.getDouble(
            self, "Fill Row", "Enter value for row:",
            1.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return

        n = self._adj_table.columnCount()
        self._updating = True
        try:
            for col in range(n):
                item = self._adj_table.item(row, col)
                if item:
                    item.setText(f"{value:g}" if value != 0 else "0")
                    if value != 0:
                        item.setForeground(QColor(Colors.SECONDARY))
                    else:
                        item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _fill_column(self, col: int) -> None:
        """Fill entire column with a value."""
        value, ok = QInputDialog.getDouble(
            self, "Fill Column", "Enter value for column:",
            1.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return

        n = self._adj_table.rowCount()
        self._updating = True
        try:
            for row in range(n):
                item = self._adj_table.item(row, col)
                if item:
                    item.setText(f"{value:g}" if value != 0 else "0")
                    if value != 0:
                        item.setForeground(QColor(Colors.SECONDARY))
                    else:
                        item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _clear_row(self, row: int) -> None:
        """Clear entire row (set to 0)."""
        n = self._adj_table.columnCount()
        self._updating = True
        try:
            for col in range(n):
                item = self._adj_table.item(row, col)
                if item:
                    item.setText("0")
                    item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    def _clear_column(self, col: int) -> None:
        """Clear entire column (set to 0)."""
        n = self._adj_table.rowCount()
        self._updating = True
        try:
            for row in range(n):
                item = self._adj_table.item(row, col)
                if item:
                    item.setText("0")
                    item.setForeground(QColor(Colors.TEXT_DIM))

            self._apply_matrix()
        finally:
            self._updating = False

    # -- graph presets -----------------------------------------------------

    def _show_graph_presets(self) -> None:
        """Show graph presets dialog."""
        dialog = GraphPresetsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            preset_type = dialog.selected_preset
            params = dialog.get_parameters()

            if preset_type:
                self._generate_graph_preset(preset_type, params)

    def _generate_graph_preset(self, preset_type: str, params: dict) -> None:
        """Generate a graph structure based on preset type."""
        names = self.graph.node_names
        n = len(names)

        if n == 0:
            QMessageBox.information(
                self, "No Nodes",
                "Please add some nodes first before generating a graph structure."
            )
            return

        self._updating = True
        try:
            # Clear existing edges
            for i in range(n):
                for j in range(n):
                    item = self._adj_table.item(i, j)
                    if item:
                        item.setText("0")
                        item.setForeground(QColor(Colors.TEXT_DIM))

            if preset_type == "complete":
                # Complete graph: all nodes connected to all others
                for i in range(n):
                    for j in range(n):
                        if i != j:
                            val = params.get("weight", 1.0)
                            item = self._adj_table.item(i, j)
                            if item:
                                item.setText(f"{val:g}" if val != 0 else "0")
                                if val != 0:
                                    item.setForeground(QColor(Colors.SECONDARY))

            elif preset_type == "cycle":
                # Cycle graph: 0→1→2→...→n-1→0
                weight = params.get("weight", 1.0)
                for i in range(n):
                    j = (i + 1) % n
                    item = self._adj_table.item(i, j)
                    if item:
                        item.setText(f"{weight:g}" if weight != 0 else "0")
                        if weight != 0:
                            item.setForeground(QColor(Colors.SECONDARY))
                    # Symmetric for undirected
                    if self._symmetric_toggle.isChecked() or not self.graph.directed:
                        item = self._adj_table.item(j, i)
                        if item:
                            item.setText(f"{weight:g}" if weight != 0 else "0")
                            if weight != 0:
                                item.setForeground(QColor(Colors.SECONDARY))

            elif preset_type == "path":
                # Path graph: 0→1→2→...→n-1 (no wrap-around)
                weight = params.get("weight", 1.0)
                for i in range(n - 1):
                    j = i + 1
                    item = self._adj_table.item(i, j)
                    if item:
                        item.setText(f"{weight:g}" if weight != 0 else "0")
                        if weight != 0:
                            item.setForeground(QColor(Colors.SECONDARY))
                    # Symmetric for undirected
                    if self._symmetric_toggle.isChecked() or not self.graph.directed:
                        item = self._adj_table.item(j, i)
                        if item:
                            item.setText(f"{weight:g}" if weight != 0 else "0")
                            if weight != 0:
                                item.setForeground(QColor(Colors.SECONDARY))

            elif preset_type == "star":
                # Star graph: node 0 connected to all others
                weight = params.get("weight", 1.0)
                center = params.get("center_node", 0)
                for i in range(n):
                    if i != center:
                        # Center to leaf
                        item = self._adj_table.item(center, i)
                        if item:
                            item.setText(f"{weight:g}" if weight != 0 else "0")
                            if weight != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                        # Leaf to center (for undirected)
                        if self._symmetric_toggle.isChecked() or not self.graph.directed:
                            item = self._adj_table.item(i, center)
                            if item:
                                item.setText(f"{weight:g}" if weight != 0 else "0")
                                if weight != 0:
                                    item.setForeground(QColor(Colors.SECONDARY))

            elif preset_type == "grid":
                # Grid graph: arrange nodes in grid, connect neighbors
                rows = params.get("grid_rows", int(n ** 0.5))
                cols = params.get("grid_cols", (n + rows - 1) // rows)
                weight = params.get("weight", 1.0)

                for idx in range(n):
                    r, c = divmod(idx, cols)
                    # Connect to right neighbor
                    if c + 1 < cols and idx + 1 < n:
                        item = self._adj_table.item(idx, idx + 1)
                        if item:
                            item.setText(f"{weight:g}" if weight != 0 else "0")
                            if weight != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                        if self._symmetric_toggle.isChecked() or not self.graph.directed:
                            item = self._adj_table.item(idx + 1, idx)
                            if item:
                                item.setText(f"{weight:g}" if weight != 0 else "0")
                                if weight != 0:
                                    item.setForeground(QColor(Colors.SECONDARY))
                    # Connect to bottom neighbor
                    if r + 1 < rows and idx + cols < n:
                        item = self._adj_table.item(idx, idx + cols)
                        if item:
                            item.setText(f"{weight:g}" if weight != 0 else "0")
                            if weight != 0:
                                item.setForeground(QColor(Colors.SECONDARY))
                        if self._symmetric_toggle.isChecked() or not self.graph.directed:
                            item = self._adj_table.item(idx + cols, idx)
                            if item:
                                item.setText(f"{weight:g}" if weight != 0 else "0")
                                if weight != 0:
                                    item.setForeground(QColor(Colors.SECONDARY))

            elif preset_type == "random":
                # Random graph with given density
                density = params.get("density", 0.3)
                weight_range = params.get("weight_range", (1.0, 10.0))
                integer_only = params.get("integer_only", False)

                for i in range(n):
                    for j in range(n):
                        if i != j and random.random() < density:
                            if integer_only:
                                val = float(random.randint(int(weight_range[0]), int(weight_range[1])))
                            else:
                                val = random.uniform(weight_range[0], weight_range[1])

                            item = self._adj_table.item(i, j)
                            if item:
                                item.setText(f"{val:g}" if val != 0 else "0")
                                if val != 0:
                                    item.setForeground(QColor(Colors.SECONDARY))

            self._apply_matrix()
        finally:
            self._updating = False

    # -- path highlighting -------------------------------------------------

    def set_highlight(self, nodes: set[str], edges: set[str]) -> None:
        """Highlight path edges in the adjacency matrix with distinct color."""
        self._highlighted_edges = edges
        # Refresh will apply highlighting automatically
        self._refresh_adjacency()

    def _get_bold_font(self) -> QFont:
        """Return a bold font for highlighted items."""
        font = QFont()
        font.setBold(True)
        return font


class RandomFillDialog(QDialog):
    """Dialog for configuring random number fill parameters."""

    def __init__(self, parent=None, include_probability: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fill with Random Values")
        self.setMinimumWidth(350)
        self._include_probability = include_probability
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Description
        desc_label = QLabel("Configure the random value generation parameters:")
        desc_label.setStyleSheet(f"color: {Colors.TEXT}; font-size: 13px;")
        layout.addWidget(desc_label)

        # Form layout
        form = QFormLayout()
        form.setSpacing(10)

        # Min value
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1000.0, 1000.0)
        self.min_spin.setValue(1.0)
        self.min_spin.setDecimals(2)
        self.min_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 10px;
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        form.addRow("Minimum Value:", self.min_spin)

        # Max value
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1000.0, 1000.0)
        self.max_spin.setValue(10.0)
        self.max_spin.setDecimals(2)
        self.max_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 10px;
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        form.addRow("Maximum Value:", self.max_spin)

        # Probability of zero (optional)
        if self._include_probability:
            self.prob_spin = QSpinBox()
            self.prob_spin.setRange(0, 100)
            self.prob_spin.setValue(50)
            self.prob_spin.setSuffix("%")
            self.prob_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {Colors.BG_INPUT};
                    color: {Colors.TEXT};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 4px;
                    padding: 6px 10px;
                }}
                QSpinBox:focus {{
                    border-color: {Colors.PRIMARY};
                }}
            """)
            form.addRow("Probability of Zero:", self.prob_spin)
        else:
            self.prob_spin = None

        # Integer values toggle
        self.integer_check = QCheckBox()
        self.integer_check.setToolTip("When checked, only integer values will be generated")
        self.integer_check.setStyleSheet(f"""
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
        """)
        form.addRow("Integer Values Only:", self.integer_check)

        layout.addLayout(form)

        # Info label
        if self._include_probability:
            info_text = (
                f"<span style='color: {Colors.TEXT_DIM}; font-size: 12px;'>"
                "Values will be uniformly distributed between min and max. "
                "Each cell has the specified chance of being set to zero."
                "</span>"
            )
        else:
            info_text = (
                f"<span style='color: {Colors.TEXT_DIM}; font-size: 12px;'>"
                "Values will be uniformly distributed between min and max."
                "</span>"
            )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 5px;
                padding: 6px 16px;
                min-height: 28px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                border-color: {Colors.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY};
            }}
        """)
        layout.addWidget(button_box)


class GraphPresetsDialog(QDialog):
    """Dialog for selecting and configuring graph structure presets."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Graph Structure Presets")
        self.setMinimumSize(500, 400)
        self.selected_preset: str | None = None
        self._parameters: dict = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Quick Graph Structure Generator")
        title_label.setStyleSheet(f"""
            color: {Colors.PRIMARY};
            font-size: 18px;
            font-weight: bold;
            padding: 10px;
        """)
        layout.addWidget(title_label)

        # Preset selection
        select_label = QLabel("Select a graph structure:")
        select_label.setStyleSheet(f"color: {Colors.TEXT}; font-size: 13px;")
        layout.addWidget(select_label)

        # Preset list with descriptions
        self._preset_list = QTableWidget()
        self._preset_list.setColumnCount(2)
        self._preset_list.setHorizontalHeaderLabels(["Structure", "Description"])
        self._preset_list.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._preset_list.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._preset_list.verticalHeader().setVisible(False)
        self._preset_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._preset_list.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._preset_list.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preset_list.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT};
                gridline-color: {Colors.BORDER};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
            }}
            QTableWidget QHeaderView::section {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                padding: 6px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY};
            }}
        """)

        presets = [
            ("Complete Graph", "Every node connected to every other node"),
            ("Cycle Graph", "Nodes form a closed loop: 0→1→2→...→n→0"),
            ("Path Graph", "Nodes form a line: 0→1→2→...→n"),
            ("Star Graph", "One central node connected to all others"),
            ("Grid Graph", "Nodes arranged in a grid, connected to neighbors"),
            ("Random Graph", "Random connections with configurable density"),
        ]

        self._preset_list.setRowCount(len(presets))
        for i, (name, desc) in enumerate(presets):
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor(Colors.SECONDARY))
            name_item.setFont(self.font())
            desc_item = QTableWidgetItem(desc)
            desc_item.setForeground(QColor(Colors.TEXT_DIM))
            self._preset_list.setItem(i, 0, name_item)
            self._preset_list.setItem(i, 1, desc_item)

        self._preset_list.itemSelectionChanged.connect(self._on_preset_selected)
        layout.addWidget(self._preset_list)

        # Parameters group
        self._params_group = QGroupBox("Parameters")
        self._params_group.setStyleSheet(f"""
            QGroupBox {{
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)
        params_layout = QVBoxLayout(self._params_group)
        params_layout.setSpacing(10)

        self._params_form = QFormLayout()
        self._params_form.setSpacing(10)
        self._param_widgets: dict = {}
        params_layout.addLayout(self._params_form)
        layout.addWidget(self._params_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        button_box.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 5px;
                padding: 6px 16px;
                min-height: 28px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                border-color: {Colors.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_DIM};
                border-color: {Colors.BORDER};
            }}
        """)
        layout.addWidget(button_box)

        # Select first preset by default
        self._preset_list.selectRow(0)

    def _on_preset_selected(self) -> None:
        """Update parameters when preset selection changes."""
        selected = self._preset_list.selectedItems()
        if not selected:
            self._ok_button.setEnabled(False)
            return

        self._ok_button.setEnabled(True)
        row = selected[0].row()
        preset_names = ["complete", "cycle", "path", "star", "grid", "random"]
        self.selected_preset = preset_names[row]

        # Clear existing parameters
        while self._params_form.count():
            item = self._params_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._param_widgets = {}

        # Add parameters based on preset
        if self.selected_preset in ["complete", "cycle", "path"]:
            # Weight parameter
            weight_spin = QDoubleSpinBox()
            weight_spin.setRange(0.0, 1000.0)
            weight_spin.setValue(1.0)
            weight_spin.setDecimals(2)
            self._style_spinbox(weight_spin)
            self._params_form.addRow("Edge Weight:", weight_spin)
            self._param_widgets["weight"] = weight_spin

        elif self.selected_preset == "star":
            # Weight parameter
            weight_spin = QDoubleSpinBox()
            weight_spin.setRange(0.0, 1000.0)
            weight_spin.setValue(1.0)
            weight_spin.setDecimals(2)
            self._style_spinbox(weight_spin)
            self._params_form.addRow("Edge Weight:", weight_spin)
            self._param_widgets["weight"] = weight_spin

            # Center node
            center_spin = QSpinBox()
            center_spin.setRange(0, 100)
            center_spin.setValue(0)
            self._style_spinbox(center_spin)
            self._params_form.addRow("Center Node Index:", center_spin)
            self._param_widgets["center_node"] = center_spin

        elif self.selected_preset == "grid":
            # Grid dimensions
            rows_spin = QSpinBox()
            rows_spin.setRange(1, 20)
            rows_spin.setValue(3)
            self._style_spinbox(rows_spin)
            self._params_form.addRow("Grid Rows:", rows_spin)
            self._param_widgets["grid_rows"] = rows_spin

            cols_spin = QSpinBox()
            cols_spin.setRange(1, 20)
            cols_spin.setValue(3)
            self._style_spinbox(cols_spin)
            self._params_form.addRow("Grid Columns:", cols_spin)
            self._param_widgets["grid_cols"] = cols_spin

            # Weight parameter
            weight_spin = QDoubleSpinBox()
            weight_spin.setRange(0.0, 1000.0)
            weight_spin.setValue(1.0)
            weight_spin.setDecimals(2)
            self._style_spinbox(weight_spin)
            self._params_form.addRow("Edge Weight:", weight_spin)
            self._param_widgets["weight"] = weight_spin

        elif self.selected_preset == "random":
            # Density
            density_spin = QDoubleSpinBox()
            density_spin.setRange(0.01, 1.0)
            density_spin.setValue(0.3)
            density_spin.setDecimals(2)
            density_spin.setSingleStep(0.05)
            self._style_spinbox(density_spin)
            self._params_form.addRow("Connection Density:", density_spin)
            self._param_widgets["density"] = density_spin

            # Weight range
            min_weight_spin = QDoubleSpinBox()
            min_weight_spin.setRange(0.0, 1000.0)
            min_weight_spin.setValue(1.0)
            min_weight_spin.setDecimals(2)
            self._style_spinbox(min_weight_spin)
            self._params_form.addRow("Min Weight:", min_weight_spin)
            self._param_widgets["min_weight"] = min_weight_spin

            max_weight_spin = QDoubleSpinBox()
            max_weight_spin.setRange(0.0, 1000.0)
            max_weight_spin.setValue(10.0)
            max_weight_spin.setDecimals(2)
            self._style_spinbox(max_weight_spin)
            self._params_form.addRow("Max Weight:", max_weight_spin)
            self._param_widgets["max_weight"] = max_weight_spin

            # Integer toggle
            self._integer_check = QCheckBox()
            self._integer_check.setToolTip("Generate only integer weights")
            self._style_checkbox(self._integer_check)
            self._params_form.addRow("Integer Weights Only:", self._integer_check)
            self._param_widgets["integer_only"] = self._integer_check

    def _style_spinbox(self, spinbox) -> None:
        """Apply consistent styling to spinbox."""
        spinbox.setStyleSheet(f"""
            QDoubleSpinBox, QSpinBox {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 10px;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)

    def _style_checkbox(self, checkbox) -> None:
        """Apply consistent styling to checkbox."""
        checkbox.setStyleSheet(f"""
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
        """)

    def _on_accept(self) -> None:
        """Collect parameters and accept dialog."""
        self._parameters = {}

        if "weight" in self._param_widgets:
            self._parameters["weight"] = self._param_widgets["weight"].value()

        if "center_node" in self._param_widgets:
            self._parameters["center_node"] = self._param_widgets["center_node"].value()

        if "grid_rows" in self._param_widgets:
            self._parameters["grid_rows"] = self._param_widgets["grid_rows"].value()

        if "grid_cols" in self._param_widgets:
            self._parameters["grid_cols"] = self._param_widgets["grid_cols"].value()

        if "density" in self._param_widgets:
            self._parameters["density"] = self._param_widgets["density"].value()

        if "min_weight" in self._param_widgets and "max_weight" in self._param_widgets:
            self._parameters["weight_range"] = (
                self._param_widgets["min_weight"].value(),
                self._param_widgets["max_weight"].value()
            )

        if "integer_only" in self._param_widgets:
            self._parameters["integer_only"] = self._param_widgets["integer_only"].isChecked()

        self.accept()

    def get_parameters(self) -> dict:
        """Get the configured parameters."""
        return self._parameters
