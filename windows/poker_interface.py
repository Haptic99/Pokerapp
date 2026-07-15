import gi
import asyncio
import websockets
import json
import os

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
from utils.helpers import load_css, set_background_image
from utils.resources import get_image_path
from data.blind_data import BlindData
from data.timer_data import TimerData

class PokerInterface(Gtk.Window):
    def __init__(self, is_admin=False):
        super().__init__(title="Poker Interface")
        self.set_default_size(800, 480)
        self.is_admin = is_admin  # Admin-Status speichern

        # CSS laden
        load_css()

        # Overlay erstellen
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        # Hintergrundbild setzen
        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        # Erstellen eines Gtk.Fixed-Containers, um die Buttons manuell zu positionieren
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Buttons erstellen
        self.create_buttons()

        # Tabellen erstellen
        self.create_table_left()
        self.create_table_right()

        # Timer starten
        self.start_timer()

        # Starte WebSocket-Client, wenn kein Admin
        if not self.is_admin:
            GLib.idle_add(asyncio.create_task, self.listen_for_updates())

    def pause_timer(self):
        """Pausiert den Timer und aktualisiert alle Bildschirme."""
        TimerData.is_running = False
        TimerData.is_paused = True  # Speichert, dass der Timer pausiert wurde
        self.update_all_timer_displays()  # Poker-Interface aktualisieren

        # Falls das Admin-Window existiert, ebenfalls aktualisieren
        if self.admin_window:
            self.admin_window.update_all_timer_displays()

    def update_all_timer_displays(self):
        """Aktualisiert den Timer-Status auf allen Bildschirmen."""
        minute = int(TimerData.minute) if TimerData.minute is not None else 0
        second = int(TimerData.second) if TimerData.second is not None else 0
        status_text = "►" if TimerData.is_running else "‖"

        # Timer im Poker-Interface aktualisieren
        if hasattr(self, "left_labels") and "Nächste Blinderhöhung" in self.left_labels:
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")

    def refresh_blinds(self):
        small_blind = BlindData.small_blind if BlindData.small_blind else "n.V."
        big_blind = BlindData.big_blind if BlindData.big_blind else "n.V."
        self.update_blinds_in_table(small_blind, big_blind)

    def add_dealerchip_to_overlay(self, image_path, width, height):
        """Fügt den Dealerchip über dem Hintergrund in der Mitte hinzu."""
        if os.path.exists(image_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, width, height, False)
            dealerchip_image = Gtk.Image.new_from_pixbuf(pixbuf)

            # Den Dealerchip in der Mitte des Fensters platzieren
            self.overlay.add_overlay(dealerchip_image)
            self.overlay.set_overlay_pass_through(dealerchip_image, False)

            # Den Dealerchip mittig positionieren
            dealerchip_image.set_halign(Gtk.Align.CENTER)
            dealerchip_image.set_valign(Gtk.Align.CENTER)
        else:
            print(f"Dealerchip-Bild nicht gefunden: {image_path}")

    def create_buttons(self):
        """Erstellt und positioniert die Hauptbuttons."""
        chipwerte_button = Gtk.Button(label="Chipwerte")
        chipwerte_button.set_size_request(100, 40)
        chipwerte_button.connect("clicked", self.button_chipwerte_click)
        chipwerte_button.get_style_context().add_class("button-custom")
        self.fixed.put(chipwerte_button, 15, 416)

        poker_hands_button = Gtk.Button(label="Poker Hands")
        poker_hands_button.set_size_request(100, 40)
        poker_hands_button.connect("clicked", self.button_poker_hands_click)
        poker_hands_button.get_style_context().add_class("button-custom")
        self.fixed.put(poker_hands_button, 150, 416)

        # Admin-Button nur für Admins anzeigen
        if self.is_admin:
            self.administration_button = Gtk.Button(label="Administration")
            self.administration_button.set_size_request(100, 40)
            self.administration_button.connect("clicked", self.button_administration_click)
            self.administration_button.get_style_context().add_class("button-custom")
            self.fixed.put(self.administration_button, 632, 416)

    def create_table_left(self):
        """Erstellt eine Tabelle mit 2 Spalten und 4 Reihen auf der linken oberen Seite."""
        self.table_left = Gtk.Grid()

        # Aktuelle Blind-Werte abrufen oder 'n.V.' setzen, wenn None
        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "n.V."
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "n.V."

        # Beispiel-Daten für die Tabelle
        data = [
            ("Blinds", ""),  # Diese Zeile wird eine zusammengeführte Zelle sein
            ("Small Blind", small_blind_value),
            ("Big Blind", big_blind_value),
            ("Nächste Blinderhöhung", "00:00")  # Initialer Wert für den Timer
        ]

        self.left_labels = {}  # Speichert die Label-Widgets für späteres Update

        # Füge die Daten in die Tabelle ein
        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)

            # Größe der Spalten festlegen
            label1.set_size_request(185, 25)
            label2.set_size_request(70, 25)

            # Erste Zeile (zusammengeführte Zelle)
            if row == 0:
                label1.set_xalign(0.5)  # Mittig ausrichten
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")
                frame1.get_style_context().add_class("red-text")

                # Verbinde die beiden Spalten
                self.table_left.attach(frame1, 0, row, 2, 1)
            else:
                # Normale Zeilen (2 Spalten)
                label1.set_xalign(0.0)  # Linksbündig
                label1.set_margin_left(6)  # Fügt 6px am linken Rand hinzu
                label2.set_xalign(1.0)  # Rechtsbündig
                label2.set_margin_right(6)  # Fügt 6px am rechten Rand hinzu

                # CSS-Klassen zu den Labels hinzufügen
                label1.get_style_context().add_class("green-text")
                label2.get_style_context().add_class("green-text")

                # Labels speichern
                self.left_labels[col1] = label2

                # Labels zur Tabelle hinzufügen und CSS-Klasse für Rahmen anwenden
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")

                frame2 = Gtk.Frame()
                frame2.add(label2)
                frame2.get_style_context().add_class("table-cell")

                self.table_left.attach(frame1, 0, row, 1, 1)
                self.table_left.attach(frame2, 1, row, 1, 1)

        # Tabelle links oben positionieren
        self.fixed.put(self.table_left, 15, 15)

    def create_table_right(self):
        """Erstellt eine Tabelle mit 2 Spalten und 2 Reihen auf der rechten oberen Seite."""
        table = Gtk.Grid()

        # Beispiel-Daten für die Tabelle
        data = [
            ("Infos", ""),
            ("Spielzeit", "n.V."),
            ("Anzahl Runden", "n.V.")
        ]

        # Füge die Daten in die Tabelle ein
        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)

            # Größe der Spalten festlegen
            label1.set_size_request(185, 25)
            label2.set_size_request(70, 25)

            # Erste Zeile (zusammengeführte Zelle)
            if row == 0:
                label1.set_xalign(0.5)  # Mittig ausrichten
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")
                frame1.get_style_context().add_class("red-text")

                # Verbinde die beiden Spalten
                table.attach(frame1, 0, row, 2, 1)
            else:
                # Normale Zeilen (2 Spalten)
                label1.set_xalign(0.0)  # Linksbündig
                label1.set_margin_left(6)  # Fügt 6px am linken Rand hinzu
                label2.set_xalign(1.0)  # Rechtsbündig
                label2.set_margin_right(6)  # Fügt 6px am rechten Rand hinzu

                # CSS-Klassen zu den Labels hinzufügen
                label1.get_style_context().add_class("green-text")
                label2.get_style_context().add_class("green-text")

                # Labels zur Tabelle hinzufügen und CSS-Klasse für Rahmen anwenden
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")

                frame2 = Gtk.Frame()
                frame2.add(label2)
                frame2.get_style_context().add_class("table-cell")

                table.attach(frame1, 0, row, 1, 1)
                table.attach(frame2, 1, row, 1, 1)

        # Tabelle rechts oben positionieren
        self.fixed.put(table, 515, 15)

    def button_chipwerte_click(self, widget):
        print("Chipwerte-Button geklickt.")

    def button_poker_hands_click(self, widget):
        self.open_poker_hands_window()

    def button_administration_click(self, widget):
        self.open_admin_window()

    def open_poker_hands_window(self):
        """Öffnet das Poker Hands Fenster."""
        poker_window = PokerHandsWindow(self)
        if self.is_fullscreen_mode:
            poker_window.fullscreen()
        poker_window.show_all()

    def open_admin_window(self):
            
        """Öffnet das Admin-Fenster und speichert die Referenz."""
        if self.admin_window is None:  # Nur ein Admin-Window zulassen
            self.admin_window = AdminWindow(self)
            self.admin_window.show_all()
            self.admin_window.connect("destroy", self.on_admin_window_closed)
        else:
            self.admin_window.present()  # Bringt das Fenster nach vorne

    def on_admin_window_closed(self, widget):
        """Setzt die Referenz auf None, wenn das Admin-Fenster geschlossen wird."""
        self.admin_window = None

    def update_blinds_in_table(self, small_blind, big_blind):
        """Aktualisiert die Blinds in der linken Tabelle."""
        self.left_labels["Small Blind"].set_text(small_blind)
        self.left_labels["Big Blind"].set_text(big_blind)

    def on_key_press(self, widget, event):
        """Keybindings für Escape und F11."""
        if event.keyval == Gdk.KEY_Escape:
            self.unfullscreen()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        """Schaltet zwischen Vollbild und Fenstergröße 800x480 um."""
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.set_default_size(800, 480)
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True

    def start_timer(self):
        """Timer im Poker-Interface starten."""
        GLib.timeout_add_seconds(1, self.update_timer)  # Jede Sekunde aktualisieren

    def update_timer(self):
        """Aktualisiert die Timer-Anzeige in der linken Tabelle."""
        if TimerData.is_running:  # Überprüfen, ob der Timer läuft
                minute = int(TimerData.minute) if TimerData.minute is not None else 0
                second = int(TimerData.second) if TimerData.second is not None else 0
                self.left_labels["Nächste Blinderhöhung"].set_text(f"{minute:02}:{second:02}")
        return True  # Timer weiterlaufen lassen
        
        
    async def listen_for_updates(self):
        """Empfängt Daten vom Server und aktualisiert das Interface."""
        uri = "ws://192.168.1.65:8765"  # Server-IP hier eintragen
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({"command": "get_status"}))
                async for message in websocket:
                    data = json.loads(message)
                    self.update_display(data)
        except Exception as e:
            print(f"Verbindung zum Server fehlgeschlagen: {e}")
            
            
    def update_display(self, data):
        """Aktualisiert die Anzeige basierend auf den Server-Daten."""
        small_blind = data.get("small_blind", "n.V.")
        big_blind = data.get("big_blind", "n.V.")
        minute = data.get("minute", 0)
        second = data.get("second", 0)
        status_text = "►" if data.get("is_running", False) else "‖"

        if hasattr(self, "left_labels") and "Nächste Blinderhöhung" in self.left_labels:
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")
