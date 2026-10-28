# ChessReader (Zed Design Language for Linux)

A high-performance Chess PGN Viewer, Editor, and Annotator for Linux combining industrial-strength chess logic with the distraction-free, hyper-minimal aesthetic of the **Zed Editor**.

## Features

- **Unified Window Chrome (CSD):** Seamless custom titlebar integrated into the workspace header with breadcrumbs and window controls. Draggable across Wayland and X11.
- **Zed Aesthetic:** Charcoal/zinc neutral palette, 1px subtle divider borders, crisp monospace typography, split-pane workspace.
- **Board Rendering:** Custom asset mapping system for PNG/SVG pieces and solid/dual-tile boards, smooth 120 FPS Cairo/GSK rendering.
- **PGN & Variation Trees:** Recursive variation trees (RAVs), line promotion, branch reordering, inline NAGs, comments, clocks, and board drawings.
- **UCI Engine Integration:** Asynchronous non-blocking Stockfish pipeline with Multi-PV, live evaluation bar, and automated game review.

## Development Setup

```bash
# Clone the repository
cd ChessReader

# Run tests
pytest tests/ -v

# Run the application
python3 -m chess_reader.main
```
