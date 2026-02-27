"""Graph DSL – lexer, parser, interpreter, and interactive console widget.

Syntax
------
# comment
set directed true|false
set weighted true|false
node <name> [at <x> <y>]
edge <src> -> <tgt> [weight <w>]     # directed
edge <src> -- <tgt> [weight <w>]     # undirected override
delete node <name>
delete edge <src> <tgt>
rename <old> <new>
color <node> <#hex>
run bfs|dfs from <src>
run dijkstra from <src> to <tgt>
run mst
run components
run topo
run info
layout circle|spring
clear
fit
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QTextEdit, QLabel, QSplitter,
)

from graphsuite.core.graph import Graph
from graphsuite.gui.style import Colors


# ═══════════════════════════════════════════════════════════════════════════
# Lexer
# ═══════════════════════════════════════════════════════════════════════════

class TT(Enum):
    """Token types."""
    KEYWORD = auto()
    IDENT = auto()
    NUMBER = auto()
    ARROW = auto()       # ->
    DASH = auto()        # --
    HASH_COLOR = auto()  # #rrggbb
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    type: TT
    value: str
    line: int = 0

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r})"


KEYWORDS = {
    "set", "node", "edge", "delete", "rename", "color",
    "run", "layout", "clear", "fit",
    "at", "weight", "from", "to",
    "directed", "undirected", "weighted", "unweighted",
    "true", "false",
    "bfs", "dfs", "dijkstra", "bellman", "mst", "components",
    "scc", "topo", "cycle", "centrality", "info",
    "circle", "spring",
}

_TOKEN_RE = re.compile(r"""
    (?P<comment>\#[^\n]*)        |
    (?P<arrow>->)                |
    (?P<dash>--)                 |
    (?P<hexcolor>\#[0-9a-fA-F]{6})\b |
    (?P<number>-?\d+(?:\.\d+)?)  |
    (?P<word>[A-Za-z_]\w*)       |
    (?P<nl>\n)                   |
    (?P<ws>[ \t\r]+)
""", re.VERBOSE)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    lineno = 1
    for m in _TOKEN_RE.finditer(source):
        kind = m.lastgroup
        val = m.group()
        if kind == "comment" or kind == "ws":
            if kind == "ws" and "\n" in val:
                lineno += val.count("\n")
            continue
        if kind == "nl":
            lineno += 1
            tokens.append(Token(TT.NEWLINE, "\\n", lineno))
            continue
        if kind == "arrow":
            tokens.append(Token(TT.ARROW, "->", lineno))
        elif kind == "dash":
            tokens.append(Token(TT.DASH, "--", lineno))
        elif kind == "hexcolor":
            tokens.append(Token(TT.HASH_COLOR, val, lineno))
        elif kind == "number":
            tokens.append(Token(TT.NUMBER, val, lineno))
        elif kind == "word":
            tt = TT.KEYWORD if val.lower() in KEYWORDS else TT.IDENT
            tokens.append(Token(tt, val, lineno))
    tokens.append(Token(TT.EOF, "", lineno))
    return tokens


# ═══════════════════════════════════════════════════════════════════════════
# Parser  →  list[Command]
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Command:
    kind: str
    args: dict[str, Any] = field(default_factory=dict)
    line: int = 0


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        t = self._tokens[self._pos]
        self._pos += 1
        return t

    def _skip_newlines(self) -> None:
        while self._peek().type == TT.NEWLINE:
            self._advance()

    def _expect_val(self, val: str) -> Token:
        t = self._advance()
        if t.value.lower() != val.lower():
            raise ParseError(
                f"Line {t.line}: expected '{val}', got '{t.value}'")
        return t

    def _read_name(self) -> str:
        """Read an identifier or keyword-used-as-name."""
        t = self._advance()
        if t.type in (TT.IDENT, TT.KEYWORD, TT.NUMBER):
            return t.value
        raise ParseError(f"Line {t.line}: expected name, got '{t.value}'")

    def parse(self) -> list[Command]:
        commands: list[Command] = []
        while self._peek().type != TT.EOF:
            self._skip_newlines()
            if self._peek().type == TT.EOF:
                break
            cmd = self._parse_command()
            if cmd:
                commands.append(cmd)
        return commands

    def _parse_command(self) -> Command | None:
        t = self._peek()
        kw = t.value.lower()

        if kw == "set":
            return self._parse_set()
        elif kw == "node":
            return self._parse_node()
        elif kw == "edge":
            return self._parse_edge()
        elif kw == "delete":
            return self._parse_delete()
        elif kw == "rename":
            return self._parse_rename()
        elif kw == "color":
            return self._parse_color()
        elif kw == "run":
            return self._parse_run()
        elif kw == "layout":
            return self._parse_layout()
        elif kw == "clear":
            self._advance()
            return Command("clear", line=t.line)
        elif kw == "fit":
            self._advance()
            return Command("fit", line=t.line)
        else:
            self._advance()  # skip unknown
            return None

    def _parse_set(self) -> Command:
        t = self._advance()  # set
        prop = self._read_name().lower()
        val = self._read_name().lower()
        return Command("set", {"prop": prop, "value": val}, t.line)

    def _parse_node(self) -> Command:
        t = self._advance()  # node
        name = self._read_name()
        x, y = None, None
        if self._peek().value.lower() == "at":
            self._advance()  # at
            x = float(self._advance().value)
            y = float(self._advance().value)
        return Command("node", {"name": name, "x": x, "y": y}, t.line)

    def _parse_edge(self) -> Command:
        t = self._advance()  # edge
        src = self._read_name()
        # -> or --
        arrow = self._advance()
        directed = arrow.type == TT.ARROW
        tgt = self._read_name()
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("edge", {
            "src": src, "tgt": tgt,
            "directed": directed, "weight": weight,
        }, t.line)

    def _parse_delete(self) -> Command:
        t = self._advance()  # delete
        what = self._read_name().lower()
        if what == "node":
            name = self._read_name()
            return Command("delete_node", {"name": name}, t.line)
        elif what == "edge":
            src = self._read_name()
            tgt = self._read_name()
            return Command("delete_edge", {"src": src, "tgt": tgt}, t.line)
        else:
            raise ParseError(f"Line {t.line}: delete what? (node/edge)")

    def _parse_rename(self) -> Command:
        t = self._advance()
        old = self._read_name()
        new = self._read_name()
        return Command("rename", {"old": old, "new": new}, t.line)

    def _parse_color(self) -> Command:
        t = self._advance()
        name = self._read_name()
        ct = self._advance()
        if ct.type != TT.HASH_COLOR:
            raise ParseError(f"Line {t.line}: expected #rrggbb color")
        return Command("color", {"name": name, "color": ct.value}, t.line)

    def _parse_run(self) -> Command:
        t = self._advance()  # run
        algo = self._read_name().lower()
        args: dict[str, Any] = {"algo": algo}
        # optional from/to
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            kw = self._peek().value.lower()
            if kw == "from":
                self._advance()
                args["source"] = self._read_name()
            elif kw == "to":
                self._advance()
                args["target"] = self._read_name()
            else:
                self._advance()  # skip
        return Command("run", args, t.line)

    def _parse_layout(self) -> Command:
        t = self._advance()
        kind = self._read_name().lower()
        return Command("layout", {"kind": kind}, t.line)


# ═══════════════════════════════════════════════════════════════════════════
# Interpreter
# ═══════════════════════════════════════════════════════════════════════════

class Interpreter:
    """Executes parsed DSL commands against a Graph model."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self._output_lines: list[str] = []
        self._highlight_nodes: set[str] = set()
        self._highlight_edges: set[tuple[str, str]] = set()

    def run(self, source: str) -> tuple[str, set[str], set[tuple[str, str]]]:
        """Parse and execute source. Returns (output_text, highlight_nodes, highlight_edges)."""
        self._output_lines = []
        self._highlight_nodes = set()
        self._highlight_edges = set()
        try:
            tokens = tokenize(source)
            commands = Parser(tokens).parse()
        except ParseError as e:
            return str(e), set(), set()

        for cmd in commands:
            try:
                self._exec(cmd)
            except Exception as e:
                self._output_lines.append(f"[Error line {cmd.line}] {e}")

        return "\n".join(self._output_lines), self._highlight_nodes, self._highlight_edges

    def _exec(self, cmd: Command) -> None:
        handler = getattr(self, f"_cmd_{cmd.kind}", None)
        if handler:
            handler(cmd.args)
        else:
            self._output_lines.append(f"Unknown command: {cmd.kind}")

    def _cmd_set(self, args: dict) -> None:
        prop = args["prop"]
        val = args["value"]
        if prop == "directed":
            self.graph.directed = val in ("true", "1", "yes")
            self._output_lines.append(f"directed = {self.graph.directed}")
        elif prop == "weighted":
            self.graph.weighted = val in ("true", "1", "yes")
            self._output_lines.append(f"weighted = {self.graph.weighted}")
        else:
            self._output_lines.append(f"Unknown property: {prop}")

    def _cmd_node(self, args: dict) -> None:
        x = args["x"] if args["x"] is not None else 200
        y = args["y"] if args["y"] is not None else 200
        node = self.graph.add_node(name=args["name"], x=x, y=y)
        self._output_lines.append(f"+ node '{node.name}' at ({node.x}, {node.y})")

    def _cmd_edge(self, args: dict) -> None:
        w = args["weight"] if args["weight"] is not None else 1.0
        edge = self.graph.add_edge(args["src"], args["tgt"], weight=w)
        if edge:
            arrow = "->" if args["directed"] else "--"
            self._output_lines.append(
                f"+ edge {edge.source} {arrow} {edge.target}"
                + (f" weight={edge.weight}" if self.graph.weighted else ""))
        else:
            self._output_lines.append(
                f"Could not add edge {args['src']} → {args['tgt']} "
                f"(nodes exist?)")

    def _cmd_delete_node(self, args: dict) -> None:
        self.graph.remove_node(args["name"])
        self._output_lines.append(f"- node '{args['name']}'")

    def _cmd_delete_edge(self, args: dict) -> None:
        self.graph.remove_edge(args["src"], args["tgt"])
        self._output_lines.append(f"- edge {args['src']} → {args['tgt']}")

    def _cmd_rename(self, args: dict) -> None:
        ok = self.graph.rename_node(args["old"], args["new"])
        if ok:
            self._output_lines.append(
                f"Renamed '{args['old']}' → '{args['new']}'")
        else:
            self._output_lines.append(f"Rename failed")

    def _cmd_color(self, args: dict) -> None:
        self.graph.set_node_color(args["name"], args["color"])
        self._output_lines.append(
            f"Color '{args['name']}' = {args['color']}")

    def _cmd_run(self, args: dict) -> None:
        import networkx as nx
        algo = args["algo"]
        G = self.graph.to_networkx()

        if algo in ("bfs", "dfs"):
            src = args.get("source")
            if not src or src not in G:
                self._output_lines.append(f"Node '{src}' not found")
                return
            if algo == "bfs":
                order = list(nx.bfs_tree(G, src).nodes())
                edges = set(nx.bfs_edges(G, src))
            else:
                order = list(nx.dfs_tree(G, src).nodes())
                edges = set(nx.dfs_edges(G, src))
            self._highlight_nodes = set(order)
            self._highlight_edges = edges
            self._output_lines.append(
                f"{algo.upper()} from '{src}': {' → '.join(order)}")

        elif algo == "dijkstra":
            src, tgt = args.get("source"), args.get("target")
            if not src or not tgt:
                self._output_lines.append("dijkstra needs 'from' and 'to'")
                return
            try:
                path = nx.dijkstra_path(G, src, tgt, weight="weight")
                cost = nx.dijkstra_path_length(G, src, tgt, weight="weight")
                self._highlight_nodes = set(path)
                self._highlight_edges = set(zip(path[:-1], path[1:]))
                self._output_lines.append(
                    f"Dijkstra {src}→{tgt}: {' → '.join(path)} (cost={cost})")
            except nx.NetworkXNoPath:
                self._output_lines.append(f"No path {src} → {tgt}")

        elif algo == "bellman":
            src, tgt = args.get("source"), args.get("target")
            if not src or not tgt:
                self._output_lines.append("bellman needs 'from' and 'to'")
                return
            try:
                path = nx.bellman_ford_path(G, src, tgt, weight="weight")
                cost = nx.bellman_ford_path_length(G, src, tgt, weight="weight")
                self._highlight_nodes = set(path)
                self._highlight_edges = set(zip(path[:-1], path[1:]))
                self._output_lines.append(
                    f"Bellman-Ford {src}→{tgt}: {' → '.join(path)} (cost={cost})")
            except nx.NetworkXNoPath:
                self._output_lines.append(f"No path {src} → {tgt}")

        elif algo == "mst":
            if self.graph.directed:
                self._output_lines.append("MST needs undirected graph")
                return
            T = nx.minimum_spanning_tree(G, weight="weight")
            self._highlight_nodes = set(T.nodes())
            self._highlight_edges = set(T.edges())
            total = sum(d.get("weight", 1) for _, _, d in T.edges(data=True))
            self._output_lines.append(f"MST total weight: {total}")

        elif algo == "components":
            if self.graph.directed:
                comps = list(nx.weakly_connected_components(G))
            else:
                comps = list(nx.connected_components(G))
            for i, c in enumerate(comps, 1):
                self._output_lines.append(f"Component {i}: {sorted(c)}")
                self._highlight_nodes |= c

        elif algo == "scc":
            comps = list(nx.strongly_connected_components(G))
            for i, c in enumerate(comps, 1):
                self._output_lines.append(f"SCC {i}: {sorted(c)}")
                self._highlight_nodes |= c

        elif algo == "topo":
            try:
                order = list(nx.topological_sort(G))
                self._output_lines.append(f"Topo: {' → '.join(order)}")
                self._highlight_nodes = set(order)
            except nx.NetworkXUnfeasible:
                self._output_lines.append("Has cycle — no topo sort")

        elif algo == "cycle":
            try:
                cycle = nx.find_cycle(G)
                self._highlight_edges = set((u, v) for u, v, *_ in cycle)
                for u, v, *_ in cycle:
                    self._highlight_nodes.add(u)
                    self._highlight_nodes.add(v)
                self._output_lines.append("Cycle found")
            except nx.NetworkXNoCycle:
                self._output_lines.append("Acyclic")

        elif algo == "info":
            self._output_lines.append(
                f"Nodes={G.number_of_nodes()} Edges={G.number_of_edges()} "
                f"Density={nx.density(G):.4f}")
        else:
            self._output_lines.append(f"Unknown algorithm: {algo}")

    def _cmd_layout(self, args: dict) -> None:
        kind = args["kind"]
        if kind == "circle":
            self.graph.layout_circle()
            self._output_lines.append("Applied circle layout")
        elif kind == "spring":
            self.graph.layout_spring()
            self._output_lines.append("Applied spring layout")
        else:
            self._output_lines.append(f"Unknown layout: {kind}")

    def _cmd_clear(self, args: dict) -> None:
        self.graph.clear()
        self._output_lines.append("Graph cleared")

    def _cmd_fit(self, args: dict) -> None:
        self._output_lines.append("Fit view (handled by GUI)")


# ═══════════════════════════════════════════════════════════════════════════
# Syntax highlighter
# ═══════════════════════════════════════════════════════════════════════════

class DSLHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []

        # keywords
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor(Colors.PRIMARY))
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        kw_pattern = r"\b(" + "|".join(KEYWORDS) + r")\b"
        self._rules.append((re.compile(kw_pattern, re.IGNORECASE), kw_fmt))

        # numbers
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor(Colors.WARNING))
        self._rules.append((re.compile(r"\b-?\d+(?:\.\d+)?\b"), num_fmt))

        # arrows
        arrow_fmt = QTextCharFormat()
        arrow_fmt.setForeground(QColor(Colors.SECONDARY))
        arrow_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"->|--"), arrow_fmt))

        # hex colours
        hex_fmt = QTextCharFormat()
        hex_fmt.setForeground(QColor(Colors.SUCCESS))
        self._rules.append((re.compile(r"#[0-9a-fA-F]{6}\b"), hex_fmt))

        # comments
        cmt_fmt = QTextCharFormat()
        cmt_fmt.setForeground(QColor(Colors.TEXT_DIM))
        cmt_fmt.setFontItalic(True)
        self._rules.append((re.compile(r"#[^\n]*"), cmt_fmt))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ═══════════════════════════════════════════════════════════════════════════
