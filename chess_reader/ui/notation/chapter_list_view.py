"""
Chapter and Game List View for the Right Sidebar in ChessReader.
Displays all games/chapters in the currently active PGN database,
enabling fast one-click traversal with active row highlighting and search filtering.
"""

from typing import Optional, Callable, List, Dict, Any
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango


class ChapterListView(Gtk.Box):
    """
    Scrollable games/chapters list for the active PGN database.
    Displays game number, title, players, result, and event with real-time search.
    """

    def __init__(
        self,
        on_select_game: Optional[Callable[[int], None]] = None
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class("chapter-list-view")
        self.set_vexpand(True)
        self.set_hexpand(True)

        self.on_select_game = on_select_game
        self.games_list: List[Dict[str, Any]] = []
        self.current_index: int = 0
        self.filter_text: str = ""
        self._row_widgets: Dict[int, Gtk.Widget] = {}

        # 1. Header with Count & Search Entry
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr_box.add_css_class("chapter-list-header")
        hdr_box.set_margin_start(8)
        hdr_box.set_margin_end(8)
        hdr_box.set_margin_top(6)
        hdr_box.set_margin_bottom(4)

        self.count_lbl = Gtk.Label(label="GAMES IN PGN (0)", xalign=0.0)
        self.count_lbl.add_css_class("chapter-list-title")
        self.count_lbl.set_hexpand(True)
        hdr_box.append(self.count_lbl)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter games...")
        self.search_entry.set_size_request(130, -1)
        self.search_entry.connect("search-changed", self._on_search_changed)
        hdr_box.append(self.search_entry)

        self.append(hdr_box)

        # 2. Scrollable List of Games
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.list_box.set_margin_start(6)
        self.list_box.set_margin_end(6)
        self.list_box.set_margin_top(2)
        self.list_box.set_margin_bottom(6)
        self.scrolled.set_child(self.list_box)

        self.append(self.scrolled)

    def update_games(self, games_list: List[Dict[str, Any]], current_index: int = 0):
        """Update game entries and active selection."""
        self.games_list = games_list or []
        self.current_index = current_index
        count = len(self.games_list)
        self.count_lbl.set_text(f"GAMES IN PGN ({count})")
        self._rebuild_list()

    def set_active_index(self, current_index: int):
        """Update active selection highlight without rebuilding entire list."""
        old_idx = self.current_index
        self.current_index = current_index

        if old_idx in self._row_widgets:
            self._row_widgets[old_idx].remove_css_class("chapter-row-active")
        if current_index in self._row_widgets:
            widget = self._row_widgets[current_index]
            widget.add_css_class("chapter-row-active")

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        self.filter_text = entry.get_text().strip().lower()
        self._rebuild_list()

    def _rebuild_list(self):
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)
        self._row_widgets.clear()

        if not self.games_list:
            empty_lbl = Gtk.Label(label="No games loaded in active file.", xalign=0.5)
            empty_lbl.add_css_class("chapter-empty-label")
            empty_lbl.set_margin_top(20)
            self.list_box.append(empty_lbl)
            return

        q = self.filter_text
        matching_count = 0

        for game in self.games_list:
            idx = game.get("index", 0)
            white = game.get("white", "White")
            black = game.get("black", "Black")
            event = game.get("event", "")
            result = game.get("result", "*")
            round_str = game.get("round", "")

            # Filter check
            if q:
                searchable = f"{white} {black} {event} {result} {round_str} #{idx + 1}".lower()
                if q not in searchable:
                    continue

            matching_count += 1
            row_btn = self._create_game_row(game, idx)
            self._row_widgets[idx] = row_btn
            self.list_box.append(row_btn)

        if matching_count == 0 and q:
            empty_lbl = Gtk.Label(label=f"No games match '{q}'", xalign=0.5)
            empty_lbl.add_css_class("chapter-empty-label")
            empty_lbl.set_margin_top(20)
            self.list_box.append(empty_lbl)

    def _create_game_row(self, game: Dict[str, Any], idx: int) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("chapter-game-row")
        if idx == self.current_index:
            btn.add_css_class("chapter-row-active")

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row_box.set_margin_start(6)
        row_box.set_margin_end(6)
        row_box.set_margin_top(4)
        row_box.set_margin_bottom(4)

        # Index badge (#1, #2...)
        idx_lbl = Gtk.Label(label=f"#{idx + 1}")
        idx_lbl.add_css_class("chapter-idx-badge")
        row_box.append(idx_lbl)

        # Title & Event
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_box.set_hexpand(True)

        white = game.get("white", "White")
        black = game.get("black", "Black")
        if white != "White" or black != "Black":
            title_str = f"{white} vs. {black}"
        else:
            title_str = game.get("event", f"Game #{idx + 1}")

        title_lbl = Gtk.Label(label=title_str, xalign=0.0)
        title_lbl.add_css_class("chapter-row-title")
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.set_width_chars(10)
        text_box.append(title_lbl)

        event = game.get("event", "")
        round_str = game.get("round", "")
        extra_parts = [p for p in (event, f"Round {round_str}" if round_str and round_str != "?" else "") if p]
        if extra_parts:
            sub_lbl = Gtk.Label(label=" · ".join(extra_parts), xalign=0.0)
            sub_lbl.add_css_class("chapter-row-desc")
            sub_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            sub_lbl.set_width_chars(10)
            text_box.append(sub_lbl)

        row_box.append(text_box)

        # Result badge
        res = game.get("result", "*")
        res_lbl = Gtk.Label(label=res)
        res_lbl.add_css_class("chapter-result-badge")
        row_box.append(res_lbl)

        btn.set_child(row_box)
        btn.connect("clicked", lambda _, i=idx: self._on_row_clicked(i))
        return btn

    def _on_row_clicked(self, idx: int):
        self.set_active_index(idx)
        if self.on_select_game:
            self.on_select_game(idx)
