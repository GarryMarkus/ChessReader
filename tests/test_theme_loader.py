"""
Unit tests for theme loader and user directory scanning.
"""

import os
import tempfile
import pytest

from chess_reader.theme.loader import ThemeManager


def test_theme_manager_loads_builtins():
    manager = ThemeManager(user_themes_dir="/tmp/non_existent_user_dir_123")
    themes = manager.list_themes()
    assert len(themes) >= 2
    ids = [t.id for t in themes]
    assert "zed-dark" in ids
    assert "classic-wood" in ids
    assert manager.active_theme.id == "zed-dark"


def test_theme_manager_user_theme_discovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock user theme in a subdirectory
        user_theme_dir = os.path.join(tmpdir, "emerald")
        os.makedirs(user_theme_dir, exist_ok=True)
        theme_yaml = os.path.join(user_theme_dir, "theme.yaml")
        with open(theme_yaml, "w") as f:
            f.write("""
            id: "emerald-city"
            name: "Emerald City"
            author: "Dorothy"
            board:
              type: "solid"
              light_square: "#a3e635"
              dark_square: "#15803d"
            pieces:
              wP: "wP.png"
              wN: "wN.png"
              wB: "wB.png"
              wR: "wR.png"
              wQ: "wQ.png"
              wK: "wK.png"
              bP: "bP.png"
              bN: "bN.png"
              bB: "bB.png"
              bR: "bR.png"
              bQ: "bQ.png"
              bK: "bK.png"
            """)

        manager = ThemeManager(user_themes_dir=tmpdir)
        theme_ids = [t.id for t in manager.list_themes()]
        assert "emerald-city" in theme_ids

        # Test switching theme
        assert manager.set_active_theme("emerald-city") is True
        assert manager.active_theme.id == "emerald-city"
        assert manager.active_theme.board.light_square == "#a3e635"


def test_theme_manager_listener_notification():
    manager = ThemeManager(user_themes_dir="/tmp/non_existent_123")
    changed_themes = []

    def on_change(new_theme):
        changed_themes.append(new_theme.id)

    manager.add_theme_listener(on_change)
    assert manager.set_active_theme("classic-wood") is True
    assert len(changed_themes) == 1
    assert changed_themes[0] == "classic-wood"

    # Switching to unknown theme returns False and does not trigger listener
    assert manager.set_active_theme("non-existent-theme-xyz") is False
    assert len(changed_themes) == 1


def test_theme_manager_handles_corrupt_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupt_file = os.path.join(tmpdir, "corrupt.yaml")
        with open(corrupt_file, "w") as f:
            f.write(":: this is not valid yaml or schema ::")

        manager = ThemeManager(user_themes_dir=tmpdir)
        # Built-in themes must still be intact
        assert manager.active_theme.id == "zed-dark"
