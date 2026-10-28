"""
Application entrypoint and GLib event loop manager.
"""

import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio

from chess_reader.ui.window import ChessReaderWindow


class ChessReaderApp(Adw.Application):
    """Main Adw.Application instance."""

    def __init__(self):
        super().__init__(
            application_id="io.github.antigravity.ChessReader",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._load_css()

        # Enforce dark mode adhering to Zed aesthetics
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ChessReaderWindow(application=self)
        win.present()

    def do_open(self, files, n_files, hint):
        self.do_activate()
        win = self.props.active_window
        if win and files:
            file_path = files[0].get_path()
            if file_path and os.path.exists(file_path):
                game_ast = win.library_store.load_game_from_pgn(file_path, 0)
                if game_ast:
                    win._on_library_game_loaded(game_ast, file_path)

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(css_path):
            css_provider.load_from_path(css_path)
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )


def main():
    app = ChessReaderApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
