"""
Piece animation trajectory detection and easing for ChessReader.
Calculates smooth forward and reverse piece animations, simultaneous
castling rooks, and captured piece transitions with cubic ease-out.
"""

from dataclasses import dataclass
from typing import Optional
import chess


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out: responsive initial velocity with natural deceleration."""
    clamped = max(0.0, min(1.0, t))
    return 1.0 - ((1.0 - clamped) ** 3)


@dataclass
class PieceAnimation:
    """Trajectory and state of an in-flight piece animation."""
    piece_symbol: str                    # Primary moving piece (e.g. 'wP', 'bK')
    from_square: chess.Square            # Screen starting square
    to_square: chess.Square              # Screen destination square
    target_square: chess.Square          # Square on new board to suppress static rendering
    start_time_us: int                   # Monotonic start time in microseconds
    duration_us: int = 150_000           # Animation duration in microseconds (150ms)

    # Secondary piece (for simultaneous castling rook)
    secondary_piece_symbol: Optional[str] = None
    secondary_from_square: Optional[chess.Square] = None
    secondary_to_square: Optional[chess.Square] = None
    secondary_target_square: Optional[chess.Square] = None

    # Captured piece (for fade out)
    captured_piece_symbol: Optional[str] = None
    captured_square: Optional[chess.Square] = None
    is_reverse: bool = False             # True if stepping backward / undoing move

    def get_progress(self, current_time_us: int) -> float:
        """Return normalized animation progress (0.0 to 1.0) with cubic ease-out applied."""
        elapsed = current_time_us - self.start_time_us
        if elapsed <= 0:
            return 0.0
        if elapsed >= self.duration_us:
            return 1.0
        linear = elapsed / self.duration_us
        return ease_out_cubic(linear)

    def is_finished(self, current_time_us: int) -> bool:
        """Check whether the animation has completed its duration."""
        return (current_time_us - self.start_time_us) >= self.duration_us


def detect_move_animation(
    old_board: Optional[chess.Board],
    new_board: chess.Board,
    last_move: Optional[chess.Move],
    start_time_us: int,
    duration_us: int = 150_000
) -> Optional[PieceAnimation]:
    """
    Detect whether transitioning from old_board to new_board is a 1-ply forward
    or backward move and construct the corresponding PieceAnimation trajectory.
    Returns None if the board jump is multi-ply, a game reset, or identical.
    """
    if old_board is None:
        return None

    if old_board.board_fen() == new_board.board_fen():
        return None

    # 1. Forward 1-ply transition check
    if last_move and last_move in old_board.legal_moves:
        test = old_board.copy()
        test.push(last_move)
        if test.board_fen() == new_board.board_fen():
            return _build_forward_animation(old_board, new_board, last_move, start_time_us, duration_us)

    # Search old_board legal moves in case last_move was omitted
    for m in old_board.legal_moves:
        test = old_board.copy()
        test.push(m)
        if test.board_fen() == new_board.board_fen():
            return _build_forward_animation(old_board, new_board, m, start_time_us, duration_us)

    # 2. Backward 1-ply transition check (undo / previous move)
    # If pushing a move on new_board yields old_board, we just stepped backward
    for m in new_board.legal_moves:
        test = new_board.copy()
        test.push(m)
        if test.board_fen() == old_board.board_fen():
            return _build_backward_animation(old_board, new_board, m, start_time_us, duration_us)

    return None


def _build_forward_animation(
    old_board: chess.Board,
    new_board: chess.Board,
    move: chess.Move,
    start_time_us: int,
    duration_us: int
) -> Optional[PieceAnimation]:
    moving_piece = old_board.piece_at(move.from_square)
    if not moving_piece:
        return None

    sym = ("w" if moving_piece.color == chess.WHITE else "b") + moving_piece.symbol().upper()

    # Castling detection
    sec_sym = None
    sec_from = None
    sec_to = None
    sec_target = None

    if old_board.is_kingside_castling(move):
        if moving_piece.color == chess.WHITE:
            sec_from, sec_to = chess.H1, chess.F1
            sec_sym = "wR"
        else:
            sec_from, sec_to = chess.H8, chess.F8
            sec_sym = "bR"
        sec_target = sec_to
    elif old_board.is_queenside_castling(move):
        if moving_piece.color == chess.WHITE:
            sec_from, sec_to = chess.A1, chess.D1
            sec_sym = "wR"
        else:
            sec_from, sec_to = chess.A8, chess.D8
            sec_sym = "bR"
        sec_target = sec_to

    # Capture detection
    cap_sym = None
    cap_sq = None
    if old_board.is_en_passant(move):
        cap_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        cap_piece = old_board.piece_at(cap_sq)
        if cap_piece:
            cap_sym = ("w" if cap_piece.color == chess.WHITE else "b") + cap_piece.symbol().upper()
    elif old_board.is_capture(move):
        cap_sq = move.to_square
        cap_piece = old_board.piece_at(cap_sq)
        if cap_piece:
            cap_sym = ("w" if cap_piece.color == chess.WHITE else "b") + cap_piece.symbol().upper()

    return PieceAnimation(
        piece_symbol=sym,
        from_square=move.from_square,
        to_square=move.to_square,
        target_square=move.to_square,
        start_time_us=start_time_us,
        duration_us=duration_us,
        secondary_piece_symbol=sec_sym,
        secondary_from_square=sec_from,
        secondary_to_square=sec_to,
        secondary_target_square=sec_target,
        captured_piece_symbol=cap_sym,
        captured_square=cap_sq,
        is_reverse=False
    )


def _build_backward_animation(
    old_board: chess.Board,
    new_board: chess.Board,
    move: chess.Move,
    start_time_us: int,
    duration_us: int
) -> Optional[PieceAnimation]:
    moving_piece = new_board.piece_at(move.from_square)
    if not moving_piece:
        return None

    sym = ("w" if moving_piece.color == chess.WHITE else "b") + moving_piece.symbol().upper()

    # Castling detection in reverse
    sec_sym = None
    sec_from = None
    sec_to = None
    sec_target = None

    if new_board.is_kingside_castling(move):
        if moving_piece.color == chess.WHITE:
            sec_from, sec_to = chess.F1, chess.H1
            sec_sym = "wR"
        else:
            sec_from, sec_to = chess.F8, chess.H8
            sec_sym = "bR"
        sec_target = sec_to
    elif new_board.is_queenside_castling(move):
        if moving_piece.color == chess.WHITE:
            sec_from, sec_to = chess.D1, chess.A1
            sec_sym = "wR"
        else:
            sec_from, sec_to = chess.D8, chess.A8
            sec_sym = "bR"
        sec_target = sec_to

    # Capture detection in reverse
    cap_sym = None
    cap_sq = None
    if new_board.is_en_passant(move):
        cap_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        cap_piece = new_board.piece_at(cap_sq)
        if cap_piece:
            cap_sym = ("w" if cap_piece.color == chess.WHITE else "b") + cap_piece.symbol().upper()
    elif new_board.is_capture(move):
        cap_sq = move.to_square
        cap_piece = new_board.piece_at(cap_sq)
        if cap_piece:
            cap_sym = ("w" if cap_piece.color == chess.WHITE else "b") + cap_piece.symbol().upper()

    # Reversing motion: piece glides from destination back to origin
    return PieceAnimation(
        piece_symbol=sym,
        from_square=move.to_square,
        to_square=move.from_square,
        target_square=move.from_square,
        start_time_us=start_time_us,
        duration_us=duration_us,
        secondary_piece_symbol=sec_sym,
        secondary_from_square=sec_from,
        secondary_to_square=sec_to,
        secondary_target_square=sec_target,
        captured_piece_symbol=cap_sym,
        captured_square=cap_sq,
        is_reverse=True
    )
