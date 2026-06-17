import queue

import cairo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

_EDGE = 6
_MIN_W = 200
_MIN_H = 50
_MAX_LINES = 50

_CURSOR_MAP = {
    Gdk.WindowEdge.NORTH: Gdk.CursorType.TOP_SIDE,
    Gdk.WindowEdge.SOUTH: Gdk.CursorType.BOTTOM_SIDE,
    Gdk.WindowEdge.WEST: Gdk.CursorType.LEFT_SIDE,
    Gdk.WindowEdge.EAST: Gdk.CursorType.RIGHT_SIDE,
    Gdk.WindowEdge.NORTH_WEST: Gdk.CursorType.TOP_LEFT_CORNER,
    Gdk.WindowEdge.NORTH_EAST: Gdk.CursorType.TOP_RIGHT_CORNER,
    Gdk.WindowEdge.SOUTH_WEST: Gdk.CursorType.BOTTOM_LEFT_CORNER,
    Gdk.WindowEdge.SOUTH_EAST: Gdk.CursorType.BOTTOM_RIGHT_CORNER,
}


class CaptionWindow:
    def __init__(self, display_queue: queue.Queue, on_close=None):
        self.display_queue = display_queue
        self.on_close = on_close
        self._poll_id = None

        self._resizing = False
        self._resize_edge = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_w = 0
        self._drag_start_h = 0
        self._drag_start_px = 0
        self._drag_start_py = 0

        self.window = Gtk.Window(title="NihonSub — Live Captions")
        
        # Calculate default size and position based on screen dimensions
        # Width: 2/3 of screen width (wide subtitle band)
        # Height: 30px (thin single-line strip)
        # Position: bottom center of screen
        screen = Gdk.Screen.get_default()
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        default_width = int(screen_width * 2 / 3)
        default_height = 30
        
        self.window.set_default_size(default_width, default_height)
        
        # Position at bottom center of screen
        window_x = (screen_width - default_width) // 2  # center horizontally
        window_y = screen_height - default_height       # bottom of screen
        self.window.move(window_x, window_y)
        
        self.window.set_keep_above(True)
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        self.window.set_visual(self.window.get_screen().get_rgba_visual())

        self.window.connect("destroy", self._on_destroy)
        self.window.connect("draw", self._on_draw)

        self._setup_ui()

    def _setup_ui(self):
        self.text_buffer = Gtk.TextBuffer()
        self.text_view = Gtk.TextView(buffer=self.text_buffer)
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        css = b"""
        scrolledwindow {
            background-color: transparent;
            background-image: none;
        }
        scrolledwindow scrollbar {
            opacity: 0;
            background-color: transparent;
        }
        textview {
            background-color: rgba(0, 0, 0, 0.78);
            font-size: 18px;
            color: white;
            padding: 12px;
        }
        textview text {
            background-color: transparent;
            color: white;
        }
        """
        self._css_provider = Gtk.CssProvider()
        self._css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.window.get_screen(),
            self._css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        event_box = Gtk.EventBox()
        event_box.set_above_child(True)
        event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        event_box.add(self.text_view)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(event_box)
        self.window.add(self.scroll)

        event_box.connect("button-press-event", self._on_click)
        event_box.connect("button-release-event", self._on_release)
        event_box.connect("motion-notify-event", self._on_motion)
        event_box.connect("leave-notify-event", self._on_leave)

    def _edge_at(self, x, y):
        w, h = self.window.get_size()
        left = x <= _EDGE
        right = x >= w - _EDGE
        top = y <= _EDGE
        bottom = y >= h - _EDGE

        if top:
            if left:
                return Gdk.WindowEdge.NORTH_WEST
            if right:
                return Gdk.WindowEdge.NORTH_EAST
            return Gdk.WindowEdge.NORTH
        if bottom:
            if left:
                return Gdk.WindowEdge.SOUTH_WEST
            if right:
                return Gdk.WindowEdge.SOUTH_EAST
            return Gdk.WindowEdge.SOUTH
        if left:
            return Gdk.WindowEdge.WEST
        if right:
            return Gdk.WindowEdge.EAST
        return None

    def _set_edge_cursor(self, edge):
        display = self.window.get_display()
        cursor_type = _CURSOR_MAP.get(edge)
        cursor = Gdk.Cursor.new_for_display(display, cursor_type)
        self.window.get_window().set_cursor(cursor)

    def _clear_cursor(self):
        self.window.get_window().set_cursor(None)

    def _on_click(self, widget, event):
        if event.button == 1:
            edge = self._edge_at(event.x, event.y)
            if edge is not None:
                w, h = self.window.get_size()
                px, py = self.window.get_position()
                self._resizing = True
                self._resize_edge = edge
                self._drag_start_x = int(event.x_root)
                self._drag_start_y = int(event.y_root)
                self._drag_start_w = w
                self._drag_start_h = h
                self._drag_start_px = px
                self._drag_start_py = py
            else:
                self.window.begin_move_drag(
                    Gdk.BUTTON_PRIMARY,
                    int(event.x_root), int(event.y_root), event.time,
                )
            return True
        return False

    def _on_motion(self, widget, event):
        if self._resizing:
            dx = int(event.x_root) - self._drag_start_x
            dy = int(event.y_root) - self._drag_start_y

            new_x = self._drag_start_px
            new_y = self._drag_start_py
            new_w = self._drag_start_w
            new_h = self._drag_start_h

            edge = self._resize_edge

            if edge in (
                Gdk.WindowEdge.EAST,
                Gdk.WindowEdge.NORTH_EAST,
                Gdk.WindowEdge.SOUTH_EAST,
            ):
                new_w = max(_MIN_W, self._drag_start_w + dx)

            if edge in (
                Gdk.WindowEdge.WEST,
                Gdk.WindowEdge.NORTH_WEST,
                Gdk.WindowEdge.SOUTH_WEST,
            ):
                new_w = max(_MIN_W, self._drag_start_w - dx)
                new_x = self._drag_start_px + self._drag_start_w - new_w

            if edge in (
                Gdk.WindowEdge.SOUTH,
                Gdk.WindowEdge.SOUTH_WEST,
                Gdk.WindowEdge.SOUTH_EAST,
            ):
                new_h = max(_MIN_H, self._drag_start_h + dy)

            if edge in (
                Gdk.WindowEdge.NORTH,
                Gdk.WindowEdge.NORTH_WEST,
                Gdk.WindowEdge.NORTH_EAST,
            ):
                new_h = max(_MIN_H, self._drag_start_h - dy)
                new_y = self._drag_start_py + self._drag_start_h - new_h

            self.window.move(new_x, new_y)
            self.window.resize(new_w, new_h)
        else:
            edge = self._edge_at(event.x, event.y)
            if edge is not None:
                self._set_edge_cursor(edge)
            else:
                self._clear_cursor()
        return False

    def _on_release(self, widget, event):
        self._resizing = False
        self._resize_edge = None
        return False

    def _on_leave(self, widget, event):
        if not self._resizing:
            self._clear_cursor()
        return False

    def _on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.paint()
        return False

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

        if self.text_buffer.get_line_count() > _MAX_LINES:
            start = self.text_buffer.get_iter_at_line(0)
            end = self.text_buffer.get_iter_at_line(self.text_buffer.get_line_count() - _MAX_LINES)
            self.text_buffer.delete(start, end)

        GLib.idle_add(self._scroll_to_end)

    def _scroll_to_end(self):
        adj = self.scroll.get_vadjustment()
        if adj:
            # Scroll to bottom: upper - page_size
            adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

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
