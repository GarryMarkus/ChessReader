"""
Automated batch game review and move classification engine.
Calculates centipawn loss (CPL), accuracy percentages, and tactical classifications.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum
import chess
import chess.engine

from chess_reader.engine.analyzer import score_to_white_cp


class MoveClassification(Enum):
    BRILLIANT = "Brilliant"      # !!
    GREAT = "Great"              # !
    BEST = "Best"                # Best move
    EXCELLENT = "Excellent"      # Near best
    GOOD = "Good"                # Acceptable move
    INACCURACY = "Inaccuracy"    # ?!
    MISTAKE = "Mistake"          # ?
    BLUNDER = "Blunder"          # ??


@dataclass
class MoveReview:
    """Analysis result for a single move played in a game."""
    ply: int
    move: chess.Move
    san: str
    played_by_white: bool
    eval_before_cp: int
    eval_after_cp: int
    best_move: chess.Move
    cpl: int  # Centipawn loss (non-negative)
    classification: MoveClassification


@dataclass
class GameReviewResult:
    """Summary of batch game analysis."""
    white_accuracy: float
    black_accuracy: float
    white_cpl_avg: float
    black_cpl_avg: float
    reviews: List[MoveReview] = field(default_factory=list)
    cpl_curve: List[Tuple[int, float]] = field(default_factory=list)  # [(ply, eval_in_pawns)]


class BatchGameReviewer:
    """Performs deep or quick batch analysis over an entire PGN game."""

    def __init__(self, engine_path: str):
        self.engine_path = engine_path

    def review_game(
        self,
        game: chess.pgn.Game,
        depth: int = 10,
        progress_callback: Optional[callable] = None
    ) -> GameReviewResult:
        """Analyze every move in game and produce GameReviewResult."""
        board = game.board()
        engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)

        reviews: List[MoveReview] = []
        cpl_curve: List[Tuple[int, float]] = [(0, 0.0)]

        white_losses = []
        black_losses = []

        moves = list(game.mainline_moves())
        total_moves = len(moves)

        try:
            curr_board = board.copy()
            # Analyze initial position
            initial_info = engine.analyse(curr_board, chess.engine.Limit(depth=depth))
            prev_eval_cp = score_to_white_cp(initial_info["score"])

            for idx, move in enumerate(moves):
                ply = idx + 1
                is_white = curr_board.turn == chess.WHITE

                # Engine evaluation of current position before move
                info_before = engine.analyse(curr_board, chess.engine.Limit(depth=depth))
                best_move = info_before.get("pv", [move])[0]
                eval_before_cp = score_to_white_cp(info_before["score"])

                # Execute move
                san_str = curr_board.san(move)
                curr_board.push(move)

                # Eval after move
                info_after = engine.analyse(curr_board, chess.engine.Limit(depth=depth))
                eval_after_cp = score_to_white_cp(info_after["score"])

                # Calculate Centipawn Loss from moving player's perspective
                if is_white:
                    cpl = max(0, eval_before_cp - eval_after_cp)
                    white_losses.append(cpl)
                else:
                    cpl = max(0, eval_after_cp - eval_before_cp)
                    black_losses.append(cpl)

                # Tactical Classification
                classification = self._classify_move(cpl, move, best_move, curr_board)

                review = MoveReview(
                    ply=ply,
                    move=move,
                    san=san_str,
                    played_by_white=is_white,
                    eval_before_cp=eval_before_cp,
                    eval_after_cp=eval_after_cp,
                    best_move=best_move,
                    cpl=cpl,
                    classification=classification
                )
                reviews.append(review)
                cpl_curve.append((ply, eval_after_cp / 100.0))

                if progress_callback:
                    progress_callback(ply, total_moves)

        finally:
            engine.quit()

        # Compute accuracy percentages
        w_avg = sum(white_losses) / len(white_losses) if white_losses else 0.0
        b_avg = sum(black_losses) / len(black_losses) if black_losses else 0.0

        w_acc = max(0.0, min(100.0, 100.0 - (w_avg * 0.35)))
        b_acc = max(0.0, min(100.0, 100.0 - (b_avg * 0.35)))

        return GameReviewResult(
            white_accuracy=round(w_acc, 1),
            black_accuracy=round(b_acc, 1),
            white_cpl_avg=round(w_avg, 1),
            black_cpl_avg=round(b_avg, 1),
            reviews=reviews,
            cpl_curve=cpl_curve
        )

    def _classify_move(
        self,
        cpl: int,
        move: chess.Move,
        best_move: chess.Move,
        board_after: chess.Board
    ) -> MoveClassification:
        """Classify move by centipawn loss and tactical criteria."""
        if move == best_move:
            # Check for brilliant/sacrificial move: piece sacrificed for advantage
            prev_board = board_after.copy()
            prev_board.pop()
            moving_piece = prev_board.piece_at(move.from_square)
            captured_piece = prev_board.piece_at(move.to_square)

            if moving_piece and moving_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
                # If moved to an attacked square without capturing equal value piece
                if not captured_piece or captured_piece.piece_type < moving_piece.piece_type:
                    if board_after.is_attacked_by(board_after.turn, move.to_square):
                        return MoveClassification.BRILLIANT

            return MoveClassification.BEST

        if cpl <= 15:
            return MoveClassification.EXCELLENT
        elif cpl <= 40:
            return MoveClassification.GOOD
        elif cpl <= 90:
            return MoveClassification.INACCURACY
        elif cpl <= 200:
            return MoveClassification.MISTAKE
        else:
            return MoveClassification.BLUNDER
