"""
Unit tests for BoardGeometry, ChessBoardView rendering, and interactive move execution.
"""

import cairo
import pytest
import chess

from chess_reader.theme.loader import ThemeManager
from chess_reader.theme.asset_cache import PieceAssetCache
from chess_reader.ui.board.geometry import BoardGeometry
from chess_reader.ui.board.board_view import ChessBoardView, parse_color
from chess_reader.ui.board.drawings import ArrowDrawing, SquareHighlight, draw_cairo_arrow


def test_board_geometry_calculations():
    # 800 x 600 viewport -> board size must be 600, square size = 75
    geo = BoardGeometry(800, 600, flipped=False)
    assert geo.board_size == 600.0
    assert geo.square_size == 75.0
    assert geo.offset_x == 100.0
    assert geo.offset_y == 0.0

    # e4 is file 4, rank 3
    e4 = chess.E4
    x, y, w, h = geo.square_to_rect(e4)
    assert w == 75.0
    assert h == 75.0
    # In unflipped: col = file = 4; row = 7 - rank = 7 - 3 = 4
    assert x == 100.0 + (4 * 75.0)
    assert y == 0.0 + (4 * 75.0)

    # Point to square lookup
    sq = geo.point_to_square(x + 10, y + 10)
    assert sq == chess.E4

    # Point outside board
    assert geo.point_to_square(10, 10) is None  # in left margin


def test_board_geometry_with_border():
    # 800 x 800 with 20px border
    geo = BoardGeometry(800, 800, border_width=20.0)
    assert geo.total_size == 800.0
    assert geo.effective_border == 20.0
    assert geo.inner_size == 760.0
    assert geo.square_size == 760.0 / 8.0
    assert geo.squares_offset_x == 20.0
    assert geo.squares_offset_y == 20.0

    # Point in border margin should be None
    assert geo.point_to_square(5, 5) is None
    # Point inside a1
    a1_sq = geo.point_to_square(25, 775)
    assert a1_sq == chess.A1


def test_board_geometry_flipped():
    geo = BoardGeometry(800, 800, flipped=True)
    e4 = chess.E4
    x, y, _, _ = geo.square_to_rect(e4)
    # In flipped: col = 7 - file = 7 - 4 = 3; row = rank = 3
    assert x == 3 * 100.0
    assert y == 3 * 100.0

    sq = geo.point_to_square(x + 50, y + 50)
    assert sq == chess.E4


def test_color_parsing():
    assert parse_color("#ffffff") == (1.0, 1.0, 1.0, 1.0)
    assert parse_color("#000000") == (0.0, 0.0, 0.0, 1.0)
    rgba = parse_color("rgba(100, 150, 200, 0.5)")
    assert abs(rgba[0] - 100 / 255.0) < 0.01
    assert abs(rgba[1] - 150 / 255.0) < 0.01
    assert abs(rgba[2] - 200 / 255.0) < 0.01
    assert abs(rgba[3] - 0.5) < 0.01


def test_board_view_move_execution():
    theme_mgr = ThemeManager(user_themes_dir="/tmp/test_non_existent")
    board_view = ChessBoardView(theme=theme_mgr.active_theme)

    assert board_view.board.turn == chess.WHITE
    assert board_view.last_move is None

    # Execute e2-e4
    e2e4 = chess.Move.from_uci("e2e4")
    board_view._execute_move(e2e4)

    assert board_view.board.turn == chess.BLACK
    assert board_view.last_move == e2e4
    assert board_view.board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board_view.board.piece_at(chess.E2) is None


def test_board_view_flipping():
    board_view = ChessBoardView()
    assert board_view.flipped is False
    board_view.flip()
    assert board_view.flipped is True
    assert board_view.geometry.flipped is True
    board_view.flip()
    assert board_view.flipped is False


def test_board_view_arrow_and_highlight_annotations():
    board_view = ChessBoardView()
    arrow = ArrowDrawing(from_square=chess.E2, to_square=chess.E4)
    board_view.arrows.append(arrow)
    board_view.highlights[chess.E4] = SquareHighlight(square=chess.E4)

    assert len(board_view.arrows) == 1
    assert chess.E4 in board_view.highlights

    board_view.clear_drawings()
    assert len(board_view.arrows) == 0
    assert len(board_view.highlights) == 0


def test_board_view_offscreen_cairo_draw():
    """Ensure complete Cairo drawing pipeline renders without raising exceptions."""
    theme_mgr = ThemeManager(user_themes_dir="/tmp/test_non_existent")
    board_view = ChessBoardView(theme=theme_mgr.active_theme)

    # Set selection, legal moves, and arrows
    board_view.selected_square = chess.E2
    board_view.legal_moves_for_selected = [
        m for m in board_view.board.legal_moves if m.from_square == chess.E2
    ]
    board_view.arrows.append(ArrowDrawing(from_square=chess.G1, to_square=chess.F3))

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 600, 600)
    ctx = cairo.Context(surface)

    # Execute draw function
    board_view._on_draw(board_view, ctx, 600, 600)

    # Verify pixels were drawn (surface is not blank)
    data = surface.get_data()
    assert any(b != 0 for b in data[:1000])
