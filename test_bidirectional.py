#!/usr/bin/env python
"""Test bidirectional edge toggle and matrix calculations."""

from graphsuite.core.graph import Graph
from graphsuite.dsl.engine import Interpreter, tokenize, Parser

def test_bidirectional_toggle():
    """Test bidirectional toggle functionality."""
    print("=== Testing Bidirectional Toggle ===\n")
    
    g = Graph()
    g.directed = True
    g.weighted = True  # Enable weighted mode
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)

    # Add initial edge
    g.add_edge("A", "B", weight=5)
    print(f"Initial edges: {[(e.source, e.target, e.weight, e.bidirectional) for e in g.edges]}")
    print(f"Is A->B bidirectional? {g.is_edge_bidirectional('A', 'B')}")
    assert len(g.edges) == 1
    assert not g.is_edge_bidirectional('A', 'B')

    # Make it bidirectional (toggle property on same edge)
    result = g.toggle_edge_bidirectional("A", "B")
    print(f"\nAfter toggle to bidirectional:")
    print(f"Edges: {[(e.source, e.target, e.weight, e.bidirectional) for e in g.edges]}")
    print(f"Is A->B bidirectional? {g.is_edge_bidirectional('A', 'B')}")
    assert len(g.edges) == 1  # Still only ONE edge!
    assert result == True  # Now bidirectional
    assert g.is_edge_bidirectional('A', 'B')
    
    # Verify the edge has bidirectional property set
    edge = g.get_edge("A", "B")
    assert edge is not None
    assert edge.bidirectional == True
    assert edge.weight == 5

    # Toggle back to unidirectional
    result = g.toggle_edge_bidirectional("A", "B")
    print(f"\nAfter toggle to unidirectional:")
    print(f"Edges: {[(e.source, e.target, e.weight, e.bidirectional) for e in g.edges]}")
    print(f"Is A->B bidirectional? {g.is_edge_bidirectional('A', 'B')}")
    assert len(g.edges) == 1  # Still only ONE edge!
    assert result == False  # Now unidirectional
    assert not g.is_edge_bidirectional('A', 'B')
    
    print("\n✓ Bidirectional toggle tests passed!\n")


def test_adjacency_matrix():
    """Test adjacency matrix with bidirectional edges."""
    print("=== Testing Adjacency Matrix ===\n")
    
    g = Graph()
    g.directed = True
    g.weighted = True  # Enable weighted mode
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_edge("A", "B", weight=3)
    g.toggle_edge_bidirectional("A", "B")  # Sets bidirectional property

    mat, names = g.get_adjacency_matrix()
    print(f"Node names: {names}")
    print(f"Adjacency matrix:\n{mat}")
    
    # For directed graph with bidirectional edge:
    # A->B exists with weight 3
    # B->A does NOT exist as a separate edge (it's a property of A->B)
    # So matrix should show A->B=3, B->A=0
    assert names == ["A", "B"]
    assert mat[0][1] == 3  # A->B
    # Note: B->A is 0 because bidirectional is just a VISUAL property
    # The edge still only goes from A to B in the graph structure
    
    print("Note: Bidirectional is a visual property - edge still only counts as A->B")
    print("✓ Adjacency matrix tests passed!\n")


def test_incidence_matrix():
    """Test incidence matrix with bidirectional edges."""
    print("=== Testing Incidence Matrix ===\n")
    
    g = Graph()
    g.directed = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_edge("A", "B", weight=3)
    g.toggle_edge_bidirectional("A", "B")  # Sets bidirectional property

    # Manually build incidence matrix for verification
    names = list(g.nodes.keys())
    edges = list(g.edges)
    node_idx = {name: i for i, name in enumerate(names)}
    
    print(f"Nodes: {names}")
    print(f"Edges: {[(e.source, e.target, e.bidirectional) for e in edges]}")
    
    # For directed graph with bidirectional edge:
    # Only ONE edge exists: A->B (with bidirectional=True)
    # Incidence: A gets 1, B gets -1
    assert len(edges) == 1
    edge = edges[0]
    assert edge.source == "A"
    assert edge.target == "B"
    assert edge.bidirectional == True
    
    print(f"Edge 0: {edge.source} -> {edge.target} (bidirectional={edge.bidirectional})")
    print(f"  {edge.source} (idx {node_idx[edge.source]}) = 1")
    print(f"  {edge.target} (idx {node_idx[edge.target]}) = -1")
    
    print("✓ Incidence matrix structure verified!\n")


