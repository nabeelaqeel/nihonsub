"""Unit tests for GTK caption window logic.

Tests core functionality without needing a running display or event loop.
"""

import sys

sys.path.insert(0, ".")

from src.ui.gtk_window import Gdk, _CURSOR_MAP


def test_cursor_map_has_all_edges():
    """All 8 resize directions have a cursor type."""
    assert len(_CURSOR_MAP) == 8
    for edge, cursor in _CURSOR_MAP.items():
        assert cursor is not None, f"No cursor for {edge}"


def test_edge_constants():
    """Constants are set correctly."""
    from src.ui.gtk_window import _EDGE, _MIN_W, _MIN_H, _MAX_LINES
    assert _EDGE == 6
    assert _MIN_W == 200
    assert _MIN_H == 50
    assert _MAX_LINES == 50


def test_cursor_types_exist():
    """All cursor types in CURSOR_MAP are valid Gdk.CursorType values."""
    for edge, cursor_type in _CURSOR_MAP.items():
        assert isinstance(cursor_type, Gdk.CursorType)
        # Just check it's a valid enum member (not an int)
        assert type(cursor_type) is Gdk.CursorType


if __name__ == "__main__":
    test_cursor_map_has_all_edges()
    test_edge_constants()
    test_cursor_types_exist()
    print("All tests passed!")
