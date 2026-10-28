"""
Unit tests for PlayerCard, Material Advantage Calculation, and Clock Extraction.
"""

import pytest
import chess
import chess.pgn
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from chess_reader.ui.board.player_card import (
    PlayerCard,
    compute_material_and_captures,
    extract_player_clocks,
)


def test_material_calculation_starting_position():
    board = chess.Board()
    res = compute_material_and_captures(board)

    assert res["white_score"] == 39
    assert res["black_score"] == 39
    assert res["white_diff"] == 0
    assert res["black_diff"] == 0
    assert res["white_captured"] == []
    assert res["black_captured"] == []


def test_material_calculation_after_captures():
    # Board after 1. e4 d5 2. exd5 (White took black pawn)
    board = chess.Board()
    board.push_san("e4")
    board.push_san("d5")
    board.push_san("exd5")

    res = compute_material_and_captures(board)
    assert res["white_score"] == 39
    assert res["black_score"] == 38
    assert res["white_diff"] == 1
    assert res["black_diff"] == 0
    assert res["white_captured"] == ["♟"]
    assert res["black_captured"] == []


def test_material_calculation_heavy_captures():
    # White lost queen, bishop, and knight; Black lost bishop
    board = chess.Board("rnbqk1nr/pppppppp/8/8/8/8/PPPPPPPP/RNB1K2R w KQkq - 0 1")
    # White has: 8P, 1N, 1B, 2R, 1K (missing Q, B, N) -> 8 + 3 + 3 + 10 = 24
    # Black has: 8P, 2N, 1B, 2R, 1Q, 1K (missing B) -> 8 + 6 + 3 + 10 + 9 = 36
    res = compute_material_and_captures(board)
    assert res["white_score"] == 24
    assert res["black_score"] == 36
    assert res["white_diff"] == 0
    assert res["black_diff"] == 12
    assert res["white_captured"] == ["♝"]
    assert res["black_captured"] == ["♕", "♗", "♘"]


def test_extract_player_clocks():
    # Build PGN node tree with clock tags
    game = chess.pgn.Game()
    node1 = game.add_variation(chess.Move.from_uci("e2e4"))
    node1.comment = "[%clk 1:29:45]"
    node2 = node1.add_variation(chess.Move.from_uci("e7e5"))
    node2.comment = "[%clk 1:29:30] Best move"

    w_clk, b_clk = extract_player_clocks(node2)
    assert w_clk == "1:29:45"
    assert b_clk == "1:29:30"


def test_player_card_widget_state():
    card = PlayerCard(color=chess.WHITE)

    # Initially default
    assert card.name_label.get_text() == "White"
    assert card.title_badge.get_visible() is False
    assert card.elo_badge.get_visible() is False

    # Update with full player profile and material advantage
    card.update_player(
        color=chess.WHITE,
        name="Carlsen, Magnus",
        elo="2882",
        title="GM",
        clock="0:15:32",
        captured_pieces=["♟", "♞"],
        material_diff=4,
        is_active_turn=True
    )

    assert card.name_label.get_text() == "Carlsen, Magnus"
    assert card.title_badge.get_text() == "GM"
    assert card.title_badge.get_visible() is True
    assert card.elo_badge.get_text() == "2882"
    assert card.elo_badge.get_visible() is True
    assert card.clock_badge.get_text() == "⏱ 0:15:32"
    assert card.clock_badge.get_visible() is True
    assert card.diff_badge.get_text() == "+4"
    assert card.diff_badge.get_visible() is True
    assert card.captured_label.get_text() == "♟ ♞"
    assert card.has_css_class("player-card-active") is True

    # Switch turn to inactive
    card.update_player(
        color=chess.WHITE,
        name="Carlsen, Magnus",
        is_active_turn=False
    )
    assert card.has_css_class("player-card-active") is False