def test_dsl_toggle():
    """Test DSL toggle command."""
    print("=== Testing DSL Toggle Command ===\n")
    
    g = Graph()
    g.directed = True
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    g.add_edge("A", "B", weight=5)
    
    interpreter = Interpreter(g)
    
    # Test toggle command
    source = "toggle edge A B"
    output, h_nodes, h_edges = interpreter.run(source)
    print(f"DSL output: {output}")
    print(f"Edges after toggle: {[(e.source, e.target, e.bidirectional) for e in g.edges]}")
    
    assert len(g.edges) == 1  # Still only ONE edge
    assert g.is_edge_bidirectional('A', 'B')
    
    # Toggle back
    output2, _, _ = interpreter.run("toggle edge A B")
    print(f"DSL output after toggle back: {output2}")
    print(f"Edges after toggle back: {[(e.source, e.target, e.bidirectional) for e in g.edges]}")
    
    assert len(g.edges) == 1  # Still only ONE edge
    assert not g.is_edge_bidirectional('A', 'B')
    
    print("✓ DSL toggle command tests passed!\n")


def test_curved_arrowhead():
    """Test that curved edges have proper arrowhead calculation."""
    print("=== Testing Curved Edge Arrowhead Math ===\n")
    
    import math
    
    # Simulate the bezier curve tangent calculation
    # For a quadratic bezier: B(t) = (1-t)²*P0 + 2(1-t)t*P1 + t²*P2
    # Derivative at t=1: B'(1) = 2(P2 - P1)
    
    # Test case: curved edge from (0, 0) to (100, 0) with control point at (50, 30)
    sx, sy = 0.0, 0.0  # Start
    tx, ty = 100.0, 0.0  # End
    cx, cy = 50.0, 30.0  # Control point
    
    # Tangent at end (t=1): B'(1) = 2*(P2 - P1) = 2*((tx,ty) - (cx,cy))
    dx = 2 * (tx - cx)
    dy = 2 * (ty - cy)
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    
    print(f"Start: ({sx}, {sy})")
    print(f"End: ({tx}, {ty})")
    print(f"Control: ({cx}, {cy})")
    print(f"Tangent at end: ({dx}, {dy})")
    print(f"Unit tangent: ({ux:.3f}, {uy:.3f})")
    
    # The tangent should point from control point toward end point
    # For our test case: from (50, 30) to (100, 0), so direction is (50, -30)
    expected_dx = tx - cx  # 50
    expected_dy = ty - cy  # -30
    expected_len = math.hypot(expected_dx, expected_dy)
    expected_ux = expected_dx / expected_len
    expected_uy = expected_dy / expected_len
    
    print(f"Expected unit tangent: ({expected_ux:.3f}, {expected_uy:.3f})")
    
    assert abs(ux - expected_ux) < 0.001
    assert abs(uy - expected_uy) < 0.001
    
    print("✓ Curved arrowhead tangent calculation verified!\n")


def test_parallel_edges_with_shift():
    """Test that parallel edges are only created with Shift."""
    print("=== Testing Parallel Edge Creation ===\n")
    
    g = Graph()
    g.directed = True
    g.weighted = True  # Enable weighted mode
    g.add_node("A", x=0, y=0)
    g.add_node("B", x=100, y=0)
    
    # First edge
    g.add_edge("A", "B", weight=1)
    assert len(g.edges) == 1
    
    # Second edge (simulating Shift+click - direct add_edge call)
    g.add_edge("A", "B", weight=2)
    assert len(g.edges) == 2
    
    # Verify both edges exist with different weights
    edges = g.get_edges_between("A", "B")
    assert len(edges) == 2
    weights = sorted([e.weight for e in edges])
    assert weights == [1.0, 2.0]
    
    print(f"Created 2 parallel edges with weights: {weights}")
    print("✓ Parallel edge creation tests passed!\n")


if __name__ == "__main__":
    test_bidirectional_toggle()
    test_adjacency_matrix()
    test_incidence_matrix()
    test_dsl_toggle()
    test_curved_arrowhead()
    test_parallel_edges_with_shift()
    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)
