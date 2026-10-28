"""
Unit tests for ChapterNavBar and in-board multi-game switching.
"""

import os
import tempfile
import shutil
import pytest
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw
import chess.pgn

from chess_reader.ui.notation.chapter_nav_bar import ChapterNavBar
from chess_reader.ui.window import ChessReaderWindow


def test_chapter_nav_bar_logic():
    nav_calls = []
    nav = ChapterNavBar(
        on_prev_game=lambda: nav_calls.append("prev"),
        on_next_game=lambda: nav_calls.append("next"),
        on_select_game=lambda idx: nav_calls.append(f"select_{idx}")
    )

    # Initial state
    assert nav.btn_prev.get_sensitive() is False
    assert nav.btn_next.get_sensitive() is False

    # Simulate multi-game update (3 games, current index = 0)
    mock_games = [
        {"index": 0, "white": "Carlsen", "black": "Nakamura", "event": "WCh", "result": "1-0"},
        {"index": 1, "white": "Kasparov", "black": "Karpov", "event": "WCh", "result": "1/2-1/2"},
        {"index": 2, "white": "Fischer", "black": "Spassky", "event": "WCh", "result": "1-0"},
    ]
    nav.update_game_info(current_index=0, total_games=3, games_list=mock_games)

    assert nav.btn_prev.get_sensitive() is False
    assert nav.btn_next.get_sensitive() is True
    assert nav.badge_lbl.get_text() == "1/3"
    assert "Carlsen vs. Nakamura" in nav.title_lbl.get_text()

    # Move to game 1 (middle)
    nav.update_game_info(current_index=1, total_games=3, games_list=mock_games)
    assert nav.btn_prev.get_sensitive() is True
    assert nav.btn_next.get_sensitive() is True
    assert nav.badge_lbl.get_text() == "2/3"

    # Move to game 2 (last)
    nav.update_game_info(current_index=2, total_games=3, games_list=mock_games)
    assert nav.btn_prev.get_sensitive() is True
    assert nav.btn_next.get_sensitive() is False
    assert nav.badge_lbl.get_text() == "3/3"

    # Button triggers
    nav.btn_prev.emit("clicked")
    assert "prev" in nav_calls

    nav.btn_next.emit("clicked")
    assert "next" in nav_calls


def test_window_chapter_switching_without_returning_to_library():
    temp_dir = tempfile.mkdtemp()
    try:
        pgn_path = os.path.join(temp_dir, "chapters.pgn")
        with open(pgn_path, "w") as f:
            f.write(
                '[Event "Chapter 1"]\n[White "P1"]\n[Black "P2"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n'
                '[Event "Chapter 2"]\n[White "P3"]\n[Black "P4"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n\n'
                '[Event "Chapter 3"]\n[White "P5"]\n[Black "P6"]\n[Result "1/2-1/2"]\n\n1. c4 c5 1/2-1/2\n'
            )

        app = Adw.Application(application_id="io.github.antigravity.ChessReader.ChapterTest")
        win = ChessReaderWindow(application=app)

        # Load game 0
        game0 = win.library_store.load_game_from_pgn(pgn_path, 0)
        win._on_library_game_loaded(game0, pgn_path, 0)

        assert win.main_stack.get_visible_child_name() == "board"
        assert win.active_game_index == 0
        assert len(win.active_pgn_games) == 3
        assert win.chapter_nav_bar.badge_lbl.get_text() == "1/3"

        # Step next to Chapter 2
        win.load_next_game()
        assert win.active_game_index == 1
        assert win.chapter_nav_bar.badge_lbl.get_text() == "2/3"

        # Step next to Chapter 3 via keyboard shortcut ']'
        handled = win._on_window_key_pressed(None, Gdk.KEY_bracketright, 0, Gdk.ModifierType(0))
        assert handled is True
        assert win.active_game_index == 2
        assert win.chapter_nav_bar.badge_lbl.get_text() == "3/3"

        # Step prev back to Chapter 2 via keyboard shortcut '['
        handled = win._on_window_key_pressed(None, Gdk.KEY_bracketleft, 0, Gdk.ModifierType(0))
        assert handled is True
        assert win.active_game_index == 1
        assert win.chapter_nav_bar.badge_lbl.get_text() == "2/3"

        # Direct selection of Chapter 1
        win.load_game_by_index(0)
        assert win.active_game_index == 0
        assert win.chapter_nav_bar.badge_lbl.get_text() == "1/3"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
