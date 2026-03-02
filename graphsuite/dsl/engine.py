"""Graph DSL – lexer, parser, interpreter, and interactive console widget.

Syntax
------
# comment
set directed true|false
set weighted true|false
cmdoutput true|false               # enable/disable command output

# Variables and Expressions
let <name> = <expr>                # variable assignment
let <name> = <expr> op <expr>      # math: +, -, *, /, %, ^
print <expr>                       # print value or message

# Nodes
node <name> [at <x> <y>]
nodes <name1> <name2> ... <nameN> [at <x> <y>]
grid <rows> <cols> [spacing <s>] [start <name>]
circle <n> [radius <r>] [start <name>]

# Iterators and Loops
iter <var> in <start>..<end> [by <step>]: <command>
iter <var> in [list]: <command>
for <var> in <start>..<end>: ...

# Edges
edge <src> -> <tgt> [weight <w>]     # directed edge
edge <src> -- <tgt> [weight <w>]     # undirected edge
edge <src> <-> <tgt> [weight <w>]    # bidirectional (single edge, two arrowheads)
edge <src> <=> <tgt> [weight <w>]    # dual edge (two separate edges)
edges <n1> <n2> ... <nN> -> <tgt>    # multiple edges to same target
connect <n1> <n2> ... <nN>           # connect all pairs (complete graph)
path <n1> <n2> ... <nN> [weight <w>] # chain of edges
cycle <n1> <n2> ... <nN> [weight <w>] # cycle (path + edge back to start)

# Advanced Patterns
path iter <var> in <start>..<end> [weight <w>]  # path through numbered nodes
cycle iter <var> in <start>..<end> [weight <w>] # cycle through numbered nodes
star <center> <n1> <n2> ...                     # star graph (center connected to all)
wheel <center> <n1> <n2> ...                    # wheel graph (cycle + center connected to all)
ladder <prefix> <n> [weight <w>]                # ladder graph with n rungs

# Edge modifications
toggle <src> <tgt>                   # toggle edge bidirectional
separate <src> <tgt>                 # separate bidirectional into two edges
curve <src> <tgt> <amount>           # set edge curvature

# Node modifications
delete node <name>
delete edge <src> <tgt>
rename <old> <new>
color <node> <#hex>

# Algorithms
run bfs|dfs from <src>
run dijkstra from <src> to <tgt>
run mst
run components
run topo
run info

# Layout
layout circle|spring

# Utility
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
    BIDIARROW = auto()   # <->
    DUALARROW = auto()   # <=>
    RANGE = auto()       # ..
    IN = auto()          # in
    COLON = auto()       # :
    EQUALS = auto()      # =
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()         # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    CARET = auto()       # ^
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
    "set", "node", "nodes", "edge", "edges", "delete", "rename", "color",
    "run", "layout", "clear", "fit", "print", "let", "cmdoutput",
    "at", "weight", "from", "to", "radius", "start", "spacing",
    "directed", "undirected", "weighted", "unweighted",
    "true", "false",
    "bfs", "dfs", "dijkstra", "bellman", "mst", "components",
    "scc", "topo", "cycle", "centrality", "info", "connect", "path",
    "circle", "spring", "grid", "star", "wheel", "ladder",
    "toggle", "separate", "curve",
    "bidirectional", "unidirectional",
    "iter", "for", "in", "by",
}

_TOKEN_RE = re.compile(r"""
    (?P<comment>\#[^\n]*)        |
    (?P<dualarrow><=>)           |
    (?P<bidiarrow><->)           |
    (?P<arrow>->)                |
    (?P<dash>--)                 |
    (?P<range>\.\.)              |
    (?P<operator>[+\-*/%^])      |
    (?P<equals>=)                |
    (?P<colon>:)                 |
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
        if kind == "dualarrow":
            tokens.append(Token(TT.DUALARROW, "<=>", lineno))
        elif kind == "bidiarrow":
            tokens.append(Token(TT.BIDIARROW, "<->", lineno))
        elif kind == "arrow":
            tokens.append(Token(TT.ARROW, "->", lineno))
        elif kind == "dash":
            tokens.append(Token(TT.DASH, "--", lineno))
        elif kind == "range":
            tokens.append(Token(TT.RANGE, "..", lineno))
        elif kind == "operator":
            op_map = {"+": TT.PLUS, "-": TT.MINUS, "*": TT.STAR, "/": TT.SLASH, "%": TT.PERCENT, "^": TT.CARET}
            tokens.append(Token(op_map[val], val, lineno))
        elif kind == "equals":
            tokens.append(Token(TT.EQUALS, "=", lineno))
        elif kind == "colon":
            tokens.append(Token(TT.COLON, ":", lineno))
        elif kind == "word":
            if val.lower() == "in":
                tokens.append(Token(TT.IN, "in", lineno))
            else:
                tt = TT.KEYWORD if val.lower() in KEYWORDS else TT.IDENT
                tokens.append(Token(tt, val, lineno))
        elif kind == "hexcolor":
            tokens.append(Token(TT.HASH_COLOR, val, lineno))
        elif kind == "number":
            tokens.append(Token(TT.NUMBER, val, lineno))
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
        elif kw == "nodes":
            return self._parse_nodes()
        elif kw == "edge":
            return self._parse_edge()
        elif kw == "edges":
            return self._parse_edges()
        elif kw == "connect":
            return self._parse_connect()
        elif kw == "path":
            # Check for "path iter" syntax
            self._advance()
            if self._peek().value.lower() == "iter":
                return self._parse_path_iter()
            # Not "path iter", rewind and parse as regular path
            self._pos -= 1
            return self._parse_path()
        elif kw == "cycle":
            # Check for "cycle iter" syntax
            self._advance()
            if self._peek().value.lower() == "iter":
                return self._parse_cycle_iter()
            # Not "cycle iter", rewind and parse as regular cycle
            self._pos -= 1
            return self._parse_cycle()
        elif kw == "star":
            return self._parse_star()
        elif kw == "wheel":
            return self._parse_wheel()
        elif kw == "ladder":
            return self._parse_ladder()
        elif kw == "iter" or kw == "for":
            return self._parse_iter()
        elif kw == "grid":
            return self._parse_grid()
        elif kw == "circle":
            return self._parse_circle_nodes()
        elif kw == "let":
            return self._parse_let()
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
        elif kw == "toggle":
            return self._parse_toggle()
        elif kw == "separate":
            return self._parse_separate()
        elif kw == "curve":
            return self._parse_curve()
        elif kw == "print":
            return self._parse_print()
        elif kw == "cmdoutput":
            return self._parse_cmdoutput()
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

    def _parse_nodes(self) -> Command:
        """Parse 'nodes <n1> <n2> ... <nN> [at <x> <y>]' command."""
        t = self._advance()  # nodes
        names = []
        # Read node names until we hit 'at' or newline
        while self._peek().value.lower() != "at" and self._peek().type not in (TT.NEWLINE, TT.EOF):
            names.append(self._read_name())
        x, y = 200, 200  # default position
        if self._peek().value.lower() == "at":
            self._advance()
            x = float(self._advance().value)
            y = float(self._advance().value)
        return Command("nodes", {"names": names, "x": x, "y": y}, t.line)

    def _parse_edges(self) -> Command:
        """Parse 'edges <n1> <n2> ... -> <tgt> [weight <w>]' command."""
        t = self._advance()  # edges
        sources = []
        # Read source node names until arrow
        while self._peek().type not in (TT.ARROW, TT.DASH, TT.BIDIARROW, TT.NEWLINE, TT.EOF):
            sources.append(self._read_name())
        # Read arrow type
        arrow = self._advance()
        directed = arrow.type in (TT.ARROW, TT.BIDIARROW)
        bidirectional = arrow.type == TT.BIDIARROW
        # Read target
        target = self._read_name()
        # Optional weight
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("edges", {"sources": sources, "target": target, 
                                  "directed": directed, "bidirectional": bidirectional,
                                  "weight": weight}, t.line)

    def _parse_connect(self) -> Command:
        """Parse 'connect <n1> <n2> ... <nN> [weight <w>]' command (complete graph)."""
        t = self._advance()  # connect
        names = []
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            if self._peek().value.lower() == "weight":
                break
            names.append(self._read_name())
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("connect", {"names": names, "weight": weight}, t.line)

    def _parse_path(self) -> Command:
        """Parse 'path <n1> <n2> ... <nN> [weight <w>]' command."""
        t = self._advance()  # path
        names = []
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            if self._peek().value.lower() == "weight":
                break
            names.append(self._read_name())
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("path", {"names": names, "weight": weight}, t.line)

    def _parse_cycle(self) -> Command:
        """Parse 'cycle <n1> <n2> ... <nN> [weight <w>]' command."""
        t = self._advance()  # cycle
        names = []
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            if self._peek().value.lower() == "weight":
                break
            names.append(self._read_name())
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("cycle", {"names": names, "weight": weight}, t.line)

    def _parse_grid(self) -> Command:
        """Parse 'grid <rows> <cols> [spacing <s>] [start <name>]' command."""
        t = self._advance()  # grid
        rows = int(self._advance().value)
        cols = int(self._advance().value)
        spacing = 80  # default
        start_name = "v1"  # default start name
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            kw = self._peek().value.lower()
            if kw == "spacing":
                self._advance()
                spacing = float(self._advance().value)
            elif kw == "start":
                self._advance()
                start_name = self._read_name()
            else:
                self._advance()
        return Command("grid", {"rows": rows, "cols": cols, "spacing": spacing, "start": start_name}, t.line)

    def _parse_circle_nodes(self) -> Command:
        """Parse 'circle <n> [radius <r>] [start <name>]' command."""
        t = self._advance()  # circle
        n = int(self._advance().value)
        radius = 150  # default
        start_name = "v1"  # default
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            kw = self._peek().value.lower()
            if kw == "radius":
                self._advance()
                radius = float(self._advance().value)
            elif kw == "start":
                self._advance()
                start_name = self._read_name()
            else:
                self._advance()
        return Command("circle_nodes", {"n": n, "radius": radius, "start": start_name}, t.line)

    def _parse_let(self) -> Command:
        """Parse 'let <name> = <value>' command."""
        t = self._advance()  # let
        name = self._read_name()
        # Expect '='
        if self._peek().value != "=":
            raise ParseError(f"Line {t.line}: expected '=' after variable name")
        self._advance()  # consume '='
        # Read value (number or identifier)
        value_token = self._advance()
        value = value_token.value
        # Check for operator
        if self._peek().value in ("+", "-", "*", "/"):
            op = self._advance().value
            value2_token = self._advance()
            value2 = value2_token.value
            return Command("let", {"name": name, "value": value, "op": op, "value2": value2}, t.line)
        return Command("let", {"name": name, "value": value}, t.line)

    def _parse_cmdoutput(self) -> Command:
        """Parse 'cmdoutput true|false' command."""
        t = self._advance()  # cmdoutput
        val = self._read_name().lower()
        return Command("cmdoutput", {"value": val in ("true", "1", "yes")}, t.line)

    def _parse_edge(self) -> Command:
        t = self._advance()  # edge
        src = self._read_name()
        # -> or -- or <-> or <=>
        arrow = self._advance()
        if arrow.type == TT.ARROW:
            directed = True
            bidirectional = False
            dual_edge = False
        elif arrow.type == TT.DASH:
            directed = False
            bidirectional = False
            dual_edge = False
        elif arrow.type == TT.BIDIARROW:
            directed = True
            bidirectional = True
            dual_edge = False
        elif arrow.type == TT.DUALARROW:
            directed = True
            bidirectional = False
            dual_edge = True  # Two separate edges
        else:
            directed = True
            bidirectional = False
            dual_edge = False
        tgt = self._read_name()
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("edge", {
            "src": src, "tgt": tgt,
            "directed": directed,
            "bidirectional": bidirectional,
            "dual_edge": dual_edge,
            "weight": weight,
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

    def _parse_toggle(self) -> Command:
        """Parse 'toggle [edge] <src> <tgt>' command."""
        t = self._advance()  # toggle
        next_word = self._peek().value.lower()
        
        # Optional 'edge' keyword
        if next_word == "edge":
            self._advance()  # consume 'edge'
        
        src = self._read_name()
        tgt = self._read_name()
        return Command("toggle_edge", {"src": src, "tgt": tgt}, t.line)

    def _parse_separate(self) -> Command:
        """Parse 'separate <src> <tgt>' command."""
        t = self._advance()  # separate
        src = self._read_name()
        tgt = self._read_name()
        return Command("separate", {"src": src, "tgt": tgt}, t.line)

    def _parse_curve(self) -> Command:
        """Parse 'curve <src> <tgt> <amount>' command."""
        t = self._advance()  # curve
        src = self._read_name()
        tgt = self._read_name()
        amount = float(self._advance().value)
        return Command("curve", {"src": src, "tgt": tgt, "amount": amount}, t.line)

    def _parse_print(self) -> Command:
        """Parse 'print <message>' command."""
        t = self._advance()  # print
        # Read rest of line as message
        message_parts = []
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            message_parts.append(self._advance().value)
        return Command("print", {"message": " ".join(message_parts)}, t.line)

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

    def _parse_iter(self) -> Command:
        """Parse 'iter <var> in <start>..<end> [by <step>]: <command>' command."""
        t = self._advance()  # iter or for
        var_name = self._read_name()
        
        # Expect 'in'
        if self._peek().value.lower() != "in":
            raise ParseError(f"Line {t.line}: expected 'in' after variable")
        self._advance()  # consume 'in'
        
        # Read range start
        start = float(self._advance().value)
        
        # Expect '..'
        if self._peek().type != TT.RANGE:
            raise ParseError(f"Line {t.line}: expected '..' in range")
        self._advance()  # consume '..'
        
        # Read range end
        end = float(self._advance().value)
        
        # Optional 'by' step
        step = 1.0
        if self._peek().value.lower() == "by":
            self._advance()  # consume 'by'
            step = float(self._advance().value)
        
        # Expect ':'
        if self._peek().type != TT.COLON:
            raise ParseError(f"Line {t.line}: expected ':' after range")
        self._advance()  # consume ':'
        
        # Read command after colon (just the keyword and args)
        cmd_kw = self._peek().value.lower()
        if cmd_kw == "node":
            self._advance()
            name_pattern = self._read_name()
            x, y = 200.0, 200.0
            if self._peek().value.lower() == "at":
                self._advance()
                x = float(self._advance().value)
                y = float(self._advance().value)
            return Command("iter_node", {"var": var_name, "start": start, "end": end, "step": step,
                                          "name_pattern": name_pattern, "x": x, "y": y}, t.line)
        elif cmd_kw == "edge":
            self._advance()
            # Read edge pattern with variable substitution
            src_pattern = self._read_name()
            arrow = self._advance()
            tgt_pattern = self._read_name()
            weight = None
            if self._peek().value.lower() == "weight":
                self._advance()
                weight = float(self._advance().value)
            return Command("iter_edge", {"var": var_name, "start": start, "end": end, "step": step,
                                          "src_pattern": src_pattern, "tgt_pattern": tgt_pattern,
                                          "arrow": arrow.value, "weight": weight}, t.line)
        else:
            raise ParseError(f"Line {t.line}: unsupported command in iter: {cmd_kw}")

    def _parse_path_iter(self) -> Command:
        """Parse 'path iter <var> in <start>..<end> [weight <w>]' command."""
        t = self._advance()  # iter
        
        var_name = self._read_name()
        
        if self._peek().value.lower() != "in":
            raise ParseError(f"Line {t.line}: expected 'in'")
        self._advance()
        
        start = int(self._advance().value)
        
        if self._peek().type != TT.RANGE:
            raise ParseError(f"Line {t.line}: expected '..'")
        self._advance()
        
        end = int(self._advance().value)
        
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        
        return Command("path_iter", {"var": var_name, "start": start, "end": end, "weight": weight}, t.line)

    def _parse_cycle_iter(self) -> Command:
        """Parse 'cycle iter <var> in <start>..<end> [weight <w>]' command."""
        t = self._advance()  # iter
        
        var_name = self._read_name()
        
        if self._peek().value.lower() != "in":
            raise ParseError(f"Line {t.line}: expected 'in'")
        self._advance()
        
        start = int(self._advance().value)
        
        if self._peek().type != TT.RANGE:
            raise ParseError(f"Line {t.line}: expected '..'")
        self._advance()
        
        end = int(self._advance().value)
        
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        
        return Command("cycle_iter", {"var": var_name, "start": start, "end": end, "weight": weight}, t.line)

    def _parse_star(self) -> Command:
        """Parse 'star <center> <n1> <n2> ...' command."""
        t = self._advance()  # star
        center = self._read_name()
        leaves = []
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            if self._peek().value.lower() == "weight":
                break
            leaves.append(self._read_name())
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("star", {"center": center, "leaves": leaves, "weight": weight}, t.line)

    def _parse_wheel(self) -> Command:
        """Parse 'wheel <center> <n1> <n2> ...' command."""
        t = self._advance()  # wheel
        center = self._read_name()
        rim_nodes = []
        while self._peek().type not in (TT.NEWLINE, TT.EOF):
            if self._peek().value.lower() == "weight":
                break
            rim_nodes.append(self._read_name())
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("wheel", {"center": center, "rim_nodes": rim_nodes, "weight": weight}, t.line)

    def _parse_ladder(self) -> Command:
        """Parse 'ladder <prefix> <n> [weight <w>]' command."""
        t = self._advance()  # ladder
        prefix = self._read_name()
        n = int(self._advance().value)
        weight = None
        if self._peek().value.lower() == "weight":
            self._advance()
            weight = float(self._advance().value)
        return Command("ladder", {"prefix": prefix, "n": n, "weight": weight}, t.line)


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
        self._cmdoutput_enabled: bool = True  # Command output enabled by default

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
            if self._cmdoutput_enabled:
                self._output_lines.append(f"directed = {self.graph.directed}")
        elif prop == "weighted":
            self.graph.weighted = val in ("true", "1", "yes")
            if self._cmdoutput_enabled:
                self._output_lines.append(f"weighted = {self.graph.weighted}")
        else:
            self._output_lines.append(f"Unknown property: {prop}")

    def _cmd_cmdoutput(self, args: dict) -> None:
        """Enable/disable command output."""
        self._cmdoutput_enabled = args["value"]
        # Always confirm cmdoutput changes
        self._output_lines.append(f"command output = {'enabled' if self._cmdoutput_enabled else 'disabled'}")

    def _cmd_node(self, args: dict) -> None:
        x = args["x"] if args["x"] is not None else 200
        y = args["y"] if args["y"] is not None else 200
        node = self.graph.add_node(name=args["name"], x=x, y=y)
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ node '{node.name}' at ({node.x}, {node.y})")

    def _cmd_nodes(self, args: dict) -> None:
        """Create multiple nodes at once."""
        names = args["names"]
        x = args["x"] if args["x"] is not None else 200
        y = args["y"] if args["y"] is not None else 200
        spacing = 60
        for i, name in enumerate(names):
            node = self.graph.add_node(name=name, x=x + i * spacing, y=y)
            if self._cmdoutput_enabled:
                self._output_lines.append(f"+ node '{node.name}' at ({node.x}, {node.y})")

    def _cmd_edges(self, args: dict) -> None:
        """Create multiple edges to same target."""
        sources = args["sources"]
        target = args["target"]
        w = args["weight"] if args["weight"] is not None else 1.0
        bidirectional = args.get("bidirectional", False)
        for src in sources:
            edge = self.graph.add_edge(src, target, weight=w)
            if edge and bidirectional:
                edge.bidirectional = True
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ {len(sources)} edge(s) to '{target}'")

    def _cmd_connect(self, args: dict) -> None:
        """Connect all pairs of nodes (complete graph), auto-creating nodes."""
        import math
        names = args["names"]
        w = args["weight"] if args["weight"] is not None else 1.0
        n = len(names)
        # Auto-create nodes in a circle if they don't exist
        cx, cy, radius = 400, 300, 150
        for i, name in enumerate(names):
            if name not in self.graph.nodes:
                angle = 2 * math.pi * i / n - math.pi / 2
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                self.graph.add_node(name=name, x=x, y=y)
        count = 0
        for i, n1 in enumerate(names):
            for n2 in names[i+1:]:
                edge = self.graph.add_edge(n1, n2, weight=w)
                if edge:
                    count += 1
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ connected {len(names)} nodes with {count} edges")

    def _cmd_path(self, args: dict) -> None:
        """Create a chain of edges, auto-creating nodes if needed."""
        names = args["names"]
        w = args["weight"] if args["weight"] is not None else 1.0
        # Auto-create nodes if they don't exist
        for i, name in enumerate(names):
            if name not in self.graph.nodes:
                self.graph.add_node(name=name, x=200 + i * 60, y=200)
        for i in range(len(names) - 1):
            self.graph.add_edge(names[i], names[i+1], weight=w)
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ path: {' -> '.join(names)}")

    def _cmd_cycle(self, args: dict) -> None:
        """Create a cycle (path + edge back to start), auto-creating nodes."""
        import math
        names = args["names"]
        w = args["weight"] if args["weight"] is not None else 1.0
        n = len(names)
        # Auto-create nodes in a circle if they don't exist
        cx, cy, radius = 400, 300, 150
        for i, name in enumerate(names):
            if name not in self.graph.nodes:
                angle = 2 * math.pi * i / n - math.pi / 2
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                self.graph.add_node(name=name, x=x, y=y)
        for i in range(n):
            next_i = (i + 1) % n
            self.graph.add_edge(names[i], names[next_i], weight=w)
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ cycle: {' -> '.join(names)} -> {names[0]}")

    def _cmd_grid(self, args: dict) -> None:
        """Create a grid of nodes."""
        rows = args["rows"]
        cols = args["cols"]
        spacing = args["spacing"]
        start = args["start"]
        
        # Parse start name to get base and number
        base_name = start.rstrip('0123456789')
        start_num = int(''.join(c for c in start if c.isdigit()) or '1')
        
        node_count = 0
        for r in range(rows):
            for c in range(cols):
                num = start_num + node_count
                name = f"{base_name}{num}"
                x = 100 + c * spacing
                y = 100 + r * spacing
                self.graph.add_node(name=name, x=x, y=y)
                node_count += 1
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ created {rows}x{cols} grid starting from '{start}'")

    def _cmd_circle_nodes(self, args: dict) -> None:
        """Create nodes in a circle."""
        import math
        n = args["n"]
        radius = args["radius"]
        start = args["start"]
        
        # Parse start name
        base_name = start.rstrip('0123456789')
        start_num = int(''.join(c for c in start if c.isdigit()) or '1')
        
        cx, cy = 400, 300  # center
        for i in range(n):
            num = start_num + i
            name = f"{base_name}{num}"
            angle = 2 * math.pi * i / n - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            self.graph.add_node(name=name, x=x, y=y)
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ created {n} nodes in circle")

    def _cmd_let(self, args: dict) -> None:
        """Variable assignment (stored in output for reference, not persisted)."""
        name = args["name"]
        value = args["value"]
        if "op" in args:
            op = args["op"]
            value2 = args["value2"]
            try:
                v1 = float(value)
                v2 = float(value2)
                if op == "+":
                    result = v1 + v2
                elif op == "-":
                    result = v1 - v2
                elif op == "*":
                    result = v1 * v2
                elif op == "/":
                    result = v1 / v2 if v2 != 0 else 0
                else:
                    result = 0
                if self._cmdoutput_enabled:
                    self._output_lines.append(f"let {name} = {result}")
            except:
                if self._cmdoutput_enabled:
                    self._output_lines.append(f"let {name} = {value} {op} {value2}")
        else:
            if self._cmdoutput_enabled:
                self._output_lines.append(f"let {name} = {value}")

    def _cmd_edge(self, args: dict) -> None:
        w = args["weight"] if args["weight"] is not None else 1.0
        src, tgt = args["src"], args["tgt"]
        bidirectional = args.get("bidirectional", False)
        dual_edge = args.get("dual_edge", False)

        if dual_edge:
            # Create two separate edges in opposite directions
            edge1 = self.graph.add_edge(src, tgt, weight=w)
            edge2 = self.graph.add_edge(tgt, src, weight=w)
            if self._cmdoutput_enabled:
                arrow = "<=>"
                self._output_lines.append(
                    f"+ two edges {src} {arrow} {tgt}"
                    + (f" weight={w}" if self.graph.weighted else ""))
        elif bidirectional:
            # Add single edge with bidirectional property
            edge = self.graph.add_edge(src, tgt, weight=w)
            if edge:
                edge.bidirectional = True
                if self._cmdoutput_enabled:
                    arrow = "<->"
                    self._output_lines.append(
                        f"+ bidirectional edge {src} {arrow} {tgt}"
                        + (f" weight={w}" if self.graph.weighted else ""))
        else:
            # Add single directed edge
            edge = self.graph.add_edge(src, tgt, weight=w)
            if edge and self._cmdoutput_enabled:
                arrow = "->" if args["directed"] else "--"
                self._output_lines.append(
                    f"+ edge {edge.source} {arrow} {edge.target}"
                    + (f" weight={edge.weight}" if self.graph.weighted else ""))

    def _cmd_delete_node(self, args: dict) -> None:
        self.graph.remove_node(args["name"])
        if self._cmdoutput_enabled:
            self._output_lines.append(f"- node '{args['name']}'")

    def _cmd_delete_edge(self, args: dict) -> None:
        self.graph.remove_edge(args["src"], args["tgt"])
        if self._cmdoutput_enabled:
            self._output_lines.append(f"- edge {args['src']} → {args['tgt']}")

    def _cmd_toggle_edge(self, args: dict) -> None:
        src, tgt = args["src"], args["tgt"]
        now_bidi = self.graph.toggle_edge_bidirectional(src, tgt)
        if self._cmdoutput_enabled:
            if now_bidi:
                self._output_lines.append(f"Made edge {src} ↔ {tgt} bidirectional")
            else:
                self._output_lines.append(f"Made edge {src} → {tgt} unidirectional")

    def _cmd_separate(self, args: dict) -> None:
        src, tgt = args["src"], args["tgt"]
        success = self.graph.separate_bidirectional_edge(src, tgt)
        if self._cmdoutput_enabled:
            if success:
                self._output_lines.append(f"Separated {src} ↔ {tgt} into two edges")
            else:
                self._output_lines.append(f"Edge {src} → {tgt} is not bidirectional")

    def _cmd_curve(self, args: dict) -> None:
        src, tgt = args["src"], args["tgt"]
        amount = args["amount"]
        self.graph.set_edge_curvature(src, tgt, amount)
        if self._cmdoutput_enabled:
            self._output_lines.append(f"Curved edge {src} → {tgt} with curvature={amount}")

    def _cmd_print(self, args: dict) -> None:
        # Print always outputs regardless of cmdoutput setting
        message = args["message"]
        self._output_lines.append(message)

    def _cmd_rename(self, args: dict) -> None:
        ok = self.graph.rename_node(args["old"], args["new"])
        if self._cmdoutput_enabled:
            if ok:
                self._output_lines.append(
                    f"Renamed '{args['old']}' → '{args['new']}'")
            else:
                self._output_lines.append(f"Rename failed")

    def _cmd_color(self, args: dict) -> None:
        self.graph.set_node_color(args["name"], args["color"])
        if self._cmdoutput_enabled:
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

    def _cmd_iter_node(self, args: dict) -> None:
        """Create nodes in a loop with variable substitution."""
        var = args["var"]
        start = int(args["start"])
        end = int(args["end"])
        step = int(args["step"])
        name_pattern = args["name_pattern"]
        x, y = args["x"], args["y"]
        
        count = 0
        for i in range(start, end, step):
            # Substitute variable in name pattern (e.g., "v{i}" -> "v1")
            name = name_pattern.replace("{" + var + "}", str(i)).replace(var, str(i))
            self.graph.add_node(name=name, x=x + count * 60, y=y)
            count += 1
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ created {count} nodes from {start} to {end-step}")

    def _cmd_iter_edge(self, args: dict) -> None:
        """Create edges in a loop with variable substitution."""
        var = args["var"]
        start = int(args["start"])
        end = int(args["end"])
        step = int(args["step"])
        src_pattern = args["src_pattern"]
        tgt_pattern = args["tgt_pattern"]
        arrow = args["arrow"]
        weight = args["weight"]
        
        count = 0
        for i in range(start, end, step):
            src = src_pattern.replace("{" + var + "}", str(i)).replace(var, str(i))
            tgt = tgt_pattern.replace("{" + var + "}", str(i)).replace(var, str(i))
            self.graph.add_edge(src, tgt, weight=weight if weight else 1.0)
            count += 1
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ created {count} edges from {start} to {end-step}")

    def _cmd_path_iter(self, args: dict) -> None:
        """Create a path through numbered nodes (auto-creates nodes)."""
        var = args["var"]
        start = args["start"]
        end = args["end"]
        weight = args["weight"] if args["weight"] else 1.0
        
        # Auto-create nodes in a line
        nodes = []
        for i in range(start, end + 1):
            name = f"{var}{i}"
            if name not in self.graph.nodes:
                self.graph.add_node(name=name, x=200 + (i-start) * 80, y=200)
            nodes.append(name)
        
        for i in range(len(nodes) - 1):
            self.graph.add_edge(nodes[i], nodes[i+1], weight=weight)
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ path: {' -> '.join(nodes)}")

    def _cmd_cycle_iter(self, args: dict) -> None:
        """Create a cycle through numbered nodes (auto-creates nodes)."""
        var = args["var"]
        start = args["start"]
        end = args["end"]
        weight = args["weight"] if args["weight"] else 1.0
        
        # Auto-create nodes in a circle
        import math
        nodes = []
        n = end - start + 1
        for i in range(start, end + 1):
            name = f"{var}{i}"
            if name not in self.graph.nodes:
                angle = 2 * math.pi * (i - start) / n - math.pi / 2
                x = 400 + 150 * math.cos(angle)
                y = 300 + 150 * math.sin(angle)
                self.graph.add_node(name=name, x=x, y=y)
            nodes.append(name)
        
        for i in range(len(nodes)):
            next_i = (i + 1) % len(nodes)
            self.graph.add_edge(nodes[i], nodes[next_i], weight=weight)
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ cycle: {' -> '.join(nodes)} -> {nodes[0]}")

    def _cmd_star(self, args: dict) -> None:
        """Create a star graph (auto-creates leaf nodes if needed)."""
        center = args["center"]
        leaves = args["leaves"]
        weight = args["weight"] if args["weight"] else 1.0
        
        # Ensure center exists
        if center not in self.graph.nodes:
            self.graph.add_node(name=center, x=400, y=300)
        
        # Create leaves and edges
        import math
        for i, leaf in enumerate(leaves):
            if leaf not in self.graph.nodes:
                angle = 2 * math.pi * i / len(leaves) - math.pi / 2
                x = 400 + 150 * math.cos(angle)
                y = 300 + 150 * math.sin(angle)
                self.graph.add_node(name=leaf, x=x, y=y)
            self.graph.add_edge(center, leaf, weight=weight)
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ star graph with center '{center}' and {len(leaves)} leaves")

    def _cmd_wheel(self, args: dict) -> None:
        """Create a wheel graph (auto-creates nodes if needed)."""
        center = args["center"]
        rim_nodes = args["rim_nodes"]
        weight = args["weight"] if args["weight"] else 1.0
        
        import math
        
        # Ensure center exists
        if center not in self.graph.nodes:
            self.graph.add_node(name=center, x=400, y=300)
        
        # Create rim nodes in circle
        n = len(rim_nodes)
        for i, rim in enumerate(rim_nodes):
            if rim not in self.graph.nodes:
                angle = 2 * math.pi * i / n - math.pi / 2
                x = 400 + 150 * math.cos(angle)
                y = 300 + 150 * math.sin(angle)
                self.graph.add_node(name=rim, x=x, y=y)
        
        # Create rim cycle
        for i in range(len(rim_nodes)):
            next_i = (i + 1) % len(rim_nodes)
            self.graph.add_edge(rim_nodes[i], rim_nodes[next_i], weight=weight)
        
        # Connect center to all rim nodes
        for rim in rim_nodes:
            self.graph.add_edge(center, rim, weight=weight)
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ wheel graph with center '{center}' and {len(rim_nodes)} rim nodes")

    def _cmd_ladder(self, args: dict) -> None:
        """Create a ladder graph with n rungs."""
        prefix = args["prefix"]
        n = args["n"]
        weight = args["weight"] if args["weight"] else 1.0
        
        # Create nodes: prefix1a, prefix1b, prefix2a, prefix2b, ...
        nodes_a = [f"{prefix}{i}a" for i in range(1, n + 1)]
        nodes_b = [f"{prefix}{i}b" for i in range(1, n + 1)]
        
        for name in nodes_a + nodes_b:
            self.graph.add_node(name=name)
        
        # Create rails
        for i in range(len(nodes_a) - 1):
            self.graph.add_edge(nodes_a[i], nodes_a[i+1], weight=weight)
            self.graph.add_edge(nodes_b[i], nodes_b[i+1], weight=weight)
        
        # Create rungs
        for i in range(len(nodes_a)):
            self.graph.add_edge(nodes_a[i], nodes_b[i], weight=weight)
        
        if self._cmdoutput_enabled:
            self._output_lines.append(f"+ ladder graph with {n} rungs")


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
        self._rules.append((re.compile(r"<=>|<->|->|--"), arrow_fmt))

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

    # Command syntax hints for tooltips
    CMD_HINTS = {
        "set": "set directed true|false\nset weighted true|false",
        "cmdoutput": "cmdoutput true|false  — enable/disable command output",
        "node": "node <name> [at <x> <y>]\nExample: node A at 100 200",
        "nodes": "nodes <n1> <n2> ... [at <x> <y>]\nExample: nodes A B C at 100 200",
        "edge": "edge <src> -> <tgt> [weight <w>]  — directed\nedge <src> -- <tgt> [weight <w>]  — undirected\nedge <src> <-> <tgt> [weight <w>]  — bidirectional\nedge <src> <=> <tgt> [weight <w>]  — dual (two edges)",
        "edges": "edges <n1> <n2> ... -> <tgt> [weight <w>]\nExample: edges A B C -> D",
        "path": "path <n1> <n2> ... <nN> [weight <w>]\npath iter <var> in <start>..<end> [weight <w>]",
        "cycle": "cycle <n1> <n2> ... <nN> [weight <w>]\ncycle iter <var> in <start>..<end> [weight <w>]",
        "connect": "connect <n1> <n2> ... <nN> [weight <w>]\nCreates complete graph (all pairs connected)",
        "star": "star <center> <leaf1> <leaf2> ...\nExample: star center n1 n2 n3 n4 n5",
        "wheel": "wheel <center> <rim1> <rim2> ...\nCreates cycle + center connected to all",
        "ladder": "ladder <prefix> <n> [weight <w>]\nExample: ladder L 4 weight 1",
        "grid": "grid <rows> <cols> [spacing <s>] [start <name>]\nExample: grid 3 4 spacing 100 start N",
        "circle": "circle <n> [radius <r>] [start <name>]\nExample: circle 6 radius 150 start V",
        "iter": "iter <var> in <start>..<end> [by <step>]: <cmd>\nfor <var> in 1..5: node v at 100 200",
        "toggle": "toggle <src> <tgt>  — toggle bidirectional",
        "separate": "separate <src> <tgt>  — split into two edges",
        "curve": "curve <src> <tgt> <amount>\nPositive = curve left, negative = curve right",
        "delete": "delete node <name>\ndelete edge <src> <tgt>",
        "rename": "rename <old> <new>",
        "color": "color <node> <#rrggbb>\nExample: color A #ff5500",
        "run": "run bfs|dfs from <src>\nrun dijkstra from <src> to <tgt>\nrun mst | topo | components | scc | cycle | centrality | info",
        "layout": "layout circle|spring",
        "let": "let <name> = <value>\nlet <name> = <expr> +|-|*|/ <expr>",
        "print": "print <message>",
        "clear": "clear  — remove all nodes and edges",
        "fit": "fit  — fit view to show all nodes",
    }

    def __init__(self, graph: Graph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self._interpreter = Interpreter(graph)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Editor with improved styling
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText(
            "# Graph DSL — Type commands here\n"
            "# Press Ctrl+Enter to run\n\n"
            "node A at 100 200\n"
            "node B at 300 200\n"
            "edge A -> B weight 5\n"
            "run bfs from A\n"
            "layout circle"
        )
        self._editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e2e;
                color: #e0e0e0;
                border: none;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                selection-background-color: #44475a;
            }
            QPlainTextEdit:focus {
                border: none;
            }
        """)
        self._highlighter = DSLHighlighter(self._editor.document())
        self._editor.cursorPositionChanged.connect(self._update_hint)
        splitter.addWidget(self._editor)

        # Command hint label (tooltip-style)
        self._hint_label = QLabel()
        self._hint_label.setStyleSheet("""
            background-color: #1e1e2e;
            color: #9cdcfe;
            padding: 10px 14px;
            border-radius: 0;
            border-top: 1px solid #3c3f41;
            border-bottom: 1px solid #3c3f41;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
        """)
        self._hint_label.setTextFormat(Qt.TextFormat.RichText)
        self._hint_label.setText("Type a command to see syntax hints...")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        # Output with improved styling
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #66bb6a;
                border: none;
                border-top: 1px solid #3c3f41;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        splitter.addWidget(self._output)

        splitter.setSizes([250, 120])
        layout.addWidget(splitter)

        # Button bar with improved styling
        btn_row = QHBoxLayout()
        btn_run = QPushButton("▶ Run Script")
        btn_run.setStyleSheet("""
            QPushButton {
                background-color: #7c4dff;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #8f64ff;
            }
            QPushButton:pressed {
                background-color: #6a35e0;
            }
        """)
        btn_run.clicked.connect(self._run)

        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: #e0e0e0;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #525252;
            }
        """)
        btn_clear.clicked.connect(self._clear_output)

        btn_example = QPushButton("Example")
        btn_example.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: #e0e0e0;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #525252;
            }
        """)
        btn_example.clicked.connect(self._load_example)

        btn_graph_to_script = QPushButton("Graph → Script")
        btn_graph_to_script.setToolTip("Generate DSL script from current graph")
        btn_graph_to_script.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: #e0e0e0;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #525252;
            }
        """)
        btn_graph_to_script.clicked.connect(self._graph_to_script)

        btn_row.addWidget(btn_run)
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_example)
        btn_row.addWidget(btn_graph_to_script)
        btn_row.addStretch()
        
        # Button bar background
        btn_widget = QWidget()
        btn_widget.setLayout(btn_row)
        btn_widget.setStyleSheet("""
            QWidget {
                background-color: #252536;
                border-top: 1px solid #3c3f41;
                padding: 8px;
            }
        """)
        layout.addWidget(btn_widget)

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

    def _update_hint(self) -> None:
        """Update command hint based on current line."""
        cursor = self._editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        line = cursor.block().text().strip().lower()

        # Find the first word (command)
        parts = line.split()
        if not parts:
            self._hint_label.setText("Type a command to see syntax hints...")
            return

        cmd = parts[0]

        # Check for matching command hint
        if cmd in self.CMD_HINTS:
            hint = self.CMD_HINTS[cmd]
            # Format hint with better visual separation
            lines = hint.split('\n')
            if len(lines) > 1:
                # Multi-line hint - show first line bold style
                formatted = f"<span style='color: #4fc3f7; font-weight: bold;'>{lines[0]}</span>"
                for line in lines[1:]:
                    formatted += f"<br><span style='color: #9cdcfe;'>{line}</span>"
                self._hint_label.setText(formatted)
            else:
                self._hint_label.setText(f"<span style='color: #9cdcfe;'>{hint}</span>")
        elif cmd.startswith("#"):
            self._hint_label.setText("<span style='color: #6a9955;'>Comment — ignored by interpreter</span>")
        else:
            self._hint_label.setText("<span style='color: #808080;'>Type a command to see syntax hints...</span>")

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

    def _graph_to_script(self) -> None:
        """Generate DSL script from current graph."""
        lines = ["# Generated from current graph"]

        # Graph settings
        lines.append(f"set directed {str(self.graph.directed).lower()}")
        lines.append(f"set weighted {str(self.graph.weighted).lower()}")
        lines.append("")

        # Nodes with positions
        for node in self.graph.nodes.values():
            x, y = int(node.x), int(node.y)
            lines.append(f"node {node.name} at {x} {y}")

        lines.append("")

        # Track processed edges to avoid duplicates
        processed = set()

        # Edges
        for edge in self.graph.edges:
            if edge.edge_id in processed:
                continue
                
            if self.graph.weighted:
                weight_str = f" weight {edge.weight}" if edge.weight != 1 else ""
            else:
                weight_str = ""

            if self.graph.directed:
                if edge.bidirectional:
                    # Single bidirectional edge with two arrowheads
                    lines.append(f"edge {edge.source} <-> {edge.target}{weight_str}")
                else:
                    # Check if there's a separate reverse edge with similar weight
                    reverse_edge = self.graph.get_edge(edge.target, edge.source)
                    if reverse_edge and reverse_edge.edge_id not in processed:
                        # Two separate edges in opposite directions - use <=> syntax
                        lines.append(f"edge {edge.source} <=> {edge.target}{weight_str}")
                        processed.add(reverse_edge.edge_id)
                    else:
                        lines.append(f"edge {edge.source} -> {edge.target}{weight_str}")
            else:
                lines.append(f"edge {edge.source} -- {edge.target}{weight_str}")

            processed.add(edge.edge_id)

            # Add curvature if set
            if edge.curvature != 0.0:
                lines.append(f"curve {edge.source} {edge.target} {edge.curvature:g}")

        self._editor.setPlainText("\n".join(lines))
        self._output.setPlainText(f"Generated {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges as DSL script.")
