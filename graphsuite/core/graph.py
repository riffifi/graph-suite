"""Core graph model with adjacency matrix support and NetworkX bridge."""

from __future__ import annotations

import copy
import json
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional
import uuid

import networkx as nx
import numpy as np


@dataclass
class Node:
    name: str
    x: float = 0.0
    y: float = 0.0
    color: str = "#4fc3f7"
    radius: float = 24.0

    def to_dict(self) -> dict:
        return {"name": self.name, "x": self.x, "y": self.y,
                "color": self.color, "radius": self.radius}

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(**d)


@dataclass
class Edge:
    source: str
    target: str
    weight: float = 1.0
    color: str = "#90a4ae"
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    curvature: float = 0.0  # User-defined curvature (positive = left, negative = right)
    bidirectional: bool = False  # If True, shows arrowheads at both ends

    @property
    def key(self) -> tuple[str, str]:
        return (self.source, self.target)

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target,
                "weight": self.weight, "color": self.color,
                "edge_id": self.edge_id, "curvature": self.curvature,
                "bidirectional": self.bidirectional}

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        edge_id = d.pop("edge_id", str(uuid.uuid4())[:8])
        curvature = d.pop("curvature", 0.0)
        bidirectional = d.pop("bidirectional", False)
        edge = cls(**d)
        edge.edge_id = edge_id
        edge.curvature = curvature
        edge.bidirectional = bidirectional
        return edge


class GraphEvent(Enum):
    NODE_ADDED = auto()
    NODE_REMOVED = auto()
    NODE_MOVED = auto()
    NODE_RENAMED = auto()
    NODE_COLOR_CHANGED = auto()
    EDGE_ADDED = auto()
    EDGE_REMOVED = auto()
    EDGE_WEIGHT_CHANGED = auto()
    GRAPH_CLEARED = auto()
    GRAPH_REBUILT = auto()
    DIRECTED_CHANGED = auto()
    WEIGHTED_CHANGED = auto()
    UNDO_REDO = auto()


