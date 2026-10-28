"""
Scalable Cairo/GSK Chessboard view for GTK4.
Implements 120 FPS piece dragging, click-to-move, legal move indicators, coordinates,
board flipping, and interactive right-click vector arrows and square highlights.
"""

from typing import Optional, List, Dict, Callable
import re
import cairo
import chess
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Pango, PangoCairo

from chess_reader.theme.schema import ChessReaderTheme
from chess_reader.theme.asset_cache import PieceAssetCache
from chess_reader.ui.board.geometry import BoardGeometry
from chess_reader.ui.board.drawings import ArrowDrawing, SquareHighlight, draw_cairo_arrow


def parse_color(color_str: str) -> tuple[float, float, float, float]:
    """Parse hex (#RRGGBB, #RRGGBBAA) or rgba(...) string into normalized 0.0-1.0 floats."""
    if not color_str:
        return (0.0, 0.0, 0.0, 1.0)
    c = color_str.strip()
    if c.startswith('#'):
        hex_val = c.lstrip('#')
        if len(hex_val) == 6:
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            return (r, g, b, 1.0)
        elif len(hex_val) == 8:
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            a = int(hex_val[6:8], 16) / 255.0
            return (r, g, b, a)
    elif c.startswith('rgba') or c.startswith('rgb'):
        nums = [float(x.strip()) for x in re.findall(r'[\d.]+', c)]
        if len(nums) == 3:
            return (nums[0] / 255.0, nums[1] / 255.0, nums[2] / 255.0, 1.0)
        elif len(nums) >= 4:
            return (nums[0] / 255.0, nums[1] / 255.0, nums[2] / 255.0, nums[3])
    return (0.0, 0.0, 0.0, 1.0)


