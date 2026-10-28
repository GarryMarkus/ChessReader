"""
Vertical engine evaluation bar with Cairo rendering.
Displays dynamic advantage proportion and numeric evaluation badge.
"""

from typing import Optional
import cairo
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Pango, PangoCairo


class EvalBar(Gtk.DrawingArea):
    """Vertical bar indicating White vs Black advantage."""

    def __init__(self, flipped: bool = False):
        super().__init__()
        self.set_size_request(22, -1)
        self.set_vexpand(True)
        self.add_css_class("eval-bar")

        self.flipped = flipped
        self.win_percentage: float = 50.0  # 0 to 100
        self.display_score: str = "0.00"

        self.set_draw_func(self._on_draw)

    def set_evaluation(self, display_score: str, win_percentage: float):
        """Update evaluation score and winning chance (0 - 100%)."""
        self.display_score = display_score
        self.win_percentage = max(0.0, min(100.0, win_percentage))
        self.queue_draw()

    def set_flipped(self, flipped: bool):
        """Update perspective flip."""
        self.flipped = flipped
        self.queue_draw()

    def _on_draw(self, area, ctx: cairo.Context, width: int, height: int):
        if width <= 0 or height <= 0:
            return

        # Border / container radius
        radius = 3.0

        # Background (Black pieces side)
        ctx.set_source_rgba(0.12, 0.13, 0.16, 1.0)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        # White proportion calculation
        # If not flipped, White is at the bottom (fill from bottom up)
        # If flipped, White is at the top (fill from top down)
        white_ratio = self.win_percentage / 100.0
        white_height = height * white_ratio

        ctx.set_source_rgba(0.92, 0.93, 0.95, 1.0)
        if not self.flipped:
            y_start = height - white_height
            ctx.rectangle(0, y_start, width, white_height)
        else:
            ctx.rectangle(0, 0, width, white_height)
        ctx.fill()

        # Center line (50% mark)
        ctx.set_source_rgba(0.4, 0.4, 0.45, 0.8)
        ctx.set_line_width(1.0)
        ctx.move_to(0, height / 2.0)
        ctx.line_to(width, height / 2.0)
        ctx.stroke()

        # Subtle 1px border
        ctx.set_source_rgba(0.2, 0.22, 0.25, 1.0)
        ctx.set_line_width(1.0)
        ctx.rectangle(0.5, 0.5, width - 1.0, height - 1.0)
        ctx.stroke()

        # Text score badge at bottom or top (whichever side is white)
        layout = PangoCairo.create_layout(ctx)
        desc = Pango.FontDescription.from_string("JetBrains Mono Bold 9")
        layout.set_font_description(desc)
        layout.set_text(self.display_score, -1)

        ink, logical = layout.get_pixel_extents()
        text_w = logical.width
        text_h = logical.height

        # Position text badge
        tx = (width - text_w) / 2.0
        if not self.flipped:
            ty = height - text_h - 4.0 if white_ratio >= 0.5 else 4.0
        else:
            ty = 4.0 if white_ratio >= 0.5 else height - text_h - 4.0

        # Contrast text color
        if (not self.flipped and white_ratio >= 0.5) or (self.flipped and white_ratio >= 0.5):
            ctx.set_source_rgba(0.1, 0.1, 0.1, 1.0)
        else:
            ctx.set_source_rgba(0.9, 0.9, 0.9, 1.0)

        ctx.move_to(tx, ty)
        PangoCairo.show_layout(ctx, layout)
