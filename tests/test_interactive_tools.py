"""
Unit tests for CommandPalette and FENSetupDialog.
"""

import pytest
import chess
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from chess_reader.ui.palette.command_palette import CommandPalette, CommandItem
from chess_reader.ui.modals.fen_dialog import FENSetupDialog


def test_command_item_matching():
    executed = []
    item = CommandItem(
        id="test_flip",
        title="Flip Board Perspective",
        category="Board",
        shortcut="F",
        action=lambda: executed.append("flip")
    )

    # Exact match
    assert item.match_score("flip board perspective") == 1.0

    # Prefix match
    assert item.match_score("flip") == 0.9

    # Substring in title
    assert item.match_score("perspective") == 0.7

    # Substring in category (where word is not in title)
    item_engine = CommandItem(id="2", title="Toggle Analysis", category="Engine", action=lambda: None)
    assert item_engine.match_score("engine") == 0.5

    # Fuzzy match
    assert item.match_score("fbp") == 0.3

    # No match
    assert item.match_score("xyz123") == 0.0

    # Execute action
    item.action()
    assert executed == ["flip"]


def test_command_palette_filtering():
    executed = []
    cmds = [
        CommandItem(id="1", title="Flip Board", category="Board", action=lambda: executed.append(1)),
        CommandItem(id="2", title="Reset Board", category="Board", action=lambda: executed.append(2)),
        CommandItem(id="3", title="Switch Theme", category="Theme", action=lambda: executed.append(3)),
    ]

    win = Gtk.Window()
    palette = CommandPalette(parent_window=win, commands=cmds)
    assert len(palette.filtered_commands) == 3

    # Filter with "reset"
    palette.search_entry.set_text("reset")
    palette._on_search_changed(palette.search_entry)
    assert len(palette.filtered_commands) == 1
    assert palette.filtered_commands[0].title == "Reset Board"


def test_fen_dialog_validation_and_load():
    loaded_fens = []

    def on_load(fen):
        loaded_fens.append(fen)

    win = Gtk.Window()
    dialog = FENSetupDialog(
        parent_window=win,
        current_fen=chess.STARTING_FEN,
        on_fen_loaded=on_load
    )

    # Initial standard FEN must be valid
    assert dialog._validate_fen(chess.STARTING_FEN) is True
    assert dialog.btn_load.get_sensitive() is True

    # Invalid FEN syntax
    assert dialog._validate_fen("not a valid fen string") is False
    assert dialog.btn_load.get_sensitive() is False

    # Valid custom FEN (e.g. Sicilian)
    sicilian_fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"
    assert dialog._validate_fen(sicilian_fen) is True
    assert dialog.btn_load.get_sensitive() is True

    # Test load execution
    dialog.entry.set_text(sicilian_fen)
    dialog._on_load_clicked(None)
    assert len(loaded_fens) == 1
    assert loaded_fens[0] == sicilian_fen
