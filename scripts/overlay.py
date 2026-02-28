#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pycairo",
#   "PyGObject",
# ]
# ///
"""
Wayland overlay: draw a colored rectangle with text that auto-dismisses.

Requires system packages: GTK3, GtkLayerShell (libgtk-layer-shell).
Usage:
    uv run scripts/overlay.py                        # demo with defaults
    uv run scripts/overlay.py 100 200 300 60 "hello" --color green --timeout 3
"""

import argparse
import cairo
import gi

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')

from gi.repository import Gdk, GLib, Gtk, GtkLayerShell


# ---------------------------------------------------------------------------
# Low-level: layer-shell surface management
# ---------------------------------------------------------------------------

def _get_monitor(monitor_idx=None):
    """Return a GdkMonitor. If monitor_idx is None, use the last monitor."""
    display = Gdk.Display.get_default()
    n = display.get_n_monitors()
    if n == 0:
        return None
    idx = monitor_idx if monitor_idx is not None else n - 1
    return display.get_monitor(min(idx, n - 1))


def create_layer_surface(width, height, x, y, monitor_idx=None):
    """Create an overlay-layer Wayland surface positioned at (x, y)."""
    window = Gtk.Window()

    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual:
        window.set_visual(visual)
    window.set_app_paintable(True)

    GtkLayerShell.init_for_window(window)
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
    GtkLayerShell.set_namespace(window, 'overlay-debug')
    GtkLayerShell.set_exclusive_zone(window, -1)

    monitor = _get_monitor(monitor_idx)
    if monitor:
        GtkLayerShell.set_monitor(window, monitor)

    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.LEFT, True)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.TOP, y)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.LEFT, x)

    GtkLayerShell.set_keyboard_mode(
        window, GtkLayerShell.KeyboardMode.NONE,
    )

    window.set_default_size(width, height)

    return window


# ---------------------------------------------------------------------------
# Low-level: Cairo drawing helpers
# ---------------------------------------------------------------------------

COLORS = {
    'red': (1.0, 0.2, 0.2),
    'green': (0.2, 0.8, 0.3),
    'blue': (0.2, 0.4, 1.0),
    'yellow': (1.0, 0.85, 0.1),
    'orange': (1.0, 0.55, 0.1),
    'cyan': (0.1, 0.85, 0.85),
    'magenta': (0.85, 0.2, 0.85),
    'white': (1.0, 1.0, 1.0),
}


def parse_color(name_or_hex):
    if name_or_hex in COLORS:
        return COLORS[name_or_hex]
    h = name_or_hex.lstrip('#')
    if len(h) == 6:
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    raise ValueError(f'Unknown color: {name_or_hex}')


def draw_rect_with_text(cr, width, height, text, color_rgb):
    """Draw a semi-transparent box with a 2px border and centered text."""
    r, g, b = color_rgb

    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_rgba(0, 0, 0, 0)
    cr.paint()

    cr.set_operator(cairo.OPERATOR_OVER)

    # filled background
    cr.set_source_rgba(r, g, b, 0.15)
    cr.rectangle(0, 0, width, height)
    cr.fill()

    # border
    lw = 2
    cr.set_source_rgba(r, g, b, 0.9)
    cr.set_line_width(lw)
    cr.rectangle(lw / 2, lw / 2, width - lw, height - lw)
    cr.stroke()

    # text
    if text:
        cr.set_source_rgba(r, g, b, 1.0)
        font_size = min(height * 0.5, 20)
        cr.select_font_face('monospace', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(font_size)
        extents = cr.text_extents(text)
        tx = (width - extents.width) / 2 - extents.x_bearing
        ty = (height - extents.height) / 2 - extents.y_bearing
        cr.move_to(tx, ty)
        cr.show_text(text)


# ---------------------------------------------------------------------------
# High-level: public API
# ---------------------------------------------------------------------------

def draw_overlay(x, y, width, height, text, color='red', timeout=2, monitor=None):
    """
    Show a rectangle overlay with text at screen position (x, y).

    The overlay appears on the OVERLAY layer (above all windows) and
    auto-dismisses after *timeout* seconds.

    Parameters
    ----------
    x, y          : int        -- top-left corner in screen pixels
    width, height : int        -- size of the rectangle
    text          : str        -- label drawn centered inside the rectangle
    color         : str        -- color name ('red', 'green', ...) or '#rrggbb' hex
    timeout       : float      -- seconds before the overlay disappears
    monitor       : int | None -- monitor index (None = last monitor)
    """
    color_rgb = parse_color(color)

    window = create_layer_surface(width, height, x, y, monitor_idx=monitor)

    drawing_area = Gtk.DrawingArea()
    drawing_area.set_size_request(width, height)

    def on_draw(_widget, cr):
        alloc = _widget.get_allocation()
        draw_rect_with_text(cr, alloc.width, alloc.height, text, color_rgb)
        return True

    drawing_area.connect('draw', on_draw)
    window.add(drawing_area)

    window.connect('destroy', Gtk.main_quit)
    GLib.timeout_add(int(timeout * 1000), window.destroy)

    window.show_all()
    Gtk.main()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Draw an overlay rectangle on screen')
    parser.add_argument('x', nargs='?', type=int, default=100)
    parser.add_argument('y', nargs='?', type=int, default=100)
    parser.add_argument('width', nargs='?', type=int, default=320)
    parser.add_argument('height', nargs='?', type=int, default=60)
    parser.add_argument('text', nargs='?', default='overlay test')
    parser.add_argument('--color', default='red')
    parser.add_argument('--timeout', type=float, default=2.0)
    parser.add_argument('--monitor', type=int, default=None,
                        help='Monitor index (default: last monitor)')
    args = parser.parse_args()

    draw_overlay(args.x, args.y, args.width, args.height,
                 args.text, args.color, args.timeout, args.monitor)


if __name__ == '__main__':
    main()
