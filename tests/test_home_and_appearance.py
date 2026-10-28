"""
Unit tests for HomeView and AppearanceDialog UI components.
"""

import os
import shutil
import tempfile
import pytest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from chess_reader.core.library_store import LibraryStore
from chess_reader.theme.loader import ThemeManager
from chess_reader.ui.home.home_view import HomeView
from chess_reader.ui.modals.appearance_dialog import AppearanceDialog
from chess_reader.ui.window import ChessReaderWindow


def test_home_view_instantiation_and_navigation():
    temp_dir = tempfile.mkdtemp()
    try:
        store = LibraryStore(config_dir=temp_dir)
        store.add_folder_shortcut(temp_dir, name="Temp Folder")

        loaded_games = []
        switched = []

        view = HomeView(
            library_store=store,
            on_load_game=lambda game, path: loaded_games.append(game),
            on_switch_to_board=lambda: switched.append(True)
        )

        assert view.has_css_class("zed-home-view")
        # ChessBase navigation defaults to 'all' databases
        assert view.active_folder_path == "all"

        # Selecting a specific folder updates active_folder_path
        view._select_folder(temp_dir)
        assert view.active_folder_path == os.path.abspath(temp_dir)

        # Trigger switch to board
        view._navigate_to_board()
        assert len(switched) == 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_appearance_dialog_instantiation():
    temp_dir = tempfile.mkdtemp()
    try:
        app = Adw.Application(application_id="io.github.antigravity.ChessReader.AppearanceTest")
        win = ChessReaderWindow(application=app)
        dialog = AppearanceDialog(parent_window=win, theme_manager=win.theme_manager)

        assert dialog.has_css_class("zed-modal-window")
        assert dialog.piece_manager is not None

        # Verify switching piece set updates theme manager
        dialog._select_piece_set("neo")
        assert win.theme_manager.active_piece_set_id == "neo"

        # Reset to default
        dialog._select_piece_set("")
        assert win.theme_manager.active_piece_set_id is None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_window_stack_view_toggle():
    app = Adw.Application(application_id="io.github.antigravity.ChessReader.StackTest")
    win = ChessReaderWindow(application=app)

    # Initial view on startup is the Home / Directory page
    assert win.main_stack.get_visible_child_name() == "home"
    assert win.titlebar.db_tab_btn.has_css_class("nav-tab-active")
    assert not win.titlebar.board_tab_btn.has_css_class("nav-tab-active")

    # Switch to board
    win.show_board_view()
    assert win.main_stack.get_visible_child_name() == "board"
    assert win.titlebar.board_tab_btn.has_css_class("nav-tab-active")
    assert not win.titlebar.db_tab_btn.has_css_class("nav-tab-active")

    # Switch back to home
    win.show_home_view()
    assert win.main_stack.get_visible_child_name() == "home"
    assert win.titlebar.db_tab_btn.has_css_class("nav-tab-active")
    assert not win.titlebar.board_tab_btn.has_css_class("nav-tab-active")

    # Switch back to board via tab button
    win.titlebar.board_tab_btn.emit("clicked")
    assert win.main_stack.get_visible_child_name() == "board"
    assert win.titlebar.board_tab_btn.has_css_class("nav-tab-active")
    assert "Library" in win.titlebar.view_btn.get_label()


def test_home_view_double_click_database_opens_board():
    temp_dir = tempfile.mkdtemp()
    try:
        store = LibraryStore(config_dir=temp_dir)
        pgn_path = os.path.join(temp_dir, "test.pgn")
        with open(pgn_path, "w") as f:
            f.write('[Event "Test Game"]\n[White "Carlsen"]\n[Black "Nakamura"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n')

        store.add_recent_file(pgn_path)
        loaded_games = []
        switched = []

        view = HomeView(
            library_store=store,
            on_load_game=lambda game, path: (loaded_games.append(game), switched.append(True)),
            on_switch_to_board=lambda: switched.append(True)
        )

        view._open_and_load_database(pgn_path)
        assert len(loaded_games) == 1
        assert len(switched) >= 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
