"""Adjacency and Incidence matrix editor – QTableWidget synced with the Graph model."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QInputDialog, QAbstractItemView, QTabWidget, QGroupBox,
)

from graphsuite.core.graph import Graph, GraphEvent
from graphsuite.gui.style import Colors


class MatrixEditor(QWidget):
    """Editable adjacency and incidence matrix view of the graph."""

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._updating = False  # guard against feedback loops

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

        self._btn_apply = QPushButton("Apply Matrix")
        self._btn_apply.setToolTip("Rebuild graph from current matrix values")
        self._btn_apply.clicked.connect(self._apply_matrix)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.setToolTip("Reload matrix from graph")
        self._btn_refresh.clicked.connect(self._refresh)

        adj_btn_row.addWidget(self._btn_add)
        adj_btn_row.addWidget(self._btn_remove)
        adj_btn_row.addStretch()
        adj_btn_row.addWidget(self._btn_apply)
        adj_btn_row.addWidget(self._btn_refresh)
        adj_layout.addLayout(adj_btn_row)

        # info label for adjacency
        self._info = QLabel()
        self._info.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 11px;")
        adj_layout.addWidget(self._info)

        # adjacency table
        self._adj_table = QTableWidget()
        self._adj_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._adj_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._adj_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._adj_table.cellChanged.connect(self._on_cell_changed)
        adj_layout.addWidget(self._adj_table)

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
                    # colour non-zero cells
                    if val != 0:
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
