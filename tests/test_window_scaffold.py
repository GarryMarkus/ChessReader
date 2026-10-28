"""
Unit tests for application window scaffolding, CSS loading, and layout.
"""

import os
import pytest
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from chess_reader.ui.window import ChessReaderWindow, ZedTitlebar, StatusBar
from chess_reader.main import ChessReaderApp


def test_package_metadata():
    import chess_reader
    assert chess_reader.__version__ == "0.1.0"


def test_css_stylesheet_exists():
    css_path = os.path.join(os.path.dirname(__file__), "..", "chess_reader", "style.css")
    assert os.path.exists(css_path)
    with open(css_path, "r") as f:
        content = f.read()
    assert "@define-color zed_bg_base" in content
    assert "headerbar.zed-titlebar" in content
    assert "zed-status-bar" in content


def test_titlebar_breadcrumbs():
    titlebar = ZedTitlebar()
    assert titlebar.has_css_class("zed-titlebar-container")
    assert titlebar.header.has_css_class("zed-titlebar")
    assert titlebar.header.get_show_title() is False

    # Test updating breadcrumbs
    titlebar.set_breadcrumb(["Category", "Group", "Player 1 vs Player 2"])
    children = []
    child = titlebar.breadcrumb_box.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()

    # 3 labels + 2 separators = 5 widgets
    assert len(children) == 5
    assert isinstance(children[0], Gtk.Label)
    assert children[0].get_text() == "Category"
    assert children[1].get_text() == "/"
    assert children[4].get_text() == "Player 1 vs Player 2"


def test_status_bar_components():
    status_bar = StatusBar()
    assert status_bar.has_css_class("zed-status-bar")
    assert "Stockfish" in status_bar.engine_label.get_text()
    assert "rnbqkbnr" in status_bar.fen_btn.get_label()
    assert "zed-dark" in status_bar.theme_label.get_text()


def test_window_layout_instantiation():
    app = Adw.Application(application_id="io.github.antigravity.ChessReader.Test")
    win = ChessReaderWindow(application=app)
    assert win.has_css_class("chess-reader-window")
    assert win.titlebar is not None
    assert win.workspace is not None
    assert win.status_bar is not None
    assert win.workspace.get_start_child() == win.board_panel
    assert win.workspace.get_end_child() == win.notation_panel
