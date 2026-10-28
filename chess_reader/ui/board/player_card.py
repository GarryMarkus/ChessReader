"""
Symmetric Over/Under-board Player Information Card for ChessReader.
Displays player name, FIDE title, Elo rating, active turn indicator,
captured pieces glyphs, material count advantage, and digital clocks.
"""

from typing import Optional, List, Tuple, Dict, Any
import gi
import chess

gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango

from chess_reader.core.annotations import parse_comment_metadata


def compute_material_and_captures(board: chess.Board) -> Dict[str, Any]:
    """
    Calculate material values, captured piece symbols, and material differences
    for White and Black given a chess.Board position.
    """
    initial_counts = {
        chess.PAWN: 8,
        chess.KNIGHT: 2,
        chess.BISHOP: 2,
        chess.ROOK: 2,
        chess.QUEEN: 1,
    }
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }

    white_counts = {pt: len(board.pieces(pt, chess.WHITE)) for pt in initial_counts}
    black_counts = {pt: len(board.pieces(pt, chess.BLACK)) for pt in initial_counts}

    white_score = sum(white_counts[pt] * piece_values[pt] for pt in initial_counts)
    black_score = sum(black_counts[pt] * piece_values[pt] for pt in initial_counts)

    # Black pieces captured by White (missing from Black)
    black_glyphs = {
        chess.QUEEN: "♛",
        chess.ROOK: "♜",
        chess.BISHOP: "♝",
        chess.KNIGHT: "♞",
        chess.PAWN: "♟",
    }
    # White pieces captured by Black (missing from White)
    white_glyphs = {
        chess.QUEEN: "♕",
        chess.ROOK: "♖",
        chess.BISHOP: "♗",
        chess.KNIGHT: "♘",
        chess.PAWN: "♙",
    }

    captured_by_white: List[str] = []
    for pt in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]:
        missing = initial_counts[pt] - black_counts[pt]
        if missing > 0:
            captured_by_white.extend([black_glyphs[pt]] * missing)

    captured_by_black: List[str] = []
    for pt in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]:
        missing = initial_counts[pt] - white_counts[pt]
        if missing > 0:
            captured_by_black.extend([white_glyphs[pt]] * missing)

    return {
        "white_score": white_score,
        "black_score": black_score,
        "white_diff": max(0, white_score - black_score),
        "black_diff": max(0, black_score - white_score),
        "white_captured": captured_by_white,
        "black_captured": captured_by_black,
    }


def extract_player_clocks(current_node: Optional[chess.pgn.GameNode]) -> Tuple[Optional[str], Optional[str]]:
    """
    Traverse backwards from current_node to find the most recent clock times
    for White and Black recorded in [%clk h:mm:ss] comments.
    Returns (white_clock, black_clock).
    """
    white_clk: Optional[str] = None
    black_clk: Optional[str] = None
    curr = current_node

    while curr and (white_clk is None or black_clk is None):
        if curr.comment:
            clk, _, _ = parse_comment_metadata(curr.comment)
            if clk:
                # If curr.turn() == chess.BLACK, White made this move
                if curr.turn() == chess.BLACK and white_clk is None:
                    white_clk = clk
                elif curr.turn() == chess.WHITE and black_clk is None:
                    black_clk = clk
        curr = curr.parent

    return white_clk, black_clk


class PlayerCard(Gtk.Box):
    """
    Symmetric player status card showing player name, title, Elo,
    material advantage, captured pieces, digital clock, and turn highlight.
    """

    def __init__(self, color: chess.Color = chess.WHITE):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.color = color
        self.add_css_class("player-card")

        # 1. Left: King Icon & Title & Player Name & Elo
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        left_box.set_hexpand(True)

        self.color_icon = Gtk.Label(label="♔" if color == chess.WHITE else "♚")
        self.color_icon.add_css_class("player-color-icon")
        left_box.append(self.color_icon)

        self.title_badge = Gtk.Label(label="")
        self.title_badge.add_css_class("player-title-badge")
        self.title_badge.set_visible(False)
        left_box.append(self.title_badge)

        self.name_label = Gtk.Label(label="White" if color == chess.WHITE else "Black", xalign=0.0)
        self.name_label.add_css_class("player-name-label")
        self.name_label.set_ellipsize(Pango.EllipsizeMode.END)
        left_box.append(self.name_label)

        self.elo_badge = Gtk.Label(label="")
        self.elo_badge.add_css_class("player-elo-badge")
        self.elo_badge.set_visible(False)
        left_box.append(self.elo_badge)

        self.append(left_box)

        # 2. Middle: Captured Pieces & Material Advantage (+2)
        self.material_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.captured_label = Gtk.Label(label="")
        self.captured_label.add_css_class("player-captured-label")
        self.material_box.append(self.captured_label)

        self.diff_badge = Gtk.Label(label="")
        self.diff_badge.add_css_class("player-mat-badge")
        self.diff_badge.set_visible(False)
        self.material_box.append(self.diff_badge)

        self.append(self.material_box)

        # 3. Right: Digital Clock / Timer
        self.clock_badge = Gtk.Label(label="")
        self.clock_badge.add_css_class("player-clock-badge")
        self.clock_badge.set_visible(False)
        self.append(self.clock_badge)

    def update_player(
        self,
        color: chess.Color,
        name: str,
        elo: Optional[str] = None,
        title: Optional[str] = None,
        clock: Optional[str] = None,
        captured_pieces: Optional[List[str]] = None,
        material_diff: int = 0,
        is_active_turn: bool = False
    ):
        """Update all player information, captured pieces, and turn highlight."""
        self.color = color
        self.color_icon.set_text("♔" if color == chess.WHITE else "♚")

        # Name
        clean_name = name.strip() if name else ("White" if color == chess.WHITE else "Black")
        self.name_label.set_text(clean_name)

        # FIDE Title (GM, IM, etc.)
        if title and title.strip() and title.strip() != "?":
            self.title_badge.set_text(title.strip().upper())
            self.title_badge.set_visible(True)
        else:
            self.title_badge.set_visible(False)

        # Elo rating
        if elo and elo.strip() and elo.strip() not in ("?", "0"):
            self.elo_badge.set_text(elo.strip())
            self.elo_badge.set_visible(True)
        else:
            self.elo_badge.set_visible(False)

        # Captured pieces & material advantage
        if captured_pieces:
            self.captured_label.set_text(" ".join(captured_pieces))
            self.captured_label.set_visible(True)
        else:
            self.captured_label.set_text("")
            self.captured_label.set_visible(False)

        if material_diff > 0:
            self.diff_badge.set_text(f"+{material_diff}")
            self.diff_badge.set_visible(True)
        else:
            self.diff_badge.set_visible(False)

        # Clock
        if clock and clock.strip():
            self.clock_badge.set_text(f"⏱ {clock.strip()}")
            self.clock_badge.set_visible(True)
        else:
            self.clock_badge.set_visible(False)

        # Active turn highlight styling
        if is_active_turn:
            self.add_css_class("player-card-active")
            self.clock_badge.add_css_class("player-clock-active")
        else:
            self.remove_css_class("player-card-active")
            self.clock_badge.remove_css_class("player-clock-active")
