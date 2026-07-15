import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
from utils.resources import get_image_path


class PlayerPositionWindow(Gtk.Window):
    def __init__(self, players):
        super().__init__(title="Spielerplatzierung")
        self.set_default_size(800, 480)

        # Hintergrundbild setzen
        self.background_image_path = get_image_path("background_start.jpg")
        self.background = Gtk.Image.new_from_file(self.background_image_path)
        self.add(self.background)

        # Overlay für Tisch und Spieler
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        # Pokertisch hinzufügen (grüne Matte)
        self.add_pokertisch()

        # Spielerplätze hinzufügen
        self.add_player_positions(players)

    def add_pokertisch(self):
        """Zeichnet den Pokertisch."""
        pokertisch_image_path = get_image_path("pokertisch.png")  # Grüne Matte
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(pokertisch_image_path, 600, 300, False)
        pokertisch_image = Gtk.Image.new_from_pixbuf(pixbuf)

        pokertisch_image.set_halign(Gtk.Align.CENTER)
        pokertisch_image.set_valign(Gtk.Align.CENTER)
        self.overlay.add_overlay(pokertisch_image)

    def add_player_positions(self, players):
        """Fügt die Spielerpositionen hinzu."""
        positions = [
            (400, 50),   # Platz 1 (oben Mitte)
            (600, 120),  # Platz 2 (rechts oben)
            (600, 300),  # Platz 3 (rechts unten)
            (400, 400),  # Platz 4 (unten Mitte)
            (200, 300),  # Platz 5 (links unten)
            (200, 120),  # Platz 6 (links oben)
            (300, 50),   # Platz 7 (oben links)
            (500, 50)    # Platz 8 (oben rechts)
        ]

        for i, (x, y) in enumerate(positions):
            if i < len(players):  # Nur so viele Plätze wie Spieler
                player_name = players[i]

                # Spielerplatz (Kreis)
                player_circle = Gtk.DrawingArea()
                player_circle.set_size_request(50, 50)
                player_circle.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0.5, 0, 1))

                # Spielernamen
                player_label = Gtk.Label(label=player_name)
                player_label.set_xalign(0.5)
                player_label.set_margin_top(5)

                # Overlay für Platz und Namen
                self.overlay.add_overlay(player_circle)
                self.overlay.add_overlay(player_label)

                player_circle.set_halign(Gtk.Align.CENTER)
                player_circle.set_valign(Gtk.Align.CENTER)
                player_label.set_halign(Gtk.Align.CENTER)
                player_label.set_valign(Gtk.Align.CENTER)
