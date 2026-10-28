"""
Main Application Window with Zed Design Language Chrome.
Unified Client-Side Decoration (CSD) headerbar, split-pane workspace, and status bar.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk


class ZedTitlebar(Gtk.Box):
    """Unified CSD headerbar housing breadcrumbs, controls, and window actions."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("zed-titlebar-container")

        self.header = Adw.HeaderBar()
        self.header.add_css_class("zed-titlebar")
        self.header.set_show_title(False)
        self.header.set_hexpand(True)
        self.append(self.header)

        # Left: Breadcrumb container
        self.breadcrumb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.breadcrumb_box.add_css_class("breadcrumb-box")

        self.set_breadcrumb(["Database", "Round 1", "Carlsen vs. Caruana (1-0)"])
        self.header.pack_start(self.breadcrumb_box)

        # Right: Quick action buttons
        self.palette_btn = Gtk.Button(label="⌘K")
        self.palette_btn.set_tooltip_text("Command Palette (Ctrl+K)")
        self.palette_btn.add_css_class("flat")
        self.header.pack_end(self.palette_btn)

    def set_breadcrumb(self, segments):
        """Update breadcrumb path segments."""
        while child := self.breadcrumb_box.get_first_child():
            self.breadcrumb_box.remove(child)

        for i, segment in enumerate(segments):
            if i > 0:
                sep = Gtk.Label(label="/")
                sep.add_css_class("breadcrumb-separator")
                self.breadcrumb_box.append(sep)

            lbl = Gtk.Label(label=segment)
            if i == len(segments) - 1:
                lbl.add_css_class("breadcrumb-active")
            else:
                lbl.add_css_class("breadcrumb-segment")
            self.breadcrumb_box.append(lbl)


class StatusBar(Gtk.Box):
    """24px Zed-style bottom status bar."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.add_css_class("zed-status-bar")

        # Engine Depth & Nodes
        self.engine_label = Gtk.Label(label="Stockfish 18 · Idle")
        self.engine_label.add_css_class("zed-status-item")
        self.append(self.engine_label)

        # Flexible spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.append(spacer)

        # FEN Quick Copy Button
        self.fen_btn = Gtk.Button(label="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
        self.fen_btn.set_tooltip_text("Click to copy FEN")
        self.fen_btn.add_css_class("flat")
        self.fen_btn.add_css_class("zed-status-interactive")
        self.append(self.fen_btn)

        # Active Theme Profile
        self.theme_label = Gtk.Label(label="Theme: zed-dark")
        self.theme_label.add_css_class("zed-status-item")
        self.append(self.theme_label)


class ChessReaderWindow(Adw.ApplicationWindow):
    """Main application window implementing the Zed layout."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("ChessReader")
        self.set_default_size(1280, 840)
        self.add_css_class("chess-reader-window")

        # Libadwaita ToolbarView handles CSD chrome and status bars seamlessly
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)

        # 1. Unified CSD HeaderBar (Top Bar)
        self.titlebar = ZedTitlebar()
        self.toolbar_view.add_top_bar(self.titlebar)

        # 2. Main Workspace Split Pane (Content)
        self.workspace = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.workspace.add_css_class("zed-workspace")
        self.workspace.set_vexpand(True)
        self.toolbar_view.set_content(self.workspace)

        # Left / Center: Chess Board Container
        self.board_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.board_panel.add_css_class("zed-panel")
        self.board_panel.set_hexpand(True)
        self.board_placeholder = Gtk.Label(label="Chess Board (Cairo/GSK Canvas)")
        self.board_placeholder.set_vexpand(True)
        self.board_panel.append(self.board_placeholder)
        self.workspace.set_start_child(self.board_panel)

        # Right: Move Notation Tree & Inspector
        self.notation_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notation_panel.add_css_class("zed-sidebar")
        self.notation_panel.set_size_request(380, -1)
        self.tree_placeholder = Gtk.Label(label="Move Notation Tree & Variations")
        self.tree_placeholder.set_vexpand(True)
        self.notation_panel.append(self.tree_placeholder)
        self.workspace.set_end_child(self.notation_panel)

        # 3. Status Bar (Bottom Bar)
        self.status_bar = StatusBar()
        self.toolbar_view.add_bottom_bar(self.status_bar)
