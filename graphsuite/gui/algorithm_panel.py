"""Algorithm panel – run graph algorithms and display results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPushButton, QLabel, QTextEdit, QLineEdit,
    QGroupBox, QCheckBox,
)

from graphsuite.core.graph import Graph
from graphsuite.gui.style import Colors

if TYPE_CHECKING:
    from graphsuite.gui.canvas import GraphCanvas


# ---------------------------------------------------------------------------
# Available algorithms
# ---------------------------------------------------------------------------

ALGORITHMS = [
    "BFS Traversal",
    "DFS Traversal",
    "Dijkstra Shortest Path",
    "Bellman-Ford Shortest Path",
    "Minimum Spanning Tree",
    "Topological Sort",
    "Connected Components",
    "Strongly Connected Components",
    "Cycle Detection",
    "Degree Centrality",
    "Graph Info",
]


class AlgorithmPanel(QWidget):
    """Run graph algorithms and show results, with canvas highlighting."""

    highlight_request = Signal(set, set)  # nodes, edge_ids
    clear_highlight = Signal()

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._canvas: GraphCanvas | None = None
        self._last_nodes: set[str] = set()
        self._last_edges: set[tuple[str, str]] = set()
        self._build_ui()

    def set_canvas(self, canvas: "GraphCanvas") -> None:
        self._canvas = canvas
        self.highlight_request.connect(canvas.set_highlight)
        self.clear_highlight.connect(canvas.clear_highlight)

    # -- UI ----------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # algorithm selector
        algo_group = QGroupBox()
        algo_layout = QVBoxLayout(algo_group)

        self._combo = QComboBox()
        self._combo.addItems(ALGORITHMS)
        self._combo.currentTextChanged.connect(self._on_algo_changed)
        algo_layout.addWidget(self._combo)

        # parameter inputs
        param_form = QFormLayout()
        param_form.setContentsMargins(0, 4, 0, 0)

        self._source_input = QLineEdit()
        self._source_input.setPlaceholderText("Source node name")
        param_form.addRow("Source:", self._source_input)

        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("Target node name")
        param_form.addRow("Target:", self._target_input)

        algo_layout.addLayout(param_form)
        layout.addWidget(algo_group)

        # buttons
        btn_row = QHBoxLayout()
        self._btn_run = QPushButton("Run")
        self._btn_run.setStyleSheet(
            f"background-color: {Colors.PRIMARY}; color: white; font-weight: bold;")
        self._btn_run.clicked.connect(self._run)

        self._btn_clear = QPushButton("Clear Highlight")
        self._btn_clear.clicked.connect(self._clear_highlight)

        self._show_only_check = QCheckBox("Show Only Path")
        self._show_only_check.setToolTip("Hide non-highlighted nodes and edges")
        self._show_only_check.stateChanged.connect(self._update_highlight)

        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_clear)
        btn_row.addWidget(self._show_only_check)
        layout.addLayout(btn_row)

        # results
        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout(result_group)
        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setMinimumHeight(120)
        result_layout.addWidget(self._result_text)
        layout.addWidget(result_group)

        layout.addStretch()
        self._on_algo_changed(self._combo.currentText())

    def _on_algo_changed(self, name: str) -> None:
        needs_source = name in (
            "BFS Traversal", "DFS Traversal",
            "Dijkstra Shortest Path", "Bellman-Ford Shortest Path",
        )
        needs_target = name in (
            "Dijkstra Shortest Path", "Bellman-Ford Shortest Path",
        )
        self._source_input.setVisible(needs_source)
        self._source_input.parent().layout()  # trigger layout
        self._target_input.setVisible(needs_target)

        # show/hide labels
        for i in range(self._source_input.parent().layout().count()):
            item = self._source_input.parent().layout().itemAt(i)
            if item and item.widget() == self._source_input:
                break

    # -- run algorithm -----------------------------------------------------

    def _run(self) -> None:
        algo = self._combo.currentText()
        src = self._source_input.text().strip()
        tgt = self._target_input.text().strip()

        if len(self.graph.nodes) == 0:
            self._show_result("Graph is empty.", set(), set())
            return

        try:
            G = self.graph.to_networkx()
        except Exception as e:
            self._show_result(f"Error building graph: {e}", set(), set())
            return

        try:
            if algo == "BFS Traversal":
                self._run_bfs(G, src)
            elif algo == "DFS Traversal":
                self._run_dfs(G, src)
            elif algo == "Dijkstra Shortest Path":
                self._run_dijkstra(G, src, tgt)
            elif algo == "Bellman-Ford Shortest Path":
                self._run_bellman_ford(G, src, tgt)
            elif algo == "Minimum Spanning Tree":
                self._run_mst(G)
            elif algo == "Topological Sort":
                self._run_topo(G)
            elif algo == "Connected Components":
                self._run_components(G)
            elif algo == "Strongly Connected Components":
                self._run_scc(G)
            elif algo == "Cycle Detection":
                self._run_cycle(G)
            elif algo == "Degree Centrality":
                self._run_centrality(G)
            elif algo == "Graph Info":
                self._run_info(G)
        except Exception as e:
            self._show_result(f"Error: {e}", set(), set())

    # -- individual algorithms ---------------------------------------------

    def _run_bfs(self, G, src: str) -> None:
        if src not in G:
            self._show_result(f"Node '{src}' not found.", set(), set())
            return
        order = list(nx.bfs_tree(G, src).nodes())
        edges_list = list(nx.bfs_edges(G, src))
        edge_set = set(edges_list)
        self._show_result(
            f"BFS from '{src}':\nOrder: {' → '.join(order)}\n"
            f"Tree edges: {edges_list}",
            set(order), edge_set)

    def _run_dfs(self, G, src: str) -> None:
        if src not in G:
            self._show_result(f"Node '{src}' not found.", set(), set())
            return
        order = list(nx.dfs_tree(G, src).nodes())
        edges_list = list(nx.dfs_edges(G, src))
        edge_set = set(edges_list)
        self._show_result(
            f"DFS from '{src}':\nOrder: {' → '.join(order)}\n"
            f"Tree edges: {edges_list}",
            set(order), edge_set)

    def _run_dijkstra(self, G, src: str, tgt: str) -> None:
        if src not in G:
            self._show_result(f"Node '{src}' not found.", set(), set())
            return
        if tgt not in G:
            self._show_result(f"Node '{tgt}' not found.", set(), set())
            return
        try:
            path = nx.dijkstra_path(G, src, tgt, weight="weight")
            cost = nx.dijkstra_path_length(G, src, tgt, weight="weight")
        except nx.NetworkXNoPath:
            self._show_result(f"No path from '{src}' to '{tgt}'.", set(), set())
            return
        edges = set(zip(path[:-1], path[1:]))
        self._show_result(
            f"Dijkstra '{src}' → '{tgt}':\n"
            f"Path: {' → '.join(path)}\nCost: {cost}",
            set(path), edges)

    def _run_bellman_ford(self, G, src: str, tgt: str) -> None:
        if src not in G:
            self._show_result(f"Node '{src}' not found.", set(), set())
            return
        if tgt not in G:
            self._show_result(f"Node '{tgt}' not found.", set(), set())
            return
        try:
            path = nx.bellman_ford_path(G, src, tgt, weight="weight")
            cost = nx.bellman_ford_path_length(G, src, tgt, weight="weight")
        except nx.NetworkXNoPath:
            self._show_result(f"No path from '{src}' to '{tgt}'.", set(), set())
            return
        except nx.NetworkXUnbounded:
            self._show_result("Negative cycle detected!", set(), set())
            return
        edges = set(zip(path[:-1], path[1:]))
        self._show_result(
            f"Bellman-Ford '{src}' → '{tgt}':\n"
            f"Path: {' → '.join(path)}\nCost: {cost}",
            set(path), edges)

    def _run_mst(self, G) -> None:
        if self.graph.directed:
            self._show_result(
                "MST requires an undirected graph.\n"
                "Switch to undirected mode first.", set(), set())
            return
        try:
            T = nx.minimum_spanning_tree(G, weight="weight")
        except nx.NetworkXError as e:
            self._show_result(f"MST error: {e}", set(), set())
            return
        total = sum(d.get("weight", 1) for _, _, d in T.edges(data=True))
        edge_set = set(T.edges())
        node_set = set(T.nodes())
        lines = [f"Minimum Spanning Tree:"]
        for u, v, d in T.edges(data=True):
            lines.append(f"  {u} — {v}  (weight: {d.get('weight', 1)})")
        lines.append(f"\nTotal weight: {total}")
        self._show_result("\n".join(lines), node_set, edge_set)

    def _run_topo(self, G) -> None:
        if not self.graph.directed:
            self._show_result(
                "Topological sort requires a directed graph.", set(), set())
            return
        try:
            order = list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            self._show_result(
                "Graph has a cycle — topological sort not possible.",
                set(), set())
            return
        self._show_result(
            f"Topological order:\n{' → '.join(order)}",
            set(order), set())

    def _run_components(self, G) -> None:
        if self.graph.directed:
            UG = G.to_undirected()
            comps = list(nx.connected_components(UG))
        else:
            comps = list(nx.connected_components(G))
        lines = [f"Connected Components: {len(comps)}"]
        all_nodes: set[str] = set()
        for i, comp in enumerate(comps, 1):
            lines.append(f"  Component {i}: {sorted(comp)}")
            all_nodes |= comp
        self._show_result("\n".join(lines), all_nodes, set())

    def _run_scc(self, G) -> None:
        if not self.graph.directed:
            self._show_result(
                "Strongly connected components require a directed graph.",
                set(), set())
            return
        comps = list(nx.strongly_connected_components(G))
        lines = [f"Strongly Connected Components: {len(comps)}"]
        all_nodes: set[str] = set()
        for i, comp in enumerate(comps, 1):
            lines.append(f"  SCC {i}: {sorted(comp)}")
            all_nodes |= comp
        self._show_result("\n".join(lines), all_nodes, set())

    def _run_cycle(self, G) -> None:
        try:
            cycle = nx.find_cycle(G)
            edges = set((u, v) for u, v, *_ in cycle)
            nodes = set()
            for u, v, *_ in cycle:
                nodes.add(u)
                nodes.add(v)
            cycle_str = " → ".join(u for u, v, *_ in cycle)
            self._show_result(
                f"Cycle found:\n{cycle_str} → {cycle[0][0]}",
                nodes, edges)
        except nx.NetworkXNoCycle:
            self._show_result("No cycles found — graph is acyclic.", set(), set())

    def _run_centrality(self, G) -> None:
        cent = nx.degree_centrality(G)
        lines = ["Degree Centrality:"]
        for node, val in sorted(cent.items(), key=lambda x: -x[1]):
            lines.append(f"  {node}: {val:.4f}")
        self._show_result("\n".join(lines), set(cent.keys()), set())

    def _run_info(self, G) -> None:
        n_nodes = G.number_of_nodes()
        n_edges = G.number_of_edges()
        density = nx.density(G)
        is_connected = (
            nx.is_weakly_connected(G) if self.graph.directed
            else nx.is_connected(G) if n_nodes > 0 else False
        )
        lines = [
            "Graph Information:",
            f"  Nodes: {n_nodes}",
            f"  Edges: {n_edges}",
            f"  Directed: {self.graph.directed}",
            f"  Weighted: {self.graph.weighted}",
            f"  Density: {density:.4f}",
            f"  Connected: {is_connected}",
        ]
        if n_nodes > 0:
            degrees = dict(G.degree())
            avg_deg = sum(degrees.values()) / n_nodes
            lines.append(f"  Avg Degree: {avg_deg:.2f}")
            max_node = max(degrees, key=degrees.get)
            lines.append(f"  Max Degree: {max_node} ({degrees[max_node]})")
        self._show_result("\n".join(lines), set(), set())

    # -- helpers -----------------------------------------------------------

    def _clear_highlight(self) -> None:
        """Clear highlight and reset 'Show Only Path' mode."""
        self._last_nodes.clear()
        self._last_edges.clear()
        self._show_only_check.setChecked(False)
        if self._canvas:
            self._canvas.clear_highlight()

    def _update_highlight(self) -> None:
        """Update highlight based on 'Show Only Path' checkbox state."""
        if self._canvas is None:
            return
            
        if self._show_only_check.isChecked():
            # Show only the highlighted path
            self._canvas.set_highlight_only(self._last_nodes, self._last_edges)
        else:
            # Show full graph with highlight
            self._canvas.set_highlight(self._last_nodes, self._last_edges)

    def _show_result(self, text: str, nodes: set[str],
                     edges: set[tuple[str, str]]) -> None:
        self._last_nodes = nodes
        self._last_edges = edges
        self._result_text.setPlainText(text)
        self._update_highlight()
