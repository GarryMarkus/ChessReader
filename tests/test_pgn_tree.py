"""
Unit tests for PGN tree parsing, RAV sub-variations, branch promotion, and annotations.
"""

import pytest
import chess
from chess_reader.core.game_model import GameModel
from chess_reader.core.annotations import parse_comment_metadata, format_comment_with_metadata, NAG_TO_SYMBOL


SAMPLE_PGN = """[Event "World Championship 2026"]
[Site "London"]
[Date "2026.11.01"]
[Round "1"]
[White "Carlsen, Magnus"]
[Black "Caruana, Fabiano"]
[Result "1-0"]

1. e4 e5 ( 1... c5 2. Nf3 d6 {Sicilian defense} 3. d4 cxd4 ) 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 1-0
"""


def test_pgn_parsing_with_variations():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    assert model.game.headers["White"] == "Carlsen, Magnus"
    assert model.game.headers["Black"] == "Caruana, Fabiano"
    assert model.game.headers["Result"] == "1-0"

    breadcrumbs = model.get_breadcrumb_title()
    assert breadcrumbs[0] == "World Championship 2026"
    assert breadcrumbs[1] == "Round 1"
    assert "Carlsen, Magnus vs. Caruana, Fabiano (1-0)" in breadcrumbs[2]

    # Navigate to 1. e4
    assert model.next_move() is True
    assert model.current_node.san() == "e4"

    # Variations at move 1: 1... e5 (mainline) and 1... c5 (sub-variation)
    assert len(model.current_node.variations) == 2
    assert model.current_node.variations[0].san() == "e5"
    assert model.current_node.variations[1].san() == "c5"


def test_branch_promotion():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    model.next_move()  # 1. e4
    e4_node = model.current_node

    c5_node = e4_node.variations[1]
    assert c5_node.san() == "c5"

    # Promote 1... c5 to mainline
    assert model.promote_variation(c5_node) is True
    # Now index 0 is c5
    assert e4_node.variations[0].san() == "c5"
    assert e4_node.variations[1].san() == "e5"

    # Promoting again returns False because it is already mainline
    assert model.promote_variation(c5_node) is False


def test_branch_deletion():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    model.next_move()  # 1. e4
    e4_node = model.current_node
    c5_node = e4_node.variations[1]

    # Step into c5 variation
    model.go_to_node(c5_node)
    assert model.current_node.san() == "c5"

    # Delete c5 variation -> model must retreat to e4_node
    assert model.delete_variation(c5_node) is True
    assert len(e4_node.variations) == 1
    assert e4_node.variations[0].san() == "e5"
    assert model.current_node == e4_node


def test_multi_game_database_loading():
    multi_pgn = """
    [Event "Game 1"]
    [Result "1-0"]
    1. e4 e5 1-0

    [Event "Game 2"]
    [Result "0-1"]
    1. d4 d5 0-1

    [Event "Game 3"]
    [Result "1/2-1/2"]
    1. c4 c5 1/2-1/2
    """
    games = GameModel.load_database(multi_pgn)
    assert len(games) == 3
    assert games[0].game.headers["Event"] == "Game 1"
    assert games[1].game.headers["Event"] == "Game 2"
    assert games[2].game.headers["Event"] == "Game 3"


def test_nag_and_comment_annotations():
    model = GameModel()
    # 1. e4!
    e4_move = chess.Move.from_uci("e2e4")
    node = model.add_move(e4_move)
    model.add_nag(node, 1)  # !
    model.add_nag(node, 14) # ⩲

    nags = model.get_nags_display(node)
    assert "!" in nags
    assert "⩲" in nags

    # Comment with clock and eval
    model.set_comment(node, "Novelty idea")
    model.set_clock(node, "1:30:00")
    model.set_evaluation(node, "+0.35")

    clk, ev, clean = parse_comment_metadata(node.comment)
    assert clk == "1:30:00"
    assert ev == "+0.35"
    assert clean == "Novelty idea"


def test_tree_navigation_controls():
    model = GameModel.from_pgn_text("1. e4 e5 2. Nf3 Nc6 3. Bb5")
    assert model.is_root is True

    model.go_to_end()
    assert model.current_node.san() == "Bb5"
    assert model.has_next is False
    assert model.has_prev is True

    model.prev_move()
    assert model.current_node.san() == "Nc6"

    model.go_to_root()
    assert model.is_root is True
    assert model.has_prev is False
