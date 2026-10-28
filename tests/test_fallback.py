"""
Unit tests for theme asset resolution and fallback handling.
"""

import os
import pytest
from chess_reader.theme.schema import ChessReaderTheme
from chess_reader.theme.fallback import AssetResolver


def test_fallback_resolver_finds_standard_assets():
    for symbol in AssetResolver.PIECE_SYMBOLS:
        path = AssetResolver.resolve_piece_path(theme=None, symbol=symbol)
        assert os.path.exists(path)
        assert path.endswith(".png") or path.endswith(".svg")


def test_theme_with_missing_piece_falls_back():
    broken_yaml = """
    id: "broken-theme"
    name: "Broken Theme"
    board:
      type: "solid"
      light_square: "#ffffff"
      dark_square: "#000000"
    pieces:
      wP: "non_existent_path/fake_wP.png"
      wN: "non_existent_path/fake_wN.png"
      wB: "non_existent_path/fake_wB.png"
      wR: "non_existent_path/fake_wR.png"
      wQ: "non_existent_path/fake_wQ.png"
      wK: "non_existent_path/fake_wK.png"
      bP: "non_existent_path/fake_bP.png"
      bN: "non_existent_path/fake_bN.png"
      bB: "non_existent_path/fake_bB.png"
      bR: "non_existent_path/fake_bR.png"
      bQ: "non_existent_path/fake_bQ.png"
      bK: "non_existent_path/fake_bK.png"
    """
    theme = ChessReaderTheme.from_yaml_string(broken_yaml, base_dir="/tmp")
    # Must not raise FileNotFoundError, but gracefully fall back
    resolved = AssetResolver.resolve_piece_path(theme, "wK")
    assert os.path.exists(resolved)
    assert "standard" in resolved or "cburnett" in resolved


def test_builtin_themes_load_and_resolve():
    zed_theme_file = os.path.join(AssetResolver._PROJECT_ROOT, "themes", "zed-dark.yaml")
    assert os.path.exists(zed_theme_file)
    theme = ChessReaderTheme.from_yaml_file(zed_theme_file)
    assert theme.id == "zed-dark"

    # Verify that all 12 pieces resolve to real files
    for sym in AssetResolver.PIECE_SYMBOLS:
        p_path = AssetResolver.resolve_piece_path(theme, sym)
        assert os.path.exists(p_path)


def test_onthefly_svg_generation():
    svg = AssetResolver.get_piece_svg_content("wK")
    assert "<svg" in svg
    assert "</svg>" in svg
