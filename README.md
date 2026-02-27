# Graph Suite

A desktop application for creating, editing, and analyzing graphs.

## Features

- **Interactive Canvas** — Drag, zoom, and pan to work with your graph
- **Matrix Editors** — Adjacency and incidence matrix views
- **Graph Algorithms** — BFS, DFS, Dijkstra, Bellman-Ford, MST, and more
- **Scripting** — Built-in DSL for automating graph creation
- **Export** — Save graphs as JSON or export as PNG images

## Installation

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### Basic Operations

| Action | Method |
|--------|--------|
| Add node | Select "Add Node" tool (N) and click on canvas |
| Add edge | Select "Add Edge" tool (E) and click two nodes |
| Delete | Select "Delete" tool (D) and click node/edge |
| Move node | Select mode (S), drag node with mouse |
| Pan view | Click-drag on empty space or middle mouse |
| Zoom | Mouse wheel or Zoom +/- buttons |

### Keyboard Shortcuts

- **S** — Select mode
- **N** — Add node mode
- **E** — Add edge mode
- **D** — Delete mode
- **F** — Fit view
- **Ctrl+Z/Y** — Undo/Redo
- **Ctrl++/-** — Zoom in/out
- **Delete** — Remove selected items

## Project Structure

```
graphsuite/
├── core/       # Graph data model
├── gui/        # User interface
├── dsl/        # Scripting language
└── main.py     # Entry point
```

## License

MIT
