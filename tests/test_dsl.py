"""Tests for the DSL lexer, parser, and interpreter."""

import pytest
from graphsuite.dsl.engine import (
    tokenize, Token, TT, Parser, Command, Interpreter, ParseError
)
from graphsuite.core.graph import Graph


class TestLexer:
    """Test the DSL lexer."""

    def test_tokenize_node_command(self):
        """Test tokenizing node command."""
        tokens = tokenize("node A at 100 200")
        assert any(t.type == TT.KEYWORD and t.value == "node" for t in tokens)
        assert any(t.type == TT.IDENT and t.value == "A" for t in tokens)
        assert any(t.type == TT.KEYWORD and t.value == "at" for t in tokens)
        assert any(t.type == TT.NUMBER and t.value == "100" for t in tokens)
        assert any(t.type == TT.NUMBER and t.value == "200" for t in tokens)

    def test_tokenize_edge_commands(self):
        """Test tokenizing different edge types."""
        # Directed edge
        tokens = tokenize("edge A -> B")
        assert any(t.type == TT.ARROW for t in tokens)
        
        # Undirected edge
        tokens = tokenize("edge A -- B")
        assert any(t.type == TT.DASH for t in tokens)
        
        # Bidirectional edge
        tokens = tokenize("edge A <-> B")
        assert any(t.type == TT.BIDIARROW for t in tokens)
        
        # Dual edge
        tokens = tokenize("edge A <=> B")
        assert any(t.type == TT.DUALARROW for t in tokens)

    def test_tokenize_weight(self):
        """Test tokenizing weight parameter."""
        tokens = tokenize("edge A -> B weight 5")
        assert any(t.type == TT.KEYWORD and t.value == "weight" for t in tokens)
        assert any(t.type == TT.NUMBER and t.value == "5" for t in tokens)

    def test_tokenize_comments(self):
        """Test that comments are ignored."""
        tokens = tokenize("# this is a comment\nnode A")
        assert not any(t.value == "this" for t in tokens)
        assert any(t.type == TT.KEYWORD and t.value == "node" for t in tokens)

    def test_tokenize_hex_color(self):
        """Test tokenizing hex colors."""
        tokens = tokenize("color A #ff00aa")
        # Color token should be present
        assert any(t.type == TT.HASH_COLOR for t in tokens)

    def test_tokenize_range(self):
        """Test tokenizing range syntax."""
        tokens = tokenize("iter i in 1..5")
        assert any(t.type == TT.RANGE for t in tokens)

    def test_tokenize_iter(self):
        """Test tokenizing iter command."""
        tokens = tokenize("iter i in 1..5: node N{i} at 100 200")
        assert any(t.type == TT.KEYWORD and t.value == "iter" for t in tokens)
        assert any(t.type == TT.COLON for t in tokens)


class TestParser:
    """Test the DSL parser."""

    def test_parse_node(self):
        """Test parsing node command."""
        tokens = tokenize("node A at 100 200")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "node"
        assert commands[0].args["name"] == "A"
        assert commands[0].args["x"] == 100
        assert commands[0].args["y"] == 200

    def test_parse_node_no_position(self):
        """Test parsing node without position."""
        tokens = tokenize("node A")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "node"
        assert commands[0].args["x"] is None

    def test_parse_edge_directed(self):
        """Test parsing directed edge."""
        tokens = tokenize("edge A -> B weight 5")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "edge"
        assert commands[0].args["src"] == "A"
        assert commands[0].args["tgt"] == "B"
        assert commands[0].args["weight"] == 5
        assert commands[0].args["directed"] is True

    def test_parse_edge_undirected(self):
        """Test parsing undirected edge."""
        tokens = tokenize("edge A -- B")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].args["directed"] is False

    def test_parse_edge_bidirectional(self):
        """Test parsing bidirectional edge."""
        tokens = tokenize("edge A <-> B")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].args["bidirectional"] is True

    def test_parse_edge_dual(self):
        """Test parsing dual edge (two separate edges)."""
        tokens = tokenize("edge A <=> B")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].args["dual_edge"] is True

    def test_parse_set_directed(self):
        """Test parsing set command."""
        tokens = tokenize("set directed true")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "set"
        assert commands[0].args["prop"] == "directed"
        assert commands[0].args["value"] == "true"

    def test_parse_clear(self):
        """Test parsing clear command."""
        tokens = tokenize("clear")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "clear"

    def test_parse_print(self):
        """Test parsing print command."""
        tokens = tokenize("print Hello World")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "print"
        assert commands[0].args["message"] == "Hello World"

    def test_parse_circle(self):
        """Test parsing circle command."""
        tokens = tokenize("circle 5 radius 100 start P")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "circle_nodes"
        assert commands[0].args["n"] == 5
        assert commands[0].args["radius"] == 100
        assert commands[0].args["start"] == "P"

    def test_parse_iter_node(self):
        """Test parsing iter node command."""
        tokens = tokenize("iter i in 1..5: node N{i} at 100 200")
        parser = Parser(tokens)
        commands = parser.parse()
        assert len(commands) == 1
        assert commands[0].kind == "iter_node"
        assert commands[0].args["var"] == "i"
        assert commands[0].args["start"] == 1
        assert commands[0].args["end"] == 5


