"""Comprehensive tests for the core graph module."""

import pytest
import json
import math
from graphsuite.core.graph import Graph, Node, Edge, GraphEvent


class TestNodeOperations:
    """Test node creation, modification, and deletion."""

    def test_add_node_auto_name(self):
        """Test automatic node naming."""
        g = Graph()
        node = g.add_node()
        assert node.name == "v1"
        node2 = g.add_node()
        assert node2.name == "v2"

    def test_add_node_custom_name(self):
        """Test adding node with custom name."""
        g = Graph()
        node = g.add_node(name="A", x=100, y=200)
        assert node.name == "A"
        assert node.x == 100
        assert node.y == 200

    def test_add_duplicate_node(self):
        """Test that duplicate node names return existing node."""
        g = Graph()
        node1 = g.add_node(name="A")
        node2 = g.add_node(name="A")
        assert node1 is node2
        assert len(g.nodes) == 1

    def test_remove_node(self):
        """Test node removal and associated edge cleanup."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        g.remove_node("A")
        assert "A" not in g.nodes
        assert len(g.edges) == 0

    def test_rename_node(self):
        """Test node renaming."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        assert g.rename_node("A", "C") is True
        assert "C" in g.nodes
        assert "A" not in g.nodes
        assert g.edges[0].source == "C"

    def test_rename_duplicate_name_fails(self):
        """Test that renaming to existing name fails."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        assert g.rename_node("A", "B") is False

    def test_move_node(self):
        """Test node movement."""
        g = Graph()
        g.add_node("A", x=0, y=0)
        g.move_node("A", 100, 200)
        assert g.nodes["A"].x == 100
        assert g.nodes["A"].y == 200

    def test_node_at_detection(self):
        """Test detecting node at coordinates."""
        g = Graph()
        g.add_node("A", x=100, y=100)
        # Node has default radius of 24
        # Point inside node circle (distance from center < radius)
        node = g.node_at(115, 100)  # 15 pixels away from center, within 24 radius
        assert node is not None
        assert node.name == "A"
        # Point outside node circle
        node_outside = g.node_at(200, 200)
        assert node_outside is None

    def test_set_node_color(self):
        """Test changing node color."""
        g = Graph()
        g.add_node("A", color="#ffffff")
        g.set_node_color("A", "#000000")
        assert g.nodes["A"].color == "#000000"


class TestEdgeOperations:
    """Test edge creation, modification, and deletion."""

    def test_add_edge(self):
        """Test basic edge creation."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        edge = g.add_edge("A", "B", weight=5)
        assert edge is not None
        assert edge.source == "A"
        assert edge.target == "B"
        # Weight is set to 1 by default if not weighted
        # Only if weighted=True is set will the weight be preserved
        g.weighted = True
        edge2 = g.add_edge("A", "B", weight=10)
        assert edge2.weight == 10

    def test_add_edge_invalid_nodes(self):
        """Test edge creation with non-existent nodes."""
        g = Graph()
        edge = g.add_edge("A", "B")
        assert edge is None

    def test_parallel_edges(self):
        """Test creating multiple edges between same nodes."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        e1 = g.add_edge("A", "B", weight=1)
        e2 = g.add_edge("A", "B", weight=2)
        e3 = g.add_edge("A", "B", weight=3)
        assert e1.edge_id != e2.edge_id != e3.edge_id
        edges = g.get_edges_between("A", "B")
        assert len(edges) == 3

    def test_get_edge_by_id(self):
        """Test retrieving edge by unique ID."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        edge = g.add_edge("A", "B")
        retrieved = g.get_edge_by_id(edge.edge_id)
        assert retrieved is edge

    def test_remove_edge(self):
        """Test edge removal."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        assert len(g.edges) == 1
        g.remove_edge("A", "B")
        assert len(g.edges) == 0

    def test_remove_edge_by_id(self):
        """Test removing specific edge by ID."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        e1 = g.add_edge("A", "B", weight=1)
        e2 = g.add_edge("A", "B", weight=2)
        g.remove_edge_by_id(e1.edge_id)
        assert len(g.edges) == 1
        assert g.edges[0].edge_id == e2.edge_id

    def test_set_edge_weight(self):
        """Test updating edge weight."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=1)
        g.set_edge_weight("A", "B", 10)
        assert g.edges[0].weight == 10

    def test_edge_at_detection(self):
        """Test detecting edge at coordinates."""
        g = Graph()
        g.add_node("A", x=0, y=0)
        g.add_node("B", x=100, y=0)
        g.add_edge("A", "B")
        # Point near edge
        edge = g.edge_at(50, 5, tolerance=10)
        assert edge is not None

    def test_bidirectional_edge_toggle(self):
        """Test toggling edge bidirectional property."""
        g = Graph()
        g.directed = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=5)
        
        # Toggle to bidirectional
        assert g.toggle_edge_bidirectional("A", "B") is True
        assert g.is_edge_bidirectional("A", "B") is True
        assert len(g.edges) == 1  # Still one edge
        
        # Toggle back to unidirectional
        assert g.toggle_edge_bidirectional("A", "B") is False
        assert g.is_edge_bidirectional("A", "B") is False

    def test_separate_bidirectional_edge(self):
        """Test separating bidirectional edge into two edges."""
        g = Graph()
        g.directed = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=5)
        g.toggle_edge_bidirectional("A", "B")
        
        # Separate into two edges
        assert g.separate_bidirectional_edge("A", "B") is True
        assert len(g.edges) == 2
        edges = g.get_edges_between("A", "B")
        reverse_edges = g.get_edges_between("B", "A")
        assert len(edges) == 1
        assert len(reverse_edges) == 1
        assert not edges[0].bidirectional
        assert not reverse_edges[0].bidirectional


class TestGraphProperties:
    """Test graph-level properties."""

    def test_directed_property(self):
        """Test switching between directed/undirected modes."""
        g = Graph()
        g.directed = True
        assert g.directed is True
        g.directed = False
        assert g.directed is False

    def test_weighted_property(self):
        """Test switching between weighted/unweighted modes."""
        g = Graph()
        g.weighted = True
        assert g.weighted is True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=5)
        g.weighted = False
        assert g.weighted is False
        assert g.edges[0].weight == 1  # Reset to 1

    def test_directed_merge_edges(self):
        """Test edge merging when switching to undirected."""
        g = Graph()
        g.directed = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        g.add_edge("B", "A")
        assert len(g.edges) == 2
        g.directed = False
        # Edges should be merged/normalized for undirected


class TestUndoRedo:
    """Test undo/redo functionality."""

    def test_undo_add_node(self):
        """Test undoing node addition."""
        g = Graph()
        g.add_node("A")
        assert len(g.nodes) == 1
        g.undo()
        assert len(g.nodes) == 0

    def test_redo_add_node(self):
        """Test redoing node addition."""
        g = Graph()
        g.add_node("A")
        g.undo()
        assert len(g.nodes) == 0
        g.redo()
        assert len(g.nodes) == 1

    def test_undo_redo_stack_limits(self):
        """Test that undo stack has maximum size."""
        g = Graph()
        g._max_history = 5
        for i in range(10):
            g.add_node(f"v{i}", record_undo=True)
        assert len(g._undo_stack) <= 5

    def test_redo_cleared_after_new_action(self):
        """Test redo stack is cleared after new action."""
        g = Graph()
        g.add_node("A")
        g.undo()
        assert len(g._redo_stack) == 1
        g.add_node("B")
        assert len(g._redo_stack) == 0

    def test_can_undo_redo(self):
        """Test can_undo and can_redo properties."""
        g = Graph()
        assert g.can_undo is False
        g.add_node("A")
        assert g.can_undo is True
        g.undo()
        assert g.can_undo is False
        assert g.can_redo is True


class TestAdjacencyMatrix:
    """Test adjacency matrix operations."""

    def test_adjacency_matrix_directed(self):
        """Test adjacency matrix for directed graph."""
        g = Graph()
        g.directed = True
        g.weighted = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=3)
        mat, names = g.get_adjacency_matrix()
        assert names == ["A", "B"]
        assert mat[0][1] == 3
        assert mat[1][0] == 0

    def test_adjacency_matrix_undirected(self):
        """Test adjacency matrix for undirected graph."""
        g = Graph()
        g.directed = False
        g.weighted = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=3)
        mat, names = g.get_adjacency_matrix()
        assert mat[0][1] == 3
        assert mat[1][0] == 3

    def test_adjacency_matrix_sum_parallel(self):
        """Test adjacency matrix sums parallel edges."""
        g = Graph()
        g.weighted = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=1)
        g.add_edge("A", "B", weight=2)
        g.add_edge("A", "B", weight=3)
        mat, _ = g.get_adjacency_matrix(sum_parallel=True)
        assert mat[0][1] == 6  # 1+2+3

    def test_adjacency_list(self):
        """Test adjacency list representation."""
        g = Graph()
        g.weighted = True
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge("A", "B", weight=2)
        g.add_edge("A", "C", weight=3)
        adj = g.get_adjacency_list()
        assert len(adj["A"]) == 2
        # Check that neighbors are present (edge IDs vary)
        neighbors = [item[0] for item in adj["A"]]
        assert "B" in neighbors
        assert "C" in neighbors

    def test_from_adjacency_matrix(self):
        """Test rebuilding graph from adjacency matrix."""
        g = Graph()
        import numpy as np
        mat = np.array([[0, 1, 2], [0, 0, 3], [0, 0, 0]])
        names = ["A", "B", "C"]
        g.add_node("A", x=0, y=0)
        g.add_node("B", x=100, y=0)
        g.add_node("C", x=200, y=0)
        g.from_adjacency_matrix(mat, names)
        assert len(g.edges) == 3


class TestSerialization:
    """Test JSON serialization and NetworkX bridge."""

    def test_json_roundtrip(self):
        """Test JSON serialization and deserialization."""
        g = Graph()
        g.directed = True
        g.weighted = True
        g.add_node("A", x=0, y=0, color="#ff0000")
        g.add_node("B", x=100, y=100)
        g.add_edge("A", "B", weight=5)
        
        json_str = g.to_json()
        data = json.loads(json_str)
        
        assert data["directed"] is True
        assert data["weighted"] is True
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        
        g2 = Graph()
        g2.from_json(json_str)
        assert len(g2.nodes) == 2
        assert len(g2.edges) == 1
        assert g2.edges[0].weight == 5

    def test_networkx_conversion_directed(self):
        """Test conversion to/from NetworkX MultiDiGraph."""
        g = Graph()
        g.directed = True
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=5)
        
        nx_g = g.to_networkx()
        assert nx_g.is_directed()
        assert nx_g.is_multigraph()
        assert nx_g.number_of_edges() == 1

    def test_networkx_conversion_undirected(self):
        """Test conversion to/from NetworkX MultiGraph."""
        g = Graph()
        g.directed = False
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=5)
        
        nx_g = g.to_networkx()
        assert not nx_g.is_directed()
        assert nx_g.is_multigraph()

    def test_networkx_roundtrip(self):
        """Test NetworkX roundtrip preserves graph."""
        g = Graph()
        g.directed = True
        g.add_node("A", x=0, y=0)
        g.add_node("B", x=100, y=100)
        g.add_edge("A", "B", weight=5)
        
        nx_g = g.to_networkx()
        g2 = Graph()
        g2.from_networkx(nx_g)
        
        assert len(g2.nodes) == 2
        assert len(g2.edges) == 1


class TestGraphEvents:
    """Test event listener system."""

    def test_node_added_event(self):
        """Test NODE_ADDED event is fired."""
        g = Graph()
        events = []
        g.add_listener(lambda event, data: events.append((event, data)))
        g.add_node("A")
        assert any(e[0] == GraphEvent.NODE_ADDED for e in events)

    def test_edge_added_event(self):
        """Test EDGE_ADDED event is fired."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        events = []
        g.add_listener(lambda event, data: events.append((event, data)))
        g.add_edge("A", "B")
        assert any(e[0] == GraphEvent.EDGE_ADDED for e in events)

    def test_remove_listener(self):
        """Test removing event listener."""
        g = Graph()
        call_count = [0]
        def listener(event, data):
            call_count[0] += 1
        g.add_listener(listener)
        g.add_node("A")
        assert call_count[0] == 1
        g.remove_listener(listener)
        g.add_node("B")
        assert call_count[0] == 1  # Should not increment


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_graph_operations(self):
        """Test operations on empty graph."""
        g = Graph()
        assert g.node_at(0, 0) is None
        assert g.edge_at(0, 0) is None
        assert g.get_edge("A", "B") is None
        mat, names = g.get_adjacency_matrix()
        assert len(mat) == 0
        assert len(names) == 0

    def test_self_loop(self):
        """Test self-loop edge."""
        g = Graph()
        g.add_node("A")
        edge = g.add_edge("A", "A", weight=5)
        assert edge is not None
        assert edge.source == "A"
        assert edge.target == "A"

    def test_clear_graph(self):
        """Test clearing entire graph."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        g.clear()
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_node_counter_resets_on_clear(self):
        """Test node counter resets after clear."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.clear()
        next_name = g.next_node_name()
        assert next_name == "v1"

    def test_distance_calculations(self):
        """Test geometric distance calculations."""
        # Point to segment distance
        dist = Graph._point_to_segment_dist(50, 0, 0, 0, 100, 0)
        assert dist == 0
        
        dist_perp = Graph._point_to_segment_dist(50, 10, 0, 0, 100, 0)
        assert dist_perp == 10
        
        # Point beyond segment
        dist_beyond = Graph._point_to_segment_dist(150, 0, 0, 0, 100, 0)
        assert dist_beyond == 50


class TestLayoutAlgorithms:
    """Test graph layout algorithms."""

    def test_layout_circle(self):
        """Test circle layout."""
        g = Graph()
        for i in range(4):
            g.add_node(f"v{i+1}")
        g.layout_circle(cx=200, cy=200, radius=100)
        
        # Check nodes are positioned in a circle (approximately)
        import math
        for i, node in enumerate(g.nodes.values()):
            # Just check that nodes are on a circle (distance from center)
            dist_from_center = math.hypot(node.x - 200, node.y - 200)
            assert abs(dist_from_center - 100) < 0.1  # Within 0.1 of radius

    def test_layout_spring(self):
        """Test spring layout runs without error."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        # Should not raise
        g.layout_spring(width=400, height=400)
        # Nodes should have been repositioned
        assert g.nodes["A"].x != 0 or g.nodes["A"].y != 0
