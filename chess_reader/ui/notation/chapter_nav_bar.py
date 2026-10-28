"""
Chapter and Multi-Game Navigation Bar for ChessReader.
Enables instant switching between chapters/games within the active PGN database
directly from the board view, via Previous/Next buttons, keyboard shortcuts,
or a searchable game selection popover.
"""

from typing import Optional, Callable, List, Dict, Any
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango


class ChapterNavBar(Gtk.Box):
    """
    Compact horizontal navigation header displaying the current game / chapter
    in the active PGN database, with Prev / Next step buttons and a searchable
    interactive game picker popover.
    """

    def __init__(
        self,
        on_prev_game: Optional[Callable[[], None]] = None,
        on_next_game: Optional[Callable[[], None]] = None,
        on_select_game: Optional[Callable[[int], None]] = None
    ):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_css_class("chapter-nav-bar")

        self.on_prev_game = on_prev_game
        self.on_next_game = on_next_game
        self.on_select_game = on_select_game

        self.current_index: int = 0
        self.total_games: int = 1
        self.games_list: List[Dict[str, Any]] = []

        # 1. Previous Game Button
        self.btn_prev = Gtk.Button(label="◀ Prev")
        self.btn_prev.add_css_class("chapter-btn-nav")
        self.btn_prev.set_tooltip_text("Previous Game / Chapter in PGN (Alt+Left / [)")
        self.btn_prev.set_sensitive(False)
        self.btn_prev.connect("clicked", lambda _: self._on_prev_clicked())
        self.append(self.btn_prev)

        # 2. Game Title / Picker Dropdown Button
        self.btn_menu = Gtk.Button()
        self.btn_menu.add_css_class("chapter-title-btn")
        self.btn_menu.set_hexpand(True)
        self.btn_menu.set_tooltip_text("Click to view & select any chapter or game in this PGN")

        menu_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.badge_lbl = Gtk.Label(label="1/1")
        self.badge_lbl.add_css_class("chapter-badge")
        menu_row.append(self.badge_lbl)

        self.title_lbl = Gtk.Label(label="Starting Position", xalign=0.0)
        self.title_lbl.add_css_class("chapter-title-text")
        self.title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_lbl.set_hexpand(True)
        menu_row.append(self.title_lbl)

        chevron = Gtk.Label(label="▾")
        chevron.add_css_class("chapter-chevron")
        menu_row.append(chevron)
        self.btn_menu.set_child(menu_row)

        self.append(self.btn_menu)

        # 3. Next Game Button
        self.btn_next = Gtk.Button(label="Next ▶")
        self.btn_next.add_css_class("chapter-btn-nav")
        self.btn_next.set_tooltip_text("Next Game / Chapter in PGN (Alt+Right / ])")
        self.btn_next.set_sensitive(False)
        self.btn_next.connect("clicked", lambda _: self._on_next_clicked())
        self.append(self.btn_next)

        # 4. Searchable Chapter / Game Picker Popover
        self._build_popover()

    def _build_popover(self):
        self.popover = Gtk.Popover()
        self.popover.set_parent(self.btn_menu)
        self.popover.set_has_arrow(True)
        self.btn_menu.connect("clicked", lambda _: self.popover.popup())

        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pop_box.set_size_request(340, 360)
        pop_box.set_margin_start(8)
        pop_box.set_margin_end(8)
        pop_box.set_margin_top(8)
        pop_box.set_margin_bottom(8)

        # Search / Filter Bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search chapter or players...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        pop_box.append(self.search_entry)

        # Scrollable Game List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(self.list_container)
        pop_box.append(scrolled)

        self.popover.set_child(pop_box)

    def update_game_info(
        self,
        current_index: int,
        total_games: int,
        games_list: Optional[List[Dict[str, Any]]] = None,
        title: Optional[str] = None
    ):
        """Update chapter navigator indicators and popover entries."""
        self.current_index = current_index
        self.total_games = max(1, total_games)
        if games_list is not None:
            self.games_list = games_list

        self.btn_prev.set_sensitive(self.current_index > 0)
        self.btn_next.set_sensitive(self.current_index + 1 < self.total_games)

        # Format Title & Badge
        self.badge_lbl.set_text(f"{self.current_index + 1}/{self.total_games}")
        if title:
            disp_title = title
        elif self.games_list and 0 <= self.current_index < len(self.games_list):
            g = self.games_list[self.current_index]
            white = g.get("white", "?")
            black = g.get("black", "?")
            event = g.get("event", "")
            if white != "?" or black != "?":
                disp_title = f"{white} vs. {black}"
            elif event:
                disp_title = event
            else:
                disp_title = f"Game #{self.current_index + 1}"
        else:
            disp_title = f"Game #{self.current_index + 1}"

        self.title_lbl.set_text(disp_title)
        self._populate_popover_list(self.games_list)

    def _populate_popover_list(self, games: List[Dict[str, Any]]):
        while child := self.list_container.get_first_child():
            self.list_container.remove(child)

        if not games:
            lbl = Gtk.Label(label="No games found.", xalign=0.0)
            lbl.add_css_class("zed-empty-label")
            self.list_container.append(lbl)
            return

        for g in games:
            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.add_css_class("chapter-popover-item")
            g_idx = g.get("index", 0)
            if g_idx == self.current_index:
                btn.add_css_class("chapter-popover-active")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_margin_start(4)
            row.set_margin_end(4)
            row.set_margin_top(4)
            row.set_margin_bottom(4)

            idx_lbl = Gtk.Label(label=f"#{g_idx + 1}")
            idx_lbl.add_css_class("zed-game-idx")
            row.append(idx_lbl)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            p_lbl = Gtk.Label(label=f"{g.get('white', '?')} vs. {g.get('black', '?')}", xalign=0.0)
            p_lbl.add_css_class("zed-game-players")
            p_lbl.set_ellipsize(Pango.EllipsizeMode.END)

            evt = g.get('event', '')
            res = g.get('result', '')
            sub_str = f"{evt} · {res}" if evt else res
            sub_lbl = Gtk.Label(label=sub_str, xalign=0.0)
            sub_lbl.add_css_class("zed-game-meta")
            sub_lbl.set_ellipsize(Pango.EllipsizeMode.END)

            vbox.append(p_lbl)
            vbox.append(sub_lbl)
            vbox.set_hexpand(True)
            row.append(vbox)

            btn.set_child(row)
            btn.connect("clicked", lambda _, idx=g_idx: self._on_item_selected(idx))
            self.list_container.append(btn)

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        q = entry.get_text().strip().lower()
        if not q:
            self._populate_popover_list(self.games_list)
            return

        filtered = [
            g for g in self.games_list
            if q in g.get("white", "").lower()
            or q in g.get("black", "").lower()
            or q in g.get("event", "").lower()
            or q in str(g.get("index", 0) + 1)
        ]
        self._populate_popover_list(filtered)

    def _on_item_selected(self, index: int):
        self.popover.popdown()
        if self.on_select_game:
            self.on_select_game(index)

    def _on_prev_clicked(self):
        if self.on_prev_game:
            self.on_prev_game()

    def _on_next_clicked(self):
        if self.on_next_game:
            self.on_next_game()
