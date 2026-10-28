"""
Engine analysis data structures and evaluation conversion utilities.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import math
import chess
import chess.engine


@dataclass
class AnalysisLine:
    """A single Multi-PV candidate line from the engine."""
    multipv: int
    depth: int
    score_cp: Optional[int] = None
    mate: Optional[int] = None
    nodes: int = 0
    nps: int = 0
    pv: List[chess.Move] = field(default_factory=list)
    san_line: str = ""

    @property
    def display_score(self) -> str:
        """Formatted evaluation string (e.g. '+0.45' or 'M3')."""
        if self.mate is not None:
            return f"M{self.mate}" if self.mate > 0 else f"-M{abs(self.mate)}"
        if self.score_cp is not None:
            pawns = self.score_cp / 100.0
            return f"+{pawns:.2f}" if pawns > 0 else f"{pawns:.2f}"
        return "0.00"

    @property
    def win_percentage(self) -> float:
        """Calculate winning chance percentage (0 - 100%) for White."""
        if self.mate is not None:
            return 100.0 if self.mate > 0 else 0.0
        cp = self.score_cp or 0
        # Lichess win chance curve formula
        return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


@dataclass
class AnalysisSnapshot:
    """Current engine search state containing all active Multi-PV lines."""
    depth: int = 0
    nodes: int = 0
    nps: int = 0
    lines: List[AnalysisLine] = field(default_factory=list)

    @property
    def top_line(self) -> Optional[AnalysisLine]:
        """Return the best candidate line (Multi-PV 1)."""
        return self.lines[0] if self.lines else None


def score_to_string(score: chess.engine.Score) -> str:
    """Format chess.engine.Score to human-readable string."""
    sc = score.white()
    if sc.is_mate():
        m = sc.mate()
        return f"M{m}" if m and m > 0 else f"-M{abs(m or 0)}"
    cp = sc.score() or 0
    pawns = cp / 100.0
    return f"+{pawns:.2f}" if pawns > 0 else f"{pawns:.2f}"


def score_to_white_cp(score: chess.engine.Score, mate_score_cp: int = 10000) -> int:
    """Convert chess.engine.Score into integer centipawns from White's perspective."""
    sc = score.white()
    if sc.is_mate():
        m = sc.mate() or 0
        if m > 0:
            return mate_score_cp - m
        else:
            return -mate_score_cp - m
    return sc.score() or 0