# Console widget
# ═══════════════════════════════════════════════════════════════════════════

class DSLConsole(QWidget):
    """DSL scripting console with editor and output pane."""

    highlight_request = Signal(set, set)
    clear_highlight = Signal()
    fit_request = Signal()

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._interpreter = Interpreter(graph)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # editor
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText(
            "# Graph DSL\n"
            "node A at 100 200\n"
            "node B at 300 200\n"
            "edge A -> B weight 5\n"
            "run bfs from A\n"
            "layout circle"
        )
        self._highlighter = DSLHighlighter(self._editor.document())
        splitter.addWidget(self._editor)

        # output
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            f"color: {Colors.SUCCESS}; background-color: {Colors.BG_INPUT};")
        splitter.addWidget(self._output)

        splitter.setSizes([200, 100])
        layout.addWidget(splitter)

        # buttons
        btn_row = QHBoxLayout()
        btn_run = QPushButton("Run Script")
        btn_run.setStyleSheet(
            f"background-color: {Colors.PRIMARY}; color: white; font-weight: bold;")
        btn_run.clicked.connect(self._run)

        btn_clear = QPushButton("Clear Output")
        btn_clear.clicked.connect(self._clear_output)

        btn_example = QPushButton("Load Example")
        btn_example.clicked.connect(self._load_example)

        btn_row.addWidget(btn_run)
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_example)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _run(self) -> None:
        source = self._editor.toPlainText()
        if not source.strip():
            return
        output, h_nodes, h_edges = self._interpreter.run(source)
        self._output.setPlainText(output)
        if h_nodes or h_edges:
            self.highlight_request.emit(h_nodes, h_edges)
        # check for fit command
        if "fit" in source.lower().split():
            self.fit_request.emit()

    def _clear_output(self) -> None:
        self._output.clear()
        self.clear_highlight.emit()

    def _load_example(self) -> None:
        example = """\
# Example: Weighted directed graph
set directed true
set weighted true

node A at 150 150
node B at 350 100
node C at 350 300
node D at 550 200
node E at 150 350

edge A -> B weight 4
edge A -> E weight 1
edge B -> C weight 2
edge C -> D weight 3
edge E -> C weight 5
edge B -> D weight 7

layout spring
"""
        self._editor.setPlainText(example)
