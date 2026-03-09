"""Domain-Specific Language for graph scripting.

The Graph Suite DSL provides a simple scripting language for creating and
manipulating graphs programmatically. Features include:

- Node and edge creation
- Graph property configuration
- Iterative patterns for bulk operations
- Layout commands
- Algorithm execution
- Variable substitution

Example:
    from graphsuite.dsl.engine import Interpreter
    from graphsuite.core.graph import Graph

    g = Graph()
    interp = Interpreter(g)
    output, _, _ = interp.run('''
        circle 5 radius 100
        path iter i in 1..5 weight 1
        layout spring
    ''')
"""

from graphsuite.dsl.engine import (
    Interpreter,
    Parser,
    tokenize,
    Token,
    TT,
    Command,
)

__all__ = [
    "Interpreter",
    "Parser",
    "tokenize",
    "Token",
    "TT",
    "Command",
]
