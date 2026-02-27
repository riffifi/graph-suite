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
    QWidget, QMenu, QInputDialog, QColorDialog,
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

        # pan / zoom
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._panning = False
        self._pan_start: QPointF | None = None
        self._pan_start_offset: QPointF | None = None

        # algorithm highlight
        self._highlighted_nodes: set[str] = set()
        self._highlighted_edges: set[tuple[str, str]] = set()

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
        self._highlighted_nodes = nodes
        self._highlighted_edges = edges
        self.update()

    def clear_highlight(self) -> None:
        self._highlighted_nodes.clear()
        self._highlighted_edges.clear()
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
        p.drawText(10, self.height() - 10,
                   f"Mode: {self._mode.name}  |  "
                   f"Zoom: {self._zoom:.0%}  |  "
                   f"Nodes: {len(self.graph.nodes)}  "
                   f"Edges: {len(self.graph.edges)}")

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

        # self-loop
        if edge.source == edge.target:
            self._draw_self_loop(p, src, edge, is_selected, is_highlighted)
            return

        color = (Colors.EDGE_SELECTED if is_selected
                 else Colors.ALGO_HIGHLIGHT if is_highlighted
                 else Colors.PRIMARY if is_hovered
                 else edge.color)
        width = 3 if (is_selected or is_highlighted) else 2

        # Check for bidirectional edges → draw double arrowhead on single line
        has_reverse = self.graph.has_edge(edge.target, edge.source)
        is_bidirectional = has_reverse and self.graph.directed

        sx, sy = src.x, src.y
        tx, ty = tgt.x, tgt.y
        dx, dy = tx - sx, ty - sy
        length = math.hypot(dx, dy)
        if length == 0:
            return

        # unit normal for weight label offset
        nx_, ny_ = -dy / length, dx / length

        # Shorten to node borders (no offset for bidirectional - single line)
        ux, uy = dx / length, dy / length
        sx2 = sx + ux * src.radius
        sy2 = sy + uy * src.radius
        tx2 = tx - ux * tgt.radius
        ty2 = ty - uy * tgt.radius

        p.setPen(QPen(QColor(color), width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(sx2, sy2), QPointF(tx2, ty2))

        # arrowhead(s) for directed
        if self.graph.directed:
            # Always draw arrowhead at target end
            self._draw_arrowhead(p, sx2, sy2, tx2, ty2, color, width)
            # For bidirectional, also draw arrowhead at source end
            if is_bidirectional:
                self._draw_arrowhead(p, tx2, ty2, sx2, sy2, color, width)

        # weight label (only draw once for bidirectional pairs)
        if self.graph.weighted:
            # Only draw weight on the edge where source < target (alphabetically)
            if not is_bidirectional or edge.source < edge.target:
                mx = (sx2 + tx2) / 2 + nx_ * 12
                my = (sy2 + ty2) / 2 + ny_ * 12
                font = QFont("sans-serif", 10)
                font.setBold(True)
                p.setFont(font)
                p.setPen(QPen(QColor(Colors.EDGE_WEIGHT)))
                w_text = (f"{edge.weight:g}" if edge.weight == int(edge.weight)
                          else f"{edge.weight:.2f}")
                p.drawText(QPointF(mx - 10, my + 4), w_text)

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
            if node:
                if self._edge_src is None:
                    self._edge_src = node.name
                else:
                    self.graph.add_edge(self._edge_src, node.name)
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
            self.clear_selection()
        elif event.key() == Qt.Key.Key_F:
            self.fit_view()
        else:
            super().keyPressEvent(event)

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
        self.setCursor(cursors.get(self._mode, Qt.CursorShape.ArrowCursor))
