"""
Unit tests for theme schema validation and YAML parsing.
"""

import pytest
from pydantic import ValidationError
from chess_reader.theme.schema import ChessReaderTheme, BoardTheme, PiecesTheme


def test_valid_theme_yaml_parsing():
    yaml_data = """
    id: "test-theme"
    name: "Test Theme"
    author: "Grandmaster"
    version: "1.2.0"
    description: "A sleek test theme"
    board:
      type: "solid"
      light_square: "#f0d9b5"
      dark_square: "#b58863"
      border_color: "#333333"
      coordinates:
        show: true
        placement: "inside"
        font_family: "JetBrains Mono"
        font_size: 12
      highlights:
        selected_square: "rgba(0, 255, 0, 0.5)"
    pieces:
      wP: "pieces/wP.png"
      wN: "pieces/wN.png"
      wB: "pieces/wB.png"
      wR: "pieces/wR.png"
      wQ: "pieces/wQ.png"
      wK: "pieces/wK.png"
      bP: "pieces/bP.png"
      bN: "pieces/bN.png"
      bB: "pieces/bB.png"
      bR: "pieces/bR.png"
      bQ: "pieces/bQ.png"
      bK: "pieces/bK.png"
    """
    theme = ChessReaderTheme.from_yaml_string(yaml_data, base_dir="/tmp/theme")
    assert theme.id == "test-theme"
    assert theme.name == "Test Theme"
    assert theme.board.type == "solid"
    assert theme.board.light_square == "#f0d9b5"
    assert theme.pieces.get_piece_path("wK") == "pieces/wK.png"
    assert theme.resolve_asset_path("pieces/wK.png") == "/tmp/theme/pieces/wK.png"


def test_invalid_theme_id_regex():
    yaml_data = """
    id: "Invalid ID With Spaces!"
    name: "Test"
    board:
      type: "solid"
    pieces:
      wP: "p.png"
    """
    with pytest.raises(ValidationError):
        ChessReaderTheme.from_yaml_string(yaml_data)


def test_backdrop_board_missing_image_fails():
    yaml_data = """
    id: "backdrop-theme"
    name: "Backdrop Theme"
    board:
      type: "backdrop"
    pieces:
      wP: "p.png"
      wN: "n.png"
      wB: "b.png"
      wR: "r.png"
      wQ: "q.png"
      wK: "k.png"
      bP: "bp.png"
      bN: "bn.png"
      bB: "bb.png"
      bR: "br.png"
      bQ: "bq.png"
      bK: "bk.png"
    """
    with pytest.raises(ValidationError) as exc_info:
        ChessReaderTheme.from_yaml_string(yaml_data)
    assert "backdrop_image must be specified" in str(exc_info.value)
