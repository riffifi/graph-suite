"""Graph import/export utilities for various formats."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import networkx as nx


class GraphIO:
    """Import/export graph data in various formats."""

    @staticmethod
    def to_dot(graph: Any, name: str = "G") -> str:
        """Export graph to DOT/Graphviz format.
        
        Args:
            graph: Graph object with nodes, edges, directed properties
            name: Graph name for DOT output
            
        Returns:
            DOT format string
        """
        lines = [f"{'digraph' if graph.directed else 'graph'} {name} {{"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=circle];")
        
        # Node definitions with positions and colors
        for node_name, node in graph.nodes.items():
            attrs = [f'label="{node_name}"']
            if node.color and node.color != "#4fc3f7":
                attrs.append(f'fillcolor="{node.color}"')
                attrs.append('style="filled"')
            lines.append(f'  "{node_name}" [{", ".join(attrs)}];')
        
        # Edge definitions
        for edge in graph.edges:
            arrow = "->" if graph.directed else "--"
            attrs = []
            if edge.weight and edge.weight != 1.0:
                attrs.append(f'label="{edge.weight}"')
            if edge.curvature != 0:
                attrs.append(f'style="curved"')
            attr_str = f" [{', '.join(attrs)}]" if attrs else ""
            lines.append(f'  "{edge.source}" {arrow} "{edge.target}"{attr_str};')
        
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def to_graphml(graph: Any) -> str:
        """Export graph to GraphML format.
        
        Args:
            graph: Graph object
            
        Returns:
            GraphML format string
        """
        import io
        G = graph.to_networkx()
        
        # Add node attributes
        for name, node in graph.nodes.items():
            G.nodes[name]['x'] = node.x
            G.nodes[name]['y'] = node.y
            G.nodes[name]['color'] = node.color
        
        output = io.BytesIO()
        nx.write_graphml(G, output)
        return output.getvalue().decode('utf-8')

    @staticmethod
    def to_csv_edge_list(graph: Any) -> str:
        """Export graph as CSV edge list.
        
        Returns:
            CSV string with columns: source, target, weight
        """
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["source", "target", "weight"])
        
        for edge in graph.edges:
            writer.writerow([edge.source, edge.target, edge.weight])
        
        return output.getvalue()

    @staticmethod
    def from_dot(dot_string: str, graph: Any) -> None:
        """Import graph from DOT format.
        
        Args:
            dot_string: DOT format string
            graph: Graph object to populate
        """
        G = nx.nx_pydot.read_dot(dot_string)
        GraphIO._from_networkx(G, graph)

    @staticmethod
    def from_graphml(graphml_string: str, graph: Any) -> None:
        """Import graph from GraphML format.
        
        Args:
            graphml_string: GraphML format string
            graph: Graph object to populate
        """
        import io
        G = nx.parse_graphml(graphml_string)
        GraphIO._from_networkx(G, graph)

    @staticmethod
    def from_csv_edge_list(csv_string: str, graph: Any) -> None:
        """Import graph from CSV edge list.
        
        Args:
            csv_string: CSV string with columns: source, target, weight
            graph: Graph object to populate
        """
        import io
        graph.clear()
        
        reader = csv.DictReader(io.StringIO(csv_string))
        for row in reader:
            source = row.get('source', '').strip()
            target = row.get('target', '').strip()
            weight = float(row.get('weight', 1.0))
            
            if source and target:
                graph.add_node(source)
                graph.add_node(target)
                graph.add_edge(source, target, weight=weight)

    @staticmethod
    def _from_networkx(nx_graph: nx.Graph, graph: Any) -> None:
        """Populate graph from NetworkX graph.
        
        Args:
            nx_graph: NetworkX graph
            graph: Graph object to populate
        """
        graph.clear()
        graph.directed = nx_graph.is_directed()
        
        # Add nodes with attributes
        for name, attrs in nx_graph.nodes(data=True):
            x = attrs.get('x', 0.0)
            y = attrs.get('y', 0.0)
            color = attrs.get('color', '#4fc3f7')
            try:
                x = float(x)
                y = float(y)
            except (ValueError, TypeError):
                x, y = 0, 0
            graph.add_node(name, x=x, y=y, color=color)
        
        # Add edges with attributes
        for u, v, attrs in nx_graph.edges(data=True):
            weight = attrs.get('weight', 1.0)
            try:
                weight = float(weight)
            except (ValueError, TypeError):
                weight = 1.0
            graph.add_edge(u, v, weight=weight)

    @staticmethod
    def export_image(graph: Any, canvas: Any, path: str, 
                     width: int = 1920, height: int = 1080) -> bool:
        """Export current canvas view as PNG image.
        
        Args:
            graph: Graph object
            canvas: GraphCanvas object
            path: Output file path
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            True if successful
        """
        from PySide6.QtGui import QPixmap, QPainter, QColor
        from PySide6.QtWidgets import QApplication
        
        # Create a pixmap at the requested size
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#1e1e2e"))  # Background color
        
        # Render the canvas onto the pixmap
        painter = QPainter(pixmap)
        
        # Save current canvas state
        original_size = canvas.size()
        
        # Temporarily resize canvas for rendering
        canvas.resize(width, height)
        
        # Paint the canvas
        canvas.paintEvent(None)
        
        # Restore original size
        canvas.resize(original_size)
        
        painter.end()
        
        # Save to file
        return pixmap.save(path)

    @staticmethod
    def export_svg(graph: Any, path: str, width: int = 800, 
                   height: int = 600) -> bool:
        """Export graph as SVG.
        
        Args:
            graph: Graph object
            path: Output file path
            width: SVG width
            height: SVG height
            
        Returns:
            True if successful
        """
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '  <style>',
            '    .node { stroke: #333; stroke-width: 2; }',
            '    .edge { stroke: #90a4ae; stroke-width: 2; fill: none; }',
            '    .label { font-family: sans-serif; font-size: 12px; fill: #fff; }',
            '  </style>',
        ]
        
        # Draw edges first
        for edge in graph.edges:
            src = graph.nodes.get(edge.source)
            tgt = graph.nodes.get(edge.target)
            if src and tgt:
                svg_parts.append(
                    f'  <line class="edge" x1="{src.x}" y1="{src.y}" '
                    f'x2="{tgt.x}" y2="{tgt.y}"/>'
                )
        
        # Draw nodes
        for node in graph.nodes.values():
            svg_parts.append(
                f'  <circle class="node" cx="{node.x}" cy="{node.y}" '
                f'r="{node.radius}" fill="{node.color}"/>'
            )
            svg_parts.append(
                f'  <text class="label" text-anchor="middle" '
                f'dominant-baseline="central" x="{node.x}" y="{node.y}">'
                f'{node.name}</text>'
            )
        
        svg_parts.append('</svg>')
        
        try:
            with open(path, 'w') as f:
                f.write('\n'.join(svg_parts))
            return True
        except Exception:
            return False
