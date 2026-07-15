import gi
import asyncio
import websockets
import json
import os
import threading

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
from utils.helpers import load_css, set_background_image
from utils.resources import get_image_path
from data.blind_data import BlindData
from data.timer_data import TimerData
from windows.admin_window import AdminWindow
from windows.poker_hands_window import PokerHandsWindow


class PokerInterface(Gtk.Window):
    def __init__(self, is_admin=False):
        super().__init__(title="Poker Interface")
        self.set_default_size(800, 480)
        self.is_admin = is_admin  # Admin-Status speichern

        # Event-Loop für asynchrone WebSocket-Kommunikation
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()

        # Spieler- oder Admin-Name
        self.player_name = None

        # Hauptcontainer für das Interface
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.main_box)

        # Overlay für den Begrüßungsbildschirm
        self.overlay = Gtk.Overlay()
        self.main_box.pack_start(self.overlay, True, True, 0)

        # Hintergrundbild setzen
        self.background_image_path = get_image_path("background_start.jpg")
        self.set_background_image(self.background_image_path)

        # Fixed-Container für Buttons
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Buttons erstellen
        self.create_buttons()

        # Begrüßungs-Bildschirm erstellen
        self.create_welcome_screen()

        # Admin-Fenster-Referenz initialisieren
        self.admin_window = None

        # Vollbildmodus-Status (wichtig für Admin-Fenster)
        self.is_fullscreen_mode = False
        
        # Key-Press-Event verbinden
        self.connect("key-press-event", self.on_key_press)

        # CSS laden
        self.load_css()

        # Tabellen erstellen
        self.create_table_left()
        self.create_table_right()

        # Timer starten
        self.start_timer()

    def create_welcome_screen(self):
        """Erstellt den Begrüßungsbildschirm mit Nameingabe."""
        # Alle Buttons deaktivieren
        self.disable_buttons()

        # Begrüßungsbox
        self.welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.welcome_box.set_halign(Gtk.Align.CENTER)
        self.welcome_box.set_valign(Gtk.Align.CENTER)
        self.welcome_box.set_name("welcome_box")  # Name für CSS

        # Begrüßungstext
        welcome_label = Gtk.Label(label="Willkommen! Möchten Sie hier Platz nehmen?")
        self.welcome_box.pack_start(welcome_label, True, True, 0)

        # Button "Hier hinsetzen"
        start_button = Gtk.Button(label="Hier hinsetzen")
        start_button.connect("clicked", self.on_start_button_clicked)
        self.welcome_box.pack_start(start_button, True, True, 0)

        # Eingabefeld für den Namen (zuerst versteckt)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Name eingeben...")
        self.name_entry.connect("activate", self.on_name_entered)
        self.name_entry.hide()
        self.welcome_box.pack_start(self.name_entry, True, True, 0)

        # Begrüßungsbox zum Overlay hinzufügen
        self.overlay.add_overlay(self.welcome_box)

    def on_start_button_clicked(self, button):
        """Speichert den Namen, schließt die Begrüßungsbox und sendet die Daten an den Server."""
        name = self.name_entry.get_text().strip()  # Namen aus dem Eingabefeld lesen
        if name:
            self.player_name = name
            print(f"Benutzername: {name}")  # Debug-Ausgabe
            self.welcome_box.destroy()  # Begrüßungsbox entfernen
            self.enable_buttons()  # Buttons aktivieren
            self.send_name_to_server()  # Namen an den Server senden
        else:
            print("Name darf nicht leer sein!")  # Debug-Ausgabe, wenn kein Name eingegeben wurde

    def send_name_to_server(self):
        """Sendet den Namen des Spielers an den Server."""
        asyncio.run_coroutine_threadsafe(self.connect_to_server(), self.loop)

    def on_name_entered(self, entry):
        """Speichert den Namen und entfernt den Begrüßungsbildschirm."""
        name = entry.get_text().strip()
        if name:
            self.player_name = name
            print(f"Benutzername: {name}")  # Debug-Ausgabe
            self.welcome_box.destroy()  # Begrüßungsbox entfernen
            self.enable_buttons()  # Buttons wieder aktivieren
            self.initialize_interface()

    def initialize_interface(self):
        """Initialisiert die Poker-Oberfläche nach der Namensabfrage."""
        asyncio.run_coroutine_threadsafe(self.connect_to_server(), self.loop)

    async def connect_to_server(self):
        """Stellt die Verbindung zum Poker-Server her und sendet den Namen."""
        try:
            uri = "ws://localhost:8765"  # Beispiel-URL
            async with websockets.connect(uri) as websocket:
                # Name an den Server senden
                await websocket.send(json.dumps({"action": "join", "name": self.player_name}))
                print("Verbindung hergestellt und Name gesendet.")
        except Exception as e:
            print(f"Fehler beim Verbinden: {e}")


    def disable_buttons(self):
        """Setzt alle Buttons im Hintergrund in den inaktiven Zustand."""
        for child in self.fixed.get_children():
            if isinstance(child, Gtk.Button):
                child.set_sensitive(False)

    def enable_buttons(self):
        """Aktiviert alle Buttons im Hintergrund."""
        for child in self.fixed.get_children():
            if isinstance(child, Gtk.Button):
                child.set_sensitive(True)

    def set_background_image(self, image_path):
        """Setzt ein Hintergrundbild."""
        full_path = os.path.join(os.path.dirname(__file__), "../images", image_path)
        if os.path.exists(full_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 800, 480, False)
            background = Gtk.Image.new_from_pixbuf(pixbuf)
            self.overlay.add(background)
            self.overlay.set_overlay_pass_through(background, True)

    def load_css(self):
        """Lädt das CSS für die GUI."""
        css_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), "../styles/style.css")
        with open(css_path, "r") as css_file:
            css_data = css_file.read()
            css_provider.load_from_data(css_data.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def run_async_loop(self):
        """Startet den asynchronen Event-Loop im Hintergrund."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_timer(self):
        """Timer im Poker-Interface starten."""
        GLib.timeout_add_seconds(1, self.update_timer)  # Jede Sekunde aktualisieren

    def update_timer(self):
        """Aktualisiert die Timer-Anzeige in der linken Tabelle."""
        if TimerData.is_running:
            minute = int(TimerData.minute) if TimerData.minute is not None else 0
            second = int(TimerData.second) if TimerData.second is not None else 0
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{minute:02}:{second:02}")
        return True  # Timer weiterlaufen lassen









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

                # Debug-Ausgabe für Initialisierung
                print(f"🔧 Initialisiere Label: {col1}")

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
        """Setzt die Referenz zurück, wenn das Admin-Fenster geschlossen wird."""
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
        small_blind = data.get("small_blind") or "n.V."
        big_blind = data.get("big_blind") or "n.V."
        try:
            minute = int(data.get("minute") or 0)
            second = int(data.get("second") or 0)
        except Exception as e:
            print("Fehler bei der Umwandlung von minute/second:", e)
            minute, second = 0, 0

        status_text = "►" if data.get("is_running", False) else "‖"

        if hasattr(self, "left_labels"):
            if "Small Blind" in self.left_labels:
                self.left_labels["Small Blind"].set_text(small_blind)
            if "Big Blind" in self.left_labels:
                self.left_labels["Big Blind"].set_text(big_blind)
            if "Nächste Blinderhöhung" in self.left_labels:
                self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")
