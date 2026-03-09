"""Graph analysis panel with metrics, degree distribution, and community detection."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QScrollArea, QFrame, QLabel, QComboBox,
)

from graphsuite.core.graph import Graph


class AnalysisPanel(QWidget):
    """Panel showing graph metrics and analysis results."""

    def __init__(self, graph: Graph) -> None:
        super().__init__()
        self.graph = graph
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("📊 Graph Analysis")
        title.setFont(QFont("sans-serif", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Analysis")
        refresh_btn.clicked.connect(self._run_analysis)
        layout.addWidget(refresh_btn)

        # Results area
        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setStyleSheet("""
            QTextEdit {
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #3a3a50;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self._results)

        # Community detection button
        community_btn = QPushButton("🔍 Detect Communities (Louvain)")
        community_btn.clicked.connect(self._detect_communities)
        layout.addWidget(community_btn)

        # Initial analysis
        self._run_analysis()

    def _run_analysis(self) -> None:
        """Run graph analysis and display results."""
        import networkx as nx
        
        G = self.graph.to_networkx()
        n = len(G)
        m = G.number_of_edges()
        
        results = []
        results.append("=" * 50)
        results.append("GRAPH METRICS")
        results.append("=" * 50)
        results.append("")
        
        # Basic metrics
        results.append(f"Nodes:           {n}")
        results.append(f"Edges:           {m}")
        
        if n > 0:
            density = nx.density(G)
            results.append(f"Density:         {density:.4f}")
        
        # Degree statistics
        if n > 0:
            degrees = [d for _, d in G.degree()]
            avg_degree = sum(degrees) / n if n > 0 else 0
            max_degree = max(degrees) if degrees else 0
            min_degree = min(degrees) if degrees else 0
            results.append("")
            results.append("DEGREE STATISTICS")
            results.append(f"Average degree:  {avg_degree:.2f}")
            results.append(f"Max degree:      {max_degree}")
            results.append(f"Min degree:      {min_degree}")
            
            # Degree distribution
            results.append("")
            results.append("DEGREE DISTRIBUTION")
            degree_counts = {}
            for d in degrees:
                degree_counts[d] = degree_counts.get(d, 0) + 1
            for d in sorted(degree_counts.keys()):
                count = degree_counts[d]
                bar = "█" * min(count, 30)
                results.append(f"  Degree {d:3d}: {count:4d} {bar}")
        
        # Connected components
        if self.graph.directed:
            weak = nx.number_weakly_connected_components(G)
            strong = nx.number_strongly_connected_components(G)
            results.append("")
            results.append("CONNECTIVITY (Directed)")
            results.append(f"Weakly connected components:   {weak}")
            results.append(f"Strongly connected components: {strong}")
        else:
            components = list(nx.connected_components(G))
            results.append("")
            results.append("CONNECTIVITY (Undirected)")
            results.append(f"Connected components: {len(components)}")
            if len(components) > 0:
                sizes = sorted([len(c) for c in components], reverse=True)
                results.append(f"Largest component size: {sizes[0]}")
                if len(sizes) > 1:
                    results.append(f"Second largest:         {sizes[1]}")
        
        # Path metrics (for connected graphs or largest component)
        if n > 1:
            try:
                if self.graph.directed:
                    if nx.is_strongly_connected(G):
                        diameter = nx.diameter(G)
                        radius = nx.radius(G)
                        avg_path = nx.average_shortest_path_length(G)
                        results.append("")
                        results.append("PATH METRICS (Strongly Connected)")
                        results.append(f"Diameter:          {diameter}")
                        results.append(f"Radius:            {radius}")
                        results.append(f"Avg path length:   {avg_path:.2f}")
                else:
                    if nx.is_connected(G):
                        diameter = nx.diameter(G)
                        radius = nx.radius(G)
                        avg_path = nx.average_shortest_path_length(G)
                        results.append("")
                        results.append("PATH METRICS (Connected)")
                        results.append(f"Diameter:          {diameter}")
                        results.append(f"Radius:            {radius}")
                        results.append(f"Avg path length:   {avg_path:.2f}")
            except (nx.NetworkXError, nx.NetworkXUnbounded):
                results.append("")
                results.append("Path metrics: Graph not connected")
        
        # Clustering coefficient
        if n > 2 and not self.graph.directed:
            clustering = nx.average_clustering(G)
            results.append("")
            results.append("CLUSTERING")
            results.append(f"Average clustering coefficient: {clustering:.4f}")
        
        # Centrality metrics (top 5)
        if n > 2:
            results.append("")
            results.append("TOP NODES BY DEGREE CENTRALITY")
            centrality = nx.degree_centrality(G)
            top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            for node, cent in top_nodes:
                results.append(f"  {node}: {cent:.4f}")
        
        results.append("")
        results.append("=" * 50)
        
        self._results.setText("\n".join(results))

    def _detect_communities(self) -> None:
        """Detect communities using Louvain algorithm."""
        import networkx as nx
        from networkx.algorithms import community
        
        G = self.graph.to_networkx()
        
        if len(G) < 2:
            self._results.append("\n⚠ Need at least 2 nodes for community detection")
            return
        
        try:
            # Use Louvain community detection
            communities = community.louvain_communities(G, seed=42)
            communities = list(communities)
            
            result_lines = ["\n" + "=" * 50, "COMMUNITY DETECTION (Louvain)", "=" * 50, ""]
            result_lines.append(f"Number of communities: {len(communities)}")
            result_lines.append("")
            
            # Sort communities by size
            sorted_comms = sorted(communities, key=len, reverse=True)
            
            for i, comm in enumerate(sorted_comms, 1):
                size = len(comm)
                nodes = sorted(comm)
                node_str = ", ".join(nodes[:10])
                if len(nodes) > 10:
                    node_str += f"... ({len(nodes)} total)"
                result_lines.append(f"Community {i} ({size} nodes): {node_str}")
            
            # Color nodes by community
            colors = [
                "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4",
                "#ffeaa7", "#dfe6e9", "#fd79a8", "#a29bfe",
                "#6c5ce7", "#00b894", "#e17055", "#74b9ff"
            ]
            
            result_lines.append("")
            result_lines.append("Applying colors to nodes...")
            
            for i, comm in enumerate(communities):
                color = colors[i % len(colors)]
                for node in comm:
                    if node in self.graph.nodes:
                        self.graph.set_node_color(node, color)
            
            result_lines.append("Done! Nodes colored by community.")
            result_lines.append("=" * 50)
            
            self._results.append("\n".join(result_lines))
            
        except Exception as e:
            self._results.append(f"\n⚠ Community detection error: {e}")
