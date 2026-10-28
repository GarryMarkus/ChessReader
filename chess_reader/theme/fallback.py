"""
Asset resolution pipeline and fallback engine for ChessReader themes.
Ensures that missing, corrupted, or incomplete theme files never crash board rendering.
"""

import os
from typing import Optional, Dict
import chess
import chess.svg

from chess_reader.theme.schema import ChessReaderTheme, PiecesTheme, BoardTheme


class AssetResolver:
    """Robust fallback resolver for piece assets and board textures."""

    # Built-in base asset directories
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    FALLBACK_PNG_DIR = os.path.join(_PROJECT_ROOT, "assets", "pieces", "standard")
    FALLBACK_SVG_DIR = os.path.join(_PROJECT_ROOT, "assets", "pieces", "cburnett")

    PIECE_SYMBOLS = ["wP", "wN", "wB", "wR", "wQ", "wK", "bP", "bN", "bB", "bR", "bQ", "bK"]

    DEFAULT_LIGHT_SQUARE = "#2d3139"
    DEFAULT_DARK_SQUARE = "#1e2227"

    @classmethod
    def resolve_piece_path(cls, theme: Optional[ChessReaderTheme], symbol: str) -> str:
        """
        Resolve the file path for a piece symbol with multi-stage fallback:
        1. Theme-specified path (resolved relative to theme file).
        2. Built-in standard PNG piece.
        3. Built-in cburnett SVG piece.
        """
        if symbol not in cls.PIECE_SYMBOLS:
            raise ValueError(f"Invalid piece symbol: {symbol}")

        # 1. Attempt theme resolution
        if theme and theme.pieces:
            specified_path = theme.pieces.get_piece_path(symbol)
            if specified_path:
                resolved = theme.resolve_asset_path(specified_path)
                if os.path.exists(resolved) and os.path.isfile(resolved):
                    return resolved

        # 2. Built-in standard PNG
        fallback_png = os.path.join(cls.FALLBACK_PNG_DIR, f"{symbol}.png")
        if os.path.exists(fallback_png):
            return fallback_png

        # 3. Built-in SVG
        fallback_svg = os.path.join(cls.FALLBACK_SVG_DIR, f"{symbol}.svg")
        if os.path.exists(fallback_svg):
            return fallback_svg

        raise FileNotFoundError(f"Critical asset failure: no fallback asset found for {symbol}")

    @classmethod
    def get_piece_svg_content(cls, symbol: str) -> str:
        """Generate vector SVG content on the fly using python-chess as ultimate guarantee."""
        piece_map = {
            'wP': 'P', 'wN': 'N', 'wB': 'B', 'wR': 'R', 'wQ': 'Q', 'wK': 'K',
            'bP': 'p', 'bN': 'n', 'bB': 'b', 'bR': 'r', 'bQ': 'q', 'bK': 'k'
        }
        fen_char = piece_map.get(symbol)
        if not fen_char:
            raise ValueError(f"Unknown symbol {symbol}")
        piece = chess.Piece.from_symbol(fen_char)
        return chess.svg.piece(piece)

    @classmethod
    def resolve_board_square(cls, theme: Optional[ChessReaderTheme], is_light: bool) -> Dict[str, str]:
        """
        Resolve light or dark square rendering attribute (hex or image path).
        Returns a dictionary: {"kind": "color" | "texture", "value": str}
        """
        if not theme or not theme.board:
            return {"kind": "color", "value": cls.DEFAULT_LIGHT_SQUARE if is_light else cls.DEFAULT_DARK_SQUARE}

        board = theme.board
        val = board.light_square if is_light else board.dark_square

        if board.type == "dual_tile":
            resolved_path = theme.resolve_asset_path(val)
            if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
                return {"kind": "texture", "value": resolved_path}
            # Fallback to default solid colors if texture missing
            return {"kind": "color", "value": cls.DEFAULT_LIGHT_SQUARE if is_light else cls.DEFAULT_DARK_SQUARE}

        # Solid color hex
        return {"kind": "color", "value": val}
