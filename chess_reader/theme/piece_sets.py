"""
Piece set discovery, custom import, and lifecycle manager for ChessReader.
Enables independent selection and custom importing of chess piece styles.
"""

import os
import json
import shutil
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class PieceSetInfo:
    """Metadata for a piece set."""
    id: str
    name: str
    directory: str
    format: str  # "png" | "svg"
    is_builtin: bool = True
    preview_symbols: List[str] = field(default_factory=lambda: ["wK", "wN", "bQ", "bP"])

    def get_piece_path(self, symbol: str) -> Optional[str]:
        """Get absolute path to a piece symbol in this set."""
        for ext in (".png", ".svg"):
            candidate = os.path.join(self.directory, f"{symbol}{ext}")
            if os.path.exists(candidate):
                return candidate
        return None


class PieceSetManager:
    """Manages piece set discovery, user preference persistence, and custom imports."""

    PIECE_SYMBOLS = ["wP", "wN", "wB", "wR", "wQ", "wK", "bP", "bN", "bB", "bR", "bQ", "bK"]

    def __init__(self, user_pieces_dir: Optional[str] = None, config_dir: Optional[str] = None):
        self._project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.builtin_pieces_dir = os.path.join(self._project_root, "assets", "pieces")

        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        self.config_dir = config_dir or os.path.join(xdg_config, "chess-reader")
        self.user_pieces_dir = user_pieces_dir or os.path.join(self.config_dir, "pieces")
        self.prefs_file = os.path.join(self.config_dir, "preferences.json")

        self._piece_sets: Dict[str, PieceSetInfo] = {}
        self._active_piece_set_id: Optional[str] = None
        self._listeners: List[Callable[[Optional[PieceSetInfo]], None]] = []

        self.reload_piece_sets()
        self._load_preferences()

    @property
    def active_piece_set(self) -> Optional[PieceSetInfo]:
        """Return the user-selected active piece set, or None if theme-default."""
        if self._active_piece_set_id:
            return self._piece_sets.get(self._active_piece_set_id)
        return None

    @property
    def active_piece_set_id(self) -> Optional[str]:
        return self._active_piece_set_id

    def list_piece_sets(self) -> List[PieceSetInfo]:
        """Return all discovered piece sets."""
        return list(self._piece_sets.values())

    def get_piece_set(self, set_id: str) -> Optional[PieceSetInfo]:
        return self._piece_sets.get(set_id)

    def set_active_piece_set(self, set_id: Optional[str]) -> bool:
        """Set active piece set override (pass None or '' for theme default)."""
        if set_id and set_id not in self._piece_sets:
            logger.warning("Attempted to set unknown piece set: %s", set_id)
            return False

        self._active_piece_set_id = set_id if set_id else None
        self._save_preferences()

        active = self.active_piece_set
        for listener in self._listeners:
            try:
                listener(active)
            except Exception as e:
                logger.error("Error in piece set listener: %s", e)
        return True

    def add_listener(self, listener: Callable[[Optional[PieceSetInfo]], None]):
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[Optional[PieceSetInfo]], None]):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def reload_piece_sets(self):
        """Discover built-in and user-installed piece sets."""
        self._piece_sets.clear()

        # 1. Built-in pieces in assets/pieces/
        if os.path.isdir(self.builtin_pieces_dir):
            for entry in os.listdir(self.builtin_pieces_dir):
                full_path = os.path.join(self.builtin_pieces_dir, entry)
                if os.path.isdir(full_path):
                    info = self._inspect_piece_directory(entry, full_path, is_builtin=True)
                    if info:
                        self._piece_sets[entry] = info

        # 2. User pieces in ~/.config/chess-reader/pieces/
        if os.path.isdir(self.user_pieces_dir):
            for entry in os.listdir(self.user_pieces_dir):
                full_path = os.path.join(self.user_pieces_dir, entry)
                if os.path.isdir(full_path):
                    info = self._inspect_piece_directory(entry, full_path, is_builtin=False)
                    if info:
                        self._piece_sets[entry] = info

        logger.info("Loaded %d piece sets: %s", len(self._piece_sets), list(self._piece_sets.keys()))

    def import_piece_set_folder(self, source_dir: str, custom_name: Optional[str] = None) -> Optional[PieceSetInfo]:
        """
        Import a piece set directory into the user config folder.
        Validates presence of piece images, copies them, and registers the set.
        """
        if not os.path.isdir(source_dir):
            raise ValueError(f"Source directory does not exist: {source_dir}")

        # Check for pieces
        found_symbols = 0
        fmt = "png"
        for symbol in self.PIECE_SYMBOLS:
            for ext in (".png", ".svg"):
                if os.path.exists(os.path.join(source_dir, f"{symbol}{ext}")):
                    found_symbols += 1
                    if ext == ".svg":
                        fmt = "svg"
                    break

        if found_symbols < 6:
            raise ValueError(f"Directory contains only {found_symbols} recognized chess pieces (minimum 6 required).")

        base_id = (custom_name or os.path.basename(source_dir.rstrip("/"))).lower().replace(" ", "-")
        target_dir = os.path.join(self.user_pieces_dir, base_id)
        os.makedirs(self.user_pieces_dir, exist_ok=True)

        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)

        self.reload_piece_sets()
        return self.get_piece_set(base_id)

    def _inspect_piece_directory(self, set_id: str, directory: str, is_builtin: bool) -> Optional[PieceSetInfo]:
        """Inspect directory for chess pieces and return PieceSetInfo if valid."""
        png_count = 0
        svg_count = 0
        for symbol in self.PIECE_SYMBOLS:
            if os.path.exists(os.path.join(directory, f"{symbol}.png")):
                png_count += 1
            if os.path.exists(os.path.join(directory, f"{symbol}.svg")):
                svg_count += 1

        if png_count == 0 and svg_count == 0:
            return None

        fmt = "svg" if svg_count > png_count else "png"
        display_names = {
            "neo": "Neo (Modern Flat)",
            "standard": "Standard (Tournament)",
            "cburnett": "CBurnett (Vector)"
        }
        name = display_names.get(set_id, set_id.replace("-", " ").title())

        return PieceSetInfo(
            id=set_id,
            name=name,
            directory=directory,
            format=fmt,
            is_builtin=is_builtin
        )

    def _load_preferences(self):
        if not os.path.exists(self.prefs_file):
            return
        try:
            with open(self.prefs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                set_id = data.get("active_piece_set")
                if set_id and set_id in self._piece_sets:
                    self._active_piece_set_id = set_id
        except Exception as e:
            logger.warning("Failed to load preferences: %s", e)

    def _save_preferences(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            data = {}
            if os.path.exists(self.prefs_file):
                with open(self.prefs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["active_piece_set"] = self._active_piece_set_id
            with open(self.prefs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save preferences: %s", e)
