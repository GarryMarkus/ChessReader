"""
Unit tests for Interactive Pawn Promotion, Underpromotion, Multi-Color Annotations, and NAG shortcuts.
"""

import pytest
import chess
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

from chess_reader.ui.board.board_view import ChessBoardView
from chess_reader.core.game_model import GameModel


def test_is_promotion_move():
    bv = ChessBoardView()

    # Position: White pawn on e7, Black king on h8, White king on h1
    board = chess.Board("7k/4P3/8/8/8/8/8/7K w - - 0 1")
    bv.set_board(board)

    # e7 to e8 is a legal pawn promotion
    assert bv._is_promotion_move(chess.E7, chess.E8) is True

    # e7 to d8 (illegal / no capture) is not a legal promotion
    assert bv._is_promotion_move(chess.E7, chess.D8) is False

    # King move h1 to h2 is not promotion
    assert bv._is_promotion_move(chess.H1, chess.H2) is False

    # Position with capture promotion: Black rook on d8
    board_cap = chess.Board("3r3k/4P3/8/8/8/8/8/7K w - - 0 1")
    bv.set_board(board_cap)
    assert bv._is_promotion_move(chess.E7, chess.D8) is True
    assert bv._is_promotion_move(chess.E7, chess.E8) is True


def test_is_promotion_move_black_turn():
    bv = ChessBoardView()
    # Position: Black pawn on b2, Black to move
    board = chess.Board("7k/8/8/8/8/8/1p6/7K b - - 0 1")
    bv.set_board(board)

    assert bv._is_promotion_move(chess.B2, chess.B1) is True
    assert bv._is_promotion_move(chess.B2, chess.A1) is False


def test_underpromotion_piece_selection():
    bv = ChessBoardView()
    board = chess.Board("7k/4P3/8/8/8/8/8/7K w - - 0 1")
    bv.set_board(board)

    moves_made = []
    bv.on_move_made = lambda m: moves_made.append(m)

    # Prompt promotion
    bv._prompt_pawn_promotion(chess.E7, chess.E8)
    assert bv._pending_promotion == (chess.E7, chess.E8)

    # Select Underpromotion to Knight
    bv._on_promotion_selected(chess.KNIGHT)
    assert bv._pending_promotion is None
    assert len(moves_made) == 1
    assert moves_made[0] == chess.Move(chess.E7, chess.E8, promotion=chess.KNIGHT)
    assert bv.board.piece_at(chess.E8) == chess.Piece(chess.KNIGHT, chess.WHITE)


def test_promotion_keyboard_shortcuts():
    bv = ChessBoardView()
    board = chess.Board("7k/4P3/8/8/8/8/8/7K w - - 0 1")
    bv.set_board(board)

    moves_made = []
    bv.on_move_made = lambda m: moves_made.append(m)

    bv._prompt_pawn_promotion(chess.E7, chess.E8)

    # Press 'r' / 'R' for Rook promotion
    handled = bv._on_key_pressed(None, Gdk.KEY_r, 0, 0)
    assert handled is True
    assert len(moves_made) == 1
    assert moves_made[0] == chess.Move(chess.E7, chess.E8, promotion=chess.ROOK)
    assert bv.board.piece_at(chess.E8) == chess.Piece(chess.ROOK, chess.WHITE)


def test_promotion_escape_dismiss():
    bv = ChessBoardView()
    board = chess.Board("7k/4P3/8/8/8/8/8/7K w - - 0 1")
    bv.set_board(board)

    bv._prompt_pawn_promotion(chess.E7, chess.E8)
    assert bv._pending_promotion == (chess.E7, chess.E8)

    # Dismiss popover
    bv._on_promotion_dismissed(None)
    assert bv._pending_promotion is None


def test_drawing_color_modifiers():
    bv = ChessBoardView()

    # Normal (no modifiers) -> Green
    arr_c, hlg_c = bv._get_drawing_color(Gdk.ModifierType(0))
    assert "152, 195, 121" in arr_c

    # Control -> Red
    arr_c, hlg_c = bv._get_drawing_color(Gdk.ModifierType.CONTROL_MASK)
    assert "224, 108, 117" in arr_c

    # Shift -> Yellow
    arr_c, hlg_c = bv._get_drawing_color(Gdk.ModifierType.SHIFT_MASK)
    assert "229, 192, 123" in arr_c

    # Alt -> Blue
    arr_c, hlg_c = bv._get_drawing_color(Gdk.ModifierType.ALT_MASK)
    assert "97, 175, 239" in arr_c


def test_game_model_toggle_nag():
    gm = GameModel()
    gm.add_move(chess.Move.from_uci("e2e4"))
    node = gm.current_node

    # Add NAG 1 (!)
    gm.toggle_nag(node, 1)
    assert 1 in node.nags
    assert gm.get_nags_display(node) == ["!"]

    # Switching to NAG 2 (?) clears 1 and sets 2
    gm.toggle_nag(node, 2)
    assert 1 not in node.nags
    assert 2 in node.nags
    assert gm.get_nags_display(node) == ["?"]

    # Toggling 2 again clears it
    gm.toggle_nag(node, 2)
    assert 2 not in node.nags
    assert gm.get_nags_display(node) == []

    # Toggling root does nothing
    gm.toggle_nag(gm.game, 1)
    assert 1 not in gm.game.nags
