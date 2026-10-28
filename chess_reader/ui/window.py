"""
Main Application Window with Zed Design Language Chrome.
Unified Client-Side Decoration (CSD) headerbar, split-pane workspace, status bar,
and integrated Zed Command Palette and FEN Setup modal.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk

import chess
from chess_reader.core.game_model import GameModel
from chess_reader.theme.loader import ThemeManager
from chess_reader.theme.asset_cache import PieceAssetCache
from chess_reader.engine.uci_client import UCIEngineManager
from chess_reader.engine.game_review import BatchGameReviewer
from chess_reader.ui.board.board_view import ChessBoardView
from chess_reader.ui.notation.move_tree_view import MoveTreeView
from chess_reader.ui.dock.eval_bar import EvalBar
from chess_reader.ui.dock.engine_dock import EngineDock
from chess_reader.ui.palette.command_palette import CommandPalette, CommandItem
from chess_reader.ui.modals.fen_dialog import FENSetupDialog


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

        self.set_breadcrumb(["Live Analysis", "Starting Position"])
        self.header.pack_start(self.breadcrumb_box)

        # Right: Quick action buttons
        self.flip_btn = Gtk.Button(label="Flip (F)")
        self.flip_btn.set_tooltip_text("Flip Board Perspective (F)")
        self.flip_btn.add_css_class("flat")
        self.header.pack_end(self.flip_btn)

        self.palette_btn = Gtk.Button(label="⌘K")
        self.palette_btn.set_tooltip_text("Command Palette (Ctrl+K / Ctrl+P)")
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
        self.fen_btn = Gtk.Button(label="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.fen_btn.set_tooltip_text("Click to copy FEN to clipboard")
        self.fen_btn.add_css_class("flat")
        self.fen_btn.add_css_class("zed-status-interactive")
        self.fen_btn.connect("clicked", self._on_fen_clicked)
        self.append(self.fen_btn)

        # Active Theme Profile
        self.theme_label = Gtk.Label(label="Theme: zed-dark")
        self.theme_label.add_css_class("zed-status-item")
        self.append(self.theme_label)

    def set_fen(self, fen: str):
        """Update FEN button text."""
        self.fen_btn.set_label(fen)

    def _on_fen_clicked(self, btn):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self.fen_btn.get_label())


class ChessReaderWindow(Adw.ApplicationWindow):
    """Main application window implementing the Zed layout."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("ChessReader")
        self.set_default_size(1280, 840)
        self.add_css_class("chess-reader-window")

        # Managers & Domain State
        self.theme_manager = ThemeManager()
        self.asset_cache = PieceAssetCache()
        self.game_model = GameModel()
        self.engine_manager = UCIEngineManager()
        self.engine_enabled = True

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

        # Left / Center: Interactive Chess Board + Eval Bar + Analysis Dock
        self.board_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.board_panel.add_css_class("zed-panel")
        self.board_panel.set_hexpand(True)

        # Board Row (EvalBar + ChessBoardView)
        board_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        board_row.set_vexpand(True)
        board_row.set_hexpand(True)

        self.eval_bar = EvalBar()
        board_row.append(self.eval_bar)

        self.board_view = ChessBoardView(
            theme=self.theme_manager.active_theme,
            asset_cache=self.asset_cache
        )
        self.board_view.on_move_made = self._on_board_move_played
        board_row.append(self.board_view)
        self.board_panel.append(board_row)

        # Bottom Dock (Collapsible Multi-PV & CPL Graph)
        self.engine_dock = EngineDock()
        self.engine_dock.cpl_graph.on_ply_selected = self._on_graph_ply_selected
        self.board_panel.append(self.engine_dock)

        self.workspace.set_start_child(self.board_panel)

        # Right: Move Notation Tree & Variations Panel
        self.notation_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notation_panel.add_css_class("zed-sidebar")
        self.notation_panel.set_size_request(380, -1)

        self.move_tree_view = MoveTreeView(game_model=self.game_model)
        self.notation_panel.append(self.move_tree_view)
        self.workspace.set_end_child(self.notation_panel)

        # 3. Status Bar (Bottom Bar)
        self.status_bar = StatusBar()
        self.toolbar_view.add_bottom_bar(self.status_bar)

        # Connect actions & listeners
        self.titlebar.flip_btn.connect("clicked", self._on_flip_clicked)
        self.titlebar.palette_btn.connect("clicked", lambda _: self.open_command_palette())
        self.theme_manager.add_theme_listener(self._on_theme_changed)
        self.game_model.add_listener(self._on_game_model_changed)

        # Attach Global Key Controller for shortcuts (Ctrl+K, Ctrl+P, etc.)
        self._setup_global_shortcuts()

        # Connect window destroy to close engine
        self.connect("destroy", lambda _: self.engine_manager.close())

        # Initial synchronization & engine trigger
        self._sync_view_to_game()
        self._trigger_engine_analysis()

    def _setup_global_shortcuts(self):
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_window_key_pressed)
        self.add_controller(key_ctrl)

    def _on_window_key_pressed(self, ctrl, keyval, keycode, state):
        is_ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        is_shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        # Ctrl+K or Ctrl+P -> Open Command Palette
        if is_ctrl and keyval in (Gdk.KEY_k, Gdk.KEY_K, Gdk.KEY_p, Gdk.KEY_P):
            self.open_command_palette()
            return True

        # Ctrl+Shift+F -> Open FEN Setup Modal
        if is_ctrl and is_shift and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.open_fen_dialog()
            return True

        # Ctrl+C -> Copy FEN
        if is_ctrl and keyval in (Gdk.KEY_c, Gdk.KEY_C):
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(self.game_model.board.fen())
            return True

        # Ctrl+N -> Reset to starting position
        if is_ctrl and keyval in (Gdk.KEY_n, Gdk.KEY_N):
            self.reset_to_start()
            return True

        # Escape -> Clear drawings
        if keyval == Gdk.KEY_Escape:
            self.board_view.clear_drawings()
            return True

        return False

    def open_command_palette(self):
        """Display Zed-style Command Palette modal."""
        commands = self._build_palette_commands()
        palette = CommandPalette(parent_window=self, commands=commands)
        palette.present()

    def open_fen_dialog(self):
        """Open interactive FEN position setup dialog."""
        current_fen = self.game_model.board.fen()
        dialog = FENSetupDialog(
            parent_window=self,
            current_fen=current_fen,
            on_fen_loaded=self._on_fen_loaded
        )
        dialog.present()

    def _on_fen_loaded(self, fen: str):
        board = chess.Board(fen)
        new_game = chess.pgn.Game()
        new_game.setup(board)
        self.game_model = GameModel(new_game)
        self.game_model.add_listener(self._on_game_model_changed)
        self.move_tree_view.model = self.game_model
        self.move_tree_view.rebuild_tree()
        self._sync_view_to_game()
        self._trigger_engine_analysis()

    def reset_to_start(self):
        """Reset board to initial chess starting position."""
        self.game_model = GameModel()
        self.game_model.add_listener(self._on_game_model_changed)
        self.move_tree_view.model = self.game_model
        self.move_tree_view.rebuild_tree()
        self._sync_view_to_game()
        self._trigger_engine_analysis()

    def run_full_game_review(self):
        """Run batch analysis across all moves in active game."""
        if not self.engine_manager.is_available():
            return
        reviewer = BatchGameReviewer(self.engine_manager.engine_path)
        result = reviewer.review_game(self.game_model.game, depth=8)
        self.engine_dock.cpl_graph.set_data(result.cpl_curve)

    def _build_palette_commands(self) -> list[CommandItem]:
        """Assemble all executable commands for the palette."""
        cmds = [
            CommandItem(
                id="board_flip",
                title="Flip Board Perspective",
                category="Board",
                shortcut="F",
                action=lambda: self._on_flip_clicked(None)
            ),
            CommandItem(
                id="board_fen_modal",
                title="Set Board Position (FEN)",
                category="Board",
                shortcut="Ctrl+Shift+F",
                action=self.open_fen_dialog
            ),
            CommandItem(
                id="board_copy_fen",
                title="Copy Current FEN to Clipboard",
                category="Board",
                shortcut="Ctrl+C",
                action=lambda: Gdk.Display.get_default().get_clipboard().set(self.game_model.board.fen())
            ),
            CommandItem(
                id="board_reset",
                title="Reset to Starting Position",
                category="Board",
                shortcut="Ctrl+N",
                action=self.reset_to_start
            ),
            CommandItem(
                id="board_clear_drawings",
                title="Clear Board Arrows and Highlights",
                category="Board",
                shortcut="Escape",
                action=self.board_view.clear_drawings
            ),
            CommandItem(
                id="engine_toggle",
                title="Toggle Live Engine Analysis",
                category="Engine",
                shortcut="Space",
                action=self._toggle_engine
            ),
            CommandItem(
                id="engine_review",
                title="Run Full Game Review & CPL Curve",
                category="Engine",
                shortcut="Ctrl+R",
                action=self.run_full_game_review
            ),
            CommandItem(
                id="pgn_export",
                title="Export PGN to Clipboard",
                category="File",
                shortcut="Ctrl+E",
                action=lambda: Gdk.Display.get_default().get_clipboard().set(self.game_model.export_pgn())
            ),
            CommandItem(
                id="nav_root",
                title="Go to Game Start",
                category="Navigation",
                shortcut="Home",
                action=self.game_model.go_to_root
            ),
            CommandItem(
                id="nav_end",
                title="Go to End of Game",
                category="Navigation",
                shortcut="End",
                action=self.game_model.go_to_end
            ),
        ]

        # Add dynamic theme switching commands
        for theme in self.theme_manager.list_themes():
            cmds.append(
                CommandItem(
                    id=f"theme_{theme.id}",
                    title=f"Switch Theme: {theme.name}",
                    category="Themes",
                    action=lambda t_id=theme.id: self.theme_manager.set_active_theme(t_id)
                )
            )

        return cmds

    def _toggle_engine(self):
        self.engine_enabled = not self.engine_enabled
        if not self.engine_enabled:
            self.engine_manager.stop_current_analysis()
            self.status_bar.engine_label.set_text("Stockfish 18 · Paused")
        else:
            self._trigger_engine_analysis()

    def _on_graph_ply_selected(self, ply: int):
        """Navigate to move when clicked on CPL graph."""
        moves = list(self.game_model.game.mainline())
        if 0 <= ply <= len(moves):
            node = self.game_model.game.root()
            for _ in range(ply):
                if node.variations:
                    node = node.variations[0]
            self.game_model.go_to_node(node)

    def _on_flip_clicked(self, btn):
        self.board_view.flip()
        self.eval_bar.set_flipped(self.board_view.flipped)

    def _on_board_move_played(self, move: chess.Move):
        self.board_view.board.pop()
        self.game_model.add_move(move)
        self.move_tree_view.rebuild_tree()

    def _on_game_model_changed(self, model: GameModel):
        self._sync_view_to_game()
        if self.engine_enabled:
            self._trigger_engine_analysis()

    def _sync_view_to_game(self):
        board = self.game_model.board
        last_move = self.game_model.current_node.move
        self.board_view.set_board(board, last_move=last_move)
        self.status_bar.set_fen(board.fen())
        self.titlebar.set_breadcrumb(self.game_model.get_breadcrumb_title())

    def _trigger_engine_analysis(self):
        if self.engine_manager.is_available() and self.engine_enabled:
            board = self.game_model.board
            self.engine_manager.analyze_position(
                board=board,
                multipv=3,
                max_depth=20,
                on_update=self._on_engine_update
            )

    def _on_engine_update(self, snapshot):
        self.engine_dock.update_snapshot(snapshot)
        top = snapshot.top_line
        if top:
            self.eval_bar.set_evaluation(top.display_score, top.win_percentage)
            n_fmt = f"{snapshot.nodes / 1_000_000:.1f}M" if snapshot.nodes >= 1_000_000 else f"{snapshot.nodes // 1000}k"
            self.status_bar.engine_label.set_text(
                f"Stockfish 18 · Depth: {snapshot.depth} · {n_fmt} nodes ({snapshot.nps // 1000}k n/s)"
            )

    def _on_theme_changed(self, new_theme):
        self.status_bar.theme_label.set_text(f"Theme: {new_theme.id}")
        self.board_view.set_theme(new_theme)
