from gi.repository import Gtk, Gdk, GdkPixbuf
from utils.resources import get_image_path

import gi
gi.require_version('Gtk', '3.0')


class PlayerPositionWindow(Gtk.Window):
    def __init__(self, players):
        super().__init__(title="Spielerplatzierung")
        self.set_default_size(800, 480)

        # Signal zum Schließen des Fensters
        self.connect("destroy", self.on_close)

        # Hauptcontainer (VBox für Layout)
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.main_container)

        # Overlay für den Hintergrund und die Spielerplätze
        self.overlay = Gtk.Overlay()
        self.main_container.pack_start(self.overlay, True, True, 0)

        # Hintergrundbild setzen
        self.background_image_path = get_image_path("background_start.jpg")
        self.set_background_image(self.background_image_path)

        # Pokertisch hinzufügen (grüne Matte)
        self.add_pokertisch()

        # Variable zum Speichern des Vollbildstatus
        self.is_fullscreen_mode = False

        # Key-Press-Event verbinden
        self.connect("key-press-event", self.on_key_press)

        # Spielerplätze hinzufügen
        self.initialize_player_positions()

        # Spielerplätze mit Spielern aktualisieren
        self.update_player_positions(players)

        # Schließen-Button hinzufügen
        self.add_close_button()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def on_close(self, widget):
        """Behandelt das Schließen des Fensters."""
        print("Spielerplatzierungsfenster wurde geschlossen.")

    def set_background_image(self, image_path):
        """Setzt das Hintergrundbild."""
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, 800, 480, False)
        background_image = Gtk.Image.new_from_pixbuf(pixbuf)
        self.overlay.add_overlay(background_image)

    def add_pokertisch(self):
        """Zeichnet den Pokertisch (grüne Matte) mit dynamischer Größe."""
        pokertisch_image_path = get_image_path("pokertisch.png")

        window_width, window_height = self.get_size()
        table_width = int(window_width)
        table_height = int(window_height)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(pokertisch_image_path, table_width, table_height, False)
        pokertisch_image = Gtk.Image.new_from_pixbuf(pixbuf)
        pokertisch_image.set_halign(Gtk.Align.CENTER)
        pokertisch_image.set_valign(Gtk.Align.CENTER)
        self.overlay.add_overlay(pokertisch_image)

    def initialize_player_positions(self):
        """Initialisiert alle Spielerpositionen mit 'Nicht belegt'."""
        center_x, center_y = 400, 240
        self.positions = [
            (0, 140), (-270, 125), (-340, 0), (-270, -115),
            (0, -130), (270, -115), (340, 0), (270, 125)
        ]
        self.player_labels = []
        for x, y in self.positions:
            adjusted_x = x + center_x
            adjusted_y = y + center_y
            player_label = Gtk.Label(label="Nicht belegt")
            player_label.set_name("player-label")
            player_label.get_style_context().add_class("player-name")
            player_label.set_xalign(0)
            player_label.set_yalign(0)
            player_label.set_margin_top(adjusted_y - 15)
            player_label.set_margin_left(adjusted_x - 25)
            self.overlay.add_overlay(player_label)
            self.player_labels.append(player_label)

    def update_player_positions(self, players):
        """Aktualisiert die Spielerplätze basierend auf der Spielerliste."""
        for i, player_label in enumerate(self.player_labels):
            player_label.set_text(players[i] if i < len(players) else "Nicht belegt")

    def add_close_button(self):
        """Fügt einen Schließen-Button hinzu."""
        close_button = Gtk.Button(label="Schließen")
        close_button.set_size_request(100, 40)
        close_button.get_style_context().add_class("button-custom")
        close_button.connect("clicked", self.on_close_button_clicked)
        if not hasattr(self, "fixed"):
            self.fixed = Gtk.Fixed()
            self.overlay.add_overlay(self.fixed)
        self.fixed.put(close_button, 658, 416)

    def on_close_button_clicked(self, widget):
        """Schließt das Fenster."""
        print("Schließen-Button gedrückt")
        self.destroy()
