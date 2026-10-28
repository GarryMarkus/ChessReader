"""
Theme discovery and lifecycle manager for ChessReader.
Discovers, validates, and manages built-in and external user themes (~/.config/chess-reader/themes/).
"""

import os
import glob
import logging
from typing import Dict, List, Optional, Callable

from chess_reader.theme.schema import ChessReaderTheme

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manages discovery, active state, and switching of chess themes."""

    DEFAULT_THEME_ID = "zed-dark"

    def __init__(self, user_themes_dir: Optional[str] = None):
        self._project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.builtin_themes_dir = os.path.join(self._project_root, "themes")

        if user_themes_dir:
            self.user_themes_dir = user_themes_dir
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            self.user_themes_dir = os.path.join(xdg_config, "chess-reader", "themes")

        self._themes: Dict[str, ChessReaderTheme] = {}
        self._active_theme_id: str = self.DEFAULT_THEME_ID
        self._listeners: List[Callable[[ChessReaderTheme], None]] = []

        self.reload_themes()

    @property
    def active_theme(self) -> ChessReaderTheme:
        """Return the currently active theme."""
        theme = self._themes.get(self._active_theme_id)
        if not theme:
            # Fall back to default theme
            theme = self._themes.get(self.DEFAULT_THEME_ID)
        if not theme and self._themes:
            # First available theme
            theme = next(iter(self._themes.values()))
        if not theme:
            raise RuntimeError("No valid themes available in system.")
        return theme

    def list_themes(self) -> List[ChessReaderTheme]:
        """Return a list of all discovered and valid themes."""
        return list(self._themes.values())

    def get_theme(self, theme_id: str) -> Optional[ChessReaderTheme]:
        """Retrieve a theme by ID."""
        return self._themes.get(theme_id)

    def set_active_theme(self, theme_id: str) -> bool:
        """Switch active theme and notify listeners."""
        if theme_id not in self._themes:
            logger.warning("Attempted to set unknown theme ID: %s", theme_id)
            return False

        self._active_theme_id = theme_id
        current = self.active_theme
        for listener in self._listeners:
            try:
                listener(current)
            except Exception as e:
                logger.error("Error invoking theme change listener: %s", e)
        return True

    def add_theme_listener(self, listener: Callable[[ChessReaderTheme], None]):
        """Register a callback when theme changes."""
        self._listeners.append(listener)

    def remove_theme_listener(self, listener: Callable[[ChessReaderTheme], None]):
        """Unregister a callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def reload_themes(self):
        """Scan built-in and user directories for themes."""
        self._themes.clear()

        # 1. Load built-ins first
        self._scan_directory(self.builtin_themes_dir)

        # 2. Load user themes (which can override or add new themes)
        if os.path.exists(self.user_themes_dir):
            self._scan_directory(self.user_themes_dir)

        logger.info("Loaded %d themes: %s", len(self._themes), list(self._themes.keys()))

    def _scan_directory(self, directory: str):
        if not os.path.isdir(directory):
            return

        # Direct *.yaml files in directory
        for yaml_path in glob.glob(os.path.join(directory, "*.yaml")):
            self._try_load_theme_file(yaml_path)

        # Subdirectories containing theme.yaml
        for sub in os.listdir(directory):
            sub_dir = os.path.join(directory, sub)
            if os.path.isdir(sub_dir):
                sub_yaml = os.path.join(sub_dir, "theme.yaml")
                if os.path.exists(sub_yaml):
                    self._try_load_theme_file(sub_yaml)

    def _try_load_theme_file(self, file_path: str):
        try:
            theme = ChessReaderTheme.from_yaml_file(file_path)
            self._themes[theme.id] = theme
        except Exception as e:
            logger.warning("Skipping invalid theme file '%s': %s", file_path, e)
