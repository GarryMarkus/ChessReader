"""
Vector Centipawn Loss (CPL) evaluation momentum graph drawn with Cairo.
Displays full game trajectory, zero-equality centerline, and interactive move jumping.
"""

from typing import List, Tuple, Optional, Callable
import cairo
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class CPLGraphView(Gtk.DrawingArea):
    """Vector momentum chart showing evaluation swings across game plies."""

    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 90)
        self.set_hexpand(True)
        self.add_css_class("cpl-graph-view")

        # Data points: [(ply, eval_pawns)]
        self.data_points: List[Tuple[int, float]] = [(0, 0.0)]
        self.current_ply: int = 0
        self.on_ply_selected: Optional[Callable[[int], None]] = None

        self.set_draw_func(self._on_draw)

        # Click controller to jump to move
        click_ctrl = Gtk.GestureClick.new()
        click_ctrl.set_button(1)
        click_ctrl.connect("pressed", self._on_clicked)
        self.add_controller(click_ctrl)

    def set_data(self, data_points: List[Tuple[int, float]], current_ply: int = 0):
        """Update evaluation points and redraw."""
        self.data_points = data_points if data_points else [(0, 0.0)]
        self.current_ply = current_ply
        self.queue_draw()

    def set_current_ply(self, ply: int):
        """Update current position marker."""
        self.current_ply = ply
        self.queue_draw()

    def _on_clicked(self, gesture, n_press, x, y):
        width = self.get_width() or getattr(self, "_last_width", 0)
        total_plies = max(1, len(self.data_points) - 1)
        if width > 0 and self.on_ply_selected:
            clicked_ply = int((x / width) * total_plies)
            clicked_ply = max(0, min(total_plies, clicked_ply))
            self.on_ply_selected(clicked_ply)

    def _on_draw(self, area, ctx: cairo.Context, width: int, height: int):
        self._last_width = width
        if width <= 0 or height <= 0 or not self.data_points:
            return

        # 1. Background
        ctx.set_source_rgba(0.09, 0.10, 0.12, 1.0)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        # 2. Zero centerline
        mid_y = height / 2.0
        ctx.set_source_rgba(0.25, 0.28, 0.32, 0.8)
        ctx.set_line_width(1.0)
        ctx.move_to(0, mid_y)
        ctx.line_to(width, mid_y)
        ctx.stroke()

        # Scaling: max eval clamped to +/- 5 pawns for clean visual curve
        max_pawns = 5.0
        total_points = len(self.data_points)
        x_step = width / max(1, total_points - 1)

        def eval_to_y(ev: float) -> float:
            clamped = max(-max_pawns, min(max_pawns, ev))
            # positive is above center, negative is below center
            return mid_y - (clamped / max_pawns) * (mid_y - 8.0)

        # 3. Fill Area (White advantage above, Black below)
        # Create filled polygon
        ctx.save()
        ctx.move_to(0, mid_y)
        for i, (ply, ev) in enumerate(self.data_points):
            px = i * x_step
            py = eval_to_y(ev)
            ctx.line_to(px, py)
        ctx.line_to(width, mid_y)
        ctx.close_path()

        # Subtle translucent fill
        ctx.set_source_rgba(0.38, 0.69, 0.94, 0.22)
        ctx.fill()
        ctx.restore()

        # 4. Stroke line
        ctx.save()
        ctx.set_line_width(2.0)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(0.38, 0.69, 0.94, 0.90)

        for i, (ply, ev) in enumerate(self.data_points):
            px = i * x_step
            py = eval_to_y(ev)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()
        ctx.restore()

        # 5. Current Ply Marker line
        if 0 <= self.current_ply < total_points:
            cur_x = self.current_ply * x_step
            ctx.set_source_rgba(0.95, 0.75, 0.48, 0.9)
            ctx.set_line_width(1.5)
            ctx.move_to(cur_x, 0)
            ctx.line_to(cur_x, height)
            ctx.stroke()

        # 6. Border
        ctx.set_source_rgba(0.18, 0.19, 0.22, 1.0)
        ctx.set_line_width(1.0)
        ctx.rectangle(0.5, 0.5, width - 1.0, height - 1.0)
        ctx.stroke()
