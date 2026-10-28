"""
Unit tests for LibraryStore: folder shortcuts, scanning, PGN creation, and game indexing.
"""

import os
import shutil
import tempfile
import pytest

from chess_reader.core.library_store import LibraryStore


def test_library_folder_shortcuts():
    temp_dir = tempfile.mkdtemp()
    temp_folder1 = os.path.join(temp_dir, "Tournaments")
    os.makedirs(temp_folder1)

    try:
        store = LibraryStore(config_dir=temp_dir)
        # Add folder shortcut
        item = store.add_folder_shortcut(temp_folder1, name="My Tournaments")
        assert item is not None
        assert item["name"] == "My Tournaments"
        assert item["path"] == os.path.abspath(temp_folder1)

        # Check list
        shortcuts = store.get_folder_shortcuts()
        assert len(shortcuts) == 1
        assert shortcuts[0]["name"] == "My Tournaments"

        # Persistence check
        store2 = LibraryStore(config_dir=temp_dir)
        shortcuts2 = store2.get_folder_shortcuts()
        assert len(shortcuts2) == 1

        # Remove shortcut
        assert store.remove_folder_shortcut(temp_folder1) is True
        assert len(store.get_folder_shortcuts()) == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_create_new_pgn_and_game_indexing():
    temp_dir = tempfile.mkdtemp()
    pgn_path = os.path.join(temp_dir, "my_study.pgn")

    try:
        store = LibraryStore(config_dir=temp_dir)
        created_path = store.create_new_pgn_file(
            pgn_path,
            event="Candidates 2024",
            white="Gukesh D",
            black="Hikaru Nakamura"
        )
        assert os.path.isfile(created_path)

        # Scan folder
        found = store.scan_folder_for_pgns(temp_dir)
        assert len(found) == 1
        assert found[0]["name"] == "my_study.pgn"
        assert found[0]["game_count"] >= 1

        # List games in PGN
        games = store.list_games_in_pgn(created_path)
        assert len(games) == 1
        assert games[0]["white"] == "Gukesh D"
        assert games[0]["black"] == "Hikaru Nakamura"
        assert games[0]["event"] == "Candidates 2024"

        # Load game AST
        game_ast = store.load_game_from_pgn(created_path, 0)
        assert game_ast is not None
        assert game_ast.headers["White"] == "Gukesh D"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
