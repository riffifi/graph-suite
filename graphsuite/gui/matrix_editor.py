"""Adjacency-matrix editor – QTableWidget synced with the Graph model."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QInputDialog, QAbstractItemView,
)

from graphsuite.core.graph import Graph, GraphEvent
from graphsuite.gui.style import Colors


class MatrixEditor(QWidget):
    """Editable adjacency-matrix view of the graph."""

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

        # button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

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

        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_apply)
        btn_row.addWidget(self._btn_refresh)
        layout.addLayout(btn_row)

        # info label
        self._info = QLabel()
        self._info.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._info)

        # table
        self._table = QTableWidget()
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)

    # -- refresh from model ------------------------------------------------

    def _refresh(self) -> None:
        self._updating = True
        try:
            mat, names = self.graph.get_adjacency_matrix()
            n = len(names)

            self._table.setRowCount(n)
            self._table.setColumnCount(n)
            self._table.setHorizontalHeaderLabels(names)
            self._table.setVerticalHeaderLabels(names)

            for i in range(n):
                for j in range(n):
                    val = mat[i][j]
                    item = QTableWidgetItem(
                        f"{val:g}" if val != 0 else "0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    # colour non-zero cells
                    if val != 0:
                        item.setForeground(QColor(Colors.SECONDARY))
                    else:
                        item.setForeground(QColor(Colors.TEXT_DIM))
                    self._table.setItem(i, j, item)

            dtype = "Directed" if self.graph.directed else "Undirected"
            wtype = "Weighted" if self.graph.weighted else "Unweighted"
            self._info.setText(
                f"{dtype} · {wtype} · {n} nodes · {len(self.graph.edges)} edges")
        finally:
            self._updating = False

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
        item = self._table.item(row, col)
        if item is None:
            return
        names = self.graph.node_names
        if row >= len(names) or col >= len(names):
            return
        try:
            val = float(item.text())
        except ValueError:
            self._refresh()
            return

        src, tgt = names[row], names[col]

        self._updating = True
        try:
            if val == 0:
                self.graph.remove_edge(src, tgt)
            else:
                existing = self.graph.get_edge(src, tgt)
                if existing is None and not self.graph.directed:
                    existing = self.graph.get_edge(tgt, src)
                if existing:
                    self.graph.set_edge_weight(src, tgt, val)
                else:
                    self.graph.add_edge(src, tgt, weight=val)
        finally:
            self._updating = False

        self._refresh()

    # -- button handlers ---------------------------------------------------

    def _add_node(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Node", "Node name:")
        if ok and name:
            self.graph.add_node(name=name, x=200, y=200)

    def _remove_node(self) -> None:
        col = self._table.currentColumn()
        row = self._table.currentRow()
        idx = col if col >= 0 else row
        names = self.graph.node_names
        if 0 <= idx < len(names):
            self.graph.remove_node(names[idx])

    def _apply_matrix(self) -> None:
        """Read the full table and rebuild the graph."""
        names = self.graph.node_names
        n = len(names)
        if n == 0:
            return
        mat = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                item = self._table.item(i, j)
                if item:
                    try:
                        mat[i][j] = float(item.text())
                    except ValueError:
                        pass
        self.graph.from_adjacency_matrix(mat, names)
