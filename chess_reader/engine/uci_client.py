"""
Asynchronous UCI engine subprocess manager.
Spawns and manages Stockfish via Linux pipes in a background thread, streaming updates safely
to the GLib main loop.
"""

import os
import shutil
import threading
import logging
from typing import Optional, Callable
import chess
import chess.engine
import gi

gi.require_version('GLib', '2.0')
from gi.repository import GLib

from chess_reader.engine.analyzer import AnalysisLine, AnalysisSnapshot, score_to_white_cp

logger = logging.getLogger(__name__)


class UCIEngineManager:
    """Non-blocking background UCI engine manager."""

    DEFAULT_ENGINE_PATHS = [
        "/home/garrymarkus/.local/bin/stockfish",
        "/usr/bin/stockfish",
        "/usr/local/bin/stockfish"
    ]

    def __init__(self, engine_path: Optional[str] = None):
        self.engine_path = engine_path or self._discover_engine_path()
        self._engine: Optional[chess.engine.SimpleEngine] = None
        self._current_analysis: Optional[chess.engine.AnalysisResult] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._is_running = False

    def _discover_engine_path(self) -> Optional[str]:
        # Check PATH
        path = shutil.which("stockfish")
        if path and os.path.exists(path):
            return path
        # Check known paths
        for p in self.DEFAULT_ENGINE_PATHS:
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p
        return None

    def is_available(self) -> bool:
        """Check if an engine binary was discovered and is executable."""
        return bool(self.engine_path and os.path.exists(self.engine_path) and os.access(self.engine_path, os.X_OK))

    def start(self) -> bool:
        """Initialize engine process."""
        with self._lock:
            if self._engine is not None:
                return True
            if not self.is_available():
                logger.warning("No UCI engine binary found.")
                return False

            try:
                self._engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
                self._is_running = True
                logger.info("UCI Engine started successfully: %s", self.engine_path)
                return True
            except Exception as e:
                logger.error("Failed to spawn UCI engine: %s", e)
                self._engine = None
                return False

    def stop_current_analysis(self):
        """Signal ongoing background analysis to stop immediately."""
        self._stop_event.set()

    def analyze_position(
        self,
        board: chess.Board,
        multipv: int = 3,
        max_depth: int = 24,
        on_update: Optional[Callable[[AnalysisSnapshot], None]] = None
    ):
        """
        Asynchronously analyze a board position streaming candidate moves.
        Updates are marshaled to the GTK main loop via GLib.idle_add.
        """
        if not self.start():
            return

        # Signal stop for previous search
        self.stop_current_analysis()

        # Create fresh board copy for thread safety
        board_copy = board.copy()

        def _worker():
            self._stop_event.clear()
            lines_dict = {}

            try:
                with self._lock:
                    if self._engine is None:
                        return
                    analysis = self._engine.analysis(
                        board_copy,
                        chess.engine.Limit(depth=max_depth),
                        multipv=multipv
                    )

                with analysis:
                    for info in analysis:
                        if self._stop_event.is_set():
                            break

                        mpv_idx = info.get("multipv", 1)
                        depth = info.get("depth", 0)
                        score = info.get("score")
                        nodes = info.get("nodes", 0)
                        nps = info.get("nps", 0)
                        pv = info.get("pv", [])

                        if score is not None:
                            sc_white = score.white()
                            mate_val = sc_white.mate() if sc_white.is_mate() else None
                            cp_val = sc_white.score() if not sc_white.is_mate() else None

                            san_str = board_copy.variation_san(pv[:6]) if pv else ""
                            line = AnalysisLine(
                                multipv=mpv_idx,
                                depth=depth,
                                score_cp=cp_val,
                                mate=mate_val,
                                nodes=nodes,
                                nps=nps,
                                pv=pv,
                                san_line=san_str
                            )
                            lines_dict[mpv_idx] = line

                            # Construct snapshot
                            sorted_lines = [lines_dict[k] for k in sorted(lines_dict.keys())]
                            snapshot = AnalysisSnapshot(
                                depth=depth,
                                nodes=nodes,
                                nps=nps,
                                lines=sorted_lines
                            )

                            if on_update and not self._stop_event.is_set():
                                GLib.idle_add(on_update, snapshot)

                        if depth >= max_depth:
                            break
            except Exception as e:
                logger.debug("Analysis stream terminated: %s", e)

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    def close(self):
        """Gracefully terminate engine process."""
        self.stop_current_analysis()
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.quit()
                except Exception:
                    pass
                self._engine = None
                self._is_running = False
