"""
Unit tests for EvalBar, CPLGraphView, EngineDock, and analysis UI integration.
"""

import cairo
import pytest
import chess

from chess_reader.engine.analyzer import AnalysisSnapshot, AnalysisLine
from chess_reader.ui.dock.eval_bar import EvalBar
from chess_reader.ui.dock.cpl_graph import CPLGraphView
from chess_reader.ui.dock.engine_dock import EngineDock


def test_eval_bar_rendering():
    bar = EvalBar(flipped=False)
    assert bar.win_percentage == 50.0

    bar.set_evaluation("+0.85", 62.5)
    assert bar.display_score == "+0.85"
    assert bar.win_percentage == 62.5

    bar.set_flipped(True)
    assert bar.flipped is True

    # Render to offscreen Cairo surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 22, 400)
    ctx = cairo.Context(surface)
    bar._on_draw(bar, ctx, 22, 400)

    # Verify pixels drawn
    data = surface.get_data()
    assert any(b != 0 for b in data[:500])


def test_cpl_graph_rendering_and_interaction():
    graph = CPLGraphView()
    test_curve = [(0, 0.0), (1, 0.4), (2, 0.3), (3, -0.8), (4, 1.5)]
    graph.set_data(test_curve, current_ply=3)

    assert len(graph.data_points) == 5
    assert graph.current_ply == 3

    # Render to offscreen Cairo surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 300, 90)
    ctx = cairo.Context(surface)
    graph._on_draw(graph, ctx, 300, 90)

    data = surface.get_data()
    assert any(b != 0 for b in data[:500])

    # Test click-to-ply callback
    selected_plies = []
    graph.on_ply_selected = lambda p: selected_plies.append(p)
    # Simulate click at 50% width
    graph._on_clicked(None, 1, 150.0, 45.0)
    assert len(selected_plies) == 1
    assert selected_plies[0] == 2


def test_engine_dock_collapse_and_snapshot_update():
    dock = EngineDock()
    assert dock.is_collapsed is False

    # Toggle collapse
    dock.toggle_btn.emit("clicked")
    assert dock.is_collapsed is True
    assert dock.content_box.get_visible() is False

    # Toggle expand
    dock.toggle_btn.emit("clicked")
    assert dock.is_collapsed is False
    assert dock.content_box.get_visible() is True

    # Update with Multi-PV lines
    line1 = AnalysisLine(
        multipv=1, depth=14, score_cp=45, nodes=1500000, nps=950000,
        pv=[chess.Move.from_uci("e2e4")], san_line="1. e4 c5 2. Nf3"
    )
    line2 = AnalysisLine(
        multipv=2, depth=14, score_cp=32, nodes=1500000, nps=950000,
        pv=[chess.Move.from_uci("d2d4")], san_line="1. d4 d5 2. c4"
    )
    snapshot = AnalysisSnapshot(depth=14, nodes=1500000, nps=950000, lines=[line1, line2])
    dock.update_snapshot(snapshot)

    assert "Depth: 14" in dock.status_label.get_text()
    assert "1.5M" in dock.status_label.get_text()
