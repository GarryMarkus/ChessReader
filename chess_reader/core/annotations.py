"""
Numeric Annotation Glyphs (NAGs) and PGN comment metadata parsing.
"""

from typing import Optional, Tuple, Dict, Set
import re

# Comprehensive mapping of standard FIDE / ChessBase Numeric Annotation Glyphs (NAGs)
NAG_TO_SYMBOL: Dict[int, str] = {
    1: "!",       # Good move
    2: "?",       # Poor move / Mistake
    3: "‼",       # Very good move / Brilliant
    4: "⁇",       # Very poor move / Blunder
    5: "⁉",       # Speculative / Interesting move
    6: "⁈",       # Questionable / Dubious move
    7: "□",       # Forced move
    10: "=",      # Equal position
    13: "∞",      # Unclear position
    14: "⩲",      # White is slightly better
    15: "⩱",      # Black is slightly better
    16: "±",      # White is better
    17: "∓",      # Black is better
    18: "+-",     # White is winning
    19: "-+",     # Black is winning
    22: "⨀",      # Zugzwang
    32: "⟳",      # Development advantage
    36: "→",      # With attack
    40: "⇈",      # With initiative
    44: "⇆",      # With counterplay
    132: "⮀",     # Counterplay
    138: "⨁",     # Time trouble
    140: "∆",     # With idea
}

SYMBOL_TO_NAG: Dict[str, int] = {v: k for k, v in NAG_TO_SYMBOL.items()}


def parse_comment_metadata(comment: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Parses [%clk ...] and [%eval ...] tags from a PGN comment string.
    Returns: (clock_time, evaluation, clean_comment_text)
    """
    if not comment:
        return (None, None, "")

    clk_match = re.search(r"\[%clk\s+([0-9:]+)\]", comment)
    eval_match = re.search(r"\[%eval\s+([#+-]?[0-9.]+)\]", comment)

    clock_time = clk_match.group(1) if clk_match else None
    evaluation = eval_match.group(1) if eval_match else None

    # Strip bracketed command tokens from display text
    clean_text = re.sub(r"\[%[a-zA-Z0-9_]+\s+[^\]]+\]", "", comment).strip()

    return (clock_time, evaluation, clean_text)


def format_comment_with_metadata(
    comment_text: str,
    clock_time: Optional[str] = None,
    evaluation: Optional[str] = None
) -> str:
    """Reconstructs PGN comment string with [%clk] and [%eval] tags prepended."""
    parts = []
    if clock_time:
        parts.append(f"[%clk {clock_time}]")
    if evaluation:
        parts.append(f"[%eval {evaluation}]")
    if comment_text:
        parts.append(comment_text.strip())
    return " ".join(parts).strip()
