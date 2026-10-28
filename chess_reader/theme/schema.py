"""
Pydantic theme schemas and validation models for ChessReader.
Supports solid, dual-tile texture, and full-board backdrop configurations.
"""

from typing import Literal, Optional, Dict
import os
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class CoordinatesTheme(BaseModel):
    """Configuration for board coordinate typography and positioning."""
    show: bool = True
    placement: Literal["inside", "border"] = "inside"
    font_family: str = "JetBrains Mono"
    font_size: int = Field(default=11, ge=6, le=24)
    light_color: str = "#71717a"
    dark_color: str = "#a1a1aa"


class HighlightsTheme(BaseModel):
    """RGBA or hex color definitions for board state indicators."""
    selected_square: str = "rgba(97, 175, 239, 0.35)"
    last_move: str = "rgba(229, 192, 123, 0.22)"
    legal_move_dot: str = "rgba(171, 178, 191, 0.45)"
    check: str = "rgba(224, 108, 117, 0.65)"
    hover: str = "rgba(255, 255, 255, 0.05)"


class DrawingsTheme(BaseModel):
    """Color palette for right-click interactive annotations and arrows."""
    arrow_primary: str = "rgba(152, 195, 121, 0.85)"      # Green (default)
    arrow_secondary: str = "rgba(229, 192, 123, 0.85)"    # Yellow/Amber
    arrow_tactical: str = "rgba(224, 108, 117, 0.85)"     # Red/Tactical
    arrow_alternate: str = "rgba(97, 175, 239, 0.85)"     # Blue


class BoardTheme(BaseModel):
    """Board rendering configuration."""
    type: Literal["solid", "dual_tile", "backdrop"]
    light_square: str = "#2d3139"
    dark_square: str = "#1e2227"
    backdrop_image: Optional[str] = None
    border_color: str = "#23272e"
    coordinates: CoordinatesTheme = Field(default_factory=CoordinatesTheme)
    highlights: HighlightsTheme = Field(default_factory=HighlightsTheme)
    drawings: DrawingsTheme = Field(default_factory=DrawingsTheme)

    @model_validator(mode="after")
    def validate_backdrop(self):
        if self.type == "backdrop" and not self.backdrop_image:
            raise ValueError("backdrop_image must be specified when board type is 'backdrop'")
        return self


class PiecesTheme(BaseModel):
    """Mapping of chess piece symbols to asset file paths."""
    wP: str = "pieces/wP.png"
    wN: str = "pieces/wN.png"
    wB: str = "pieces/wB.png"
    wR: str = "pieces/wR.png"
    wQ: str = "pieces/wQ.png"
    wK: str = "pieces/wK.png"
    bP: str = "pieces/bP.png"
    bN: str = "pieces/bN.png"
    bB: str = "pieces/bB.png"
    bR: str = "pieces/bR.png"
    bQ: str = "pieces/bQ.png"
    bK: str = "pieces/bK.png"

    def get_piece_path(self, symbol: str) -> Optional[str]:
        """Lookup piece path by symbol (e.g. 'wP' or 'bK')."""
        return getattr(self, symbol, None)


class ChessReaderTheme(BaseModel):
    """Root theme configuration model."""
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    author: str = "Unknown"
    version: str = "1.0.0"
    description: str = ""
    board: BoardTheme
    pieces: PiecesTheme
    base_dir: Optional[str] = None

    @classmethod
    def from_yaml_string(cls, content: str, base_dir: Optional[str] = None) -> "ChessReaderTheme":
        """Parse and validate theme from a YAML string."""
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("YAML content must evaluate to a dictionary")
        theme = cls.model_validate(data)
        theme.base_dir = base_dir
        return theme

    @classmethod
    def from_yaml_file(cls, file_path: str) -> "ChessReaderTheme":
        """Load and validate theme from a YAML file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Theme file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.from_yaml_string(content, base_dir=os.path.dirname(os.path.abspath(file_path)))

    def resolve_asset_path(self, relative_or_absolute_path: str) -> str:
        """Resolve asset path relative to the theme base directory if not absolute."""
        if os.path.isabs(relative_or_absolute_path):
            return relative_or_absolute_path
        if self.base_dir:
            return os.path.join(self.base_dir, relative_or_absolute_path)
        return relative_or_absolute_path