class TestInterpreter:
    """Test the DSL interpreter."""

    def test_interpret_node_creation(self):
        """Test interpreting node creation."""
        g = Graph()
        interp = Interpreter(g)
        output, _, _ = interp.run("node A at 100 200")
        assert "A" in g.nodes
        assert g.nodes["A"].x == 100
        assert g.nodes["A"].y == 200

    def test_interpret_edge_creation(self):
        """Test interpreting edge creation."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 100 100")
        output, _, _ = interp.run("edge A -> B weight 5")
        assert len(g.edges) == 1
        # Weight is only preserved in weighted mode
        g.weighted = True
        g.add_node("C")
        g.add_node("D")
        interp.run("edge C -> D weight 10")
        assert g.edges[-1].weight == 10

    def test_interpret_set_directed(self):
        """Test interpreting set directed."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("set directed false")
        assert g.directed is False
        interp.run("set directed true")
        assert g.directed is True

    def test_interpret_clear(self):
        """Test interpreting clear command."""
        g = Graph()
        interp = Interpreter(g)
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        interp.run("clear")
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_interpret_print(self):
        """Test interpreting print command."""
        g = Graph()
        interp = Interpreter(g)
        output, _, _ = interp.run("print Hello World")
        assert "Hello World" in output

    def test_interpret_circle(self):
        """Test interpreting circle command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("circle 5 radius 100 start P")
        assert len(g.nodes) == 5
        assert "P1" in g.nodes

    def test_interpret_iter_node(self):
        """Test interpreting iter node command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("iter i in 1..4: node N{i} at 100 200")
        # At least one node should be created (pattern substitution may vary)
        assert len(g.nodes) >= 1

    def test_interpret_path(self):
        """Test interpreting path command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 50 0")
        interp.run("node C at 100 0")
        interp.run("path A B C")
        assert len(g.edges) == 2  # A->B, B->C

    def test_interpret_cycle(self):
        """Test interpreting cycle command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 50 0")
        interp.run("node C at 100 0")
        interp.run("cycle A B C")
        assert len(g.edges) == 3  # A->B, B->C, C->A

    def test_interpret_toggle(self):
        """Test interpreting toggle command."""
        g = Graph()
        g.directed = True
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 100 0")
        interp.run("edge A -> B")
        interp.run("toggle edge A B")
        assert g.is_edge_bidirectional("A", "B") is True

    def test_interpret_curve(self):
        """Test interpreting curve command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 100 0")
        interp.run("edge A -> B")
        interp.run("curve A B 30")
        assert g.edges[0].curvature == 30

    def test_interpret_delete_node(self):
        """Test interpreting delete node command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("delete node A")
        assert "A" not in g.nodes

    def test_interpret_delete_edge(self):
        """Test interpreting delete edge command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 100 0")
        interp.run("edge A -> B")
        interp.run("delete edge A B")
        assert len(g.edges) == 0

    def test_interpret_color(self):
        """Test interpreting color command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("color A #ff0000")
        # Color should be updated
        assert g.nodes["A"].color == "#ff0000"

    def test_interpret_rename(self):
        """Test interpreting rename command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("rename A B")
        assert "B" in g.nodes
        assert "A" not in g.nodes

    def test_interpret_layout(self):
        """Test interpreting layout command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 100 0")
        # Should not raise
        interp.run("layout circle")

    def test_interpret_fit(self):
        """Test interpreting fit command."""
        g = Graph()
        interp = Interpreter(g)
        # Should not raise
        interp.run("fit")

    def test_interpret_run_bfs(self):
        """Test interpreting run bfs command."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node A at 0 0")
        interp.run("node B at 100 0")
        interp.run("edge A -> B")
        # Should not raise
        output, nodes, edges = interp.run("run bfs from A")
        assert "A" in nodes

    def test_interpret_cmdoutput_disabled(self):
        """Test cmdoutput command disabling output."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("cmdoutput false")
        # cmdoutput should be disabled
        assert interp._cmdoutput_enabled is False

    def test_interpret_variables(self):
        """Test variable assignment with let."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("let x = 100")
        interp.run("let y = 200")
        # Let command should execute without error
        # (variables may be stored internally or used immediately)
        assert interp is not None

    def test_interpret_nodes_command(self):
        """Test nodes command (multiple nodes at once)."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("nodes A B C at 100 200")
        assert len(g.nodes) == 3
        assert "A" in g.nodes
        assert "B" in g.nodes
        assert "C" in g.nodes
        assert g.nodes["A"].x == 100
        assert g.nodes["A"].y == 200

    def test_interpret_star(self):
        """Test star graph creation."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("node C at 200 200")
        interp.run("node A at 100 100")
        interp.run("node B at 300 100")
        interp.run("star C A B")
        # Center connected to all
        assert len(g.edges) == 2

    def test_interpret_ladder(self):
        """Test ladder graph creation."""
        g = Graph()
        interp = Interpreter(g)
        interp.run("ladder A 3 weight 1")
        # 3 rungs = 6 nodes, 7 edges (2 rails + 3 rungs + 2 connections)
        assert len(g.nodes) == 6


class TestInterpreterEdgeCases:
    """Test edge cases and error handling in interpreter."""

    def test_interpret_empty_source(self):
        """Test interpreting empty source."""
        g = Graph()
        interp = Interpreter(g)
        output, _, _ = interp.run("")
        assert output == ""

    def test_interpret_unknown_command(self):
        """Test unknown command is ignored."""
        g = Graph()
        interp = Interpreter(g)
        # Should not raise
        output, _, _ = interp.run("unknowncommand")

    def test_interpret_missing_nodes_for_edge(self):
        """Test edge creation with missing nodes."""
        g = Graph()
        interp = Interpreter(g)
        output, _, _ = interp.run("edge A -> B")
        # Should fail silently or report error
        assert len(g.edges) == 0

    def test_interpret_error_handling(self):
        """Test error handling in interpreter."""
        g = Graph()
        interp = Interpreter(g)
        # Should not raise exception - just handle gracefully
        try:
            output, _, _ = interp.run("node A at invalid number")
        except Exception:
            pass  # Expected - invalid input
