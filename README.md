# Graph Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-106%20passed-green)](tests/)

A professional desktop application for creating, editing, and analyzing graphs. Built with PySide6 and NetworkX.

![Graph Suite](https://via.placeholder.com/800x450.png?text=Graph+Suite+Screenshot)

## Features

### Core Functionality
- **Interactive Canvas** — Drag, zoom, and pan to work with your graph
- **Multigraph Support** — Create parallel edges between nodes (hold Shift)
- **Bidirectional Edges** — Single edge with arrowheads at both ends
- **Edge Curvature** — Manually curve edges using Ctrl+drag handles
- **Matrix Editors** — Adjacency and incidence matrix views with live editing
- **Graph Algorithms** — BFS, DFS, Dijkstra, Bellman-Ford, MST, and more
- **Scripting DSL** — Built-in domain-specific language for automation
- **Export Options** — Save graphs as JSON or export as PNG images

### Graph Types Supported
- Directed and undirected graphs
- Weighted and unweighted edges
- Parallel edges (multiple edges between same nodes)
- Bidirectional edges (single edge, two arrowheads)
- Self-loops

## Installation

### From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/graph-suite.git
cd graph-suite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Development Installation
```bash
# Install with development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Using pip (when published)
```bash
pip install graph-suite
graph-suite  # Launch the application
```

## Usage

### Launch the Application
```bash
python main.py
```

### Basic Operations

| Action | Method |
|--------|--------|
| **Add node** | Select "Add Node" tool (N) and click on canvas |
| **Add edge** | Select "Add Edge" tool (E) and click two nodes |
| **Add parallel edge** | Hold Shift while adding edge between same nodes |
| **Delete** | Select "Delete" tool (D) and click node/edge |
| **Move node** | Select mode (S), drag node with mouse |
| **Curve edge** | Hold Ctrl and drag the curve handle on edge |
| **Toggle bidirectional** | Right-click edge → Toggle Bidirectional |
| **Pan view** | Click-drag on empty space or middle mouse button |
| **Zoom** | Mouse wheel or Zoom +/- buttons |

### Keyboard Shortcuts

#### Modes
| Key | Action |
|-----|--------|
| **S** | Select mode |
| **N** | Add node mode |
| **E** | Add edge mode |
| **D** | Delete mode |

#### View
| Key | Action |
|-----|--------|
| **F** | Fit view (show all nodes) |
| **Ctrl++** | Zoom in |
| **Ctrl+-** | Zoom out |

#### Edit
| Key | Action |
|-----|--------|
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Delete** | Remove selected items |

#### File
| Key | Action |
|-----|--------|
| **Ctrl+N** | New graph |
| **Ctrl+O** | Open graph |
| **Ctrl+S** | Save graph |
| **Ctrl+Shift+S** | Save as |
| **Ctrl+Q** | Quit |

### DSL Scripting

Graph Suite includes a powerful domain-specific language for scripting graph creation:

```dsl
# Create a pentagon with all diagonals (complete graph K5)
set directed true
set weighted true

# Create 5 nodes in a circle
circle 5 radius 150 start P

# Connect as pentagon
cycle iter i in 1..5 weight 1

# Add diagonals
edge P1 -> P3 weight 2
edge P1 -> P4 weight 2
edge P2 -> P4 weight 2
edge P2 -> P5 weight 2
edge P3 -> P5 weight 2

# Apply spring layout
layout spring
print Complete Graph K5 Created!
```

Run DSL scripts from the Script Console at the bottom of the application, or load the included `beautiful_graphs.dsl` file.

#### DSL Commands Reference

| Command | Description |
|---------|-------------|
| `node <name> [at <x> <y>]` | Create a node |
| `nodes <n1> <n2> ... [at <x> <y>]` | Create multiple nodes |
| `edge <src> -> <tgt> [weight <w>]` | Create directed edge |
| `edge <src> -- <tgt> [weight <w>]` | Create undirected edge |
| `edge <src> <-> <tgt> [weight <w>]` | Create bidirectional edge |
| `edge <src> <=> <tgt> [weight <w>]` | Create dual edge (two separate edges) |
| `circle <n> [radius <r>] [start <name>]` | Create nodes in circle |
| `iter <var> in <start>..<end>: <cmd>` | Iterate and create nodes/edges |
| `path <n1> <n2> ...` | Create path of edges |
| `cycle <n1> <n2> ...` | Create cycle (path + closing edge) |
| `star <center> <n1> <n2> ...` | Create star graph |
| `ladder <prefix> <n> [weight <w>]` | Create ladder graph |
| `layout circle\|spring` | Apply layout algorithm |
| `run bfs\|dfs\|dijkstra ...` | Run graph algorithm |
| `toggle <src> <tgt>` | Toggle edge bidirectional |
| `curve <src> <tgt> <amount>` | Set edge curvature |
| `clear` | Clear entire graph |
| `print <message>` | Print message |

## Project Structure

```
graphsuite/
├── core/           # Graph data model and operations
│   ├── graph.py    # Main Graph class with Node/Edge
│   └── __init__.py
├── gui/            # Qt-based user interface
│   ├── main_window.py
│   ├── canvas.py   # Interactive graph canvas
│   ├── matrix_editor.py
│   ├── algorithm_panel.py
│   └── style.py    # Color palette and stylesheet
├── dsl/            # Domain-specific language
│   ├── engine.py   # Lexer, parser, interpreter
│   └── __init__.py
└── __init__.py

tests/              # Comprehensive test suite
├── test_graph.py   # Core graph tests
├── test_dsl.py     # DSL tests
├── test_algorithms.py
└── conftest.py     # Test fixtures
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=graphsuite --cov-report=html

# Run specific test file
pytest tests/test_graph.py -v

# Run original standalone tests
python test_bidirectional.py
python test_parallel_edges.py
```

## Configuration

### pyproject.toml
The project uses `pyproject.toml` for:
- Build system configuration
- Package metadata
- pytest settings
- Coverage configuration
- Ruff linting rules
- mypy type checking

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## Edge Case Testing

See [EDGE_CASE_TESTS.md](EDGE_CASE_TESTS.md) for comprehensive edge case testing scenarios including:
- Graph structure edge cases (empty graphs, self-loops, parallel edges)
- UI interaction edge cases (rapid clicking, zoom extremes)
- DSL scripting edge cases (invalid syntax, large scripts)
- Algorithm edge cases (negative weights, disconnected components)
- Serialization edge cases (unicode, large graphs)

## Troubleshooting

### Display Issues
- **Problem**: Application window appears too small/large
  - **Solution**: The app supports High-DPI scaling. Check your system's display scaling settings.

### Performance Issues
- **Problem**: Slow rendering with many nodes
  - **Solution**: Try reducing zoom level or using "Fit View" (F). Graphs with 1000+ nodes may have reduced performance.

### DSL Script Errors
- **Problem**: "Unknown command" errors
  - **Solution**: Check DSL syntax. Comments start with `#`, commands are case-insensitive.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Run linter: `ruff check .`
6. Commit: `git commit -m "Add my feature"`
7. Push: `git push origin feature/my-feature`
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython-6/)
- Graph algorithms powered by [NetworkX](https://networkx.org/)
- Numerical operations with [NumPy](https://numpy.org/)

## Version History

### 1.0.0
- Initial release
- Full multigraph support with parallel edges
- Bidirectional edge toggle and separation
- Manual edge curvature with Ctrl+drag
- Comprehensive test suite (106+ tests)
- DSL scripting with 30+ commands
- High-DPI support
- Professional dark theme UI
