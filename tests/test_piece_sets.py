"""
Unit tests for PieceSetManager, custom piece imports, and piece set selection.
"""

import os
import shutil
import tempfile
import pytest

from chess_reader.theme.piece_sets import PieceSetManager
from chess_reader.theme.loader import ThemeManager
from chess_reader.theme.fallback import AssetResolver


def test_piece_set_discovery():
    mgr = PieceSetManager(user_pieces_dir="/tmp/non_existent_pieces_test", config_dir="/tmp/test_cfg_123")
    piece_sets = mgr.list_piece_sets()
    set_ids = [ps.id for ps in piece_sets]

    # Must find built-in piece sets: neo, standard, cburnett
    assert "neo" in set_ids
    assert "standard" in set_ids
    assert "cburnett" in set_ids

    neo = mgr.get_piece_set("neo")
    assert neo is not None
    assert neo.format == "png"
    assert neo.get_piece_path("wK") is not None
    assert os.path.exists(neo.get_piece_path("wK"))


def test_piece_set_selection_and_persistence():
    temp_cfg = tempfile.mkdtemp()
    try:
        mgr = PieceSetManager(user_pieces_dir="/tmp/empty_pieces_dir", config_dir=temp_cfg)
        assert mgr.active_piece_set is None

        # Select neo
        assert mgr.set_active_piece_set("neo") is True
        assert mgr.active_piece_set is not None
        assert mgr.active_piece_set.id == "neo"

        # Verify persisted to preferences.json
        mgr2 = PieceSetManager(user_pieces_dir="/tmp/empty_pieces_dir", config_dir=temp_cfg)
        assert mgr2.active_piece_set is not None
        assert mgr2.active_piece_set.id == "neo"

        # Reset to theme default (None)
        mgr2.set_active_piece_set(None)
        assert mgr2.active_piece_set is None
    finally:
        shutil.rmtree(temp_cfg, ignore_errors=True)


def test_piece_set_custom_import():
    temp_cfg = tempfile.mkdtemp()
    temp_user_pieces = os.path.join(temp_cfg, "pieces")
    temp_src = tempfile.mkdtemp()

    try:
        # Create a mock piece set folder with PNG pieces
        for sym in PieceSetManager.PIECE_SYMBOLS:
            with open(os.path.join(temp_src, f"{sym}.png"), "w") as f:
                f.write("mock png data")

        mgr = PieceSetManager(user_pieces_dir=temp_user_pieces, config_dir=temp_cfg)
        imported = mgr.import_piece_set_folder(temp_src, custom_name="custom-wood")

        assert imported is not None
        assert imported.id == "custom-wood"
        assert imported.is_builtin is False
        assert os.path.exists(imported.get_piece_path("wK"))
    finally:
        shutil.rmtree(temp_cfg, ignore_errors=True)
        shutil.rmtree(temp_src, ignore_errors=True)


def test_asset_resolver_with_piece_set_override():
    theme_mgr = ThemeManager(user_themes_dir="/tmp/non_existent_theme_dir")
    theme = theme_mgr.active_theme
    piece_mgr = theme_mgr.piece_set_manager

    neo_set = piece_mgr.get_piece_set("neo")
    assert neo_set is not None

    path_neo_wk = AssetResolver.resolve_piece_path(theme, "wK", piece_set=neo_set)
    assert "neo" in path_neo_wk
    assert os.path.exists(path_neo_wk)
