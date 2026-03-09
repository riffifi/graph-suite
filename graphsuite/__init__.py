"""Graph Suite - A professional graph visualization and analysis tool.

Graph Suite provides an interactive desktop application for creating,
editing, and analyzing graphs. It features:

- Interactive canvas with drag, zoom, and pan
- Support for directed/undirected and weighted/unweighted graphs
- Parallel edges and bidirectional edges
- Built-in DSL for scripting graph creation
- Graph algorithms (BFS, DFS, Dijkstra, MST, etc.)
- Adjacency and incidence matrix editors
- Export to JSON and PNG

Example:
    from graphsuite.core.graph import Graph

    g = Graph()
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=100)
    g.add_edge("A", "B", weight=5)
    print(g.to_json())
"""

__version__ = "1.0.0"
__author__ = "Graph Suite Team"
__all__ = ["__version__"]
