"""
Board projection geometry and coordinate mapping.
Handles centering, aspect-ratio enforcement, and square-to-pixel transformations.
"""

from typing import Tuple, Optional
import chess


class BoardGeometry:
    """Calculates pixel coordinates and spatial projections for an 8x8 chessboard."""

    def __init__(self, widget_width: float = 0.0, widget_height: float = 0.0, flipped: bool = False):
        self.widget_width = max(0.0, widget_width)
        self.widget_height = max(0.0, widget_height)
        self.flipped = flipped

        # Calculate square board dimensions
        self.board_size = max(0.0, min(self.widget_width, self.widget_height))
        self.square_size = self.board_size / 8.0 if self.board_size > 0 else 0.0

        # Centering offsets
        self.offset_x = (self.widget_width - self.board_size) / 2.0
        self.offset_y = (self.widget_height - self.board_size) / 2.0

    def update_bounds(self, width: float, height: float):
        """Update widget viewport dimensions."""
        self.widget_width = max(0.0, width)
        self.widget_height = max(0.0, height)
        self.board_size = max(0.0, min(self.widget_width, self.widget_height))
        self.square_size = self.board_size / 8.0 if self.board_size > 0 else 0.0
        self.offset_x = (self.widget_width - self.board_size) / 2.0
        self.offset_y = (self.widget_height - self.board_size) / 2.0

    def square_to_rect(self, square: chess.Square) -> Tuple[float, float, float, float]:
        """
        Convert a chess.Square (0..63) into a screen rectangle (x, y, width, height).
        """
        file_idx = chess.square_file(square)  # 0..7 (a..h)
        rank_idx = chess.square_rank(square)  # 0..7 (1..8)

        if self.flipped:
            col = 7 - file_idx
            row = rank_idx
        else:
            col = file_idx
            row = 7 - rank_idx

        x = self.offset_x + (col * self.square_size)
        y = self.offset_y + (row * self.square_size)
        return (x, y, self.square_size, self.square_size)

    def point_to_square(self, x: float, y: float) -> Optional[chess.Square]:
        """
        Convert screen coordinates (x, y) into a chess.Square.
        Returns None if coordinates fall outside the 8x8 grid.
        """
        if self.square_size <= 0:
            return None

        # Check bounds
        if not (self.offset_x <= x <= self.offset_x + self.board_size):
            return None
        if not (self.offset_y <= y <= self.offset_y + self.board_size):
            return None

        col = int((x - self.offset_x) / self.square_size)
        row = int((y - self.offset_y) / self.square_size)

        col = max(0, min(7, col))
        row = max(0, min(7, row))

        if self.flipped:
            file_idx = 7 - col
            rank_idx = row
        else:
            file_idx = col
            rank_idx = 7 - row

        return chess.square(file_idx, rank_idx)

    def square_center(self, square: chess.Square) -> Tuple[float, float]:
        """Return the (center_x, center_y) of a chess square."""
        x, y, size, _ = self.square_to_rect(square)
        return (x + size / 2.0, y + size / 2.0)
