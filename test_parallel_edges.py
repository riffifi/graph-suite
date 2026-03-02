#!/usr/bin/env python3
"""Test parallel edges (multigraph) support."""

import sys
sys.path.insert(0, '/home/leo/graph-suite')

from graphsuite.core.graph import Graph, Edge


def test_parallel_edges():
    """Test that multiple edges can exist between the same pair of nodes."""
    g = Graph()
    g.weighted = True  # Enable weighted edges
    
    # Add nodes
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    
    # Add multiple parallel edges
    e1 = g.add_edge("A", "B", weight=1.0)
    e2 = g.add_edge("A", "B", weight=2.0)
    e3 = g.add_edge("A", "B", weight=3.0)
    
    print(f"✓ Created 3 parallel edges: {e1.edge_id}, {e2.edge_id}, {e3.edge_id}")
    assert e1 is not None and e2 is not None and e3 is not None
    assert e1.edge_id != e2.edge_id != e3.edge_id
    
    # Verify all edges exist
    edges = g.get_edges_between("A", "B")
    print(f"✓ get_edges_between returned {len(edges)} edges")
    assert len(edges) == 3
    
    # Verify weights
    weights = [e.weight for e in edges]
    print(f"✓ Edge weights: {weights}")
    assert 1.0 in weights and 2.0 in weights and 3.0 in weights
    
    # Test adjacency matrix (sums parallel edges)
    mat, names = g.get_adjacency_matrix(sum_parallel=True)
    print(f"✓ Adjacency matrix (summed): {mat[0][1]}")
    assert mat[0][1] == 6.0  # 1+2+3
    
    # Test adjacency matrix (individual)
    mat2, _ = g.get_adjacency_matrix(sum_parallel=False)
    print(f"✓ Adjacency matrix (last edge only): {mat2[0][1]}")
    assert mat2[0][1] == 3.0  # last edge weight
    
    # Test adjacency list
    adj_list = g.get_adjacency_list()
    print(f"✓ Adjacency list for A: {adj_list['A']}")
    assert len(adj_list['A']) == 3
    
    # Test remove specific edge by ID
    g.remove_edge_by_id(e2.edge_id)
    edges_after = g.get_edges_between("A", "B")
    print(f"✓ After removing e2, {len(edges_after)} edges remain")
    assert len(edges_after) == 2
    
    # Test JSON serialization
    json_str = g.to_json()
    print(f"✓ JSON serialization works, length: {len(json_str)}")
    
    # Test deserialization
    g2 = Graph()
    g2.from_json(json_str)
    edges_restored = g2.get_edges_between("A", "B")
    print(f"✓ After JSON round-trip: {len(edges_restored)} edges")
    assert len(edges_restored) == 2
    
    # Test NetworkX MultiGraph conversion
    nx_g = g.to_networkx()
    print(f"✓ NetworkX conversion: {nx_g.number_of_edges()} edges")
    assert nx_g.number_of_edges() == 2
    assert nx_g.is_multigraph()
    
    print("\n✅ All parallel edges tests passed!")


def test_undirected_parallel():
    """Test parallel edges in undirected mode."""
    g = Graph()
    g.directed = False
    
    g.add_node("X", x=0, y=0)
    g.add_node("Y", x=100, y=0)
    
    e1 = g.add_edge("X", "Y", weight=5.0)
    e2 = g.add_edge("X", "Y", weight=10.0)
    
    edges = g.get_edges_between("X", "Y")
    print(f"✓ Undirected parallel edges: {len(edges)}")
    assert len(edges) == 2
    
    print("\n✅ Undirected parallel edges test passed!")


if __name__ == "__main__":
    test_parallel_edges()
    test_undirected_parallel()
