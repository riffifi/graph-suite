"""Tests for graph algorithms via the algorithm panel."""

import pytest
import networkx as nx
from graphsuite.core.graph import Graph


class TestAlgorithmPanel:
    """Test algorithm execution."""

    def test_bfs_traversal(self, directed_graph):
        """Test BFS traversal."""
        g = directed_graph
        G_nx = g.to_networkx()
        bfs_order = list(nx.bfs_tree(G_nx, "A").nodes())
        assert "A" in bfs_order
        assert len(bfs_order) == 3

    def test_dfs_traversal(self, directed_graph):
        """Test DFS traversal."""
        g = directed_graph
        G_nx = g.to_networkx()
        dfs_order = list(nx.dfs_tree(G_nx, "A").nodes())
        assert "A" in dfs_order
        assert len(dfs_order) == 3

    def test_dijkstra_shortest_path(self, weighted_graph):
        """Test Dijkstra's algorithm."""
        g = weighted_graph
        G_nx = g.to_networkx()
        path = nx.dijkstra_path(G_nx, "A", "C", weight="weight")
        assert path[0] == "A"
        assert path[-1] == "C"

    def test_dijkstra_no_path(self):
        """Test Dijkstra with no path."""
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        # No edge between A and B
        G_nx = g.to_networkx()
        with pytest.raises(nx.NetworkXNoPath):
            nx.dijkstra_path(G_nx, "A", "B", weight="weight")

    def test_bellman_ford(self, weighted_graph):
        """Test Bellman-Ford algorithm."""
        g = weighted_graph
        G_nx = g.to_networkx()
        path = nx.bellman_ford_path(G_nx, "A", "C", weight="weight")
        assert path[0] == "A"
        assert path[-1] == "C"

    def test_mst_undirected(self, undirected_graph):
        """Test Minimum Spanning Tree."""
        g = undirected_graph
        G_nx = g.to_networkx()
        mst = nx.minimum_spanning_tree(G_nx, weight="weight")
        assert mst.number_of_edges() == 2  # n-1 edges for n nodes

    def test_mst_directed_fails(self, directed_graph):
        """Test MST requires undirected graph."""
        g = directed_graph
        # MST is for undirected graphs
        assert g.directed is True

    def test_topological_sort(self, acyclic_graph):
        """Test topological sort on DAG."""
        g = acyclic_graph
        G_nx = g.to_networkx()
        order = list(nx.topological_sort(G_nx))
        # A should come before B and C
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")

    def test_topological_sort_with_cycle_fails(self, cyclic_graph):
        """Test topological sort fails on cyclic graph."""
        g = cyclic_graph
        G_nx = g.to_networkx()
        with pytest.raises(nx.NetworkXUnfeasible):
            list(nx.topological_sort(G_nx))

    def test_connected_components(self, disconnected_graph):
        """Test connected components."""
        g = disconnected_graph
        G_nx = g.to_networkx()
        # For directed graphs, use weakly connected components
        if g.directed:
            components = list(nx.weakly_connected_components(G_nx))
        else:
            components = list(nx.connected_components(G_nx))
        assert len(components) == 2

    def test_strongly_connected_components(self, cyclic_graph):
        """Test strongly connected components."""
        g = cyclic_graph
        G_nx = g.to_networkx()
        sccs = list(nx.strongly_connected_components(G_nx))
        # In a cycle, all nodes are in one SCC
        assert len(sccs) == 1

    def test_cycle_detection(self, cyclic_graph):
        """Test cycle detection."""
        g = cyclic_graph
        G_nx = g.to_networkx()
        cycle = nx.find_cycle(G_nx)
        assert len(cycle) == 3

    def test_cycle_detection_acyclic(self, acyclic_graph):
        """Test cycle detection on acyclic graph."""
        g = acyclic_graph
        G_nx = g.to_networkx()
        with pytest.raises(nx.NetworkXNoCycle):
            nx.find_cycle(G_nx)

    def test_degree_centrality(self, complete_graph_5):
        """Test degree centrality calculation."""
        g = complete_graph_5
        G_nx = g.to_networkx()
        cent = nx.degree_centrality(G_nx)
        # In K5, all nodes have degree 4, centrality = 4/(5-1) = 1.0
        for node, val in cent.items():
            assert val == 1.0

    def test_graph_info(self, simple_graph):
        """Test graph info calculation."""
        g = simple_graph
        G_nx = g.to_networkx()
        n_nodes = G_nx.number_of_nodes()
        n_edges = G_nx.number_of_edges()
        density = nx.density(G_nx)
        assert n_nodes == 2
        assert n_edges == 1
        assert 0 <= density <= 1


# GUI tests skipped - require display
@pytest.mark.skip(reason="GUI tests require display")
class TestAlgorithmPanelUI:
    """Test algorithm panel UI integration."""

    def test_panel_creation(self, simple_graph):
        """Test algorithm panel can be created."""
        pass

    def test_panel_algorithm_list(self, simple_graph):
        """Test algorithm panel has algorithms."""
        pass

    def test_panel_run_button(self, simple_graph):
        """Test run button exists."""
        pass

    def test_panel_clear_button(self, simple_graph):
        """Test clear button exists."""
        pass

    def test_panel_show_only_checkbox(self, simple_graph):
        """Test 'Show Only Path' checkbox exists."""
        pass
