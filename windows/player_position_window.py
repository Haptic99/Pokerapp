from gi.repository import Gtk, Gdk, GdkPixbuf
from utils.resources import get_image_path

import gi
gi.require_version('Gtk', '3.0')


class PlayerPositionWindow(Gtk.Window):
    def __init__(self, parent, players):
        super().__init__(title="Spielerplatzierung")
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        
        self.is_fullscreen_mode = False
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        # Signal zum Schließen des Fensters
        self.connect("destroy", self.on_close)

        # Hauptcontainer (VBox für Layout)
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_container.set_halign(Gtk.Align.CENTER)
        self.main_container.set_valign(Gtk.Align.CENTER)
        self.add(self.main_container)

        # Overlay für den Hintergrund und die Spielerplätze
        self.overlay = Gtk.Overlay()
        self.overlay.set_size_request(800, 480)
        self.main_container.pack_start(self.overlay, True, True, 0)

        # Hintergrundbild setzen
        self.background_image_path = get_image_path("background_start.jpg")
        self.set_background_image(self.background_image_path)

        # Pokertisch hinzufügen (grüne Matte)
        self.add_pokertisch()

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
        """Zeichnet den Pokertisch (grüne Matte) in fester Größe (800x480)."""
        pokertisch_image_path = get_image_path("pokertisch.png")

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(pokertisch_image_path, 800, 480, False)
        pokertisch_image = Gtk.Image.new_from_pixbuf(pixbuf)
        pokertisch_image.set_halign(Gtk.Align.CENTER)
        pokertisch_image.set_valign(Gtk.Align.CENTER)
        self.overlay.add_overlay(pokertisch_image)

    def initialize_player_positions(self):
        """Initialisiert alle Spielerpositionen mit Platz-Karten ('Badges'). 400, 240"""
        center_x, center_y = 387.1, 228
        self.positions = [
            (0, 160), (-250, 110), (-310, 0), (-250, -110),
            (0, -160), (250, -110), (310, 0), (250, 110)
        ]
        self.player_labels = []
        for i, (x, y) in enumerate(self.positions):
            adjusted_x = x + center_x
            adjusted_y = y + center_y
            
            # Hauptcontainer für die Platz-Karte
            badge_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            badge_box.get_style_context().add_class("seat-badge")
            badge_box.set_size_request(140, -1)
            
            # Ausrichtung auf dem Overlay
            badge_box.set_halign(Gtk.Align.START)
            badge_box.set_valign(Gtk.Align.START)
            # -70 zentriert horizontal (da max-width 140px ist)
            # -25 zentriert vertikal (halbe Höhe)
            badge_box.set_margin_top(adjusted_y - 25)
            badge_box.set_margin_left(adjusted_x - 70)
            
            # 1. Sitz-Nummer (z.B. "Sitz 1")
            lbl_seat = Gtk.Label(label=f"Sitz {i+1}")
            lbl_seat.get_style_context().add_class("seat-number")
            lbl_seat.set_xalign(0.5)
            badge_box.pack_start(lbl_seat, False, False, 0)
            
            # 2. Spieler-Name
            lbl_name = Gtk.Label(label="Nicht belegt")
            lbl_name.get_style_context().add_class("player-name")
            lbl_name.set_xalign(0.5)
            badge_box.pack_start(lbl_name, False, False, 0)
            
            # 3. Geräte-Status (Placeholder für später)
            lbl_status = Gtk.Label(label="Wartet...")
            lbl_status.get_style_context().add_class("seat-status")
            lbl_status.set_xalign(0.5)
            badge_box.pack_start(lbl_status, False, False, 0)
            
            self.overlay.add_overlay(badge_box)
            
            # Wir speichern die UI-Elemente, um sie später updaten zu können
            self.player_labels.append((badge_box, lbl_name, lbl_status))

    def update_player_positions(self, players):
        """Aktualisiert die Spielerplätze basierend auf der Spielerliste."""
        for i, (badge_box, lbl_name, lbl_status) in enumerate(self.player_labels):
            if i < len(players):
                name = players[i]
                # Damit ein langer Name das Layout nicht sprengt
                if len(name) > 13:
                    name = name[:11] + "..."
                lbl_name.set_text(name)
                lbl_status.set_text("Verbunden")
                
                # Active styling
                badge_box.get_style_context().add_class("seat-badge-active")
                lbl_status.get_style_context().add_class("seat-status-active")
            else:
                lbl_name.set_text("Nicht belegt")
                lbl_status.set_text("Wartet...")
                
                # Remove active styling
                badge_box.get_style_context().remove_class("seat-badge-active")
                lbl_status.get_style_context().remove_class("seat-status-active")

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
