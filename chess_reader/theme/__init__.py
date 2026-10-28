"""
Theme engine and asset mapping subsystem for ChessReader.
"""

from chess_reader.theme.schema import ChessReaderTheme, BoardTheme, PiecesTheme
from chess_reader.theme.fallback import AssetResolver
from chess_reader.theme.loader import ThemeManager
from chess_reader.theme.asset_cache import PieceAssetCache

__all__ = [
    "ChessReaderTheme",
    "BoardTheme",
    "PiecesTheme",
    "AssetResolver",
    "ThemeManager",
    "PieceAssetCache"
]
