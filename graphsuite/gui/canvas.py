"""Interactive graph canvas – the main visual editor."""

from __future__ import annotations

import math
from enum import Enum, auto

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QFontMetrics,
    QPainterPath, QPolygonF, QWheelEvent, QMouseEvent,
    QKeyEvent, QInputMethodEvent,
)
from PySide6.QtWidgets import (
    QWidget, QMenu, QInputDialog, QColorDialog, QApplication,
)

from graphsuite.core.graph import Graph, GraphEvent, Node, Edge
from graphsuite.gui.style import Colors


class CanvasMode(Enum):
    SELECT = auto()
    ADD_NODE = auto()
    ADD_EDGE = auto()
    DELETE = auto()


class GraphCanvas(QWidget):
    """Custom-painted widget for interactive graph editing."""

    mode_changed = Signal(CanvasMode)
    selection_changed = Signal()  # emitted when selected node/edge changes

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._mode = CanvasMode.SELECT

        # interaction state
        self._selected_nodes: set[str] = set()
        self._selected_edges: set[tuple[str, str]] = set()
        self._hovered_node: str | None = None
        self._hovered_edge: tuple[str, str] | None = None
        self._dragging_node: str | None = None
        self._drag_start: QPointF | None = None

        # edge creation
        self._edge_src: str | None = None
        self._edge_temp_end: QPointF | None = None

        # edge curvature editing
        self._hovered_edge_curvature: tuple[str, str, str] | None = None  # (src, tgt, edge_id)
        self._dragging_edge_curvature: tuple[str, str, str] | None = None
        self._curve_handle_radius: float = 10.0

        # pan / zoom
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._panning = False
        self._pan_start: QPointF | None = None
        self._pan_start_offset: QPointF | None = None

        # algorithm highlight
        self._highlighted_nodes: set[str] = set()
        self._highlighted_edges: set[tuple[str, str]] = set()
        self._hide_non_highlighted: bool = False  # "Show Only Path" mode

        # settings
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(400, 300)

        # listen to graph changes
        self.graph.add_listener(self._on_graph_event)

    # -- public API --------------------------------------------------------

    @property
    def mode(self) -> CanvasMode:
        return self._mode

    @mode.setter
    def mode(self, m: CanvasMode) -> None:
        self._mode = m
        self._edge_src = None
        self._edge_temp_end = None
        self._update_cursor()
        self.mode_changed.emit(m)
        self.update()

    def clear_selection(self) -> None:
        self._selected_nodes.clear()
        self._selected_edges.clear()
        self.selection_changed.emit()
        self.update()

    def set_highlight(self, nodes: set[str],
                      edges: set[tuple[str, str]]) -> None:
        """Set highlight and show full graph with highlighted elements."""
        self._highlighted_nodes = nodes
        self._highlighted_edges = edges
        self._hide_non_highlighted = False  # Show full graph
        self.update()

    def clear_highlight(self) -> None:
        self._highlighted_nodes.clear()
        self._highlighted_edges.clear()
        self._hide_non_highlighted = False
        self.update()

    def set_highlight_only(self, nodes: set[str],
                           edges: set[tuple[str, str]]) -> None:
        """Set highlight and hide non-highlighted elements."""
        self._highlighted_nodes = nodes
        self._highlighted_edges = edges
        self._hide_non_highlighted = True
        self.update()

    def clear_highlight_only(self) -> None:
        """Clear highlight and show all elements."""
        self._highlighted_nodes.clear()
        self._highlighted_edges.clear()
        self._hide_non_highlighted = False
        self.update()

    def fit_view(self) -> None:
        """Adjust zoom/pan so all nodes are visible."""
        if not self.graph.nodes:
            return
        xs = [n.x for n in self.graph.nodes.values()]
        ys = [n.y for n in self.graph.nodes.values()]
        margin = 60
        min_x, max_x = min(xs) - margin, max(xs) + margin
        min_y, max_y = min(ys) - margin, max(ys) + margin
        gw = max_x - min_x or 1
        gh = max_y - min_y or 1
        zx = self.width() / gw
        zy = self.height() / gh
        self._zoom = min(zx, zy, 3.0)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        self._pan = QPointF(
            self.width() / 2 - cx * self._zoom,
            self.height() / 2 - cy * self._zoom,
        )
        self.update()

    # -- coordinate transforms ---------------------------------------------

    def _to_scene(self, widget_pos: QPointF) -> QPointF:
        return QPointF(
            (widget_pos.x() - self._pan.x()) / self._zoom,
            (widget_pos.y() - self._pan.y()) / self._zoom,
        )

    def _to_widget(self, scene_pos: QPointF) -> QPointF:
        return QPointF(
            scene_pos.x() * self._zoom + self._pan.x(),
            scene_pos.y() * self._zoom + self._pan.y(),
        )

    # -- graph events ------------------------------------------------------

    def _on_graph_event(self, event: GraphEvent, data: dict) -> None:
        self.update()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # background
        p.fillRect(self.rect(), QColor(Colors.CANVAS_BG))
        self._draw_grid(p)

        p.save()
        p.translate(self._pan)
        p.scale(self._zoom, self._zoom)

        # draw edges first
        for edge in self.graph.edges:
            self._draw_edge(p, edge)

        # draw curve handles for hovered edges (Ctrl mode)
        self._draw_curve_handles(p)

        # temp edge while creating
        if self._edge_src and self._edge_temp_end:
            src_node = self.graph.nodes.get(self._edge_src)
            if src_node:
                p.setPen(QPen(QColor(Colors.PRIMARY), 2, Qt.PenStyle.DashLine))
                end = self._to_scene(self._edge_temp_end)
                p.drawLine(QPointF(src_node.x, src_node.y),
                           QPointF(end.x(), end.y()))

        # draw nodes
        for node in self.graph.nodes.values():
            self._draw_node(p, node)

        p.restore()

        # HUD: mode indicator
        p.setPen(QPen(QColor(Colors.TEXT_DIM)))
        font = QFont("sans-serif", 10)
        p.setFont(font)
        
        # Check for Shift modifier for parallel edge hint
        shift_held = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ctrl_held = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier
        parallel_hint = " | Hold Shift: Parallel Edge" if shift_held and self._mode == CanvasMode.ADD_EDGE else ""
        curve_hint = " | Ctrl+Drag: Curve Edges" if ctrl_held and self._mode == CanvasMode.SELECT else ""

        p.drawText(10, self.height() - 10,
                   f"Mode: {self._mode.name}  |  "
                   f"Zoom: {self._zoom:.0%}  |  "
                   f"Nodes: {len(self.graph.nodes)}  "
                   f"Edges: {len(self.graph.edges)}{parallel_hint}{curve_hint}")

    def _draw_grid(self, p: QPainter) -> None:
        step = max(20, int(40 * self._zoom))
        pen = QPen(QColor(Colors.CANVAS_GRID), 1)
        p.setPen(pen)
        ox = int(self._pan.x()) % step
        oy = int(self._pan.y()) % step
        for x in range(ox, self.width(), step):
            p.drawLine(x, 0, x, self.height())
        for y in range(oy, self.height(), step):
            p.drawLine(0, y, self.width(), y)

    def _draw_node(self, p: QPainter, node: Node) -> None:
        r = node.radius
        is_selected = node.name in self._selected_nodes
        is_highlighted = node.name in self._highlighted_nodes
        is_hovered = node.name == self._hovered_node

        # "Show Only Path" mode - hide non-highlighted nodes
        if self._hide_non_highlighted and not is_highlighted and not is_selected:
            return  # Skip drawing this node

        # outer glow for selection / highlight
        if is_selected:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(Colors.NODE_SELECTED + "44")))
            p.drawEllipse(QPointF(node.x, node.y), r + 8, r + 8)
        elif is_highlighted:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(Colors.ALGO_HIGHLIGHT + "44")))
            p.drawEllipse(QPointF(node.x, node.y), r + 8, r + 8)

        # fill
        fill_color = (Colors.NODE_SELECTED if is_selected
                      else Colors.ALGO_HIGHLIGHT if is_highlighted
                      else Colors.NODE_HOVER if is_hovered
                      else node.color)
        p.setBrush(QBrush(QColor(fill_color)))

        # border
        border_color = (Colors.NODE_SELECTED if is_selected
                        else Colors.ALGO_HIGHLIGHT if is_highlighted
                        else Colors.TEXT_BRIGHT if is_hovered
                        else "#00000044")
        p.setPen(QPen(QColor(border_color), 2))
        p.drawEllipse(QPointF(node.x, node.y), r, r)

        # label
        font = QFont("sans-serif", max(9, int(12 * min(self._zoom, 1.5) / self._zoom)))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QPen(QColor(Colors.NODE_LABEL)))
        text_rect = QRectF(node.x - r, node.y - r, 2 * r, 2 * r)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, node.name)

    def _get_parallel_edge_index(self, edge: Edge) -> int:
        """Get the index of this edge among parallel edges between same nodes."""
        edges_between = self.graph.get_edges_between(edge.source, edge.target)
        # Sort by edge_id for consistent ordering
        sorted_edges = sorted(edges_between, key=lambda e: e.edge_id)
        for i, e in enumerate(sorted_edges):
            if e.edge_id == edge.edge_id:
                return i
        return 0

    def _draw_edge(self, p: QPainter, edge: Edge) -> None:
        src = self.graph.nodes.get(edge.source)
        tgt = self.graph.nodes.get(edge.target)
        if src is None or tgt is None:
            return

        key = (edge.source, edge.target)
        is_selected = key in self._selected_edges
        is_highlighted = (key in self._highlighted_edges or
                          (edge.target, edge.source) in self._highlighted_edges)
        is_hovered = (key == self._hovered_edge)

        # "Show Only Path" mode - hide non-highlighted edges
        if self._hide_non_highlighted and not is_highlighted and not is_selected:
            return  # Skip drawing this edge

        # self-loop
        if edge.source == edge.target:
            self._draw_self_loop(p, src, edge, is_selected, is_highlighted)
            return

        color = (Colors.EDGE_SELECTED if is_selected
                 else Colors.ALGO_HIGHLIGHT if is_highlighted
                 else Colors.PRIMARY if is_hovered
                 else edge.color)
        width = 3 if (is_selected or is_highlighted) else 2

        sx, sy = src.x, src.y
        tx, ty = tgt.x, tgt.y
        dx, dy = tx - sx, ty - sy
        length = math.hypot(dx, dy)
        if length == 0:
            return

        # unit normal for offset/perpendicular direction
        nx_, ny_ = -dy / length, dx / length

        # Safeguard: ensure normal is unit length
        normal_len = math.hypot(nx_, ny_)
        if normal_len > 0:
            nx_, ny_ = nx_ / normal_len, ny_ / normal_len

        # Check for parallel edges (multiple edges in same direction)
        parallel_edges = self.graph.get_edges_between(edge.source, edge.target)
        num_parallel = len(parallel_edges)
        edge_idx = self._get_parallel_edge_index(edge)

        # Use user-defined curvature if set
        # Bidirectional edges stay straight unless user explicitly curves them
        curvature = edge.curvature  # User-defined curvature takes priority

        # Only auto-curve edges that are NOT bidirectional and have no user curvature
        if curvature == 0.0 and num_parallel > 1 and not edge.bidirectional:
            # Auto-curve only non-bidirectional edges without user curvature
            spacing = 30.0  # pixels between parallel edges
            if num_parallel % 2 == 1:
                # Odd: center edge is straight, others offset symmetrically
                parallel_offset = (edge_idx - num_parallel // 2) * spacing
            else:
                # Even: all edges offset, no straight center line
                parallel_offset = (edge_idx - (num_parallel - 1) / 2) * spacing
            # Curvature for parallel edges
            curvature = (edge_idx - (num_parallel - 1) / 2) * 100.0

        # unit direction vector
        ux, uy = dx / length, dy / length

        # Start/end points at node borders
        sx2 = sx + ux * src.radius
        sy2 = sy + uy * src.radius
        tx2 = tx - ux * tgt.radius
        ty2 = ty - uy * tgt.radius

        p.setPen(QPen(QColor(color), width))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Draw curved edge if curvature is non-zero (user-defined or auto for parallel)
        if curvature != 0.0:
            # Quadratic bezier curve with control point at midpoint + curvature
            mid_x = (sx2 + tx2) / 2
            mid_y = (sy2 + ty2) / 2
            # Control point offset perpendicular to the edge direction
            ctrl_x = mid_x + nx_ * curvature
            ctrl_y = mid_y + ny_ * curvature

            path = QPainterPath(QPointF(sx2, sy2))
            path.quadTo(QPointF(ctrl_x, ctrl_y), QPointF(tx2, ty2))
            p.drawPath(path)

            # Store control point for arrowhead calculation
            ctrl_point = QPointF(ctrl_x, ctrl_y)
        else:
            p.drawLine(QPointF(sx2, sy2), QPointF(tx2, ty2))
            ctrl_point = None

        # arrowhead(s) for directed
        if self.graph.directed:
            if ctrl_point is not None:
                # For curved edges, calculate tangent at end point using bezier derivative
                self._draw_curved_arrowhead(p, sx2, sy2, tx2, ty2,
                                            ctrl_point.x(), ctrl_point.y(),
                                            color, width)
            else:
                self._draw_arrowhead(p, sx2, sy2, tx2, ty2, color, width)

            # For bidirectional edges, also draw arrowhead at source end
            if edge.bidirectional:
                # Draw arrowhead at source end, pointing along the curve toward source
                if ctrl_point is not None:
                    # Use tangent at START of curve (t=0) for correct arrowhead direction
                    self._draw_curved_arrowhead_at_start(p, sx2, sy2, tx2, ty2,
                                                         ctrl_point.x(), ctrl_point.y(),
                                                         color, width)
                else:
                    self._draw_arrowhead(p, tx2, ty2, sx2, sy2, color, width)

        # weight label
        if self.graph.weighted:
            # Calculate midpoint along curve (or straight line)
            if ctrl_point is not None:
                # For bezier curve, calculate exact midpoint and tangent
                t = 0.5
                one_minus_t = 1 - t
                
                # Point on curve at t=0.5
                mt_x = (one_minus_t ** 2) * sx2 + 2 * one_minus_t * t * ctrl_point.x() + (t ** 2) * tx2
                mt_y = (one_minus_t ** 2) * sy2 + 2 * one_minus_t * t * ctrl_point.y() + (t ** 2) * ty2
                
                # Tangent at midpoint (derivative of bezier)
                tan_x = 2 * one_minus_t * (ctrl_point.x() - sx2) + 2 * t * (tx2 - ctrl_point.x())
                tan_y = 2 * one_minus_t * (ctrl_point.y() - sy2) + 2 * t * (ty2 - ctrl_point.y())
                tan_len = math.hypot(tan_x, tan_y)
                
                # Normal (perpendicular to tangent)
                if tan_len > 0:
                    nmx, nmy = -tan_y / tan_len, tan_x / tan_len
                else:
                    nmx, nmy = nx_, ny_
            else:
                # Straight line - use edge normal
                mt_x = (sx2 + tx2) / 2
                mt_y = (sy2 + ty2) / 2
                nmx, nmy = nx_, ny_

            # Keep label close to edge - fixed small offset
            label_offset = 6
            mx = mt_x + nmx * label_offset
            my = mt_y + nmy * label_offset

            # Draw weight text with clean outline for visibility
            font = QFont("Consolas", 9)
            font.setBold(True)
            p.setFont(font)
            
            w_text = (f"{edge.weight:g}" if edge.weight == int(edge.weight)
                      else f"{edge.weight:.2f}")
            
            # Draw text with outline: white stroke then colored text
            p.setPen(QPen(QColor("#ffffff"), 3))
            p.drawText(QPointF(mx, my), w_text)
            p.setPen(QPen(QColor("#ff6b6b"), 1))  # Reddish color for visibility
            p.drawText(QPointF(mx, my), w_text)

    def _draw_curve_handles(self, p: QPainter) -> None:
        """Draw draggable curve handles for edges when Ctrl is held."""
        # Only show in SELECT mode with Ctrl held
        if self._mode != CanvasMode.SELECT:
            return

        # Check if Ctrl is held
        if not (QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier):
            return

        for edge in self.graph.edges:
            src = self.graph.nodes.get(edge.source)
            tgt = self.graph.nodes.get(edge.target)
            if src is None or tgt is None:
                continue

            # Skip self-loops
            if edge.source == edge.target:
                continue

            # Check if this edge is being dragged
            is_dragging = (self._dragging_edge_curvature and
                          self._dragging_edge_curvature[0] == edge.source and
                          self._dragging_edge_curvature[1] == edge.target and
                          self._dragging_edge_curvature[2] == edge.edge_id)
            
            # Always show handles when Ctrl is held (for all edges)
            # This allows users to curve any edge, not just already-curved ones

            sx, sy = src.x, src.y
            tx, ty = tgt.x, tgt.y

            # Calculate edge endpoints at node borders
            dx, dy = tx - sx, ty - sy
            length = math.hypot(dx, dy)
            if length == 0:
                continue

            ux, uy = dx / length, dy / length
            nx_, ny_ = -dy / length, dx / length  # perpendicular

            sx2 = sx + ux * src.radius
            sy2 = sy + uy * src.radius
            tx2 = tx - ux * tgt.radius
            ty2 = ty - uy * tgt.radius

            # Calculate curve control point based on current curvature
            curvature = edge.curvature
            mid_x = (sx2 + tx2) / 2
            mid_y = (sy2 + ty2) / 2
            ctrl_x = mid_x + nx_ * curvature
            ctrl_y = mid_y + ny_ * curvature

            # Draw handle at control point
            handle_pos = QPointF(ctrl_x, ctrl_y)

            # Draw handle
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.setBrush(QBrush(QColor(Colors.PRIMARY)))
            p.drawEllipse(handle_pos, self._curve_handle_radius, self._curve_handle_radius)

            # Draw inner circle for visibility
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(Colors.PRIMARY), 2))
            p.drawEllipse(handle_pos, self._curve_handle_radius - 3, self._curve_handle_radius - 3)

            # Draw line from handle to edge midpoint (visual guide)
            p.setPen(QPen(QColor(Colors.PRIMARY + "88"), 1, Qt.PenStyle.DashLine))
            p.drawLine(handle_pos, QPointF(mid_x, mid_y))

    def _draw_curved_arrowhead(self, p: QPainter, sx: float, sy: float,
                                tx: float, ty: float,
                                cx: float, cy: float,
                                color: str, width: float) -> None:
        """Draw arrowhead for curved edge using tangent at endpoint."""
        # Calculate tangent at end of quadratic bezier: derivative at t=1
        # B'(t) = 2(1-t)(P1-P0) + 2t(P2-P1)
        # At t=1: B'(1) = 2(P2-P1)
        dx = 2 * (tx - cx)
        dy = 2 * (ty - cy)
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length

        size = 12
        ax = tx - ux * size
        ay = ty - uy * size
        nx_, ny_ = -uy, ux
        p1 = QPointF(ax + nx_ * size * 0.4, ay + ny_ * size * 0.4)
        p2 = QPointF(ax - nx_ * size * 0.4, ay - ny_ * size * 0.4)
        tip = QPointF(tx, ty)

        poly = QPolygonF([tip, p1, p2])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(poly)

    def _draw_curved_arrowhead_at_start(self, p: QPainter, sx: float, sy: float,
                                          tx: float, ty: float,
                                          cx: float, cy: float,
                                          color: str, width: float) -> None:
        """Draw arrowhead for curved edge at the START point (t=0).
        
        For bidirectional edges - draws arrowhead at source end pointing INTO the source
        (as if traveling backward along the curve from target to source).
        
        Tangent at t=0: B'(0) = 2(P1 - P0), but we negate it for backward direction.
        """
        # Tangent at start points AWAY from start; negate to point INTO start
        dx = -2 * (cx - sx)
        dy = -2 * (cy - sy)
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length

        size = 12
        ax = sx - ux * size
        ay = sy - uy * size
        nx_, ny_ = -uy, ux
        p1 = QPointF(ax + nx_ * size * 0.4, ay + ny_ * size * 0.4)
        p2 = QPointF(ax - nx_ * size * 0.4, ay - ny_ * size * 0.4)
        tip = QPointF(sx, sy)

        poly = QPolygonF([tip, p1, p2])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(poly)

    def _draw_arrowhead(self, p: QPainter, sx: float, sy: float,
                        tx: float, ty: float,
                        color: str, width: float) -> None:
        dx, dy = tx - sx, ty - sy
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length
        size = 12
        ax = tx - ux * size
        ay = ty - uy * size
        nx_, ny_ = -uy, ux
        p1 = QPointF(ax + nx_ * size * 0.4, ay + ny_ * size * 0.4)
        p2 = QPointF(ax - nx_ * size * 0.4, ay - ny_ * size * 0.4)
        tip = QPointF(tx, ty)

        poly = QPolygonF([tip, p1, p2])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(poly)

    def _draw_self_loop(self, p: QPainter, node: Node, edge: Edge,
                        is_selected: bool, is_highlighted: bool) -> None:
        color = (Colors.EDGE_SELECTED if is_selected
                 else Colors.ALGO_HIGHLIGHT if is_highlighted
                 else edge.color)
        width = 3 if (is_selected or is_highlighted) else 2
        p.setPen(QPen(QColor(color), width))
        p.setBrush(Qt.BrushStyle.NoBrush)

        loop_r = node.radius * 1.2
        cx = node.x
        cy = node.y - node.radius - loop_r + 4
        
        # Draw the loop circle
        p.drawEllipse(QPointF(cx, cy), loop_r, loop_r)

        if self.graph.directed:
            # Arrowhead at the bottom of the loop where it reconnects to node
            # The loop goes from top of node, around, and back to top
            arrow_x = node.x
            arrow_y = node.y - node.radius  # Top of node where loop connects
            # Point slightly inside the loop for proper arrow placement
            base_x = arrow_x
            base_y = arrow_y - 2
            
            self._draw_arrowhead_at_top(p, base_x, base_y, arrow_x, arrow_y, color, width)

        if self.graph.weighted:
            font = QFont("sans-serif", 10)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QPen(QColor(Colors.EDGE_WEIGHT)))
            w_text = f"{edge.weight:g}"
            p.drawText(QPointF(cx - 8, cy - loop_r - 4), w_text)

    def _draw_arrowhead_at_top(self, p: QPainter, sx: float, sy: float,
                                tx: float, ty: float,
                                color: str, width: float) -> None:
        """Draw arrowhead pointing downward (for self-loop at top of node)."""
        size = 10
        # Arrow pointing down from the loop back to node
        tip_x = tx
        tip_y = ty + 3  # Slightly into the node
        base_y = ty - size + 3
        
        # Left and right points of arrow base
        left_x = tip_x - size * 0.5
        right_x = tip_x + size * 0.5
        
        poly = QPolygonF([
            QPointF(tip_x, tip_y),
            QPointF(left_x, base_y),
            QPointF(right_x, base_y)
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(poly)

    # -- mouse handling ----------------------------------------------------

    def _get_curve_handle_at(self, x: float, y: float) -> tuple[str, str, str] | None:
        """Check if (x, y) is near any edge's curve handle. Returns (src, tgt, edge_id) or None."""
        for edge in self.graph.edges:
            src = self.graph.nodes.get(edge.source)
            tgt = self.graph.nodes.get(edge.target)
            if src is None or tgt is None or edge.source == edge.target:
                continue

            sx, sy = src.x, src.y
            tx, ty = tgt.x, tgt.y

            dx, dy = tx - sx, ty - sy
            length = math.hypot(dx, dy)
            if length == 0:
                continue

            ux, uy = dx / length, dy / length
            nx_, ny_ = -dy / length, dx / length

            # Use node BORDER points (matches _draw_curve_handles exactly)
            sx2 = sx + ux * src.radius
            sy2 = sy + uy * src.radius
            tx2 = tx - ux * tgt.radius
            ty2 = ty - uy * tgt.radius

            # Calculate curve control point based on current curvature
            mid_x = (sx2 + tx2) / 2
            mid_y = (sy2 + ty2) / 2
            ctrl_x = mid_x + nx_ * edge.curvature
            ctrl_y = mid_y + ny_ * edge.curvature

            # Check distance to control point
            dist = math.hypot(x - ctrl_x, y - ctrl_y)
            if dist <= self._curve_handle_radius + 5:  # +5 for easier grabbing
                return (edge.source, edge.target, edge.edge_id)

        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = QPointF(event.position())
        scene = self._to_scene(pos)

        # middle-click → start pan
        if event.button() == Qt.MouseButton.MiddleButton:
            self._start_pan(pos)
            return

        # right-click → context menu
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(pos, scene)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        node = self.graph.node_at(scene.x(), scene.y())

        if self._mode == CanvasMode.SELECT:
            # Check for curve handle click first (Ctrl mode)
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                handle = self._get_curve_handle_at(scene.x(), scene.y())
                if handle:
                    self._dragging_edge_curvature = handle
                    return  # Start dragging curve handle
            
            if node:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    # toggle selection
                    if node.name in self._selected_nodes:
                        self._selected_nodes.discard(node.name)
                    else:
                        self._selected_nodes.add(node.name)
                else:
                    if node.name not in self._selected_nodes:
                        self._selected_nodes = {node.name}
                        self._selected_edges.clear()
                    self._dragging_node = node.name
                    self._drag_start = scene
                self.selection_changed.emit()
            else:
                edge = self.graph.edge_at(scene.x(), scene.y())
                if edge:
                    self._selected_edges = {edge.key}
                    self._selected_nodes.clear()
                    self.selection_changed.emit()
                else:
                    # Click on empty space in SELECT mode → start pan
                    self._start_pan(pos)
                    return

        elif self._mode == CanvasMode.ADD_NODE:
            self.graph.add_node(x=scene.x(), y=scene.y())
            self.update()
            return

        elif self._mode == CanvasMode.ADD_EDGE:
            # Ctrl held in ADD_EDGE mode → don't create edges, allow curve editing
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Just select/highlight, don't create
                if node:
                    self._edge_src = node.name
                    self._edge_temp_end = None
                return

            if node:
                if self._edge_src is None:
                    self._edge_src = node.name
                else:
                    shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                    src = self._edge_src
                    tgt = node.name

                    # Check if edge already exists in the direction we're creating
                    existing_edge = self.graph.get_edge(src, tgt)

                    if shift_held:
                        # Shift held - ALWAYS create new parallel edge
                        self.graph.add_edge(src, tgt)
                    elif existing_edge:
                        # Edge exists in this direction - do nothing (edge already exists)
                        pass
                    else:
                        # No edge in this direction - check if reverse exists
                        reverse_edge = self.graph.get_edge(tgt, src)
                        if reverse_edge:
                            # Reverse edge exists - make it bidirectional
                            self.graph.toggle_edge_bidirectional(tgt, src, reverse_edge.edge_id)
                        else:
                            # Create new edge
                            self.graph.add_edge(src, tgt)

                    self._edge_src = None
                    self._edge_temp_end = None
                self.update()
                return

        elif self._mode == CanvasMode.DELETE:
            if node:
                self.graph.remove_node(node.name)
                self._selected_nodes.discard(node.name)
            else:
                edge = self.graph.edge_at(scene.x(), scene.y())
                if edge:
                    self.graph.remove_edge(edge.source, edge.target)
            self.update()
            return

        self.update()

    def _start_pan(self, pos: QPointF) -> None:
        """Start panning the view."""
        self._panning = True
        self._pan_start = pos
        self._pan_start_offset = QPointF(self._pan)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pos = QPointF(event.position())
        scene = self._to_scene(pos)

        # panning
        if self._panning and self._pan_start and self._pan_start_offset:
            delta = pos - self._pan_start
            self._pan = self._pan_start_offset + delta
            self.update()
            return

        # dragging curve handle (Ctrl mode)
        if self._dragging_edge_curvature:
            edge = self.graph.get_edge_by_id(self._dragging_edge_curvature[2])
            if edge:
                # Calculate new curvature based on mouse position relative to edge
                src = self.graph.nodes.get(edge.source)
                tgt = self.graph.nodes.get(edge.target)
                if src and tgt:
                    sx, sy = src.x, src.y
                    tx, ty = tgt.x, tgt.y
                    
                    dx, dy = tx - sx, ty - sy
                    length = math.hypot(dx, dy)
                    if length > 0:
                        ux, uy = dx / length, dy / length
                        nx_, ny_ = -dy / length, dx / length  # perpendicular
                        
                        # Vector from edge midpoint to mouse
                        mid_x = (sx + tx) / 2
                        mid_y = (sy + ty) / 2
                        to_mouse_x = scene.x() - mid_x
                        to_mouse_y = scene.y() - mid_y
                        
                        # Project onto perpendicular direction
                        curvature_amount = to_mouse_x * nx_ + to_mouse_y * ny_
                        edge.curvature = curvature_amount
                        self.graph._notify(GraphEvent.EDGE_WEIGHT_CHANGED, edge=edge)
                        self.update()
                    return

        # dragging node(s)
        if self._dragging_node and self._drag_start:
            dx = scene.x() - self._drag_start.x()
            dy = scene.y() - self._drag_start.y()
            for name in self._selected_nodes:
                n = self.graph.nodes.get(name)
                if n:
                    self.graph.move_node(name, n.x + dx, n.y + dy)
            self._drag_start = scene
            self.update()
            return

        # temp edge
        if self._mode == CanvasMode.ADD_EDGE and self._edge_src:
            self._edge_temp_end = pos
            self.update()

        # hover detection
        node = self.graph.node_at(scene.x(), scene.y())
        old_hover = self._hovered_node
        self._hovered_node = node.name if node else None

        edge = self.graph.edge_at(scene.x(), scene.y()) if not node else None
        old_edge_hover = self._hovered_edge
        self._hovered_edge = edge.key if edge else None

        if self._hovered_node != old_hover or self._hovered_edge != old_edge_hover:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._pan_start = None
            self._pan_start_offset = None
            self._update_cursor()
        if event.button() == Qt.MouseButton.LeftButton:
            if self._panning:
                self._panning = False
                self._pan_start = None
                self._pan_start_offset = None
                self._update_cursor()
            if self._dragging_edge_curvature:
                # Finish curve handle drag - save undo state
                self._dragging_edge_curvature = None
                self.update()
                return
            if self._dragging_node:
                # record undo for final position
                self.graph.move_node(self._dragging_node,
                                     self.graph.nodes[self._dragging_node].x,
                                     self.graph.nodes[self._dragging_node].y,
                                     record_undo=True)
            self._dragging_node = None
            self._drag_start = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        scene = self._to_scene(QPointF(event.position()))
        node = self.graph.node_at(scene.x(), scene.y())
        if node:
            new_name, ok = QInputDialog.getText(
                self, "Rename Node", "New name:", text=node.name)
            if ok and new_name and new_name != node.name:
                self.graph.rename_node(node.name, new_name)
        else:
            edge = self.graph.edge_at(scene.x(), scene.y())
            if edge and self.graph.weighted:
                w, ok = QInputDialog.getDouble(
                    self, "Edge Weight", "Weight:", edge.weight, -1e9, 1e9, 2)
                if ok:
                    self.graph.set_edge_weight(edge.source, edge.target, w)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        pos = QPointF(event.position())
        old_scene = self._to_scene(pos)
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        new_zoom = max(0.1, min(5.0, self._zoom * factor))
        self._zoom = new_zoom
        new_scene = self._to_scene(pos)
        self._pan += QPointF(
            (new_scene.x() - old_scene.x()) * self._zoom,
            (new_scene.y() - old_scene.y()) * self._zoom,
        )
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        # Repaint when Shift or Ctrl is pressed to update HUD hint and cursor
        if event.key() in (Qt.Key.Key_Shift, Qt.Key.Key_Control):
            self.update()
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            for name in list(self._selected_nodes):
                self.graph.remove_node(name)
            for src, tgt in list(self._selected_edges):
                self.graph.remove_edge(src, tgt)
            self._selected_nodes.clear()
            self._selected_edges.clear()
            self.selection_changed.emit()
            self.update()
        elif event.key() == Qt.Key.Key_Escape:
            self._edge_src = None
            self._edge_temp_end = None
            self._dragging_edge_curvature = None
            self.clear_selection()
        elif event.key() == Qt.Key.Key_F:
            self.fit_view()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        # Repaint when Shift or Ctrl is released to update HUD hint and cursor
        if event.key() in (Qt.Key.Key_Shift, Qt.Key.Key_Control):
            self.update()
        super().keyReleaseEvent(event)

    # -- context menu ------------------------------------------------------

    def _show_context_menu(self, widget_pos: QPointF, scene: QPointF) -> None:
        menu = QMenu(self)
        node = self.graph.node_at(scene.x(), scene.y())

        if node:
            menu.addAction("Rename…", lambda: self._ctx_rename(node))
            menu.addAction("Change Color…", lambda: self._ctx_color(node))
            menu.addSeparator()
            menu.addAction("Delete Node", lambda: self.graph.remove_node(node.name))
        else:
            edge = self.graph.edge_at(scene.x(), scene.y())
            if edge:
                if self.graph.weighted:
                    menu.addAction("Set Weight…",
                                   lambda: self._ctx_edge_weight(edge))

                # Bidirectional options (only for directed graphs)
                if self.graph.directed:
                    is_bidi = self.graph.is_edge_bidirectional(edge.source, edge.target, edge.edge_id)
                    
                    if is_bidi:
                        # Edge is bidirectional - offer both unidirectional AND separate options
                        menu.addAction("Make Unidirectional",
                                       lambda: self._ctx_toggle_bidirectional(edge))
                        menu.addAction("Separate into Two Edges",
                                       lambda: self._ctx_separate_bidirectional(edge))
                    else:
                        # Edge is unidirectional - offer make bidirectional
                        menu.addAction("Make Bidirectional",
                                       lambda: self._ctx_toggle_bidirectional(edge))

                menu.addAction("Delete Edge",
                               lambda: self.graph.remove_edge(edge.source, edge.target))
            else:
                menu.addAction("Add Node Here",
                               lambda: self.graph.add_node(x=scene.x(), y=scene.y()))
                menu.addSeparator()
                menu.addAction("Fit View", self.fit_view)
                menu.addAction("Reset Zoom", self._reset_zoom)

        menu.exec(self.mapToGlobal(widget_pos.toPoint()))

    def _ctx_rename(self, node: Node) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Rename Node", "New name:", text=node.name)
        if ok and new_name:
            self.graph.rename_node(node.name, new_name)

    def _ctx_color(self, node: Node) -> None:
        color = QColorDialog.getColor(QColor(node.color), self, "Node Color")
        if color.isValid():
            self.graph.set_node_color(node.name, color.name())

    def _ctx_edge_weight(self, edge: Edge) -> None:
        w, ok = QInputDialog.getDouble(
            self, "Edge Weight", "Weight:", edge.weight, -1e9, 1e9, 2)
        if ok:
            self.graph.set_edge_weight(edge.source, edge.target, w)

    def _ctx_toggle_bidirectional(self, edge: Edge) -> None:
        """Toggle edge between unidirectional and bidirectional."""
        self.graph.toggle_edge_bidirectional(edge.source, edge.target, edge.edge_id)
        self.update()

    def _ctx_separate_bidirectional(self, edge: Edge) -> None:
        """Separate bidirectional edge into two separate parallel edges."""
        self.graph.separate_bidirectional_edge(edge.source, edge.target, edge.edge_id)
        self.update()

    def _reset_zoom(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self.update()

    def _update_cursor(self) -> None:
        cursors = {
            CanvasMode.SELECT: Qt.CursorShape.ArrowCursor,
            CanvasMode.ADD_NODE: Qt.CursorShape.CrossCursor,
            CanvasMode.ADD_EDGE: Qt.CursorShape.PointingHandCursor,
            CanvasMode.DELETE: Qt.CursorShape.ForbiddenCursor,
        }
        base_cursor = cursors.get(self._mode, Qt.CursorShape.ArrowCursor)
        
        # Show different cursor when Shift is held in ADD_EDGE mode
        if self._mode == CanvasMode.ADD_EDGE:
            shift_held = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
            if shift_held:
                base_cursor = Qt.CursorShape.CrossCursor  # Indicates parallel edge creation

        self.setCursor(base_cursor)