class Graph:
    """Central graph model – single source of truth for the application."""

    def __init__(self) -> None:
        self._nodes: OrderedDict[str, Node] = OrderedDict()
        self._edges: list[Edge] = []
        self._directed: bool = True
        self._weighted: bool = False
        self._listeners: list[Callable[[GraphEvent, dict[str, Any]], None]] = []

        # undo / redo
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._max_history = 100

        # auto-naming counter
        self._node_counter = 0

    # -- observer ----------------------------------------------------------

    def add_listener(self, cb: Callable[[GraphEvent, dict[str, Any]], None]) -> None:
        self._listeners.append(cb)

    def remove_listener(self, cb: Callable) -> None:
        self._listeners = [l for l in self._listeners if l is not cb]

    def _notify(self, event: GraphEvent, **kwargs: Any) -> None:
        for cb in self._listeners:
            cb(event, kwargs)

    # -- properties --------------------------------------------------------

    @property
    def directed(self) -> bool:
        return self._directed

    @directed.setter
    def directed(self, value: bool) -> None:
        if value != self._directed:
            self._save_undo()
            self._directed = value
            # When switching to undirected, merge duplicate edges
            if not value:
                self._merge_undirected_edges()
            self._notify(GraphEvent.DIRECTED_CHANGED, directed=value)

    @property
    def weighted(self) -> bool:
        return self._weighted

    @weighted.setter
    def weighted(self, value: bool) -> None:
        if value != self._weighted:
            self._save_undo()
            self._weighted = value
            if not value:
                for e in self._edges:
                    e.weight = 1.0
            self._notify(GraphEvent.WEIGHTED_CHANGED, weighted=value)

    @property
    def nodes(self) -> OrderedDict[str, Node]:
        return self._nodes

    @property
    def edges(self) -> list[Edge]:
        return self._edges

    @property
    def node_names(self) -> list[str]:
        return list(self._nodes.keys())

    # -- node operations ---------------------------------------------------

    def next_node_name(self) -> str:
        while True:
            self._node_counter += 1
            name = f"v{self._node_counter}"
            if name not in self._nodes:
                return name

    def add_node(self, name: str | None = None, x: float = 0.0, y: float = 0.0,
                 color: str = "#4fc3f7", record_undo: bool = True) -> Node:
        if name is None:
            name = self.next_node_name()
        if name in self._nodes:
            return self._nodes[name]
        if record_undo:
            self._save_undo()
        node = Node(name=name, x=x, y=y, color=color)
        self._nodes[name] = node
        self._notify(GraphEvent.NODE_ADDED, node=node)
        return node

    def remove_node(self, name: str, record_undo: bool = True) -> None:
        if name not in self._nodes:
            return
        if record_undo:
            self._save_undo()
        del self._nodes[name]
        self._edges = [e for e in self._edges
                       if e.source != name and e.target != name]
        self._notify(GraphEvent.NODE_REMOVED, name=name)

    def rename_node(self, old_name: str, new_name: str) -> bool:
        if old_name not in self._nodes or new_name in self._nodes:
            return False
        self._save_undo()
        node = self._nodes[old_name]
        node.name = new_name
        # Rebuild ordered dict preserving order
        new_nodes: OrderedDict[str, Node] = OrderedDict()
        for k, v in self._nodes.items():
            new_nodes[new_name if k == old_name else k] = v
        self._nodes = new_nodes
        for e in self._edges:
            if e.source == old_name:
                e.source = new_name
            if e.target == old_name:
                e.target = new_name
        self._notify(GraphEvent.NODE_RENAMED, old=old_name, new=new_name)
        return True

    def move_node(self, name: str, x: float, y: float,
                  record_undo: bool = False) -> None:
        if name in self._nodes:
            n = self._nodes[name]
            if record_undo:
                self._save_undo()
            n.x, n.y = x, y
            self._notify(GraphEvent.NODE_MOVED, name=name, x=x, y=y)

    def set_node_color(self, name: str, color: str) -> None:
        if name in self._nodes:
            self._save_undo()
            self._nodes[name].color = color
            self._notify(GraphEvent.NODE_COLOR_CHANGED, name=name, color=color)

    def node_at(self, x: float, y: float) -> Node | None:
        """Return the top-most node whose circle contains (x, y)."""
        for node in reversed(list(self._nodes.values())):
            dx = node.x - x
            dy = node.y - y
            if math.hypot(dx, dy) <= node.radius:
                return node
        return None

    # -- edge operations ---------------------------------------------------

    def get_edge(self, src: str, tgt: str, edge_id: str | None = None) -> Edge | None:
        """Get edge between src and tgt. If edge_id is provided, get specific edge."""
        for e in self._edges:
            if e.source == src and e.target == tgt:
                if edge_id is None or e.edge_id == edge_id:
                    return e
        return None

    def get_edge_by_id(self, edge_id: str) -> Edge | None:
        """Get edge by its unique ID."""
        for e in self._edges:
            if e.edge_id == edge_id:
                return e
        return None

    def has_edge(self, src: str, tgt: str, edge_id: str | None = None) -> bool:
        """Check if edge exists. If edge_id is provided, check for specific edge."""
        return self.get_edge(src, tgt, edge_id) is not None

    def get_edges_between(self, src: str, tgt: str) -> list[Edge]:
        """Get all parallel edges between src and tgt."""
        return [e for e in self._edges if e.source == src and e.target == tgt]

    def add_edge(self, source: str, target: str, weight: float = 1.0,
                 edge_id: str | None = None, record_undo: bool = True) -> Edge | None:
        """Add edge between source and target. Allows parallel edges."""
        if source not in self._nodes or target not in self._nodes:
            return None
        if record_undo:
            self._save_undo()
        edge = Edge(source=source, target=target,
                    weight=weight if self._weighted else 1.0,
                    edge_id=edge_id or str(uuid.uuid4())[:8])
        self._edges.append(edge)
        self._notify(GraphEvent.EDGE_ADDED, edge=edge)
        return edge

    def remove_edge(self, source: str, target: str,
                    edge_id: str | None = None,
                    record_undo: bool = True) -> None:
        """Remove edge(s) between source and target. If edge_id provided, remove specific edge."""
        before = len(self._edges)
        if edge_id is not None:
            self._edges = [e for e in self._edges
                           if not (e.source == source and e.target == target and e.edge_id == edge_id)]
        else:
            self._edges = [e for e in self._edges
                           if not (e.source == source and e.target == target)]
            if not self._directed:
                self._edges = [e for e in self._edges
                               if not (e.source == target and e.target == source)]
        if len(self._edges) < before:
            if record_undo:
                self._save_undo()
            self._notify(GraphEvent.EDGE_REMOVED,
                         source=source, target=target, edge_id=edge_id)

    def remove_edge_by_id(self, edge_id: str, record_undo: bool = True) -> None:
        """Remove a specific edge by its ID."""
        edge = self.get_edge_by_id(edge_id)
        if edge is not None:
            self.remove_edge(edge.source, edge.target, edge_id=edge_id, record_undo=record_undo)

    def set_edge_weight(self, source: str, target: str, weight: float,
                        edge_id: str | None = None) -> None:
        """Set weight of edge. If edge_id provided, set weight of specific edge."""
        edge = self.get_edge(source, target, edge_id)
        # For directed graphs, also check reverse direction if edge_id is provided
        # (handles bidirectional edge weight updates from either direction)
        if edge is None and edge_id is not None and self._directed:
            edge = self.get_edge(target, source, edge_id)
        if edge is None and not self._directed:
            edge = self.get_edge(target, source, edge_id)
        if edge is not None:
            self._save_undo()
            edge.weight = weight
            self._notify(GraphEvent.EDGE_WEIGHT_CHANGED, edge=edge)

    def set_edge_curvature(self, source: str, target: str, curvature: float,
                           edge_id: str | None = None) -> None:
        """Set curvature of edge. If edge_id provided, set curvature of specific edge.
        Positive curvature = curve to the left, Negative = curve to the right."""
        edge = self.get_edge(source, target, edge_id)
        if edge is None and not self._directed:
            edge = self.get_edge(target, source, edge_id)
        if edge is not None:
            self._save_undo()
            edge.curvature = curvature
            self._notify(GraphEvent.EDGE_WEIGHT_CHANGED, edge=edge)  # reuse event

    def toggle_edge_bidirectional(self, source: str, target: str,
                                   edge_id: str | None = None) -> bool:
        """Toggle an edge's bidirectional property.
        
        This toggles a property on the edge itself - no separate reverse edge is created.
        When bidirectional=True, the edge shows arrowheads at both ends.
        
        Returns True if now bidirectional, False if now unidirectional.
        """
        if not self._directed:
            return False  # Only makes sense for directed graphs
        
        edge = self.get_edge(source, target, edge_id)
        if edge is None:
            return False
        
        # Toggle the bidirectional property on the edge itself
        self._save_undo()
        edge.bidirectional = not edge.bidirectional
        self._notify(GraphEvent.EDGE_WEIGHT_CHANGED, edge=edge)
        return edge.bidirectional

    def separate_bidirectional_edge(self, source: str, target: str,
                                     edge_id: str | None = None) -> bool:
        """Separate a bidirectional edge into two separate parallel edges.
        
        Converts one bidirectional edge (A→B with bidirectional=True) into
        two separate edges (A→B and B→A).
        
        Returns True if successful, False if edge was not bidirectional.
        """
        if not self._directed:
            return False
        
        edge = self.get_edge(source, target, edge_id)
        if edge is None or not edge.bidirectional:
            return False
        
        # Create the reverse edge with same properties
        self._save_undo()
        reverse_edge = Edge(source=target, target=source,
                           weight=edge.weight,
                           color=edge.color,
                           curvature=edge.curvature,
                           bidirectional=False)
        self._edges.append(reverse_edge)
        
        # Remove bidirectional property from original edge
        edge.bidirectional = False
        
        self._notify(GraphEvent.EDGE_ADDED, edge=reverse_edge)
        self._notify(GraphEvent.EDGE_WEIGHT_CHANGED, edge=edge)
        return True

    def is_edge_bidirectional(self, source: str, target: str,
                               edge_id: str | None = None) -> bool:
        """Check if an edge has the bidirectional property set."""
        if not self._directed:
            return False
        edge = self.get_edge(source, target, edge_id)
        if edge is None:
            return False
        return edge.bidirectional

    def edge_at(self, x: float, y: float, tolerance: float = 10.0) -> Edge | None:
        """Return edge closest to (x, y) within tolerance.
        Accounts for curved edges using bezier curve distance."""
        best: Edge | None = None
        best_dist = tolerance
        for e in self._edges:
            src = self._nodes.get(e.source)
            tgt = self._nodes.get(e.target)
            if src is None or tgt is None:
                continue
            
            # Self-loop check
            if e.source == e.target:
                d = self._point_to_self_loop_dist(x, y, src.x, src.y, src.radius)
            elif e.curvature != 0.0:
                # Use bezier curve distance for curved edges
                d = self._point_to_bezier_dist(x, y, src.x, src.y, tgt.x, tgt.y, e.curvature)
            else:
                # Straight line distance
                d = self._point_to_segment_dist(x, y, src.x, src.y, tgt.x, tgt.y)
            
            if d < best_dist:
                best_dist = d
                best = e
        return best

    @staticmethod
    def _point_to_segment_dist(px: float, py: float,
                                x1: float, y1: float,
                                x2: float, y2: float) -> float:
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    @staticmethod
    def _point_to_bezier_dist(px: float, py: float,
                               x1: float, y1: float,
                               x2: float, y2: float,
                               curvature: float) -> float:
        """Distance from point to quadratic bezier curve.
        Samples the curve at multiple points for accuracy."""
        # Calculate control point (same as in canvas)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return math.hypot(px - x1, py - y1)
        
        # Perpendicular direction for control point offset
        nx, ny = -dy / length, dx / length
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ctrl_x = mid_x + nx * curvature
        ctrl_y = mid_y + ny * curvature
        
        # Sample the bezier curve at multiple points
        min_dist = float('inf')
        num_samples = 20  # More samples = more accurate but slower
        
        for i in range(num_samples + 1):
            t = i / num_samples
            # Quadratic bezier: B(t) = (1-t)²*P0 + 2(1-t)t*P1 + t²*P2
            one_minus_t = 1 - t
            bx = one_minus_t * one_minus_t * x1 + 2 * one_minus_t * t * ctrl_x + t * t * x2
            by = one_minus_t * one_minus_t * y1 + 2 * one_minus_t * t * ctrl_y + t * t * y2
            dist = math.hypot(px - bx, py - by)
            min_dist = min(min_dist, dist)
        
        return min_dist

    @staticmethod
    def _point_to_self_loop_dist(px: float, py: float,
                                  cx: float, cy: float,
                                  radius: float) -> float:
        """Distance from point to self-loop edge."""
        loop_r = radius * 1.2
        loop_center_y = cy - radius - loop_r + 4
        # Distance to the loop circle
        dist_to_circle = math.hypot(px - cx, py - loop_center_y) - loop_r
        return max(0, dist_to_circle)

    # -- clear / rebuild ---------------------------------------------------

    def clear(self, record_undo: bool = True) -> None:
        if record_undo:
            self._save_undo()
        self._nodes.clear()
        self._edges.clear()
        self._node_counter = 0
        self._notify(GraphEvent.GRAPH_CLEARED)

    # -- adjacency matrix --------------------------------------------------

    def get_adjacency_matrix(self, sum_parallel: bool = True) -> tuple[np.ndarray, list[str]]:
        """Get adjacency matrix. For multigraphs, sum_parallel=True sums weights of parallel edges."""
        names = list(self._nodes.keys())
        n = len(names)
        idx = {name: i for i, name in enumerate(names)}
        mat = np.zeros((n, n), dtype=float)
        for e in self._edges:
            i, j = idx.get(e.source), idx.get(e.target)
            if i is not None and j is not None:
                if sum_parallel:
                    mat[i][j] += e.weight
                    if not self._directed:
                        mat[j][i] += e.weight
                else:
                    mat[i][j] = e.weight
                    if not self._directed:
                        mat[j][i] = e.weight
        return mat, names

    def get_adjacency_list(self) -> dict[str, list[tuple[str, float, str]]]:
        """Get adjacency list with edge weights and edge IDs.
        Returns: {node_name: [(neighbor, weight, edge_id), ...]}"""
        adj: dict[str, list[tuple[str, float, str]]] = {name: [] for name in self._nodes}
        for e in self._edges:
            if e.source in adj:
                adj[e.source].append((e.target, e.weight, e.edge_id))
            if not self._directed:
                if e.target in adj:
                    adj[e.target].append((e.source, e.weight, e.edge_id))
        return adj

    def from_adjacency_matrix(self, matrix: np.ndarray, names: list[str]) -> None:
        """Rebuild graph from an adjacency matrix, preserving node positions
        where possible. Note: parallel edges are not recreated from matrix."""
        self._save_undo()
        old_positions = {n.name: (n.x, n.y) for n in self._nodes.values()}
        self._nodes.clear()
        self._edges.clear()

        n = len(names)
        for i, name in enumerate(names):
            ox, oy = old_positions.get(name, (100 + i * 80, 200))
            self._nodes[name] = Node(name=name, x=ox, y=oy)

        for i in range(n):
            for j in range(n):
                w = float(matrix[i][j])
                if w != 0:
                    if not self._directed and j < i:
                        continue  # avoid duplicates for undirected
                    self._edges.append(
                        Edge(source=names[i], target=names[j], weight=w))

        self._notify(GraphEvent.GRAPH_REBUILT)

    # -- NetworkX bridge ---------------------------------------------------

    def to_networkx(self) -> nx.MultiDiGraph | nx.MultiGraph:
        """Convert to NetworkX MultiGraph (supports parallel edges)."""
        G = nx.MultiDiGraph() if self._directed else nx.MultiGraph()
        for name, node in self._nodes.items():
            G.add_node(name, x=node.x, y=node.y, color=node.color)
        for e in self._edges:
            G.add_edge(e.source, e.target, key=e.edge_id, weight=e.weight)
        return G

    def from_networkx(self, G: nx.MultiDiGraph | nx.MultiGraph) -> None:
        """Load graph from NetworkX MultiGraph."""
        self._save_undo()
        self._nodes.clear()
        self._edges.clear()
        for name, data in G.nodes(data=True):
            self._nodes[name] = Node(
                name=name,
                x=data.get("x", 0.0),
                y=data.get("y", 0.0),
                color=data.get("color", "#4fc3f7")
            )
        if G.is_multigraph():
            for u, v, key, data in G.edges(keys=True, data=True):
                self._edges.append(Edge(
                    source=u, target=v,
                    weight=data.get("weight", 1.0),
                    edge_id=key
                ))
        else:
            for u, v, data in G.edges(data=True):
                self._edges.append(Edge(
                    source=u, target=v,
                    weight=data.get("weight", 1.0)
                ))
        self._directed = G.is_directed()
        self._node_counter = len(self._nodes)
        self._notify(GraphEvent.GRAPH_REBUILT)

    # -- undo / redo -------------------------------------------------------

    def _snapshot(self) -> dict:
        return {
            "nodes": [(n.name, n.to_dict()) for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "directed": self._directed,
            "weighted": self._weighted,
            "counter": self._node_counter,
        }

    def _restore(self, snap: dict) -> None:
        self._nodes = OrderedDict()
        for _, d in snap["nodes"]:
            n = Node.from_dict(d)
            self._nodes[n.name] = n
        self._edges = [Edge.from_dict(d) for d in snap["edges"]]
        self._directed = snap["directed"]
        self._weighted = snap["weighted"]
        self._node_counter = snap["counter"]
        self._notify(GraphEvent.UNDO_REDO)

    def _save_undo(self) -> None:
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    # -- serialization (JSON) ----------------------------------------------

    def to_json(self) -> str:
        return json.dumps({
            "directed": self._directed,
            "weighted": self._weighted,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }, indent=2)

    def from_json(self, data: str) -> None:
        self._save_undo()
        d = json.loads(data)
        self._directed = d.get("directed", True)
        self._weighted = d.get("weighted", False)
        self._nodes = OrderedDict()
        for nd in d.get("nodes", []):
            n = Node.from_dict(nd)
            self._nodes[n.name] = n
        self._edges = [Edge.from_dict(ed) for ed in d.get("edges", [])]
        self._node_counter = len(self._nodes)
        self._notify(GraphEvent.GRAPH_REBUILT)

    # -- helpers -----------------------------------------------------------

    def _merge_undirected_edges(self) -> None:
        """Merge duplicate edges when switching to undirected mode.
        Now preserves parallel edges by using edge_id."""
        # For undirected graphs, we normalize edge direction
        # but keep parallel edges with different edge_ids
        seen: dict[tuple[str, str], Edge] = {}
        merged: list[Edge] = []
        for e in self._edges:
            key = tuple(sorted((e.source, e.target)))
            if key not in seen:
                seen[key] = e
                merged.append(e)
            # Keep parallel edges - they have different edge_ids
        self._edges = merged

    def layout_circle(self, cx: float = 400, cy: float = 300,
                      radius: float = 200) -> None:
        names = list(self._nodes.keys())
        n = len(names)
        if n == 0:
            return
        self._save_undo()
        for i, name in enumerate(names):
            angle = 2 * math.pi * i / n - math.pi / 2
            self._nodes[name].x = cx + radius * math.cos(angle)
            self._nodes[name].y = cy + radius * math.sin(angle)
        self._notify(GraphEvent.GRAPH_REBUILT)

    def layout_spring(self, width: float = 800, height: float = 600) -> None:
        """Use NetworkX spring layout to position nodes."""
        G = self.to_networkx()
        if len(G) == 0:
            return
        self._save_undo()
        pos = nx.spring_layout(G, scale=min(width, height) * 0.35,
                               center=(width / 2, height / 2), seed=42)
        for name, (x, y) in pos.items():
            if name in self._nodes:
                self._nodes[name].x = float(x)
                self._nodes[name].y = float(y)
        self._notify(GraphEvent.GRAPH_REBUILT)

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return (f"Graph(nodes={len(self._nodes)}, edges={len(self._edges)}, "
                f"directed={self._directed}, weighted={self._weighted})")
