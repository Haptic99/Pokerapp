from gi.repository import Gtk, Gdk, GdkPixbuf
from utils.resources import get_style_path
import os
import gi
gi.require_version('Gtk', '3.0')


def load_css():
    css_provider = Gtk.CssProvider()
    css_file = get_style_path("style.css")
    if os.path.exists(css_file):
        css_provider.load_from_path(css_file)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    else:
        print(f"CSS-Datei nicht gefunden: {css_file}")


def set_background_image(widget, image_path):
    if os.path.exists(image_path):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            image_path, 800, 480, False
        )
        background_image = Gtk.Image.new_from_pixbuf(pixbuf)
        widget.add(background_image)
    else:
        print(f"Hintergrundbild nicht gefunden: {image_path}")


def set_background_image_in_overlay(overlay, image_path):
    """Setzt das Hintergrundbild im Overlay."""
    if os.path.exists(image_path):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            image_path, 800, 480, False
        )
        background_image = Gtk.Image.new_from_pixbuf(pixbuf)
        overlay.add(background_image)
    else:
        print(f"Hintergrundbild nicht gefunden: {image_path}")


def format_timer_with_status(minute, second, is_running):
    """Formatiert Timer-Werte mit Statussymbol (‖ für Pause) oder gibt '-' zurück, wenn beide Werte 0 sind."""
    if int(minute) == 0 and int(second) == 0:
        return "-"
    status_text = "" if is_running else "‖"
    return f"{status_text} {int(minute):02}:{int(second):02}"
