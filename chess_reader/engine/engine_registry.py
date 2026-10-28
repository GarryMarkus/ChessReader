"""
UCI Chess Engine Registry and Manager for ChessReader.
Enables discovery, custom engine registration, validation, and persistent storage
of multiple chess engines.
"""

import os
import json
import shutil
import subprocess
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Manages configured UCI chess engines and persistence."""

    DEFAULT_KNOWN_PATHS = [
        "/home/garrymarkus/.local/bin/stockfish",
        "/usr/bin/stockfish",
        "/usr/local/bin/stockfish"
    ]

    def __init__(self, config_dir: Optional[str] = None):
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        self.config_dir = config_dir or os.path.join(xdg_config, "chess-reader")
        self.engines_file = os.path.join(self.config_dir, "engines.json")

        self.engines: List[Dict[str, Any]] = []
        self.active_engine_id: Optional[str] = None

        self._load()

        # If empty, discover stockfish
        if not self.engines:
            self._discover_defaults()

    def list_engines(self) -> List[Dict[str, Any]]:
        """Return all registered engines."""
        return list(self.engines)

    def get_engine(self, engine_id: str) -> Optional[Dict[str, Any]]:
        for eng in self.engines:
            if eng["id"] == engine_id:
                return eng
        return None

    def get_active_engine(self) -> Optional[Dict[str, Any]]:
        """Return active engine dictionary, or first available."""
        if self.active_engine_id:
            eng = self.get_engine(self.active_engine_id)
            if eng:
                return eng
        if self.engines:
            return self.engines[0]
        return None

    def set_active_engine(self, engine_id: str) -> bool:
        eng = self.get_engine(engine_id)
        if not eng:
            return False
        self.active_engine_id = engine_id
        self._save()
        return True

    def add_engine(self, binary_path: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate executable binary via UCI handshake, register it, and save.
        Raises ValueError if file is not an executable UCI chess engine.
        """
        abs_path = os.path.abspath(os.path.expanduser(binary_path))
        if not os.path.isfile(abs_path):
            raise ValueError(f"Engine file not found: {binary_path}")
        if not os.access(abs_path, os.X_OK):
            raise ValueError(f"File is not marked executable: {binary_path}")

        # Check existing
        for eng in self.engines:
            if eng["path"] == abs_path:
                return eng

        # Test UCI handshake & extract official engine name
        detected_name = self.probe_uci_engine(abs_path)
        name = custom_name or detected_name or os.path.basename(abs_path).title()

        engine_id = name.lower().replace(" ", "-")
        # Ensure unique id
        base_id = engine_id
        counter = 1
        while self.get_engine(engine_id):
            engine_id = f"{base_id}-{counter}"
            counter += 1

        new_entry = {
            "id": engine_id,
            "name": name,
            "path": abs_path,
            "is_builtin": False
        }
        self.engines.append(new_entry)
        self._save()
        return new_entry

    def remove_engine(self, engine_id: str) -> bool:
        """Remove a registered engine."""
        orig_len = len(self.engines)
        self.engines = [e for e in self.engines if e["id"] != engine_id]
        if len(self.engines) < orig_len:
            if self.active_engine_id == engine_id:
                self.active_engine_id = self.engines[0]["id"] if self.engines else None
            self._save()
            return True
        return False

    @staticmethod
    def probe_uci_engine(binary_path: str, timeout_seconds: float = 3.0) -> str:
        """
        Probe an executable with 'uci' and verify 'uciok' response.
        Returns the discovered engine name, or raises ValueError.
        """
        try:
            p = subprocess.Popen(
                [binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, _ = p.communicate("uci\nquit\n", timeout=timeout_seconds)
        except Exception as e:
            raise ValueError(f"Failed to execute engine binary: {e}")

        has_uciok = False
        engine_name = None
        for line in stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("id name "):
                engine_name = line_str[len("id name "):].strip()
            if line_str == "uciok":
                has_uciok = True

        if not has_uciok:
            raise ValueError("Binary did not respond with 'uciok'. Ensure it is a valid UCI chess engine.")

        return engine_name or os.path.basename(binary_path)

    def _discover_defaults(self):
        """Discover Stockfish on system and register as default engine."""
        path = shutil.which("stockfish")
        if not path or not os.path.exists(path):
            for candidate in self.DEFAULT_KNOWN_PATHS:
                if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                    path = candidate
                    break

        if path:
            try:
                name = self.probe_uci_engine(path)
            except Exception:
                name = "Stockfish 18"
            self.engines.append({
                "id": "stockfish-default",
                "name": name,
                "path": path,
                "is_builtin": True
            })
            self.active_engine_id = "stockfish-default"
            self._save()

    def _load(self):
        if not os.path.exists(self.engines_file):
            return
        try:
            with open(self.engines_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.engines = data.get("engines", [])
                self.active_engine_id = data.get("active_engine_id")
        except Exception as e:
            logger.warning("Failed to load engines list: %s", e)

    def _save(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            data = {
                "engines": self.engines,
                "active_engine_id": self.active_engine_id
            }
            with open(self.engines_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save engines list: %s", e)
