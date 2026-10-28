"""
Zed-style code-editor Move Tree View for GTK4.
Renders recursive variations (RAVs) with code indentation, inline NAG badges, comments,
clock/evaluation pills, and keyboard navigation.
"""

from typing import Optional, Dict
import gi
import chess
import chess.pgn

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

from chess_reader.core.game_model import GameModel
from chess_reader.core.annotations import NAG_TO_SYMBOL, parse_comment_metadata


class MoveTreeView(Gtk.Box):
    """Monospace nested move tree panel styled like a code editor."""

    def __init__(self, game_model: GameModel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("move-tree-panel")
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.model = game_model
        self._node_widgets: Dict[chess.pgn.GameNode, Gtk.Widget] = {}

        # 1. Navigation Toolbar
        self.toolbar = self._build_toolbar()
        self.append(self.toolbar)

        # 2. Scrollable Move Tree View
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.add_css_class("notation-scroll")
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(self.scrolled_window)

        # Tree Container
        self.tree_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.tree_container.add_css_class("move-tree-box")
        self.scrolled_window.set_child(self.tree_container)

        # Attach keyboard navigation controller
        self._setup_keyboard_nav()

        # Connect to model updates
        self.model.add_listener(self._on_model_changed)

        # Initial build
        self.rebuild_tree()

    def _build_toolbar(self) -> Gtk.Box:
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.add_css_class("notation-toolbar")

        # Step First
        self.btn_first = Gtk.Button(label="|◀")
        self.btn_first.set_tooltip_text("Start of Game (Home)")
        self.btn_first.add_css_class("flat")
        self.btn_first.connect("clicked", lambda _: self.model.go_to_root())
        toolbar.append(self.btn_first)

        # Step Prev
        self.btn_prev = Gtk.Button(label="◀")
        self.btn_prev.set_tooltip_text("Previous Move (Left Arrow)")
        self.btn_prev.add_css_class("flat")
        self.btn_prev.connect("clicked", lambda _: self.model.prev_move())
        toolbar.append(self.btn_prev)

        # Step Next
        self.btn_next = Gtk.Button(label="▶")
        self.btn_next.set_tooltip_text("Next Move (Right Arrow)")
        self.btn_next.add_css_class("flat")
        self.btn_next.connect("clicked", lambda _: self.model.next_move(0))
        toolbar.append(self.btn_next)

        # Step Last
        self.btn_last = Gtk.Button(label="▶|")
        self.btn_last.set_tooltip_text("End of Mainline (End)")
        self.btn_last.add_css_class("flat")
        self.btn_last.connect("clicked", lambda _: self.model.go_to_end())
        toolbar.append(self.btn_last)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        # Promote Branch
        self.btn_promote = Gtk.Button(label="↑ Promote")
        self.btn_promote.set_tooltip_text("Promote current variation to mainline")
        self.btn_promote.add_css_class("flat")
        self.btn_promote.connect("clicked", self._on_promote_clicked)
        toolbar.append(self.btn_promote)

        # Delete Branch
        self.btn_delete = Gtk.Button(label="✕ Delete")
        self.btn_delete.set_tooltip_text("Delete current variation branch")
        self.btn_delete.add_css_class("flat")
        self.btn_delete.connect("clicked", self._on_delete_clicked)
        toolbar.append(self.btn_delete)

        return toolbar

    def _setup_keyboard_nav(self):
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Left:
            self.model.prev_move()
            return True
        elif keyval == Gdk.KEY_Right:
            self.model.next_move(0)
            return True
        elif keyval == Gdk.KEY_Home:
            self.model.go_to_root()
            return True
        elif keyval == Gdk.KEY_End:
            self.model.go_to_end()
            return True
        elif keyval == Gdk.KEY_Up:
            # Jump to previous variation sibling
            parent = self.model.current_node.parent
            if parent and len(parent.variations) > 1:
                idx = parent.variations.index(self.model.current_node)
                prev_idx = (idx - 1) % len(parent.variations)
                self.model.go_to_node(parent.variations[prev_idx])
                return True
        elif keyval == Gdk.KEY_Down:
            # Jump to next variation sibling
            parent = self.model.current_node.parent
            if parent and len(parent.variations) > 1:
                idx = parent.variations.index(self.model.current_node)
                next_idx = (idx + 1) % len(parent.variations)
                self.model.go_to_node(parent.variations[next_idx])
                return True
        return False

    def _on_promote_clicked(self, btn):
        if not self.model.is_root:
            self.model.promote_variation(self.model.current_node)

    def _on_delete_clicked(self, btn):
        if not self.model.is_root:
            self.model.delete_variation(self.model.current_node)

    def _on_model_changed(self, model: GameModel):
        self.update_active_selection()

    def update_active_selection(self):
        """Update active move highlight without rebuilding entire tree."""
        current = self.model.current_node
        for node, widget in self._node_widgets.items():
            if node == current:
                widget.add_css_class("active-move")
            else:
                widget.remove_css_class("active-move")

    def rebuild_tree(self):
        """Recursively construct the indented code-like move tree."""
        while child := self.tree_container.get_first_child():
            self.tree_container.remove(child)

        self._node_widgets.clear()
        root = self.model.game.root()
        if not root.variations:
            empty_lbl = Gtk.Label(label="No moves recorded. Play a move on the board.")
            empty_lbl.add_css_class("comment-block")
            self.tree_container.append(empty_lbl)
            return

        self._render_node_continuation(root, self.tree_container, is_mainline=True)
        self.update_active_selection()

    def _render_node_continuation(self, start_node: chess.pgn.GameNode, parent_box: Gtk.Box, is_mainline: bool):
        """Traverse and render mainline continuation and nested RAV variations."""
        node = start_node
        current_row = None

        while node.variations:
            mainline_child = node.variations[0]
            alt_variations = node.variations[1:]

            # Move number & SAN
            if current_row is None:
                current_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                current_row.add_css_class("move-row")
                parent_box.append(current_row)

            # Move Token Widget
            move_btn = self._create_move_token(mainline_child)
            self._node_widgets[mainline_child] = move_btn
            current_row.append(move_btn)

            # Optional comments or clocks for mainline_child
            if mainline_child.comment:
                comment_widget = self._create_comment_widget(mainline_child.comment)
                parent_box.append(comment_widget)
                current_row = None  # Start fresh row after comment

            # Render alternative branches (RAVs) indented below
            for alt in alt_variations:
                current_row = None
                var_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                var_box.add_css_class("variation-box")
                parent_box.append(var_box)

                var_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                var_btn = self._create_move_token(alt, is_alt_start=True)
                self._node_widgets[alt] = var_btn
                var_header.append(var_btn)
                var_box.append(var_header)

                if alt.comment:
                    var_box.append(self._create_comment_widget(alt.comment))

                # Recursively render continuation inside variation
                if alt.variations:
                    self._render_node_continuation(alt, var_box, is_mainline=False)

            node = mainline_child

    def _create_move_token(self, node: chess.pgn.GameNode, is_alt_start: bool = False) -> Gtk.Button:
        """Create clickable button for a move with move number, SAN, and NAG badges."""
        san = node.san()
        ply = node.ply()
        move_num = (ply + 1) // 2

        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("move-token")
        if node == self.model.current_node:
            btn.add_css_class("active-move")

        token_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        btn.set_child(token_box)

        # Move Number Prefix: e.g. "1." or "1..."
        if node.turn() == chess.BLACK:  # White just played
            num_lbl = Gtk.Label(label=f"{move_num}.")
            num_lbl.add_css_class("move-number")
            token_box.append(num_lbl)
        elif is_alt_start or node.parent.move is None:
            num_lbl = Gtk.Label(label=f"{move_num}...")
            num_lbl.add_css_class("move-number")
            token_box.append(num_lbl)

        # Move SAN
        san_lbl = Gtk.Label(label=san)
        token_box.append(san_lbl)

        # NAG Badges (e.g. "!", "?", "⩲")
        nags = self.model.get_nags_display(node)
        for nag_sym in nags:
            nag_lbl = Gtk.Label(label=nag_sym)
            nag_lbl.add_css_class("nag-badge")
            token_box.append(nag_lbl)

        btn.connect("clicked", lambda _, n=node: self.model.go_to_node(n))
        return btn

    def _create_comment_widget(self, comment_text: str) -> Gtk.Box:
        """Create styled block for inline move commentary and metadata."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        clk, ev, clean_txt = parse_comment_metadata(comment_text)

        if clean_txt:
            lbl = Gtk.Label(label=clean_txt)
            lbl.add_css_class("comment-block")
            lbl.set_wrap(True)
            box.append(lbl)

        if clk:
            clk_lbl = Gtk.Label(label=f"⏱ {clk}")
            clk_lbl.add_css_class("meta-pill")
            box.append(clk_lbl)

        if ev:
            ev_lbl = Gtk.Label(label=f"eval {ev}")
            ev_lbl.add_css_class("meta-pill")
            box.append(ev_lbl)

        return box
