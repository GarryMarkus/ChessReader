"""
Vertical engine evaluation bar with Cairo rendering and external score indicator.
Displays dynamic White vs Black advantage proportion with the numeric score
positioned clearly BELOW the bar with explicit '+' or '-' signs.
"""

from typing import Optional
import re
import cairo
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class EvalBar(Gtk.Box):
    """Vertical bar indicating White vs Black advantage with score display below the bar."""

    def __init__(self, flipped: bool = False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_size_request(32, -1)
        self.set_vexpand(True)
        self.add_css_class("eval-bar-container")

        self.flipped = flipped
        self.win_percentage: float = 50.0  # 0 to 100
        self.display_score: str = "+0.00"

        # 1. Vertical Advantage Proportion Bar
        self.bar_area = Gtk.DrawingArea()
        self.bar_area.set_size_request(20, -1)
        self.bar_area.set_vexpand(True)
        self.bar_area.set_hexpand(True)
        self.bar_area.add_css_class("eval-bar")
        self.bar_area.set_draw_func(self._on_draw)
        self.append(self.bar_area)

        # 2. Score Badge positioned cleanly BELOW the bar
        self.score_label = Gtk.Label(label="+0.0")
        self.score_label.add_css_class("eval-score-label")
        self.score_label.add_css_class("eval-score-even")
        self.score_label.set_hexpand(True)
        self.append(self.score_label)

    def set_evaluation(self, display_score: str, win_percentage: float):
        """Update evaluation score and winning chance (0 - 100%)."""
        formatted = self._format_score(display_score)
        self.display_score = formatted
        self.win_percentage = max(0.0, min(100.0, win_percentage))

        self.score_label.set_text(self.display_score)
        self._update_score_class(self.display_score)
        self.bar_area.queue_draw()

    def set_flipped(self, flipped: bool):
        """Update perspective flip."""
        self.flipped = flipped
        self.bar_area.queue_draw()

    def _format_score(self, raw_score: str) -> str:
        """Format score string ensuring explicit '+' or '-' prefix."""
        s = raw_score.strip()
        if not s:
            return "+0.0"

        # Mate scores
        if s.startswith("#") or "M" in s:
            cleaned = s.lstrip("#M ")
            try:
                m_val = int(cleaned)
                return f"+M{m_val}" if m_val > 0 else f"-M{abs(m_val)}"
            except ValueError:
                return s if s.startswith(("+", "-")) else f"+{s}"

        # Centipawn / decimal float scores
        try:
            val = float(s)
            if val > 0:
                return f"+{val:.1f}" if not s.startswith("+") else s
            elif val < 0:
                return f"{val:.1f}"
            else:
                return "0.0"
        except ValueError:
            return s if s.startswith(("+", "-")) else f"+{s}"

    def _update_score_class(self, score_str: str):
        self.score_label.remove_css_class("eval-score-pos")
        self.score_label.remove_css_class("eval-score-neg")
        self.score_label.remove_css_class("eval-score-even")

        if score_str.startswith("+"):
            self.score_label.add_css_class("eval-score-pos")
        elif score_str.startswith("-"):
            self.score_label.add_css_class("eval-score-neg")
        else:
            self.score_label.add_css_class("eval-score-even")

    def _on_draw(self, area, ctx: cairo.Context, width: int, height: int):
        if width <= 0 or height <= 0:
            return

        # Background (Black pieces side - dark charcoal)
        ctx.set_source_rgba(0.12, 0.13, 0.16, 1.0)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        # White proportion calculation
        # If not flipped, White is at bottom (fills upward)
        # If flipped, White is at top (fills downward)
        white_ratio = self.win_percentage / 100.0
        white_height = height * white_ratio

        # White side advantage (soft off-white)
        ctx.set_source_rgba(0.92, 0.93, 0.96, 1.0)
        if not self.flipped:
            y_start = height - white_height
            ctx.rectangle(0, y_start, width, white_height)
        else:
            ctx.rectangle(0, 0, width, white_height)
        ctx.fill()

        # Center line (50% mark)
        ctx.set_source_rgba(0.42, 0.44, 0.50, 0.85)
        ctx.set_line_width(1.0)
        ctx.move_to(0, height / 2.0)
        ctx.line_to(width, height / 2.0)
        ctx.stroke()

        # Crisp 1px border around the vertical bar
        ctx.set_source_rgba(0.22, 0.24, 0.28, 1.0)
        ctx.set_line_width(1.0)
        ctx.rectangle(0.5, 0.5, width - 1.0, height - 1.0)
        ctx.stroke()
