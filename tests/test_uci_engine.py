"""
Unit tests for UCI engine controller, multi-PV streaming, and batch game review.
"""

import time
import pytest
import chess
import chess.pgn

from chess_reader.engine.analyzer import AnalysisLine, AnalysisSnapshot, score_to_string, score_to_white_cp
from chess_reader.engine.uci_client import UCIEngineManager
from chess_reader.engine.game_review import BatchGameReviewer, MoveClassification


def test_analyzer_score_conversions():
    # CP score
    cp_score = chess.engine.PovScore(chess.engine.Cp(75), chess.WHITE)
    assert score_to_string(cp_score) == "+0.75"
    assert score_to_white_cp(cp_score) == 75

    # Negative CP score
    neg_cp = chess.engine.PovScore(chess.engine.Cp(-120), chess.WHITE)
    assert score_to_string(neg_cp) == "-1.20"
    assert score_to_white_cp(neg_cp) == -120

    # Mate in 2
    mate_score = chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)
    assert score_to_string(mate_score) == "M2"
    assert score_to_white_cp(mate_score) > 9000

    # Mate against white (-M1)
    neg_mate = chess.engine.PovScore(chess.engine.Mate(-1), chess.WHITE)
    assert score_to_string(neg_mate) == "-M1"
    assert score_to_white_cp(neg_mate) < -9000


def test_uci_engine_discovery_and_analysis():
    manager = UCIEngineManager()
    assert manager.is_available() is True
    assert manager.start() is True

    board = chess.Board()
    received_snapshots = []

    def on_update(snapshot):
        received_snapshots.append(snapshot)

    # Analyze starting position to depth 6
    manager.analyze_position(board, multipv=2, max_depth=6, on_update=on_update)

    # Wait briefly for thread to stream info pumping GLib context
    import gi
    gi.require_version('GLib', '2.0')
    from gi.repository import GLib

    context = GLib.MainContext.default()
    timeout = 3.0
    start = time.time()
    while not received_snapshots and (time.time() - start) < timeout:
        context.iteration(False)
        time.sleep(0.05)

    manager.close()
    assert len(received_snapshots) > 0
    top = received_snapshots[-1].top_line
    assert top is not None
    assert top.depth > 0
    assert len(top.pv) > 0


def test_batch_game_review():
    manager = UCIEngineManager()
    reviewer = BatchGameReviewer(manager.engine_path)

    # 4-ply Scholar's Mate game: 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#
    game = chess.pgn.Game()
    node = game.add_variation(chess.Move.from_uci("e2e4"))
    node = node.add_variation(chess.Move.from_uci("e7e5"))
    node = node.add_variation(chess.Move.from_uci("d1h5"))
    node = node.add_variation(chess.Move.from_uci("b8c6"))

    result = reviewer.review_game(game, depth=6)
    assert result.white_accuracy >= 50.0
    assert result.black_accuracy >= 50.0
    assert len(result.reviews) == 4
    assert len(result.cpl_curve) == 5  # Initial + 4 moves
    assert result.reviews[0].san == "e4"
