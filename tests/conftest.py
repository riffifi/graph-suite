"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphsuite.core.graph import Graph


@pytest.fixture
def empty_graph():
    """Provide an empty graph instance."""
    return Graph()


@pytest.fixture
def simple_graph():
    """Provide a simple graph with 2 nodes and 1 edge."""
    g = Graph()
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=100)
    g.add_edge("A", "B", weight=5)
    return g


@pytest.fixture
def directed_graph():
    """Provide a directed graph."""
    g = Graph()
    g.directed = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_node("C", x=50, y=100)
    g.add_edge("A", "B", weight=1)
    g.add_edge("B", "C", weight=2)
    g.add_edge("A", "C", weight=3)
    return g


@pytest.fixture
def undirected_graph():
    """Provide an undirected graph."""
    g = Graph()
    g.directed = False
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_node("C", x=50, y=100)
    g.add_edge("A", "B", weight=1)
    g.add_edge("B", "C", weight=2)
    g.add_edge("A", "C", weight=3)
    return g


@pytest.fixture
def weighted_graph():
    """Provide a weighted graph."""
    g = Graph()
    g.weighted = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_node("C", x=50, y=100)
    g.add_edge("A", "B", weight=5)
    g.add_edge("B", "C", weight=10)
    g.add_edge("A", "C", weight=15)
    return g


@pytest.fixture
def graph_with_parallel_edges():
    """Provide a graph with parallel edges."""
    g = Graph()
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_edge("A", "B", weight=1)
    g.add_edge("A", "B", weight=2)
    g.add_edge("A", "B", weight=3)
    return g


@pytest.fixture
def graph_with_bidirectional_edge():
    """Provide a graph with a bidirectional edge."""
    g = Graph()
    g.directed = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_edge("A", "B", weight=5)
    g.toggle_edge_bidirectional("A", "B")
    return g


@pytest.fixture
def cyclic_graph():
    """Provide a graph with a cycle."""
    g = Graph()
    g.directed = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_node("C", x=50, y=100)
    g.add_edge("A", "B", weight=1)
    g.add_edge("B", "C", weight=2)
    g.add_edge("C", "A", weight=3)
    return g


@pytest.fixture
def acyclic_graph():
    """Provide a directed acyclic graph (DAG)."""
    g = Graph()
    g.directed = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_node("C", x=50, y=100)
    g.add_edge("A", "B", weight=1)
    g.add_edge("A", "C", weight=2)
    g.add_edge("B", "C", weight=3)
    return g


@pytest.fixture
def disconnected_graph():
    """Provide a graph with multiple components."""
    g = Graph()
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=50, y=0)
    g.add_edge("A", "B")
    g.add_node("C", x=200, y=0)
    g.add_node("D", x=250, y=0)
    g.add_edge("C", "D")
    return g


@pytest.fixture
def complete_graph_5():
    """Provide a complete graph K5."""
    g = Graph()
    g.directed = False
    nodes = ["A", "B", "C", "D", "E"]
    for i, name in enumerate(nodes):
        g.add_node(name, x=i * 50, y=0)
    for i, n1 in enumerate(nodes):
        for n2 in nodes[i+1:]:
            g.add_edge(n1, n2, weight=1)
    return g
