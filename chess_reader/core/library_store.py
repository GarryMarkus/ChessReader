"""
Library and Database Store for ChessReader.
Manages persistent folder shortcuts, PGN file scanning, new PGN creation,
and high-speed PGN game index caching.
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional, Any
import chess.pgn

logger = logging.getLogger(__name__)


class LibraryStore:
    """Manages folder shortcuts, recent PGN files, and local database indexation."""

    def __init__(self, config_dir: Optional[str] = None):
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        self.config_dir = config_dir or os.path.join(xdg_config, "chess-reader")
        self.library_file = os.path.join(self.config_dir, "library.json")

        self.folder_shortcuts: List[Dict[str, str]] = []
        self.recent_files: List[Dict[str, Any]] = []

        self._load()

        # Seed with a default user Chess shortcut if empty and directory exists
        if not self.folder_shortcuts:
            default_chess_dir = os.path.expanduser("~/Chess")
            if os.path.isdir(default_chess_dir):
                self.add_folder_shortcut(default_chess_dir, name="My Chess")

    def add_folder_shortcut(self, folder_path: str, name: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Add a folder shortcut to the persistent library."""
        abs_path = os.path.abspath(os.path.expanduser(folder_path))
        if not os.path.isdir(abs_path):
            raise ValueError(f"Path is not a valid directory: {folder_path}")

        # Check existing
        for shortcut in self.folder_shortcuts:
            if shortcut["path"] == abs_path:
                return shortcut

        shortcut_name = name or os.path.basename(abs_path) or abs_path
        item = {
            "name": shortcut_name,
            "path": abs_path,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.folder_shortcuts.append(item)
        self._save()
        return item

    def remove_folder_shortcut(self, folder_path: str) -> bool:
        """Remove a folder shortcut by path."""
        abs_path = os.path.abspath(os.path.expanduser(folder_path))
        orig_len = len(self.folder_shortcuts)
        self.folder_shortcuts = [s for s in self.folder_shortcuts if s["path"] != abs_path]
        if len(self.folder_shortcuts) < orig_len:
            self._save()
            return True
        return False

    def get_folder_shortcuts(self) -> List[Dict[str, str]]:
        """Return all folder shortcuts."""
        return list(self.folder_shortcuts)

    def scan_folder_for_pgns(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Scan a directory for all .pgn and .db chess files.
        Returns metadata: name, path, size, modified date, game count estimate.
        """
        abs_path = os.path.abspath(os.path.expanduser(folder_path))
        if not os.path.isdir(abs_path):
            return []

        results = []
        try:
            entries = sorted(os.listdir(abs_path))
        except OSError as e:
            logger.error("Failed to list folder %s: %s", abs_path, e)
            return []

        for entry in entries:
            if entry.lower().endswith((".pgn", ".db")):
                full_path = os.path.join(abs_path, entry)
                if os.path.isfile(full_path):
                    try:
                        stat = os.stat(full_path)
                        size_bytes = stat.st_size
                        size_str = self._format_file_size(size_bytes)
                        mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))

                        # Quick count games by counting "[Event " tags
                        game_count = self._estimate_game_count(full_path)

                        results.append({
                            "name": entry,
                            "path": full_path,
                            "size_bytes": size_bytes,
                            "size_str": size_str,
                            "mtime_str": mtime_str,
                            "game_count": game_count,
                            "is_db": entry.lower().endswith(".db")
                        })
                    except OSError:
                        continue

        return results

    def add_recent_file(self, file_path: str, game_count: Optional[int] = None):
        """Add or update a file in the recent files list."""
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.isfile(abs_path):
            return

        stat = os.stat(abs_path)
        count = game_count if game_count is not None else self._estimate_game_count(abs_path)

        # Remove previous occurrence
        self.recent_files = [r for r in self.recent_files if r.get("path") != abs_path]

        self.recent_files.insert(0, {
            "name": os.path.basename(abs_path),
            "path": abs_path,
            "size_str": self._format_file_size(stat.st_size),
            "last_opened": time.strftime("%Y-%m-%d %H:%M:%S"),
            "game_count": count
        })

        # Cap at 20 recent files
        self.recent_files = self.recent_files[:20]
        self._save()

    def get_recent_files(self) -> List[Dict[str, Any]]:
        """Return list of recently opened PGN / database files."""
        # Filter out files that no longer exist on disk
        valid = [r for r in self.recent_files if os.path.exists(r["path"])]
        if len(valid) != len(self.recent_files):
            self.recent_files = valid
            self._save()
        return list(self.recent_files)

    def remove_recent_file(self, file_path: str):
        """Remove a file from the recent databases list."""
        abs_path = os.path.abspath(file_path)
        self.recent_files = [r for r in self.recent_files if os.path.abspath(r.get("path", "")) != abs_path]
        self._save()

    def create_new_pgn_file(
        self,
        file_path: str,
        event: str = "Casual Game",
        white: str = "White Player",
        black: str = "Black Player"
    ) -> str:
        """Create a new, valid PGN file on the filesystem with initial headers."""
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        if not abs_path.lower().endswith(".pgn"):
            abs_path += ".pgn"

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        today = time.strftime("%Y.%m.%d")

        pgn_template = (
            f'[Event "{event}"]\n'
            f'[Site "ChessReader Local"]\n'
            f'[Date "{today}"]\n'
            f'[Round "1"]\n'
            f'[White "{white}"]\n'
            f'[Black "{black}"]\n'
            f'[Result "*"]\n\n'
            f'*\n'
        )

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(pgn_template)

        self.add_recent_file(abs_path, game_count=1)
        return abs_path

    @staticmethod
    def list_games_in_pgn(file_path: str) -> List[Dict[str, Any]]:
        """
        Fast-parse game headers for all games inside a PGN file.
        Returns lightweight index entries without parsing movetext.
        """
        if not os.path.isfile(file_path):
            return []

        games = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                idx = 0
                while True:
                    headers = chess.pgn.read_headers(f)
                    if headers is None:
                        break

                    white = headers.get("White", "White")
                    black = headers.get("Black", "Black")
                    event = headers.get("Event", "Game")
                    result = headers.get("Result", "*")
                    date = headers.get("Date", "????.??.??")
                    eco = headers.get("ECO", "")
                    round_str = headers.get("Round", "")

                    games.append({
                        "index": idx,
                        "title": f"{white} vs. {black}",
                        "white": white,
                        "black": black,
                        "event": event,
                        "result": result,
                        "date": date,
                        "eco": eco,
                        "round": round_str
                    })
                    idx += 1
        except Exception as e:
            logger.error("Failed to read headers from %s: %s", file_path, e)

        return games

    @staticmethod
    def load_game_from_pgn(file_path: str, game_index: int = 0) -> Optional[chess.pgn.Game]:
        """Load and parse the full game AST at the specified index."""
        if not os.path.isfile(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(game_index):
                    if not chess.pgn.skip_game(f):
                        return None
                return chess.pgn.read_game(f)
        except Exception as e:
            logger.error("Failed to load game at index %d from %s: %s", game_index, file_path, e)
            return None

    def _estimate_game_count(self, file_path: str) -> int:
        """Fast approximate count of games in a PGN by counting '[Event ' tags."""
        count = 0
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("[Event "):
                        count += 1
        except Exception:
            return 0
        return max(count, 1 if os.path.getsize(file_path) > 10 else 0)

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _load(self):
        if not os.path.exists(self.library_file):
            return
        try:
            with open(self.library_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.folder_shortcuts = data.get("folder_shortcuts", [])
                self.recent_files = data.get("recent_files", [])
        except Exception as e:
            logger.warning("Failed to load library data: %s", e)

    def _save(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            data = {
                "folder_shortcuts": self.folder_shortcuts,
                "recent_files": self.recent_files
            }
            with open(self.library_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save library data: %s", e)
