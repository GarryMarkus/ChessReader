"""
Chess Engine Management Dialog for ChessReader.
Enables switching active UCI engines and adding new custom chess engine binaries from disk.
"""

import os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

from chess_reader.engine.uci_client import UCIEngineManager


class EngineDialog(Gtk.Window):
    """Modal dialog allowing users to view, switch, and add UCI chess engines."""

    def __init__(self, parent_window: Gtk.Window, engine_manager: UCIEngineManager, on_engine_switched=None):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_title("Chess Engine Manager")
        self.set_default_size(540, 440)
        self.add_css_class("zed-modal-window")

        self.engine_manager = engine_manager
        self.registry = engine_manager.registry
        self.on_engine_switched = on_engine_switched

        # Root layout
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("zed-modal-header")
        header.set_margin_top(14)
        header.set_margin_bottom(12)
        header.set_margin_start(18)
        header.set_margin_end(18)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label="Chess Engine Manager", xalign=0.0)
        title_lbl.add_css_class("zed-modal-title")
        sub_lbl = Gtk.Label(label="Switch active analysis engine or add custom UCI binaries", xalign=0.0)
        sub_lbl.add_css_class("zed-modal-subtitle")
        title_box.append(title_lbl)
        title_box.append(sub_lbl)
        title_box.set_hexpand(True)
        header.append(title_box)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("flat")
        close_btn.add_css_class("circular")
        close_btn.connect("clicked", lambda _: self.close())
        header.append(close_btn)
        root.append(header)

        # Content Box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.set_margin_top(14)
        content.set_margin_bottom(18)
        root.append(content)

        # Section Header + Add Button
        sec_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sec_title = Gtk.Label(label="CONFIGURED ENGINES", xalign=0.0)
        sec_title.add_css_class("zed-section-title")
        sec_title.set_hexpand(True)
        sec_hdr.append(sec_title)

        add_btn = Gtk.Button(label="+ Add Chess Engine...")
        add_btn.add_css_class("zed-btn-secondary")
        add_btn.set_tooltip_text("Select an engine executable on your system (e.g. Stockfish, Leela, Komodo)")
        add_btn.connect("clicked", self._on_add_engine_clicked)
        sec_hdr.append(add_btn)
        content.append(sec_hdr)

        # Scrolled Engines List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.engines_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scrolled.set_child(self.engines_container)
        content.append(scrolled)

        self._populate_engines()

        # Escape key
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _populate_engines(self):
        while child := self.engines_container.get_first_child():
            self.engines_container.remove(child)

        active = self.registry.get_active_engine()
        active_id = active["id"] if active else None

        for eng in self.registry.list_engines():
            is_active = (eng["id"] == active_id)
            card = self._create_engine_card(eng, is_active)
            self.engines_container.append(card)

    def _create_engine_card(self, eng: dict, is_active: bool) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        card.add_css_class("zed-card-button")
        if is_active:
            card.add_css_class("zed-card-active")

        # Select button
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.set_hexpand(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(8)
        row.set_margin_bottom(8)

        icon = Gtk.Label(label="⚙")
        row.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_lbl = Gtk.Label(label=eng["name"], xalign=0.0)
        name_lbl.add_css_class("zed-card-title")

        type_str = "Built-in" if eng.get("is_builtin") else "Custom Binary"
        path_lbl = Gtk.Label(label=f"{eng['path']} · {type_str}", xalign=0.0)
        path_lbl.add_css_class("zed-card-desc")
        vbox.append(name_lbl)
        vbox.append(path_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        if is_active:
            pill = Gtk.Label(label="Active ✓")
            pill.add_css_class("zed-pill-active")
            row.append(pill)

        btn.set_child(row)
        btn.connect("clicked", lambda _, e=eng: self._activate_engine(e))
        card.append(btn)

        # Remove button (if not builtin)
        if not eng.get("is_builtin"):
            del_btn = Gtk.Button(label="✕")
            del_btn.add_css_class("flat")
            del_btn.add_css_class("zed-btn-remove")
            del_btn.set_tooltip_text("Remove engine from list")
            del_btn.connect("clicked", lambda _, e_id=eng["id"]: self._remove_engine(e_id))
            card.append(del_btn)

        return card

    def _activate_engine(self, eng: dict):
        self.engine_manager.switch_engine(eng["path"], engine_id=eng["id"])
        self._populate_engines()
        if self.on_engine_switched:
            self.on_engine_switched(eng)

    def _remove_engine(self, engine_id: str):
        self.registry.remove_engine(engine_id)
        self._populate_engines()

    def _on_add_engine_clicked(self, _btn):
        chooser = Gtk.FileChooserNative(
            title="Select UCI Chess Engine Binary",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Add Engine",
            cancel_label="_Cancel"
        )

        def on_response(native, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                f = native.get_file()
                if f and f.get_path():
                    path = f.get_path()
                    try:
                        eng = self.registry.add_engine(path)
                        self._activate_engine(eng)
                    except Exception as err:
                        dlg = Gtk.AlertDialog(message=f"Failed to Add Engine: {err}")
                        dlg.show(self)

        chooser.connect("response", on_response)
        chooser.show()
