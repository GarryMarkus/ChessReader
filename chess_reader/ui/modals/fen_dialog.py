"""
Interactive FEN Setup Modal with live validation and clipboard integration.
"""

from typing import Optional, Callable
import chess
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk


class FENSetupDialog(Gtk.Window):
    """Modal dialog for interactive FEN position entry, validation, and clipboard I/O."""

    def __init__(self, parent_window: Gtk.Window, current_fen: str, on_fen_loaded: Callable[[str], None]):
        super().__init__(
            transient_for=parent_window,
            modal=True,
            title="Set Board Position (FEN)"
        )
        self.set_default_size(580, 260)
        self.add_css_class("fen-dialog-window")

        self.on_fen_loaded = on_fen_loaded

        # Root vertical box
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.add_css_class("fen-dialog-content")
        self.set_child(root)

        # Title & Description
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label="Set Board Position (FEN)")
        title_lbl.add_css_class("fen-dialog-title")
        title_lbl.set_xalign(0.0)
        header_box.append(title_lbl)

        desc_lbl = Gtk.Label(label="Paste or edit standard Forsyth-Edwards Notation (FEN) to configure the board.")
        desc_lbl.add_css_class("fen-dialog-desc")
        desc_lbl.set_xalign(0.0)
        header_box.append(desc_lbl)
        root.append(header_box)

        # FEN Entry Box
        self.entry = Gtk.Entry()
        self.entry.set_text(current_fen)
        self.entry.add_css_class("fen-dialog-entry")
        self.entry.set_hexpand(True)
        self.entry.connect("changed", self._on_entry_changed)
        root.append(self.entry)

        # Validation status label
        self.status_lbl = Gtk.Label(label="✓ Valid FEN position")
        self.status_lbl.add_css_class("fen-status-valid")
        self.status_lbl.set_xalign(0.0)
        root.append(self.status_lbl)

        # Quick preset buttons (Starting, Clear, Paste)
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_start = Gtk.Button(label="Starting Position")
        btn_start.add_css_class("flat")
        btn_start.connect("clicked", lambda _: self.entry.set_text(chess.STARTING_FEN))
        preset_box.append(btn_start)

        btn_empty = Gtk.Button(label="Clear Board")
        btn_empty.add_css_class("flat")
        btn_empty.connect("clicked", lambda _: self.entry.set_text("8/8/8/8/8/8/8/8 w - - 0 1"))
        preset_box.append(btn_empty)

        btn_paste = Gtk.Button(label="Paste from Clipboard")
        btn_paste.add_css_class("flat")
        btn_paste.connect("clicked", self._on_paste_clicked)
        preset_box.append(btn_paste)

        root.append(preset_box)

        # Action Buttons (Cancel / Load Position)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.END)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda _: self.close())
        action_box.append(btn_cancel)

        self.btn_load = Gtk.Button(label="Load Position")
        self.btn_load.add_css_class("suggested-action")
        self.btn_load.connect("clicked", self._on_load_clicked)
        action_box.append(self.btn_load)

        root.append(action_box)

        # Validate initial
        self._validate_fen(current_fen)

    def _on_entry_changed(self, entry):
        self._validate_fen(entry.get_text().strip())

    def _validate_fen(self, fen: str) -> bool:
        try:
            board = chess.Board(fen)
            # Valid FEN
            self.status_lbl.set_text("✓ Valid FEN position")
            self.status_lbl.remove_css_class("fen-status-invalid")
            self.status_lbl.add_css_class("fen-status-valid")
            self.btn_load.set_sensitive(True)
            return True
        except ValueError as e:
            self.status_lbl.set_text(f"✗ Invalid FEN: {str(e)}")
            self.status_lbl.remove_css_class("fen-status-valid")
            self.status_lbl.add_css_class("fen-status-invalid")
            self.btn_load.set_sensitive(False)
            return False

    def _on_paste_clicked(self, btn):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text_ready)

    def _on_clipboard_text_ready(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self.entry.set_text(text.strip())
        except Exception:
            pass

    def _on_load_clicked(self, btn):
        fen = self.entry.get_text().strip()
        if self._validate_fen(fen):
            self.close()
            self.on_fen_loaded(fen)