class ChessBoardView(Gtk.DrawingArea):
    """High-performance hardware-accelerated interactive chessboard widget."""

    def __init__(
        self,
        theme: Optional[ChessReaderTheme] = None,
        asset_cache: Optional[PieceAssetCache] = None,
        piece_set: Optional[object] = None
    ):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_focusable(True)

        self.theme: Optional[ChessReaderTheme] = theme
        self.piece_set: Optional[object] = piece_set
        self.asset_cache: PieceAssetCache = asset_cache or PieceAssetCache()
        self.geometry = BoardGeometry(border_width=22.0)

        # Domain State
        self.board = chess.Board()
        self.flipped = False
        self.last_move: Optional[chess.Move] = None

        # Interaction State
        self.selected_square: Optional[chess.Square] = None
        self.legal_moves_for_selected: List[chess.Move] = []

        # Drag state
        self.is_dragging = False
        self.drag_square: Optional[chess.Square] = None
        self.drag_x = 0.0
        self.drag_y = 0.0
        self._drag_start_x = 0.0
        self._drag_start_y = 0.0

        # Annotations (Drawings)
        self.arrows: List[ArrowDrawing] = []
        self.highlights: Dict[chess.Square, SquareHighlight] = {}
        self.active_arrow_color = "rgba(152, 195, 121, 0.85)"  # Green (default)
        self.active_highlight_color = "rgba(152, 195, 121, 0.50)"
        self.active_drawing_color = self.active_arrow_color
        self._right_drag_start: Optional[chess.Square] = None
        self._right_drag_current_square: Optional[chess.Square] = None

        # Pawn Promotion Popover & State
        self._pending_promotion: Optional[tuple[chess.Square, chess.Square]] = None
        self._build_promotion_popover()

        # Callbacks
        self.on_move_made: Optional[Callable[[chess.Move], None]] = None
        self.on_flipped: Optional[Callable[[bool], None]] = None

        # Connect drawing pipeline
        self.set_draw_func(self._on_draw)

        # Attach Event Controllers
        self._setup_input_controllers()

    def _build_promotion_popover(self):
        """Construct interactive popover for underpromotion piece selection."""
        self.promotion_popover = Gtk.Popover()
        self.promotion_popover.set_parent(self)
        self.promotion_popover.set_has_arrow(True)
        self.promotion_popover.connect("closed", self._on_promotion_dismissed)

        pop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pop_box.add_css_class("promotion-popover-box")
        pop_box.set_margin_start(6)
        pop_box.set_margin_end(6)
        pop_box.set_margin_top(6)
        pop_box.set_margin_bottom(6)

        self.promo_buttons: Dict[chess.PieceType, Gtk.Button] = {}
        for p_type, default_lbl in [
            (chess.QUEEN, "♕ Queen (Q)"),
            (chess.KNIGHT, "♘ Knight (N)"),
            (chess.ROOK, "♖ Rook (R)"),
            (chess.BISHOP, "♗ Bishop (B)")
        ]:
            btn = Gtk.Button(label=default_lbl)
            btn.add_css_class("flat")
            btn.add_css_class("promotion-piece-btn")
            btn.connect("clicked", lambda _, pt=p_type: self._on_promotion_selected(pt))
            self.promo_buttons[p_type] = btn
            pop_box.append(btn)

        self.promotion_popover.set_child(pop_box)

    def _is_promotion_move(self, from_sq: chess.Square, to_sq: chess.Square) -> bool:
        """Check whether moving from_sq to to_sq constitutes a pawn promotion."""
        piece = self.board.piece_at(from_sq)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        if piece.color != self.board.turn:
            return False
        target_rank = 7 if piece.color == chess.WHITE else 0
        if chess.square_rank(to_sq) != target_rank:
            return False
        return chess.Move(from_sq, to_sq, promotion=chess.QUEEN) in self.board.legal_moves

    def _prompt_pawn_promotion(self, from_sq: chess.Square, to_sq: chess.Square):
        """Display interactive promotion picker popover at the destination square."""
        self._pending_promotion = (from_sq, to_sq)
        x, y, w, h = self.geometry.square_to_rect(to_sq)
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = int(w)
        rect.height = int(h)
        self.promotion_popover.set_pointing_to(rect)

        is_white = self.board.turn == chess.WHITE
        glyphs = {
            chess.QUEEN: ("♕" if is_white else "♛", "Queen (Q)"),
            chess.KNIGHT: ("♘" if is_white else "♞", "Knight (N)"),
            chess.ROOK: ("♖" if is_white else "♜", "Rook (R)"),
            chess.BISHOP: ("♗" if is_white else "♝", "Bishop (B)")
        }
        for p_type, (glyph, label_text) in glyphs.items():
            self.promo_buttons[p_type].set_label(f"{glyph} {label_text}")

        if self.get_realized() and self.get_root() is not None:
            self.promotion_popover.popup()

    def _on_promotion_selected(self, piece_type: chess.PieceType):
        """Execute selected promotion move."""
        if not self._pending_promotion:
            return
        from_sq, to_sq = self._pending_promotion
        self._pending_promotion = None
        if self.get_realized() and self.get_root() is not None:
            self.promotion_popover.popdown()
        move = chess.Move(from_sq, to_sq, promotion=piece_type)
        if move in self.board.legal_moves:
            self._execute_move(move)

    def _on_promotion_dismissed(self, popover):
        """Handle promotion cancelled without piece selection."""
        if self._pending_promotion:
            self._pending_promotion = None
            self.selected_square = None
            self.legal_moves_for_selected.clear()
            self.queue_draw()

    def _get_drawing_color(self, state: Gdk.ModifierType) -> tuple[str, str]:
        """Return (arrow_color, highlight_color) based on keyboard modifiers."""
        is_shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        is_ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        is_alt = bool(state & Gdk.ModifierType.ALT_MASK)

        if is_ctrl:
            # Red (tactical / threat)
            return ("rgba(224, 108, 117, 0.85)", "rgba(224, 108, 117, 0.50)")
        elif is_shift:
            # Yellow / Amber (caution / alternative)
            return ("rgba(229, 192, 123, 0.85)", "rgba(229, 192, 123, 0.50)")
        elif is_alt:
            # Blue (strategic / positional)
            return ("rgba(97, 175, 239, 0.85)", "rgba(97, 175, 239, 0.50)")
        else:
            # Green (standard / good)
            return ("rgba(152, 195, 121, 0.85)", "rgba(152, 195, 121, 0.50)")

    def set_theme(self, theme: ChessReaderTheme, piece_set: Optional[object] = None):
        """Update active theme and piece set and queue repaint."""
        self.theme = theme
        self.piece_set = piece_set
        self.queue_draw()

    def set_board(self, board: chess.Board, last_move: Optional[chess.Move] = None):
        """Update active board position and redraw."""
        self.board = board
        self.last_move = last_move
        self.selected_square = None
        self.legal_moves_for_selected.clear()
        self.is_dragging = False
        self.drag_square = None
        self.queue_draw()

    def flip(self):
        """Toggle board perspective between White and Black."""
        self.flipped = not self.flipped
        self.geometry.flipped = self.flipped
        self.queue_draw()
        if self.on_flipped:
            self.on_flipped(self.flipped)

    def clear_drawings(self):
        """Clear all user arrow and highlight annotations."""
        self.arrows.clear()
        self.highlights.clear()
        self.queue_draw()

    # -------------------------------------------------------------------------
    # Input Controllers (Click, Drag, Keyboard)
    # -------------------------------------------------------------------------
    def _setup_input_controllers(self):
        # 1. Left Click & Drag for Pieces
        drag_ctrl = Gtk.GestureDrag.new()
        drag_ctrl.set_button(1)
        drag_ctrl.connect("drag-begin", self._on_left_drag_begin)
        drag_ctrl.connect("drag-update", self._on_left_drag_update)
        drag_ctrl.connect("drag-end", self._on_left_drag_end)
        self.add_controller(drag_ctrl)

        # 2. Right Click & Drag for Arrows and Highlights
        right_drag_ctrl = Gtk.GestureDrag.new()
        right_drag_ctrl.set_button(3)
        right_drag_ctrl.connect("drag-begin", self._on_right_drag_begin)
        right_drag_ctrl.connect("drag-update", self._on_right_drag_update)
        right_drag_ctrl.connect("drag-end", self._on_right_drag_end)
        self.add_controller(right_drag_ctrl)

        # 3. Keyboard Controller (F for Flip)
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_left_drag_begin(self, gesture, start_x, start_y):
        self.grab_focus()
        square = self.geometry.point_to_square(start_x, start_y)
        self._drag_start_x = start_x
        self._drag_start_y = start_y

        if square is None:
            # Clicked outside board -> clear selection & drawings
            if self.selected_square is not None or self.arrows or self.highlights:
                self.selected_square = None
                self.legal_moves_for_selected.clear()
                self.clear_drawings()
            return

        # Check if clicking on an already selected piece's legal destination
        if self.selected_square is not None and square != self.selected_square:
            if self._is_promotion_move(self.selected_square, square):
                self._prompt_pawn_promotion(self.selected_square, square)
                return
            move = self._find_legal_move(self.selected_square, square)
            if move:
                self._execute_move(move)
                return

        # Check if clicking a piece belonging to the active player
        piece = self.board.piece_at(square)
        if piece and piece.color == self.board.turn:
            self.selected_square = square
            self.legal_moves_for_selected = [
                m for m in self.board.legal_moves if m.from_square == square
            ]
            self.is_dragging = True
            self.drag_square = square
            self.drag_x = start_x
            self.drag_y = start_y
            self.queue_draw()
        else:
            # Clicked empty square or opponent piece -> clear selection
            self.selected_square = None
            self.legal_moves_for_selected.clear()
            self.clear_drawings()
            self.queue_draw()

    def _on_left_drag_update(self, gesture, offset_x, offset_y):
        if self.is_dragging:
            self.drag_x = self._drag_start_x + offset_x
            self.drag_y = self._drag_start_y + offset_y
            self.queue_draw()

    def _on_left_drag_end(self, gesture, offset_x, offset_y):
        if not self.is_dragging:
            return

        drop_x = self._drag_start_x + offset_x
        drop_y = self._drag_start_y + offset_y
        dest_square = self.geometry.point_to_square(drop_x, drop_y)

        from_sq = self.drag_square
        self.is_dragging = False
        self.drag_square = None

        if dest_square is not None and from_sq is not None and dest_square != from_sq:
            if self._is_promotion_move(from_sq, dest_square):
                self._prompt_pawn_promotion(from_sq, dest_square)
                return
            move = self._find_legal_move(from_sq, dest_square)
            if move:
                self._execute_move(move)
                return

        # If dropped on same square or invalid, keep square selected for click-to-move
        self.queue_draw()

    def _on_right_drag_begin(self, gesture, start_x, start_y):
        self._right_drag_start_x = start_x
        self._right_drag_start_y = start_y
        sq = self.geometry.point_to_square(start_x, start_y)
        self._right_drag_start = sq
        self._right_drag_current_square = sq
        state = gesture.get_current_event_state()
        self.active_arrow_color, self.active_highlight_color = self._get_drawing_color(state)
        self.active_drawing_color = self.active_arrow_color

    def _on_right_drag_update(self, gesture, offset_x, offset_y):
        curr_x = getattr(self, "_right_drag_start_x", 0.0) + offset_x
        curr_y = getattr(self, "_right_drag_start_y", 0.0) + offset_y
        sq = self.geometry.point_to_square(curr_x, curr_y)
        if sq != self._right_drag_current_square:
            self._right_drag_current_square = sq
            self.queue_draw()

    def _on_right_drag_end(self, gesture, offset_x, offset_y):
        from_sq = self._right_drag_start
        to_sq = self._right_drag_current_square
        self._right_drag_start = None
        self._right_drag_current_square = None

        if from_sq is None:
            return

        if to_sq is None or to_sq == from_sq:
            # Single right-click -> toggle square highlight
            if from_sq in self.highlights:
                del self.highlights[from_sq]
            else:
                self.highlights[from_sq] = SquareHighlight(
                    square=from_sq,
                    color=self.active_highlight_color
                )
        else:
            # Dragged between two squares -> toggle arrow
            arrow = ArrowDrawing(from_square=from_sq, to_square=to_sq, color=self.active_arrow_color)
            if arrow in self.arrows:
                self.arrows.remove(arrow)
            else:
                self.arrows.append(arrow)

        self.queue_draw()

    def _on_key_pressed(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if self._pending_promotion:
            if keyname in ("q", "Q"):
                self._on_promotion_selected(chess.QUEEN)
                return True
            elif keyname in ("n", "N"):
                self._on_promotion_selected(chess.KNIGHT)
                return True
            elif keyname in ("r", "R"):
                self._on_promotion_selected(chess.ROOK)
                return True
            elif keyname in ("b", "B"):
                self._on_promotion_selected(chess.BISHOP)
                return True
            elif keyname in ("Escape",):
                if self.get_realized() and self.get_root() is not None:
                    self.promotion_popover.popdown()
                else:
                    self._on_promotion_dismissed(None)
                return True

        if keyname in ("f", "F"):
            self.flip()
            return True
        return False

    def _find_legal_move(self, from_sq: chess.Square, to_sq: chess.Square) -> Optional[chess.Move]:
        # Check standard moves or queen promotion by default
        for promo in [chess.QUEEN, None, chess.KNIGHT, chess.ROOK, chess.BISHOP]:
            m = chess.Move(from_sq, to_sq, promotion=promo)
            if m in self.board.legal_moves:
                return m
        return None

    def _execute_move(self, move: chess.Move):
        self.board.push(move)
        self.last_move = move
        self.selected_square = None
        self.legal_moves_for_selected.clear()
        self.clear_drawings()
        self.queue_draw()

        if self.on_move_made:
            self.on_move_made(move)

    # -------------------------------------------------------------------------
    # Cairo Drawing Pipeline (120 FPS capable)
    # -------------------------------------------------------------------------
    def _on_draw(self, area, ctx: cairo.Context, width: int, height: int):
        self.geometry.update_bounds(width, height, border_width=22.0)
        sq_size = self.geometry.square_size
        if sq_size <= 0:
            return

        # 1. Background: Neutral dark container background (no board color spill!)
        ctx.set_source_rgba(0.094, 0.094, 0.106, 1.0)  # #18181b
        ctx.paint()

        # 2. Board Frame & Border (ChessBase style)
        tot_sz = self.geometry.total_size
        bx = self.geometry.offset_x
        by = self.geometry.offset_y
        border_c = parse_color(self.theme.board.border_color if self.theme else "#23272e")
        ctx.set_source_rgba(border_c[0], border_c[1], border_c[2], 1.0)
        ctx.rectangle(bx, by, tot_sz, tot_sz)
        ctx.fill()

        # Crisp outer border frame stroke
        ctx.set_source_rgba(0.25, 0.27, 0.32, 0.8)
        ctx.set_line_width(1.0)
        ctx.rectangle(bx + 0.5, by + 0.5, tot_sz - 1.0, tot_sz - 1.0)
        ctx.stroke()

        # 3. Board Grid (Squares)
        self._draw_grid_squares(ctx)

        # 4. Coordinate Labels (Above/On border, ChessBase style)
        self._draw_coordinates(ctx)

        # 5. State Highlights (Last Move, Check, Selection)
        self._draw_highlights(ctx)

        # 6. Static Pieces
        self._draw_pieces(ctx)

        # 7. Legal Move Indicators
        self._draw_legal_move_indicators(ctx)

        # 8. Interactive Drawings (Arrows & Live Drag)
        self._draw_annotations(ctx)

        # 9. Floating Dragged Piece
        if self.is_dragging and self.drag_square is not None:
            self._draw_dragged_piece(ctx)

    def _draw_grid_squares(self, ctx: cairo.Context):
        sq_size = self.geometry.square_size
        scale_factor = self.get_scale_factor()
        board_sz = int(self.geometry.board_size)
        sx = self.geometry.squares_offset_x
        sy = self.geometry.squares_offset_y

        # 1. Full-board backdrop image rendering
        if self.theme and self.theme.board.type == "backdrop":
            backdrop_surf = self.asset_cache.get_board_backdrop_surface(self.theme, board_sz, scale_factor)
            if backdrop_surf:
                ctx.save()
                if self.flipped:
                    cx = sx + (board_sz / 2.0)
                    cy = sy + (board_sz / 2.0)
                    ctx.translate(cx, cy)
                    ctx.rotate(3.141592653589793)
                    ctx.translate(-cx, -cy)
                ctx.set_source_surface(backdrop_surf, sx, sy)
                ctx.paint()
                ctx.restore()

                # Inner border outline between squares and border rim
                ctx.set_source_rgba(0.12, 0.13, 0.16, 0.9)
                ctx.set_line_width(1.0)
                ctx.rectangle(sx - 0.5, sy - 0.5, board_sz + 1.0, board_sz + 1.0)
                ctx.stroke()
                return

        # 2. Standard solid/dual-tile square grid rendering
        light_color = parse_color(self.theme.board.light_square if self.theme else "#2d3139")
        dark_color = parse_color(self.theme.board.dark_square if self.theme else "#1e2227")

        for sq in range(64):
            x, y, w, h = self.geometry.square_to_rect(sq)
            is_light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 != 0
            color = light_color if is_light else dark_color
            ctx.set_source_rgba(color[0], color[1], color[2], color[3])
            ctx.rectangle(x, y, w, h)
            ctx.fill()

        # Inner border outline between squares and border rim
        ctx.set_source_rgba(0.12, 0.13, 0.16, 0.9)
        ctx.set_line_width(1.0)
        ctx.rectangle(sx - 0.5, sy - 0.5, board_sz + 1.0, board_sz + 1.0)
        ctx.stroke()

    def _draw_coordinates(self, ctx: cairo.Context):
        if self.theme and not self.theme.board.coordinates.show:
            return

        font_size = self.theme.board.coordinates.font_size if self.theme else 10
        font_family = self.theme.board.coordinates.font_family if self.theme else "JetBrains Mono"
        light_c = parse_color(self.theme.board.coordinates.light_color if self.theme else "#a1a1aa")
        dark_c = parse_color(self.theme.board.coordinates.dark_color if self.theme else "#d4d4d8")

        layout = PangoCairo.create_layout(ctx)
        desc = Pango.FontDescription.from_string(f"{font_family} Bold {font_size}")
        layout.set_font_description(desc)

        files = "abcdefgh"
        ranks = "12345678"
        sq_size = self.geometry.square_size
        border = self.geometry.effective_border

        if border >= 12.0:
            # ChessBase Style: Render notation cleanly on the border margins
            # 1. Files along bottom and top border
            for col in range(8):
                file_char = files[7 - col] if self.flipped else files[col]
                layout.set_text(file_char, -1)
                ink, logical = layout.get_pixel_extents()
                cx = self.geometry.squares_offset_x + (col * sq_size) + (sq_size / 2.0) - (logical.width / 2.0)
                
                # Bottom border
                cy_bot = self.geometry.offset_y + self.geometry.total_size - (border / 2.0) - (logical.height / 2.0)
                ctx.set_source_rgba(dark_c[0], dark_c[1], dark_c[2], dark_c[3])
                ctx.move_to(cx, cy_bot)
                PangoCairo.show_layout(ctx, layout)

                # Top border
                cy_top = self.geometry.offset_y + (border / 2.0) - (logical.height / 2.0)
                ctx.move_to(cx, cy_top)
                PangoCairo.show_layout(ctx, layout)

            # 2. Ranks along left and right border
            for row in range(8):
                rank_char = ranks[row] if self.flipped else ranks[7 - row]
                layout.set_text(rank_char, -1)
                ink, logical = layout.get_pixel_extents()
                cy = self.geometry.squares_offset_y + (row * sq_size) + (sq_size / 2.0) - (logical.height / 2.0)

                # Left border
                cx_left = self.geometry.offset_x + (border / 2.0) - (logical.width / 2.0)
                ctx.set_source_rgba(dark_c[0], dark_c[1], dark_c[2], dark_c[3])
                ctx.move_to(cx_left, cy)
                PangoCairo.show_layout(ctx, layout)

                # Right border
                cx_right = self.geometry.offset_x + self.geometry.total_size - (border / 2.0) - (logical.width / 2.0)
                ctx.move_to(cx_right, cy)
                PangoCairo.show_layout(ctx, layout)
        else:
            # Fallback to inside square coordinates if no border
            for col in range(8):
                file_char = files[7 - col] if self.flipped else files[col]
                sq = chess.square(7 - col if self.flipped else col, 0 if not self.flipped else 7)
                x, y, w, h = self.geometry.square_to_rect(sq)
                is_light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 != 0
                color = dark_c if is_light else light_c

                layout.set_text(file_char, -1)
                ctx.set_source_rgba(color[0], color[1], color[2], color[3])
                ctx.move_to(x + w - 12.0, y + h - 14.0)
                PangoCairo.show_layout(ctx, layout)

            for row in range(8):
                rank_char = ranks[row] if self.flipped else ranks[7 - row]
                sq = chess.square(0 if not self.flipped else 7, row if self.flipped else 7 - row)
                x, y, w, h = self.geometry.square_to_rect(sq)
                is_light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 != 0
                color = dark_c if is_light else light_c

                layout.set_text(rank_char, -1)
                ctx.set_source_rgba(color[0], color[1], color[2], color[3])
                ctx.move_to(x + 3.0, y + 2.0)
                PangoCairo.show_layout(ctx, layout)

    def _draw_highlights(self, ctx: cairo.Context):
        # 1. Last Move Highlight
        if self.last_move:
            lm_color = parse_color(
                self.theme.board.highlights.last_move if self.theme else "rgba(229, 192, 123, 0.22)"
            )
            for sq in (self.last_move.from_square, self.last_move.to_square):
                x, y, w, h = self.geometry.square_to_rect(sq)
                ctx.set_source_rgba(lm_color[0], lm_color[1], lm_color[2], lm_color[3])
                ctx.rectangle(x, y, w, h)
                ctx.fill()

        # 2. Check Highlight
        if self.board.is_check():
            king_sq = self.board.king(self.board.turn)
            if king_sq is not None:
                check_color = parse_color(
                    self.theme.board.highlights.check if self.theme else "rgba(224, 108, 117, 0.65)"
                )
                x, y, w, h = self.geometry.square_to_rect(king_sq)
                ctx.set_source_rgba(check_color[0], check_color[1], check_color[2], check_color[3])
                ctx.rectangle(x, y, w, h)
                ctx.fill()

        # 3. User Square Highlights (from right-clicks)
        for sq, highlight in self.highlights.items():
            x, y, w, h = self.geometry.square_to_rect(sq)
            c = parse_color(highlight.color)
            ctx.set_source_rgba(c[0], c[1], c[2], c[3])
            ctx.rectangle(x, y, w, h)
            ctx.fill()

        # 4. Selected Square Highlight
        if self.selected_square is not None:
            sel_color = parse_color(
                self.theme.board.highlights.selected_square if self.theme else "rgba(97, 175, 239, 0.35)"
            )
            x, y, w, h = self.geometry.square_to_rect(self.selected_square)
            ctx.set_source_rgba(sel_color[0], sel_color[1], sel_color[2], sel_color[3])
            ctx.rectangle(x, y, w, h)
            ctx.fill()

    def _draw_pieces(self, ctx: cairo.Context):
        sq_size = int(self.geometry.square_size)
        scale_factor = self.get_scale_factor()

        for sq in range(64):
            if self.is_dragging and sq == self.drag_square:
                continue  # Drawn in floating layer

            piece = self.board.piece_at(sq)
            if piece:
                sym = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
                surf = self.asset_cache.get_piece_surface(
                    self.theme, sym, sq_size, scale_factor, piece_set=self.piece_set
                )
                x, y, _, _ = self.geometry.square_to_rect(sq)

                ctx.save()
                ctx.set_source_surface(surf, x, y)
                ctx.paint()
                ctx.restore()

    def _draw_legal_move_indicators(self, ctx: cairo.Context):
        if not self.selected_square or not self.legal_moves_for_selected:
            return

        dot_color = parse_color(
            self.theme.board.highlights.legal_move_dot if self.theme else "rgba(171, 178, 191, 0.45)"
        )
        sq_size = self.geometry.square_size

        for move in self.legal_moves_for_selected:
            to_sq = move.to_square
            cx, cy = self.geometry.square_center(to_sq)
            piece_at_dest = self.board.piece_at(to_sq)

            ctx.save()
            ctx.set_source_rgba(dot_color[0], dot_color[1], dot_color[2], dot_color[3])

            if piece_at_dest:
                # Capture Ring around the square
                ctx.set_line_width(sq_size * 0.08)
                radius = sq_size * 0.44
                ctx.arc(cx, cy, radius, 0, 2 * 3.14159)
                ctx.stroke()
            else:
                # Small solid dot at center
                radius = sq_size * 0.16
                ctx.arc(cx, cy, radius, 0, 2 * 3.14159)
                ctx.fill()

            ctx.restore()

    def _draw_annotations(self, ctx: cairo.Context):
        sq_size = self.geometry.square_size

        # Render committed arrows
        for arrow in self.arrows:
            sx, sy = self.geometry.square_center(arrow.from_square)
            ex, ey = self.geometry.square_center(arrow.to_square)
            c = parse_color(arrow.color)
            draw_cairo_arrow(
                ctx, sx, sy, ex, ey,
                c[0], c[1], c[2], c[3],
                shaft_width=sq_size * 0.18,
                head_length=sq_size * 0.36,
                head_width=sq_size * 0.40
            )

        # Render active right-drag preview arrow
        if self._right_drag_start is not None and self._right_drag_current_square is not None:
            if self._right_drag_start != self._right_drag_current_square:
                sx, sy = self.geometry.square_center(self._right_drag_start)
                ex, ey = self.geometry.square_center(self._right_drag_current_square)
                c = parse_color(self.active_drawing_color)
                draw_cairo_arrow(
                    ctx, sx, sy, ex, ey,
                    c[0], c[1], c[2], 0.55,  # Slightly translucent preview
                    shaft_width=sq_size * 0.18,
                    head_length=sq_size * 0.36,
                    head_width=sq_size * 0.40
                )

    def _draw_dragged_piece(self, ctx: cairo.Context):
        piece = self.board.piece_at(self.drag_square)
        if not piece:
            return

        sq_size = int(self.geometry.square_size)
        scale_factor = self.get_scale_factor()
        sym = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
        surf = self.asset_cache.get_piece_surface(
            self.theme, sym, sq_size, scale_factor, piece_set=self.piece_set
        )

        # Centered on mouse cursor
        px = self.drag_x - (sq_size / 2.0)
        py = self.drag_y - (sq_size / 2.0)

        ctx.save()
        # Drop shadow for floating effect
        ctx.set_source_rgba(0, 0, 0, 0.25)
        ctx.rectangle(px + 4, py + 6, sq_size, sq_size)
        ctx.fill()

        # Floating piece
        ctx.set_source_surface(surf, px, py)
        ctx.paint_with_alpha(0.92)
        ctx.restore()
