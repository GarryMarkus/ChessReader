"""
Unit tests for Piece Animation trajectory detection, cubic easing, and castling/capture synchronization.
"""

import pytest
import chess
from chess_reader.ui.board.animation import (
    PieceAnimation,
    ease_out_cubic,
    detect_move_animation
)
from chess_reader.ui.board.board_view import ChessBoardView


def test_ease_out_cubic():
    assert ease_out_cubic(0.0) == 0.0
    assert pytest.approx(ease_out_cubic(0.5), 0.001) == 0.875
    assert ease_out_cubic(1.0) == 1.0
    # Clamping behavior
    assert ease_out_cubic(-0.5) == 0.0
    assert ease_out_cubic(1.5) == 1.0


def test_piece_animation_progress_and_finish():
    anim = PieceAnimation(
        piece_symbol="wP",
        from_square=chess.E2,
        to_square=chess.E4,
        target_square=chess.E4,
        start_time_us=1_000_000,
        duration_us=200_000  # 200ms
    )

    # At start
    assert anim.get_progress(1_000_000) == 0.0
    assert anim.is_finished(1_000_000) is False

    # At halfway (100ms in)
    halfway_prog = anim.get_progress(1_100_000)
    assert pytest.approx(halfway_prog, 0.001) == 0.875
    assert anim.is_finished(1_100_000) is False

    # At completion
    assert anim.get_progress(1_200_000) == 1.0
    assert anim.is_finished(1_200_000) is True

    # After completion
    assert anim.get_progress(1_300_000) == 1.0
    assert anim.is_finished(1_300_000) is True


def test_detect_forward_standard_move():
    b1 = chess.Board()
    m = chess.Move.from_uci("e2e4")
    b2 = b1.copy()
    b2.push(m)

    anim = detect_move_animation(b1, b2, last_move=m, start_time_us=1000)
    assert anim is not None
    assert anim.piece_symbol == "wP"
    assert anim.from_square == chess.E2
    assert anim.to_square == chess.E4
    assert anim.target_square == chess.E4
    assert anim.captured_piece_symbol is None
    assert anim.secondary_piece_symbol is None
    assert anim.is_reverse is False


def test_detect_forward_capture():
    b1 = chess.Board()
    b1.push_san("e4")
    b1.push_san("d5")
    # Move is exd5
    m = chess.Move.from_uci("e4d5")
    b2 = b1.copy()
    b2.push(m)

    anim = detect_move_animation(b1, b2, last_move=m, start_time_us=2000)
    assert anim is not None
    assert anim.piece_symbol == "wP"
    assert anim.from_square == chess.E4
    assert anim.to_square == chess.D5
    assert anim.captured_piece_symbol == "bP"
    assert anim.captured_square == chess.D5


def test_detect_forward_kingside_castling():
    b1 = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    m = chess.Move.from_uci("e1g1")
    b2 = b1.copy()
    b2.push(m)

    anim = detect_move_animation(b1, b2, last_move=m, start_time_us=3000)
    assert anim is not None
    # Primary: White King e1 -> g1
    assert anim.piece_symbol == "wK"
    assert anim.from_square == chess.E1
    assert anim.to_square == chess.G1
    # Secondary: White Rook h1 -> f1
    assert anim.secondary_piece_symbol == "wR"
    assert anim.secondary_from_square == chess.H1
    assert anim.secondary_to_square == chess.F1
    assert anim.secondary_target_square == chess.F1


def test_detect_forward_queenside_castling():
    b1 = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    m = chess.Move.from_uci("e1c1")
    b2 = b1.copy()
    b2.push(m)

    anim = detect_move_animation(b1, b2, last_move=m, start_time_us=4000)
    assert anim is not None
    # Primary: White King e1 -> c1
    assert anim.piece_symbol == "wK"
    assert anim.from_square == chess.E1
    assert anim.to_square == chess.C1
    # Secondary: White Rook a1 -> d1
    assert anim.secondary_piece_symbol == "wR"
    assert anim.secondary_from_square == chess.A1
    assert anim.secondary_to_square == chess.D1


def test_detect_forward_en_passant():
    b1 = chess.Board("8/8/8/3Pp3/8/8/8/k6K w - e6 0 2")
    m = chess.Move.from_uci("d5e6")
    b2 = b1.copy()
    b2.push(m)

    anim = detect_move_animation(b1, b2, last_move=m, start_time_us=5000)
    assert anim is not None
    assert anim.piece_symbol == "wP"
    assert anim.from_square == chess.D5
    assert anim.to_square == chess.E6
    assert anim.captured_piece_symbol == "bP"
    assert anim.captured_square == chess.E5


def test_detect_backward_move():
    b_before = chess.Board()
    m = chess.Move.from_uci("e2e4")
    b_after = b_before.copy()
    b_after.push(m)

    # Stepping backward from b_after to b_before
    anim = detect_move_animation(old_board=b_after, new_board=b_before, last_move=None, start_time_us=6000)
    assert anim is not None
    assert anim.is_reverse is True
    assert anim.piece_symbol == "wP"
    # Moving backwards: from e4 back to e2
    assert anim.from_square == chess.E4
    assert anim.to_square == chess.E2
    assert anim.target_square == chess.E2


def test_detect_backward_castling():
    b_before = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    m = chess.Move.from_uci("e1g1")
    b_after = b_before.copy()
    b_after.push(m)

    # Stepping backward from b_after to b_before
    anim = detect_move_animation(old_board=b_after, new_board=b_before, last_move=None, start_time_us=7000)
    assert anim is not None
    assert anim.is_reverse is True
    # King returns g1 -> e1
    assert anim.from_square == chess.G1
    assert anim.to_square == chess.E1
    # Rook returns f1 -> h1
    assert anim.secondary_piece_symbol == "wR"
    assert anim.secondary_from_square == chess.F1
    assert anim.secondary_to_square == chess.H1


def test_detect_multi_ply_jump_returns_none():
    b1 = chess.Board()
    b2 = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2")

    # Jumps multiple plies without single-move transition
    anim = detect_move_animation(b1, b2, last_move=None, start_time_us=8000)
    assert anim is None


def test_chessboardview_animation_integration():
    bv = ChessBoardView()
    assert bv.animations_enabled is True
    assert bv.animation_duration_ms == 150
    assert bv.active_animation is None

    # Flip board cancels active animation if any
    bv.flip()
    assert bv.active_animation is None
