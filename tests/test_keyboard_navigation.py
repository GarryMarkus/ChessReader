"""
Unit tests for window-level keyboard navigation and shortcuts.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw
import chess

from chess_reader.ui.window import ChessReaderWindow


def test_board_arrow_key_navigation():
    app = Adw.Application(application_id="io.github.antigravity.ChessReader.KeyNavTest")
    win = ChessReaderWindow(application=app)
    win.show_board_view()

    # Play e2e4 and e7e5 on the game model
    win.game_model.add_move(chess.Move.from_uci("e2e4"))
    win.game_model.add_move(chess.Move.from_uci("e7e5"))
    assert not win.game_model.has_next
    assert win.game_model.has_prev

    # Simulate Left Arrow -> prev_move
    handled = win._on_window_key_pressed(None, Gdk.KEY_Left, 0, Gdk.ModifierType(0))
    assert handled is True
    assert win.game_model.has_next  # Stepped back to after 1. e4

    # Simulate Up Arrow -> go_to_root
    handled = win._on_window_key_pressed(None, Gdk.KEY_Up, 0, Gdk.ModifierType(0))
    assert handled is True
    assert not win.game_model.has_prev  # At starting position

    # Simulate Down Arrow -> go_to_end
    handled = win._on_window_key_pressed(None, Gdk.KEY_Down, 0, Gdk.ModifierType(0))
    assert handled is True
    assert not win.game_model.has_next  # At end after 1... e5

    # Simulate F -> Flip board and eval bar
    initial_flip = win.board_view.flipped
    handled = win._on_window_key_pressed(None, Gdk.KEY_f, 0, Gdk.ModifierType(0))
    assert handled is True
    assert win.board_view.flipped != initial_flip
    assert win.eval_bar.flipped == win.board_view.flipped

    # Simulate Spacebar -> Toggle engine
    initial_engine_state = win.engine_enabled
    handled = win._on_window_key_pressed(None, Gdk.KEY_space, 0, Gdk.ModifierType(0))
    assert handled is True
    assert win.engine_enabled != initial_engine_state
