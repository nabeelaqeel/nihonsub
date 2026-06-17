import queue
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib


class CaptionWindow:
    def __init__(self, display_queue: queue.Queue, on_close=None):
        self.display_queue = display_queue
        self.on_close = on_close
        self._poll_id = None

        self.window = Gtk.Window(title="NihonSub — Live Captions")
        self.window.set_default_size(600, 200)
        self.window.set_keep_above(True)
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        self.window.set_visual(self.window.get_screen().get_rgba_visual())

        self.window.connect("destroy", self._on_destroy)
        self.window.connect("button-press-event", self._on_click)

        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        self._setup_ui()

    def _setup_ui(self):
        self.text_buffer = Gtk.TextBuffer()
        self.text_view = Gtk.TextView(buffer=self.text_buffer)
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        css = b"""
        textview {
            background-color: rgba(0, 0, 0, 200);
            font-size: 18px;
            color: white;
            padding: 12px;
        }
        textview text {
            background-color: transparent;
            color: white;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.window.get_screen(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.text_view)

        self.window.add(scroll)

        self._drag_start_x = 0
        self._drag_start_y = 0

    def _on_click(self, widget, event):
        if event.button == 1:
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self.window.begin_move_drag(
                Gdk.BUTTON_PRIMARY,
                int(event.x_root),
                int(event.y_root),
                event.time,
            )

    def _on_destroy(self, widget):
        if self._poll_id is not None:
            GLib.source_remove(self._poll_id)
        if self.on_close:
            self.on_close()

    def add_caption(self, text: str):
        end_iter = self.text_buffer.get_end_iter()
        if self.text_buffer.get_char_count() > 0:
            self.text_buffer.insert(end_iter, "\n")
            end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, text)

        mark = self.text_buffer.create_mark(None, self.text_buffer.get_end_iter(), False)
        self.text_view.scroll_to_mark(mark, 0.0, False, 0.0, 0.0)

    def _poll_display(self):
        try:
            while True:
                seg = self.display_queue.get_nowait()
                text = seg.get("text", "").strip()
                if text and seg.get("id", -1) >= 0:
                    GLib.idle_add(self.add_caption, text)
        except queue.Empty:
            pass
        return True

    def run(self):
        self.window.show_all()
        self._poll_id = GLib.timeout_add(200, self._poll_display)
        Gtk.main()
