"""Core graph data structures and operations.

This module provides the fundamental graph model used throughout Graph Suite,
including Node and Edge dataclasses, the main Graph class, and support for:

- Directed and undirected graphs
- Weighted and unweighted edges
- Parallel edges (multigraph support)
- Bidirectional edges
- Undo/redo functionality
- Adjacency matrix and list representations
- NetworkX integration
- JSON serialization
"""

from graphsuite.core.graph import (
    Graph,
    GraphEvent,
    Node,
    Edge,
)

__all__ = [
    "Graph",
    "GraphEvent",
    "Node",
    "Edge",
]
