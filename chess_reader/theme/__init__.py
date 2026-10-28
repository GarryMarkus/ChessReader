"""
Theme engine and asset mapping subsystem for ChessReader.
"""

from chess_reader.theme.schema import ChessReaderTheme, BoardTheme, PiecesTheme
from chess_reader.theme.fallback import AssetResolver
from chess_reader.theme.loader import ThemeManager

__all__ = ["ChessReaderTheme", "BoardTheme", "PiecesTheme", "AssetResolver", "ThemeManager"]
