"""
Zed-style floating Command Palette (Ctrl+K / Ctrl+P) with fuzzy command matching.
"""

from dataclasses import dataclass
from typing import List, Callable, Optional
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk


@dataclass
class CommandItem:
    """An executable command displayed in the palette."""
    id: str
    title: str
    category: str
    action: Callable[[], None]
    shortcut: str = ""

    def match_score(self, query: str) -> float:
        """Calculate relevance score for search query (0.0 = no match, 1.0 = exact)."""
        q = query.lower().strip()
        if not q:
            return 1.0

        title_lower = self.title.lower()
        cat_lower = self.category.lower()

        # Exact match
        if q == title_lower:
            return 1.0
        # Title starts with query
        if title_lower.startswith(q):
            return 0.9
        # Substring in title
        if q in title_lower:
            return 0.7
        # Substring in category
        if q in cat_lower:
            return 0.5

        # Subsequence / fuzzy match
        t_idx = 0
        matched = 0
        for char in q:
            pos = title_lower.find(char, t_idx)
            if pos != -1:
                matched += 1
                t_idx = pos + 1
        if matched == len(q):
            return 0.3

        return 0.0


class CommandPalette(Gtk.Window):
    """Floating modal command launcher."""

    def __init__(self, parent_window: Gtk.Window, commands: List[CommandItem]):
        super().__init__(
            transient_for=parent_window,
            modal=True,
            title="Command Palette"
        )
        self.set_default_size(540, 360)
        self.add_css_class("command-palette-window")

        self.all_commands = commands
        self.filtered_commands: List[CommandItem] = list(commands)

        # Root Container
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root_box)

        # 1. Search Entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_box.add_css_class("palette-search-box")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Type a command or search...")
        self.search_entry.set_hexpand(True)
        self.search_entry.add_css_class("palette-search-entry")
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.append(self.search_entry)
        root_box.append(search_box)

        # 2. Scrollable Command List
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root_box.append(self.scrolled)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("palette-list-box")
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)
        self.scrolled.set_child(self.list_box)

        # Keyboard handling
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

        # Initial populate
        self._populate_list(self.all_commands)

    def _populate_list(self, items: List[CommandItem]):
        while row := self.list_box.get_first_child():
            self.list_box.remove(row)

        for item in items:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.add_css_class("palette-row-box")

            # Category pill
            cat_lbl = Gtk.Label(label=item.category)
            cat_lbl.add_css_class("palette-category-badge")
            row_box.append(cat_lbl)

            # Title
            title_lbl = Gtk.Label(label=item.title)
            title_lbl.add_css_class("palette-title-label")
            title_lbl.set_hexpand(True)
            title_lbl.set_xalign(0.0)
            row_box.append(title_lbl)

            # Shortcut (optional)
            if item.shortcut:
                shortcut_lbl = Gtk.Label(label=item.shortcut)
                shortcut_lbl.add_css_class("palette-shortcut-badge")
                row_box.append(shortcut_lbl)

            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            row.command_item = item
            self.list_box.append(row)

        # Select first row by default
        first_row = self.list_box.get_row_at_index(0)
        if first_row:
            self.list_box.select_row(first_row)

    def _on_search_changed(self, entry):
        query = entry.get_text()
        scored = []
        for cmd in self.all_commands:
            score = cmd.match_score(query)
            if score > 0.0:
                scored.append((score, cmd))

        scored.sort(key=lambda x: x[0], reverse=True)
        self.filtered_commands = [item for _, item in scored]
        self._populate_list(self.filtered_commands)

    def _on_row_activated(self, list_box, row):
        if hasattr(row, "command_item"):
            item = row.command_item
            self.close()
            item.action()

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            selected = self.list_box.get_selected_row()
            if selected and hasattr(selected, "command_item"):
                self.close()
                selected.command_item.action()
                return True
        elif keyval == Gdk.KEY_Down:
            selected = self.list_box.get_selected_row()
            idx = selected.get_index() if selected else -1
            next_row = self.list_box.get_row_at_index(idx + 1)
            if next_row:
                self.list_box.select_row(next_row)
            return True
        elif keyval == Gdk.KEY_Up:
            selected = self.list_box.get_selected_row()
            idx = selected.get_index() if selected else 1
            if idx > 0:
                prev_row = self.list_box.get_row_at_index(idx - 1)
                if prev_row:
                    self.list_box.select_row(prev_row)
            return True
        return False
