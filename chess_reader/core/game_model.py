"""
Hierarchical GameNode tree manager for PGN games and recursive variations (RAVs).
Handles tree navigation, branch promotion, branch deletion, NAGs, comments, and PGN export.
"""

from typing import Optional, List, Callable
import io
import chess
import chess.pgn

from chess_reader.core.annotations import (
    NAG_TO_SYMBOL,
    parse_comment_metadata,
    format_comment_with_metadata
)


class GameModel:
    """Manages an active PGN game, tree branching, and navigation."""

    def __init__(self, game: Optional[chess.pgn.Game] = None):
        self.game = game or chess.pgn.Game()
        self.current_node: chess.pgn.GameNode = self.game.root()
        self._listeners: List[Callable[["GameModel"], None]] = []

    @staticmethod
    def _sanitize_pgn_text(pgn_text: str) -> str:
        """Strip leading whitespace from header tag lines for permissive parsing."""
        clean_lines = [
            line.strip() if line.strip().startswith("[") else line
            for line in pgn_text.splitlines()
        ]
        return "\n".join(clean_lines)

    @classmethod
    def from_pgn_text(cls, pgn_text: str) -> "GameModel":
        """Parse a single PGN game from a string."""
        stream = io.StringIO(cls._sanitize_pgn_text(pgn_text))
        game = chess.pgn.read_game(stream)
        if game is None:
            game = chess.pgn.Game()
        return cls(game)

    @classmethod
    def load_database(cls, pgn_text: str) -> List["GameModel"]:
        """Parse multiple games from a single PGN database stream."""
        stream = io.StringIO(cls._sanitize_pgn_text(pgn_text))
        games = []
        while True:
            game = chess.pgn.read_game(stream)
            if game is None:
                break
            games.append(cls(game))
        return games

    @property
    def board(self) -> chess.Board:
        """Return the chess.Board position corresponding to current_node."""
        return self.current_node.board()

    @property
    def is_root(self) -> bool:
        """Whether current_node is the game root position."""
        return self.current_node == self.game.root()

    @property
    def has_next(self) -> bool:
        """Whether current_node has any continuation variations."""
        return len(self.current_node.variations) > 0

    @property
    def has_prev(self) -> bool:
        """Whether current_node has a parent move."""
        return self.current_node.parent is not None

    def add_listener(self, listener: Callable[["GameModel"], None]):
        """Register a callback for game tree and navigation updates."""
        self._listeners.append(listener)

    def _notify(self):
        for listener in self._listeners:
            listener(self)

    # -------------------------------------------------------------------------
    # Tree Navigation
    # -------------------------------------------------------------------------
    def go_to_root(self):
        """Navigate to the starting board position."""
        self.current_node = self.game.root()
        self._notify()

    def go_to_end(self):
        """Navigate to the end of the current mainline continuation."""
        node = self.current_node
        while node.variations:
            node = node.variations[0]
        self.current_node = node
        self._notify()

    def next_move(self, variation_idx: int = 0) -> bool:
        """Advance one move along the specified variation index (0 = mainline)."""
        if self.current_node.variations and 0 <= variation_idx < len(self.current_node.variations):
            self.current_node = self.current_node.variations[variation_idx]
            self._notify()
            return True
        return False

    def prev_move(self) -> bool:
        """Step back one move to the parent position."""
        if self.current_node.parent is not None:
            self.current_node = self.current_node.parent
            self._notify()
            return True
        return False

    def go_to_node(self, node: chess.pgn.GameNode):
        """Jump directly to a specific GameNode in the variation tree."""
        self.current_node = node
        self._notify()

    # -------------------------------------------------------------------------
    # Move Execution & Branching
    # -------------------------------------------------------------------------
    def add_move(self, move: chess.Move) -> chess.pgn.GameNode:
        """
        Plays a move from the current position.
        If the move already exists as a child variation, selects it.
        Otherwise, appends it as a new variation and steps into it.
        """
        # Check existing variations
        for child in self.current_node.variations:
            if child.move == move:
                self.current_node = child
                self._notify()
                return child

        # Add as new branch
        new_node = self.current_node.add_variation(move)
        self.current_node = new_node
        self._notify()
        return new_node

    def promote_variation(self, node: chess.pgn.GameNode) -> bool:
        """
        Promotes a sub-variation to become the mainline continuation at its junction.
        Returns True if promoted, False if already mainline or root.
        """
        parent = node.parent
        if parent is None or len(parent.variations) <= 1:
            return False

        if node not in parent.variations:
            return False

        idx = parent.variations.index(node)
        if idx == 0:
            return False  # Already mainline

        # Move to index 0
        parent.variations.insert(0, parent.variations.pop(idx))
        self._notify()
        return True

    def delete_variation(self, node: chess.pgn.GameNode) -> bool:
        """
        Deletes a variation node and all its descendants.
        If current_node is within the deleted branch, retreats to parent.
        """
        parent = node.parent
        if parent is None or node not in parent.variations:
            return False

        # If current node is this node or a descendant, retreat to parent
        curr = self.current_node
        while curr is not None:
            if curr == node:
                self.current_node = parent
                break
            curr = curr.parent

        parent.variations.remove(node)
        self._notify()
        return True

    # -------------------------------------------------------------------------
    # Annotations: NAGs, Comments, Clocks & Evals
    # -------------------------------------------------------------------------
    def add_nag(self, node: chess.pgn.GameNode, nag: int):
        """Add a Numeric Annotation Glyph (NAG) to a node."""
        node.nags.add(nag)
        self._notify()

    def remove_nag(self, node: chess.pgn.GameNode, nag: int):
        """Remove a NAG from a node."""
        node.nags.discard(nag)
        self._notify()

    def toggle_nag(self, node: chess.pgn.GameNode, nag: int):
        """Toggle an evaluation NAG on a node, clearing competing move-eval NAGs (1-6)."""
        if node == self.game:
            return  # Root game node has no move
        if nag in node.nags:
            node.nags.discard(nag)
        else:
            if nag in (1, 2, 3, 4, 5, 6):
                for ev_nag in (1, 2, 3, 4, 5, 6):
                    node.nags.discard(ev_nag)
            node.nags.add(nag)
        self._notify()

    def get_nags_display(self, node: chess.pgn.GameNode) -> List[str]:
        """Return list of human-readable NAG symbols (e.g. ['!', '±'])."""
        return [NAG_TO_SYMBOL[n] for n in sorted(node.nags) if n in NAG_TO_SYMBOL]

    def set_comment(self, node: chess.pgn.GameNode, text: str):
        """Update node comment preserving [%clk] and [%eval] tags."""
        clk, ev, _ = parse_comment_metadata(node.comment)
        node.comment = format_comment_with_metadata(text, clock_time=clk, evaluation=ev)
        self._notify()

    def set_clock(self, node: chess.pgn.GameNode, clock_time: str):
        """Set [%clk ...] tag on node."""
        _, ev, clean_txt = parse_comment_metadata(node.comment)
        node.comment = format_comment_with_metadata(clean_txt, clock_time=clock_time, evaluation=ev)
        self._notify()

    def set_evaluation(self, node: chess.pgn.GameNode, eval_str: str):
        """Set [%eval ...] tag on node."""
        clk, _, clean_txt = parse_comment_metadata(node.comment)
        node.comment = format_comment_with_metadata(clean_txt, clock_time=clk, evaluation=eval_str)
        self._notify()

    # -------------------------------------------------------------------------
    # Metadata & Formatting
    # -------------------------------------------------------------------------
    def get_breadcrumb_title(self) -> List[str]:
        """Return breadcrumb segments: [Event, Round, White vs Black (Result)]."""
        headers = self.game.headers
        event = headers.get("Event", "Game")
        round_num = headers.get("Round", "")
        white = headers.get("White", "White")
        black = headers.get("Black", "Black")
        result = headers.get("Result", "*")

        matchup = f"{white} vs. {black}"
        if result and result != "*":
            matchup += f" ({result})"

        segments = [event]
        if round_num and round_num != "?":
            segments.append(f"Round {round_num}")
        segments.append(matchup)
        return segments

    def export_pgn(self) -> str:
        """Export game to clean PGN string format."""
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        return self.game.accept(exporter)
