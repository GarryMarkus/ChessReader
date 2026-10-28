"""
Home Page and Local Database / PGN Library View for ChessReader.
Provides a dedicated section for folder shortcuts, PGN file creation,
database exploration, and one-click game loading into the active board.
"""

import os
from typing import Optional, Callable, List, Dict, Any
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, Pango

import chess.pgn
from chess_reader.core.library_store import LibraryStore


class HomeView(Gtk.Box):
    """
    Dedicated Home Page with Folder Shortcuts, Database & PGN File Manager,
    and fast multi-game PGN browser.
    """

    def __init__(
        self,
        library_store: Optional[LibraryStore] = None,
        on_load_game: Optional[Callable[[chess.pgn.Game, str], None]] = None,
        on_switch_to_board: Optional[Callable[[], None]] = None,
        parent_window: Optional[Gtk.Window] = None
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("zed-home-view")

        self.library_store = library_store or LibraryStore()
        self.on_load_game = on_load_game
        self.on_switch_to_board = on_switch_to_board
        self.parent_window = parent_window

        self.active_folder_path: Optional[str] = None
        self.active_pgn_path: Optional[str] = None
        self.cached_games: List[Dict[str, Any]] = []

        # 1. Top Action & Navigation Bar
        self._build_top_bar()

        # 2. Main Library Split Panes (Shortcuts / Files / Games)
        self._build_workspace()

        # Initial data population
        self.refresh_shortcuts()
        self.refresh_recents()

    def _build_top_bar(self):
        """Construct top action bar with New, Open, Add Folder, and Board navigation."""
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_bar.add_css_class("zed-home-topbar")
        top_bar.set_margin_start(20)
        top_bar.set_margin_end(20)
        top_bar.set_margin_top(16)
        top_bar.set_margin_bottom(14)

        # Title & Subtitle
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label="♟ ChessReader Library", xalign=0.0)
        title_lbl.add_css_class("zed-home-title")
        subtitle_lbl = Gtk.Label(label="Databases, Folder Shortcuts & Local PGN Archives", xalign=0.0)
        subtitle_lbl.add_css_class("zed-home-subtitle")
        title_box.append(title_lbl)
        title_box.append(subtitle_lbl)
        title_box.set_hexpand(True)
        top_bar.append(title_box)

        # Action Buttons
        add_folder_btn = Gtk.Button(label="📁 Add Folder Shortcut")
        add_folder_btn.add_css_class("zed-btn-secondary")
        add_folder_btn.set_tooltip_text("Pin a folder on your computer to easily access its PGNs")
        add_folder_btn.connect("clicked", self._on_add_folder_clicked)
        top_bar.append(add_folder_btn)

        open_file_btn = Gtk.Button(label="📂 Open PGN File...")
        open_file_btn.add_css_class("zed-btn-secondary")
        open_file_btn.set_tooltip_text("Open any PGN or database file from your computer")
        open_file_btn.connect("clicked", self._on_open_file_clicked)
        top_bar.append(open_file_btn)

        new_pgn_btn = Gtk.Button(label="➕ New PGN Database")
        new_pgn_btn.add_css_class("zed-btn-secondary")
        new_pgn_btn.set_tooltip_text("Create a new .pgn file on your computer")
        new_pgn_btn.connect("clicked", self._on_new_pgn_clicked)
        top_bar.append(new_pgn_btn)

        board_btn = Gtk.Button(label="♟ Go to Board")
        board_btn.add_css_class("zed-btn-primary")
        board_btn.set_tooltip_text("Switch to interactive chessboard analysis (Ctrl+B)")
        board_btn.connect("clicked", lambda _: self._navigate_to_board())
        top_bar.append(board_btn)

        self.append(top_bar)

    def _build_workspace(self):
        """Construct the split panels: Left (Folder Shortcuts & Recents), Right (Files & Game Browser)."""
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.add_css_class("zed-workspace")
        paned.set_position(360)
        paned.set_shrink_start_child(False)
        paned.set_resize_start_child(False)
        paned.set_shrink_end_child(False)
        paned.set_resize_end_child(True)
        paned.set_vexpand(True)
        self.append(paned)

        # ---------------------------------------------------------------------
        # Left Panel: Folder Shortcuts & Recent Files
        # ---------------------------------------------------------------------
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left_box.add_css_class("zed-sidebar")
        left_box.set_size_request(280, -1)
        paned.set_start_child(left_box)

        left_scrolled = Gtk.ScrolledWindow()
        left_scrolled.set_vexpand(True)
        left_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_box.append(left_scrolled)

        left_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        left_content.set_margin_start(16)
        left_content.set_margin_end(16)
        left_content.set_margin_top(16)
        left_content.set_margin_bottom(16)
        left_scrolled.set_child(left_content)

        # Folder Shortcuts Header
        shortcuts_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sc_lbl = Gtk.Label(label="FOLDER SHORTCUTS", xalign=0.0)
        sc_lbl.add_css_class("zed-section-title")
        sc_lbl.set_hexpand(True)
        shortcuts_hdr.append(sc_lbl)

        sc_plus_btn = Gtk.Button(label="+ Add")
        sc_plus_btn.add_css_class("flat")
        sc_plus_btn.connect("clicked", self._on_add_folder_clicked)
        shortcuts_hdr.append(sc_plus_btn)
        left_content.append(shortcuts_hdr)

        self.shortcuts_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_content.append(self.shortcuts_container)

        # Recent Files Header
        recent_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        recent_lbl = Gtk.Label(label="RECENT DATABASES", xalign=0.0)
        recent_lbl.add_css_class("zed-section-title")
        recent_lbl.set_margin_top(14)
        recent_hdr.append(recent_lbl)
        left_content.append(recent_hdr)

        self.recents_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_content.append(self.recents_container)

        # ---------------------------------------------------------------------
        # Right Panel: Folder PGN Files & Game Explorer
        # ---------------------------------------------------------------------
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right_box.add_css_class("zed-panel")
        right_box.set_hexpand(True)
        paned.set_end_child(right_box)

        # Split into Files list (top) and Game list (bottom)
        right_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        right_paned.set_position(300)
        right_paned.set_shrink_start_child(False)
        right_paned.set_shrink_end_child(False)
        right_paned.set_resize_start_child(True)
        right_paned.set_resize_end_child(True)
        right_paned.set_vexpand(True)
        right_box.append(right_paned)

        # PGN Files in Folder Pane
        files_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        files_section.set_size_request(-1, 140)
        files_section.set_margin_start(18)
        files_section.set_margin_end(18)
        files_section.set_margin_top(14)
        files_section.set_margin_bottom(10)

        self.folder_title_lbl = Gtk.Label(label="Select a folder shortcut to view its chess databases", xalign=0.0)
        self.folder_title_lbl.add_css_class("zed-section-title")
        self.folder_title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        files_section.append(self.folder_title_lbl)

        files_scrolled = Gtk.ScrolledWindow()
        files_scrolled.set_vexpand(True)
        files_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.files_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        files_scrolled.set_child(self.files_container)
        files_section.append(files_scrolled)

        right_paned.set_start_child(files_section)

        # Games inside selected PGN Pane
        games_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        games_section.set_size_request(-1, 160)
        games_section.set_margin_start(18)
        games_section.set_margin_end(18)
        games_section.set_margin_top(10)
        games_section.set_margin_bottom(16)

        # Search Bar + Header
        games_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pgn_title_lbl = Gtk.Label(label="GAMES IN ARCHIVE", xalign=0.0)
        self.pgn_title_lbl.add_css_class("zed-section-title")
        self.pgn_title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.pgn_title_lbl.set_hexpand(True)
        games_hdr.append(self.pgn_title_lbl)

        self.filter_entry = Gtk.SearchEntry()
        self.filter_entry.set_placeholder_text("Filter by player, opening, or year...")
        self.filter_entry.set_size_request(240, -1)
        self.filter_entry.connect("search-changed", self._on_filter_changed)
        games_hdr.append(self.filter_entry)
        games_section.append(games_hdr)

        games_scrolled = Gtk.ScrolledWindow()
        games_scrolled.set_vexpand(True)
        games_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.games_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        games_scrolled.set_child(self.games_container)
        games_section.append(games_scrolled)

        right_paned.set_end_child(games_section)

    # -------------------------------------------------------------------------
    # Data Population
    # -------------------------------------------------------------------------
    def refresh_shortcuts(self):
        """Re-render folder shortcuts list."""
        while child := self.shortcuts_container.get_first_child():
            self.shortcuts_container.remove(child)

        # 1. ChessBase-style 'All Databases' master shortcut at the top
        all_db_card = self._create_all_databases_card()
        self.shortcuts_container.append(all_db_card)

        shortcuts = self.library_store.get_folder_shortcuts()
        for sc in shortcuts:
            card = self._create_shortcut_card(sc)
            self.shortcuts_container.append(card)

        # Default to All Databases on initial load
        if not self.active_folder_path:
            self._select_all_databases()
        elif self.active_folder_path == "all":
            self._select_all_databases()
        elif os.path.exists(self.active_folder_path):
            self._select_folder(self.active_folder_path)
        else:
            self._select_all_databases()

    def _create_all_databases_card(self) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("zed-shortcut-card")
        if self.active_folder_path == "all" or not self.active_folder_path:
            btn.add_css_class("zed-card-active")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(8)
        row.set_margin_end(8)
        row.set_margin_top(6)
        row.set_margin_bottom(6)

        icon = Gtk.Label(label="🗄")
        row.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name_lbl = Gtk.Label(label="All Databases & Archives", xalign=0.0)
        name_lbl.add_css_class("zed-card-title")
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        desc_lbl = Gtk.Label(label="Aggregated view of all local chess databases", xalign=0.0)
        desc_lbl.add_css_class("zed-card-desc")
        desc_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.append(name_lbl)
        vbox.append(desc_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        btn.set_child(row)
        btn.connect("clicked", lambda _: self._select_all_databases())
        return btn

    def refresh_recents(self):
        """Re-render recent files list."""
        while child := self.recents_container.get_first_child():
            self.recents_container.remove(child)

        recents = self.library_store.get_recent_files()
        if not recents:
            empty_lbl = Gtk.Label(label="No recent PGN files opened.", xalign=0.0)
            empty_lbl.add_css_class("zed-empty-label")
            self.recents_container.append(empty_lbl)
            return

        for rec in recents:
            card = self._create_recent_card(rec)
            self.recents_container.append(card)

    def _create_shortcut_card(self, shortcut: Dict[str, str]) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        card.add_css_class("zed-shortcut-card")
        if self.active_folder_path == shortcut["path"]:
            card.add_css_class("zed-card-active")

        # Folder button (selects folder)
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.set_hexpand(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(6)
        row.set_margin_top(4)
        row.set_margin_bottom(4)

        icon = Gtk.Label(label="📁")
        row.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name_lbl = Gtk.Label(label=shortcut["name"], xalign=0.0)
        name_lbl.add_css_class("zed-card-title")
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        path_lbl = Gtk.Label(label=shortcut["path"], xalign=0.0)
        path_lbl.add_css_class("zed-card-desc")
        path_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        vbox.append(name_lbl)
        vbox.append(path_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        btn.set_child(row)
        btn.connect("clicked", lambda _, p=shortcut["path"]: self._select_folder(p))
        card.append(btn)

        # Delete shortcut button
        del_btn = Gtk.Button(label="✕")
        del_btn.add_css_class("flat")
        del_btn.add_css_class("zed-btn-remove")
        del_btn.set_hexpand(False)
        del_btn.set_tooltip_text("Remove folder shortcut")
        del_btn.connect("clicked", lambda _, p=shortcut["path"]: self._remove_folder(p))
        card.append(del_btn)

        return card

    def _create_recent_card(self, rec: Dict[str, Any]) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        card.add_css_class("zed-shortcut-card")
        if self.active_pgn_path == rec["path"]:
            card.add_css_class("zed-card-active")

        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.set_hexpand(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(8)
        row.set_margin_end(8)
        row.set_margin_top(4)
        row.set_margin_bottom(4)

        icon = Gtk.Label(label="♟")
        row.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name_lbl = Gtk.Label(label=rec["name"], xalign=0.0)
        name_lbl.add_css_class("zed-card-title")
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        name_lbl.set_width_chars(10)

        count = rec.get("game_count", 1)
        desc_lbl = Gtk.Label(label=f"{count} game{'s' if count != 1 else ''} · {rec.get('size_str', '')}", xalign=0.0)
        desc_lbl.add_css_class("zed-card-desc")
        desc_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        desc_lbl.set_width_chars(10)
        vbox.append(name_lbl)
        vbox.append(desc_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        btn.set_child(row)
        click_ctrl = Gtk.GestureClick.new()
        click_ctrl.connect(
            "pressed",
            lambda gesture, n_press, x, y, p=rec["path"]:
                self._open_and_load_database(p) if n_press >= 2 else self._select_pgn(p)
        )
        btn.add_controller(click_ctrl)
        btn.connect("clicked", lambda _, p=rec["path"]: self._select_pgn(p))
        card.append(btn)

        # Delete / remove recent database button
        del_btn = Gtk.Button(label="✕")
        del_btn.add_css_class("flat")
        del_btn.add_css_class("zed-btn-remove")
        del_btn.set_hexpand(False)
        del_btn.set_tooltip_text("Remove from recent databases")
        del_btn.connect("clicked", lambda _, p=rec["path"]: self._remove_recent(p))
        card.append(del_btn)

        return card

    def _remove_recent(self, file_path: str):
        self.library_store.remove_recent_file(file_path)
        self.refresh_recents()
        if self.active_folder_path == "all":
            self._select_all_databases()

    def _select_all_databases(self):
        """Aggregate and display all databases from all pinned folders and recents."""
        self.active_folder_path = "all"
        self.folder_title_lbl.set_text("ALL DATABASES & ARCHIVES (Double-click to open on board)")

        while child := self.files_container.get_first_child():
            self.files_container.remove(child)

        all_pgns: List[Dict[str, Any]] = []
        seen_paths = set()

        # 1. From pinned shortcut folders
        for sc in self.library_store.get_folder_shortcuts():
            for pgn in self.library_store.scan_folder_for_pgns(sc["path"]):
                if pgn["path"] not in seen_paths:
                    seen_paths.add(pgn["path"])
                    all_pgns.append(pgn)

        # 2. From recent files
        for rec in self.library_store.get_recent_files():
            if rec["path"] not in seen_paths and os.path.exists(rec["path"]):
                seen_paths.add(rec["path"])
                try:
                    stat = os.stat(rec["path"])
                    all_pgns.append({
                        "name": rec["name"],
                        "path": rec["path"],
                        "size_bytes": stat.st_size,
                        "size_str": rec.get("size_str", ""),
                        "mtime_str": rec.get("last_opened", "")[:16],
                        "game_count": rec.get("game_count", 1),
                        "is_db": rec["name"].lower().endswith(".db")
                    })
                except OSError:
                    continue

        if not all_pgns:
            empty_lbl = Gtk.Label(
                label="No chess databases found yet.\nUse '+ New PGN Database' or 'Open PGN File' to add databases.",
                xalign=0.0
            )
            empty_lbl.add_css_class("zed-empty-label")
            self.files_container.append(empty_lbl)
            return

        for pgn_info in all_pgns:
            card = self._create_pgn_file_card(pgn_info)
            self.files_container.append(card)

        # Pre-select first
        if all_pgns:
            self._select_pgn(all_pgns[0]["path"])

    def _open_and_load_database(self, pgn_path: str):
        """ChessBase-style: Double-clicking database immediately opens it on the board."""
        self._select_pgn(pgn_path)
        if self.cached_games:
            self._load_game_index(0)
        else:
            self._navigate_to_board()

    def _select_folder(self, folder_path: str):
        """Scan and display PGN files in selected folder."""
        self.active_folder_path = folder_path
        self.folder_title_lbl.set_text(f"PGN FILES IN: {os.path.basename(folder_path)} ({folder_path})")

        while child := self.files_container.get_first_child():
            self.files_container.remove(child)

        pgns = self.library_store.scan_folder_for_pgns(folder_path)
        if not pgns:
            empty_lbl = Gtk.Label(label="No .pgn files found in this folder. Use '+ New PGN Database' to create one.", xalign=0.0)
            empty_lbl.add_css_class("zed-empty-label")
            self.files_container.append(empty_lbl)
            return

        for pgn_info in pgns:
            card = self._create_pgn_file_card(pgn_info)
            self.files_container.append(card)

        # Automatically inspect the first PGN
        if pgns:
            self._select_pgn(pgns[0]["path"])

    def _create_pgn_file_card(self, pgn_info: Dict[str, Any]) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("zed-card-button")
        btn.set_tooltip_text("Double-click to open database on board\nSingle-click to view games below")
        if self.active_pgn_path == pgn_info["path"]:
            btn.add_css_class("zed-card-active")

        # Double-click opens directly on board; single-click selects
        click_ctrl = Gtk.GestureClick.new()
        click_ctrl.connect(
            "pressed",
            lambda gesture, n_press, x, y, p=pgn_info["path"]:
                self._open_and_load_database(p) if n_press >= 2 else self._select_pgn(p)
        )
        btn.add_controller(click_ctrl)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_start(12)
        row.set_margin_end(12)
        row.set_margin_top(8)
        row.set_margin_bottom(8)

        icon = Gtk.Label(label="🗄" if pgn_info.get("is_db") else "📄")
        row.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_lbl = Gtk.Label(label=pgn_info["name"], xalign=0.0)
        name_lbl.add_css_class("zed-card-title")
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        meta_str = f"{pgn_info['game_count']} game{'s' if pgn_info['game_count'] != 1 else ''} · {pgn_info['size_str']} · Modified: {pgn_info['mtime_str']}"
        meta_lbl = Gtk.Label(label=meta_str, xalign=0.0)
        meta_lbl.add_css_class("zed-card-desc")
        meta_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.append(name_lbl)
        vbox.append(meta_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        open_pill = Gtk.Label(label="Explore →")
        open_pill.add_css_class("zed-pill-explore")
        row.append(open_pill)

        btn.set_child(row)
        btn.connect("clicked", lambda _, p=pgn_info["path"]: self._select_pgn(p))
        return btn

    def _select_pgn(self, pgn_path: str):
        """Index games in PGN and populate the Game Browser."""
        self.active_pgn_path = pgn_path
        self.library_store.add_recent_file(pgn_path)
        self.refresh_recents()

        games = self.library_store.list_games_in_pgn(pgn_path)
        self.cached_games = games
        self.pgn_title_lbl.set_text(f"GAMES IN: {os.path.basename(pgn_path)} ({len(games)} games)")
        self._render_games_list(games)

    def _render_games_list(self, games: List[Dict[str, Any]]):
        while child := self.games_container.get_first_child():
            self.games_container.remove(child)

        if not games:
            empty_lbl = Gtk.Label(label="No games found matching filter.", xalign=0.0)
            empty_lbl.add_css_class("zed-empty-label")
            self.games_container.append(empty_lbl)
            return

        for game in games:
            btn = self._create_game_row(game)
            self.games_container.append(btn)

    def _create_game_row(self, game: Dict[str, Any]) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("zed-game-row")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(6)
        row.set_margin_bottom(6)

        # Index #
        idx_lbl = Gtk.Label(label=f"#{game['index'] + 1}")
        idx_lbl.add_css_class("zed-game-idx")
        row.append(idx_lbl)

        # Players & Event
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        players_lbl = Gtk.Label(label=f"{game['white']} vs. {game['black']}", xalign=0.0)
        players_lbl.add_css_class("zed-game-players")
        players_lbl.set_ellipsize(Pango.EllipsizeMode.END)

        eco_part = f"[{game['eco']}] " if game.get("eco") else ""
        meta_str = f"{eco_part}{game['event']} · {game['date']}"
        meta_lbl = Gtk.Label(label=meta_str, xalign=0.0)
        meta_lbl.add_css_class("zed-game-meta")
        meta_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.append(players_lbl)
        vbox.append(meta_lbl)
        vbox.set_hexpand(True)
        row.append(vbox)

        # Result badge (1-0, 0-1, 1/2-1/2)
        res_lbl = Gtk.Label(label=game["result"])
        res_lbl.add_css_class("zed-result-badge")
        row.append(res_lbl)

        # Play / Load Button
        load_lbl = Gtk.Label(label="Load ♟")
        load_lbl.add_css_class("zed-pill-load")
        row.append(load_lbl)

        btn.set_child(row)
        btn.set_tooltip_text("Double-click to open game on board")
        click_ctrl = Gtk.GestureClick.new()
        click_ctrl.connect(
            "pressed",
            lambda gesture, n_press, x, y, g_idx=game["index"]:
                self._load_game_index(g_idx) if n_press >= 1 else None
        )
        btn.add_controller(click_ctrl)
        btn.connect("clicked", lambda _, g_idx=game["index"]: self._load_game_index(g_idx))
        return btn

    def _on_filter_changed(self, entry: Gtk.SearchEntry):
        query = entry.get_text().strip().lower()
        if not query:
            self._render_games_list(self.cached_games)
            return

        filtered = [
            g for g in self.cached_games
            if query in g["white"].lower()
            or query in g["black"].lower()
            or query in g["event"].lower()
            or query in g.get("eco", "").lower()
            or query in g["date"].lower()
        ]
        self._render_games_list(filtered)

    def _load_game_index(self, index: int):
        """Load selected game AST and switch to board view."""
        if not self.active_pgn_path:
            return
        game_ast = self.library_store.load_game_from_pgn(self.active_pgn_path, index)
        if game_ast and self.on_load_game:
            try:
                self.on_load_game(game_ast, self.active_pgn_path, index)
            except TypeError:
                self.on_load_game(game_ast, self.active_pgn_path)

    def _navigate_to_board(self):
        if self.on_switch_to_board:
            self.on_switch_to_board()

    # -------------------------------------------------------------------------
    # Dialog Actions (Add Folder, Open PGN, New PGN)
    # -------------------------------------------------------------------------
    def _on_add_folder_clicked(self, _btn):
        chooser = Gtk.FileChooserNative(
            title="Select Chess Folder to Bookmark",
            transient_for=self.parent_window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Add Shortcut",
            cancel_label="_Cancel"
        )

        def on_response(native, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                f = native.get_file()
                if f and f.get_path():
                    self.library_store.add_folder_shortcut(f.get_path())
                    self.refresh_shortcuts()
                    self._select_folder(f.get_path())

        chooser.connect("response", on_response)
        chooser.show()

    def _remove_folder(self, path: str):
        self.library_store.remove_folder_shortcut(path)
        self.refresh_shortcuts()

    def _on_open_file_clicked(self, _btn):
        chooser = Gtk.FileChooserNative(
            title="Open Chess PGN File",
            transient_for=self.parent_window,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Open PGN",
            cancel_label="_Cancel"
        )

        filter_pgn = Gtk.FileFilter()
        filter_pgn.set_name("Chess PGN & DB (*.pgn, *.db)")
        filter_pgn.add_pattern("*.pgn")
        filter_pgn.add_pattern("*.PGN")
        filter_pgn.add_pattern("*.db")
        chooser.add_filter(filter_pgn)

        def on_response(native, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                f = native.get_file()
                if f and f.get_path():
                    folder = os.path.dirname(f.get_path())
                    self.library_store.add_folder_shortcut(folder)
                    self.refresh_shortcuts()
                    self._select_folder(folder)
                    self._select_pgn(f.get_path())

        chooser.connect("response", on_response)
        chooser.show()

    def _on_new_pgn_clicked(self, _btn):
        chooser = Gtk.FileChooserNative(
            title="Create New PGN File",
            transient_for=self.parent_window,
            action=Gtk.FileChooserAction.SAVE,
            accept_label="_Create PGN",
            cancel_label="_Cancel"
        )
        chooser.set_current_name("new_database.pgn")

        def on_response(native, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                f = native.get_file()
                if f and f.get_path():
                    path = f.get_path()
                    created = self.library_store.create_new_pgn_file(
                        path,
                        event="Local Study",
                        white="Player 1",
                        black="Player 2"
                    )
                    folder = os.path.dirname(created)
                    self.library_store.add_folder_shortcut(folder)
                    self.refresh_shortcuts()
                    self._select_folder(folder)
                    self._select_pgn(created)

        chooser.connect("response", on_response)
        chooser.show()
