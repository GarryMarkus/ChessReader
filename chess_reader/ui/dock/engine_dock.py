"""
Collapsible bottom Engine Analysis Dock for Multi-PV lines and CPL momentum graph.
"""

from typing import Optional, Callable
import gi
import chess

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from chess_reader.engine.analyzer import AnalysisSnapshot, AnalysisLine
from chess_reader.ui.dock.cpl_graph import CPLGraphView


class EngineDock(Gtk.Box):
    """Collapsible bottom dock displaying live Multi-PV lines or CPL momentum curve."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("engine-dock")

        self.is_collapsed = False
        self.on_candidate_line_clicked: Optional[Callable[[chess.Move], None]] = None

        # 1. Dock Header Bar
        self.header = self._build_header()
        self.append(self.header)

        # 2. Dock Content Stack (Live Multi-PV vs Momentum Graph)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content_box.add_css_class("engine-dock-content")
        self.append(self.content_box)

        # Multi-PV Lines Container
        self.lines_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.content_box.append(self.lines_container)

        # Vector CPL Graph (initially visible alongside lines or toggleable)
        self.cpl_graph = CPLGraphView()
        self.content_box.append(self.cpl_graph)

        # Initial placeholder lines
        self._build_placeholder_lines()

    def _build_header(self) -> Gtk.Box:
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("engine-dock-header")

        # Collapse / Expand Toggle
        self.toggle_btn = Gtk.Button(label="▾")
        self.toggle_btn.set_tooltip_text("Collapse/Expand Analysis Dock")
        self.toggle_btn.add_css_class("flat")
        self.toggle_btn.connect("clicked", self._on_toggle_collapse)
        header.append(self.toggle_btn)

        # Engine Name & Depth Badge
        self.status_label = Gtk.Label(label="Stockfish 18 · Idle")
        self.status_label.add_css_class("engine-header-title")
        header.append(self.status_label)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        # Multi-PV Toggle
        self.multipv_btn = Gtk.Button(label="3 Lines")
        self.multipv_btn.set_tooltip_text("Multi-PV candidate lines")
        self.multipv_btn.add_css_class("flat")
        self.multipv_btn.add_css_class("engine-header-badge")
        header.append(self.multipv_btn)

        return header

    def _on_toggle_collapse(self, btn):
        self.is_collapsed = not self.is_collapsed
        self.content_box.set_visible(not self.is_collapsed)
        self.toggle_btn.set_label("▴" if self.is_collapsed else "▾")

    def _build_placeholder_lines(self):
        while child := self.lines_container.get_first_child():
            self.lines_container.remove(child)

        lbl = Gtk.Label(label="Engine idle. Start analysis or play a move.")
        lbl.add_css_class("comment-block")
        self.lines_container.append(lbl)

    def update_snapshot(self, snapshot: AnalysisSnapshot):
        """Update live Multi-PV candidate lines."""
        if not snapshot or not snapshot.lines:
            return

        # Update header status
        top = snapshot.top_line
        n_fmt = f"{snapshot.nodes / 1_000_000:.1f}M" if snapshot.nodes >= 1_000_000 else f"{snapshot.nodes // 1000}k"
        self.status_label.set_text(f"Stockfish 18 · Depth: {snapshot.depth} · {n_fmt} nodes ({snapshot.nps // 1000}k n/s)")

        # Clear and populate lines
        while child := self.lines_container.get_first_child():
            self.lines_container.remove(child)

        for line in snapshot.lines:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add_css_class("engine-line-row")

            # PV Number badge
            num_lbl = Gtk.Label(label=f"#{line.multipv}")
            num_lbl.add_css_class("engine-pv-badge")
            row.append(num_lbl)

            # Score badge
            score_lbl = Gtk.Label(label=line.display_score)
            score_lbl.add_css_class("engine-score-badge")
            row.append(score_lbl)

            # Candidate Line SAN
            san_lbl = Gtk.Label(label=line.san_line)
            san_lbl.add_css_class("engine-san-line")
            san_lbl.set_hexpand(True)
            san_lbl.set_xalign(0.0)
            row.append(san_lbl)

            self.lines_container.append(row)
