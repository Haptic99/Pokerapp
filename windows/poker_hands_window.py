# windows/poker_hands_window.py

import gi
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
from utils.helpers import set_background_image_in_overlay
from utils.resources import get_image_path

class PokerHandsWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="Poker Hands")
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)

        overlay = Gtk.Overlay()
        self.add(overlay)

        # Set background image
        set_background_image_in_overlay(overlay, get_image_path("background_start.jpg"))

        # Add Poker Hands image
        poker_hands_image_path = get_image_path("poker_hands.jpeg")
        if os.path.exists(poker_hands_image_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(poker_hands_image_path, 700, 400, False)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            overlay.add_overlay(image)
            image.set_halign(Gtk.Align.CENTER)
            image.set_valign(Gtk.Align.CENTER)

        # Close button
        close_button = Gtk.Button(label="Schliessen")
        close_button.set_size_request(80, 40)
        close_button.connect("clicked", lambda w: self.close())
        close_button.get_style_context().add_class("button-custom")

        fixed = Gtk.Fixed()
        overlay.add_overlay(fixed)
        fixed.put(close_button, 658, 416)

        self.connect("key-press-event", self.on_key_press)
    
    def on_key_press(self, widget, event):
        """Keybindings für Escape und F11 im Poker Hands Fenster."""
        if event.keyval == Gtk.KEY_Escape:
            self.unfullscreen()
        elif event.keyval == Gtk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        """Schaltet zwischen Vollbild und Fenstergröße um."""
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True
