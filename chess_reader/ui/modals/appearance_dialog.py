"""
Appearance and Piece Set Selector Modal for ChessReader.
Provides a clear, elegant visual interface to change piece styles and board themes,
as well as import custom piece set folders.
"""

import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

from chess_reader.theme.loader import ThemeManager
from chess_reader.theme.piece_sets import PieceSetInfo


class AppearanceDialog(Gtk.Window):
    """Modal dialog allowing users to switch piece styles, themes, and import custom piece assets."""

    def __init__(self, parent_window: Gtk.Window, theme_manager: ThemeManager):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_title("Appearance & Chess Pieces")
        self.set_default_size(580, 520)
        self.add_css_class("zed-modal-window")

        self.theme_manager = theme_manager
        self.piece_manager = theme_manager.piece_set_manager

        # Root vertical layout
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        # Header Bar
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("zed-modal-header")
        header.set_margin_top(14)
        header.set_margin_bottom(12)
        header.set_margin_start(18)
        header.set_margin_end(18)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label="Appearance & Styles", xalign=0.0)
        title_lbl.add_css_class("zed-modal-title")
        subtitle_lbl = Gtk.Label(label="Select piece sets, board themes, or import custom piece directories", xalign=0.0)
        subtitle_lbl.add_css_class("zed-modal-subtitle")
        title_box.append(title_lbl)
        title_box.append(subtitle_lbl)
        title_box.set_hexpand(True)
        header.append(title_box)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("flat")
        close_btn.add_css_class("circular")
        close_btn.connect("clicked", lambda _: self.close())
        header.append(close_btn)
        root.append(header)

        # Scrolled content container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.append(scrolled)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content_box.set_margin_start(18)
        content_box.set_margin_end(18)
        content_box.set_margin_bottom(18)
        scrolled.set_child(content_box)

        # ---------------------------------------------------------------------
        # Section 1: Chess Piece Sets
        # ---------------------------------------------------------------------
        piece_section_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        piece_title = Gtk.Label(label="CHESS PIECE STYLES", xalign=0.0)
        piece_title.add_css_class("zed-section-title")
        piece_title.set_hexpand(True)
        piece_section_header.append(piece_title)

        import_btn = Gtk.Button(label="+ Import Pieces Folder")
        import_btn.add_css_class("zed-btn-secondary")
        import_btn.set_tooltip_text("Import a folder of chess piece images (.png or .svg)")
        import_btn.connect("clicked", self._on_import_pieces_clicked)
        piece_section_header.append(import_btn)
        content_box.append(piece_section_header)

        # Piece sets container
        self.piece_cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content_box.append(self.piece_cards_box)
        self._populate_piece_sets()

        # ---------------------------------------------------------------------
        # Section 2: Board Themes
        # ---------------------------------------------------------------------
        theme_title = Gtk.Label(label="CHESSBOARD THEMES", xalign=0.0)
        theme_title.add_css_class("zed-section-title")
        theme_title.set_margin_top(8)
        content_box.append(theme_title)

        self.theme_cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content_box.append(self.theme_cards_box)
        self._populate_themes()

        # Escape shortcut to close
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _populate_piece_sets(self):
        """Populate visual cards for all discovered piece sets."""
        while child := self.piece_cards_box.get_first_child():
            self.piece_cards_box.remove(child)

        active_id = self.piece_manager.active_piece_set_id

        # 1. Option for "Theme Default Pieces"
        default_card = self._create_piece_card(
            set_id="",
            name="Theme Default Pieces",
            info=None,
            is_active=(active_id is None)
        )
        self.piece_cards_box.append(default_card)

        # 2. Each discovered piece set
        for info in self.piece_manager.list_piece_sets():
            card = self._create_piece_card(
                set_id=info.id,
                name=info.name,
                info=info,
                is_active=(active_id == info.id)
            )
            self.piece_cards_box.append(card)

    def _create_piece_card(self, set_id: str, name: str, info: PieceSetInfo, is_active: bool) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("zed-card-button")
        if is_active:
            btn.add_css_class("zed-card-active")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        row.set_margin_start(12)
        row.set_margin_end(12)

        # Text Info
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_lbl = Gtk.Label(label=name, xalign=0.0)
        name_lbl.add_css_class("zed-card-title")
        vbox.append(name_lbl)

        format_str = f"Format: {info.format.upper()} · {'Built-in' if info.is_builtin else 'User Installed'}" if info else "Uses pieces specified in active board theme"
        fmt_lbl = Gtk.Label(label=format_str, xalign=0.0)
        fmt_lbl.add_css_class("zed-card-desc")
        vbox.append(fmt_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        # Preview piece icons (wK, wN, bQ, bP) if available
        if info:
            preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            for sym in ["wK", "wN", "bQ", "bP"]:
                piece_file = info.get_piece_path(sym)
                if piece_file:
                    img = Gtk.Image.new_from_file(piece_file)
                    img.set_pixel_size(28)
                    preview_box.append(img)
            row.append(preview_box)

        # Active check indicator
        if is_active:
            active_pill = Gtk.Label(label="Active ✓")
            active_pill.add_css_class("zed-pill-active")
            row.append(active_pill)

        btn.set_child(row)
        btn.connect("clicked", lambda _: self._select_piece_set(set_id))
        return btn

    def _select_piece_set(self, set_id: str):
        self.piece_manager.set_active_piece_set(set_id if set_id else None)
        self._populate_piece_sets()

    def _populate_themes(self):
        """Populate cards for board themes."""
        while child := self.theme_cards_box.get_first_child():
            self.theme_cards_box.remove(child)

        active_theme_id = self.theme_manager.active_theme.id

        for theme in self.theme_manager.list_themes():
            is_active = (theme.id == active_theme_id)
            btn = Gtk.Button()
            btn.add_css_class("zed-card-button")
            if is_active:
                btn.add_css_class("zed-card-active")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.set_margin_top(8)
            row.set_margin_bottom(8)
            row.set_margin_start(12)
            row.set_margin_end(12)

            # Palette swatch / preview
            swatch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            swatch.set_size_request(24, 24)
            # Two square indicators
            l_sq = Gtk.Box()
            l_sq.set_size_request(12, 24)
            l_sq.add_css_class("theme-swatch-light")
            d_sq = Gtk.Box()
            d_sq.set_size_request(12, 24)
            d_sq.add_css_class("theme-swatch-dark")
            swatch.append(l_sq)
            swatch.append(d_sq)
            row.append(swatch)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=theme.name, xalign=0.0)
            name_lbl.add_css_class("zed-card-title")
            vbox.append(name_lbl)

            desc = theme.description or f"Type: {theme.board.type.capitalize()}"
            desc_lbl = Gtk.Label(label=desc, xalign=0.0)
            desc_lbl.add_css_class("zed-card-desc")
            vbox.append(desc_lbl)
            vbox.set_hexpand(True)
            row.append(vbox)

            if is_active:
                active_pill = Gtk.Label(label="Active ✓")
                active_pill.add_css_class("zed-pill-active")
                row.append(active_pill)

            btn.set_child(row)
            btn.connect("clicked", lambda _, t_id=theme.id: self._select_theme(t_id))
            self.theme_cards_box.append(btn)

    def _select_theme(self, theme_id: str):
        self.theme_manager.set_active_theme(theme_id)
        self._populate_themes()

    def _on_import_pieces_clicked(self, _btn):
        """Open folder chooser to import custom chess pieces folder."""
        chooser = Gtk.FileChooserNative(
            title="Select Custom Chess Pieces Folder",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Import Pieces",
            cancel_label="_Cancel"
        )

        def on_response(native, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                folder_file = native.get_file()
                if folder_file:
                    folder_path = folder_file.get_path()
                    try:
                        imported = self.piece_manager.import_piece_set_folder(folder_path)
                        if imported:
                            self.piece_manager.set_active_piece_set(imported.id)
                            self._populate_piece_sets()
                    except Exception as err:
                        dlg = Gtk.AlertDialog(message=f"Import Failed: {err}")
                        dlg.show(self)

        chooser.connect("response", on_response)
        chooser.show()
