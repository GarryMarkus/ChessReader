"""
Board projection geometry and coordinate mapping.
Handles centering, aspect-ratio enforcement, square-to-pixel transformations,
and ChessBase-style border coordinate margins.
"""

from typing import Tuple, Optional
import chess


class BoardGeometry:
    """Calculates pixel coordinates and spatial projections for an 8x8 chessboard with border margins."""

    def __init__(
        self,
        widget_width: float = 0.0,
        widget_height: float = 0.0,
        flipped: bool = False,
        border_width: float = 0.0
    ):
        self.widget_width = max(0.0, widget_width)
        self.widget_height = max(0.0, widget_height)
        self.flipped = flipped
        self.border_width = max(0.0, border_width)
        self._recalculate()

    def update_bounds(self, width: float, height: float, border_width: Optional[float] = None):
        """Update widget viewport dimensions and border width."""
        self.widget_width = max(0.0, width)
        self.widget_height = max(0.0, height)
        if border_width is not None:
            self.border_width = max(0.0, border_width)
        self._recalculate()

    def _recalculate(self):
        # Outer board dimension (including border frame)
        self.total_size = max(0.0, min(self.widget_width, self.widget_height))

        # Effective border width (caps at 8% of total board size)
        eff_border = min(self.border_width, self.total_size * 0.08) if self.total_size > 0 else 0.0
        self.effective_border = eff_border

        # Inner 8x8 playable squares area
        self.inner_size = max(0.0, self.total_size - (2.0 * eff_border))
        self.board_size = self.inner_size
        self.square_size = self.inner_size / 8.0 if self.inner_size > 0 else 0.0

        # Outer centering offsets (border frame position)
        self.offset_x = (self.widget_width - self.total_size) / 2.0
        self.offset_y = (self.widget_height - self.total_size) / 2.0

        # Inner squares start coordinates
        self.squares_offset_x = self.offset_x + eff_border
        self.squares_offset_y = self.offset_y + eff_border

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

        x = self.squares_offset_x + (col * self.square_size)
        y = self.squares_offset_y + (row * self.square_size)
        return (x, y, self.square_size, self.square_size)

    def point_to_square(self, x: float, y: float) -> Optional[chess.Square]:
        """
        Convert screen coordinates (x, y) into a chess.Square.
        Returns None if coordinates fall outside the 8x8 playable grid.
        """
        if self.square_size <= 0:
            return None

        # Check inner squares bounds
        if not (self.squares_offset_x <= x <= self.squares_offset_x + self.inner_size):
            return None
        if not (self.squares_offset_y <= y <= self.squares_offset_y + self.inner_size):
            return None

        col = int((x - self.squares_offset_x) / self.square_size)
        row = int((y - self.squares_offset_y) / self.square_size)

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
