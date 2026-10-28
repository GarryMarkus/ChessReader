"""
Unit tests for MoveTreeView UI, indentation of variations, and keyboard navigation.
"""

import pytest
import gi
import chess

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

from chess_reader.core.game_model import GameModel
from chess_reader.ui.notation.move_tree_view import MoveTreeView


SAMPLE_PGN = """[Event "Grand Prix 2026"]
[White "Player A"]
[Black "Player B"]
[Result "*"]

1. e4 e5 ( 1... c5 2. Nf3 d6 ) 2. Nf3 Nc6 *
"""


def test_move_tree_initialization_and_rebuild():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    tree_view = MoveTreeView(game_model=model)

    assert tree_view.tree_container is not None
    assert len(tree_view._node_widgets) >= 5

    # Initially at root (no active move token)
    assert model.is_root is True

    # Advance to 1. e4
    model.next_move(0)
    assert model.current_node.san() == "e4"

    # Verify active move widget has .active-move class
    active_widget = tree_view._node_widgets.get(model.current_node)
    assert active_widget is not None
    assert active_widget.has_css_class("active-move")


def test_keyboard_navigation_keys():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    tree_view = MoveTreeView(game_model=model)

    # Simulate Right Arrow -> steps forward to 1. e4
    handled = tree_view._on_key_pressed(None, Gdk.KEY_Right, 0, 0)
    assert handled is True
    assert model.current_node.san() == "e4"

    # Simulate Right Arrow again -> steps forward to 1... e5 (mainline)
    handled = tree_view._on_key_pressed(None, Gdk.KEY_Right, 0, 0)
    assert handled is True
    assert model.current_node.san() == "e5"

    # Simulate Left Arrow -> steps back to 1. e4
    handled = tree_view._on_key_pressed(None, Gdk.KEY_Left, 0, 0)
    assert handled is True
    assert model.current_node.san() == "e4"

    # Simulate End -> jumps to end of mainline (Nc6)
    handled = tree_view._on_key_pressed(None, Gdk.KEY_End, 0, 0)
    assert handled is True
    assert model.current_node.san() == "Nc6"

    # Simulate Home -> jumps back to root
    handled = tree_view._on_key_pressed(None, Gdk.KEY_Home, 0, 0)
    assert handled is True
    assert model.is_root is True


def test_toolbar_button_actions():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    tree_view = MoveTreeView(game_model=model)

    # Click Next button
    tree_view.btn_next.emit("clicked")
    assert model.current_node.san() == "e4"

    # Click Next button again
    tree_view.btn_next.emit("clicked")
    assert model.current_node.san() == "e5"

    # Click Prev button
    tree_view.btn_prev.emit("clicked")
    assert model.current_node.san() == "e4"

    # Click Last button
    tree_view.btn_last.emit("clicked")
    assert model.current_node.san() == "Nc6"

    # Click First button
    tree_view.btn_first.emit("clicked")
    assert model.is_root is True


def test_promote_and_delete_buttons():
    model = GameModel.from_pgn_text(SAMPLE_PGN)
    tree_view = MoveTreeView(game_model=model)

    # Navigate to 1. e4, then select c5 variation
    model.next_move(0)
    c5_node = model.current_node.variations[1]
    model.go_to_node(c5_node)
    assert model.current_node.san() == "c5"

    # Click promote button
    tree_view.btn_promote.emit("clicked")
    # Now c5 is mainline
    assert model.current_node.parent.variations[0].san() == "c5"

    # Click delete button on c5 branch
    tree_view.btn_delete.emit("clicked")
    # c5 deleted, retreated to e4
    assert model.current_node.san() == "e4"
