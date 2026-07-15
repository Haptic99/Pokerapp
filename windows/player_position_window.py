import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
from utils.resources import get_image_path


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

                # Spielerplätze hinzufügen
                self.initialize_player_positions()

                # Spielerplätze mit Spielern aktualisieren
                self.update_player_positions(players)

                # Schließen-Button hinzufügen
                self.add_close_button()

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
                pokertisch_image_path = get_image_path("pokertisch.png")  # Grüne Matte

                # Fenstergröße abrufen
                window_width, window_height = self.get_size()
                
                # Dynamische Größe für den Tisch (100% der Breite und Höhe des Fensters)
                table_width = int(window_width * 1)
                table_height = int(window_height * 1)

                # Bild skalieren und hinzufügen
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(pokertisch_image_path, table_width, table_height, False)
                pokertisch_image = Gtk.Image.new_from_pixbuf(pixbuf)

                # Positionierung in der Mitte
                pokertisch_image.set_halign(Gtk.Align.CENTER)
                pokertisch_image.set_valign(Gtk.Align.CENTER)
                self.overlay.add_overlay(pokertisch_image)

        def initialize_player_positions(self):
                """Initialisiert alle Spielerpositionen mit 'Nicht belegt'."""
                # Fenster-Mitte berechnen
                center_x, center_y = 400, 240  # Beispiel: Fenstergröße 800x480

                # Hardcodierte Positionen relativ zur Mitte
                self.positions = [
                        (0, 140),  # Platz 1 (oben Mitte)
                        (-270, 125),  # Platz 2 (rechts oben)
                        (-340, 0),    # Platz 3 (rechts unten)
                        (-270, -115), # Platz 4 (unten Mitte)
                        (0, -130),    # Platz 5 (links unten)
                        (270, -115),  # Platz 6 (links oben)
                        (340, 0),     # Platz 7 (oben links)
                        (270, 125)    # Platz 8 (oben rechts)
                ]

                # Spielerplätze initialisieren
                self.player_labels = []  # Liste, um die Label-Widgets zu speichern
                for i, (x, y) in enumerate(self.positions):
                        # Positionen relativ zur Mitte berechnen
                        adjusted_x = x + center_x
                        adjusted_y = y + center_y

                        # Spielername (Label), standardmäßig "Nicht belegt"
                        player_label = Gtk.Label(label="Nicht belegt")
                        player_label.set_name("player-label")  # Name für CSS
                        player_label.get_style_context().add_class("player-name")
                        player_label.set_xalign(0)  # Horizontale Zentrierung
                        player_label.set_yalign(0)  # Vertikale Zentrierung

                        # Position setzen
                        player_label.set_margin_top(adjusted_y - 15)  # Feinanpassung für vertikale Ausrichtung
                        player_label.set_margin_left(adjusted_x - 25)  # Feinanpassung für horizontale Ausrichtung

                        # Label hinzufügen
                        self.overlay.add_overlay(player_label)
                        self.player_labels.append(player_label)  # Label speichern

        def update_player_positions(self, players):
                """Aktualisiert die Spielerplätze basierend auf der Spielerliste."""
                for i, player_label in enumerate(self.player_labels):
                        if i < len(players):
                                # Spielername anzeigen
                                player_label.set_text(players[i])
                        else:
                                # Platz ist leer
                                player_label.set_text("Nicht belegt")

        def add_close_button(self):
                """Fügt einen Schließen-Button hinzu."""
                close_button = Gtk.Button(label="Schließen")
                close_button.set_size_request(100, 40)
                # Button horizontal zentrieren, sodass er seine feste Breite behält
                close_button.set_halign(Gtk.Align.CENTER)
                close_button.get_style_context().add_class("button-custom")
                close_button.connect("clicked", self.on_close_button_clicked)

                # Schließen-Button unten im Hauptcontainer hinzufügen
                self.main_container.pack_end(close_button, False, False, 10)

        def on_close_button_clicked(self, widget):
                """Schließt das Fenster."""
                print("Schließen-Button gedrückt")
                self.destroy()
