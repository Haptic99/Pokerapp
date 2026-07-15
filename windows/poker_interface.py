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

        # Spieler- oder Admin-Name (wird über den Begrüßungsbildschirm gesetzt)
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
        welcome_label = Gtk.Label(label="Willkommen! Bitte geben Sie Ihren Namen ein und nehmen Sie Platz.")
        self.welcome_box.pack_start(welcome_label, True, True, 0)

        # Eingabefeld für den Namen
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Name eingeben...")
        self.name_entry.connect("activate", self.on_name_entered)
        self.welcome_box.pack_start(self.name_entry, True, True, 0)

        # Button "Hier hinsetzen" – hier wird lediglich der Begrüßungsbildschirm entfernt
        start_button = Gtk.Button(label="Weiter")
        start_button.connect("clicked", self.on_start_button_clicked)
        self.welcome_box.pack_start(start_button, True, True, 0)

        # Begrüßungsbox zum Overlay hinzufügen
        self.overlay.add_overlay(self.welcome_box)

    def on_start_button_clicked(self, button):
        """
        Wird ausgeführt, wenn der Benutzer seinen Namen eingegeben hat.
        Der Name wird gespeichert, der Begrüßungsbildschirm entfernt und die Buttons wieder aktiviert.
        Das eigentliche „Hinsetzen“ erfolgt erst über den Toggle-Button.
        """
        name = self.name_entry.get_text().strip()
        if name:
            self.player_name = name
            print(f"Benutzername: {name}")
            self.welcome_box.destroy()
            self.enable_buttons()
            # Hier wird NICHT sofort eine Verbindung zum Server aufgebaut!
        else:
            print("Name darf nicht leer sein!")

    def on_name_entered(self, entry):
        """Speichert den Namen und entfernt den Begrüßungsbildschirm."""
        self.on_start_button_clicked(None)

    def run_async_loop(self):
        """Startet den asynchronen Event-Loop im Hintergrund."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

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

    def set_background_image(self, image_path):
        """Setzt ein Hintergrundbild."""
        full_path = os.path.join(os.path.dirname(__file__), "../images", image_path)
        if os.path.exists(full_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 800, 480, False)
            background = Gtk.Image.new_from_pixbuf(pixbuf)
            self.overlay.add(background)
            self.overlay.set_overlay_pass_through(background, True)

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

    def create_buttons(self):
        # Button: Chipwerte
        chipwerte_button = Gtk.Button(label="Chipwerte")
        chipwerte_button.set_size_request(100, 40)
        chipwerte_button.connect("clicked", self.button_chipwerte_click)
        chipwerte_button.get_style_context().add_class("button-custom")
        self.fixed.put(chipwerte_button, 15, 416)

        # Button: Poker Hands
        poker_hands_button = Gtk.Button(label="Poker Hands")
        poker_hands_button.set_size_request(100, 40)
        poker_hands_button.connect("clicked", self.button_poker_hands_click)
        poker_hands_button.get_style_context().add_class("button-custom")
        self.fixed.put(poker_hands_button, 150, 416)

        # Falls Admin: Button "Administration" – 40 Pixel weiter links (vorher 490, jetzt 450)
        if self.is_admin:
            self.administration_button = Gtk.Button(label="Administration")
            self.administration_button.set_size_request(100, 40)
            self.administration_button.connect("clicked", self.button_administration_click)
            self.administration_button.get_style_context().add_class("button-custom")
            self.fixed.put(self.administration_button, 450, 416)

        # Toggle-Button zum Hinsetzen bzw. Wegsetzen – 40 Pixel weiter links (vorher 650, jetzt 610)
        self.toggle_seat_button = Gtk.ToggleButton(label="Platz nehmen")
        self.toggle_seat_button.set_size_request(120, 40)
        self.toggle_seat_button.get_style_context().add_class("button-custom")
        self.toggle_seat_button.connect("toggled", self.on_toggle_seat)
        self.fixed.put(self.toggle_seat_button, 610, 416)

    def on_toggle_seat(self, button):
        """
        Wenn der Toggle-Button betätigt wird:
         - Bei Aktivierung: Bestätigungsdialog, und bei Zustimmung wird eine Join-Nachricht an den Server gesendet.
         - Bei Deaktivierung: Bestätigungsdialog und ggf. eine Leave-Nachricht an den Server.
        """
        if button.get_active():
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Hinsetzen bestätigen?"
            )
            dialog.format_secondary_text("Möchten Sie sich wirklich hinsetzen?")
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                button.set_label("Platz verlassen")
                print("Spieler nimmt Platz.")
                # Sende Join-Nachricht an den Server
                asyncio.run_coroutine_threadsafe(self.send_join_message(), self.loop)
            else:
                button.set_active(False)
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Wegsetzen bestätigen?"
            )
            dialog.format_secondary_text("Möchten Sie sich wirklich wegsetzen?")
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                button.set_label("Platz nehmen")
                print("Spieler setzt sich weg.")
                # Sende Leave-Nachricht an den Server
                asyncio.run_coroutine_threadsafe(self.send_leave_message(), self.loop)
            else:
                button.set_active(True)

    async def send_join_message(self):
        """Stellt die Verbindung zum Server her und sendet eine Join-Nachricht mit dem Spielernamen."""
        try:
            uri = "ws://localhost:8765"  # Passe ggf. die Adresse an
            async with websockets.connect(uri) as websocket:
                message = {"action": "join", "name": self.player_name}
                await websocket.send(json.dumps(message))
                print("Join-Nachricht gesendet.")
        except Exception as e:
            print(f"Fehler beim Senden der Join-Nachricht: {e}")

    async def send_leave_message(self):
        """Stellt die Verbindung zum Server her und sendet eine Leave-Nachricht mit dem Spielernamen."""
        try:
            uri = "ws://localhost:8765"  # Passe ggf. die Adresse an
            async with websockets.connect(uri) as websocket:
                message = {"action": "leave", "name": self.player_name}
                await websocket.send(json.dumps(message))
                print("Leave-Nachricht gesendet.")
        except Exception as e:
            print(f"Fehler beim Senden der Leave-Nachricht: {e}")

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
        if self.admin_window is None:
            self.admin_window = AdminWindow(self)
            self.admin_window.show_all()
            self.admin_window.connect("destroy", self.on_admin_window_closed)
        else:
            self.admin_window.present()

    def on_admin_window_closed(self, widget):
        """Setzt die Referenz zurück, wenn das Admin-Fenster geschlossen wird."""
        self.admin_window = None

    def create_table_left(self):
        """Erstellt eine Tabelle mit 2 Spalten und 4 Reihen auf der linken oberen Seite."""
        self.table_left = Gtk.Grid()

        # Aktuelle Blind-Werte oder Standardwerte
        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "n.V."
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "n.V."

        data = [
            ("Blinds", ""),
            ("Small Blind", small_blind_value),
            ("Big Blind", big_blind_value),
            ("Nächste Blinderhöhung", "00:00")
        ]

        self.left_labels = {}

        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)

            label1.set_size_request(185, 25)
            label2.set_size_request(70, 25)

            if row == 0:
                label1.set_xalign(0.5)
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")
                frame1.get_style_context().add_class("red-text")
                self.table_left.attach(frame1, 0, row, 2, 1)
            else:
                label1.set_xalign(0.0)
                label1.set_margin_left(6)
                label2.set_xalign(1.0)
                label2.set_margin_right(6)
                label1.get_style_context().add_class("green-text")
                label2.get_style_context().add_class("green-text")
                self.left_labels[col1] = label2
                print(f"🔧 Initialisiere Label: {col1}")
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")
                frame2 = Gtk.Frame()
                frame2.add(label2)
                frame2.get_style_context().add_class("table-cell")
                self.table_left.attach(frame1, 0, row, 1, 1)
                self.table_left.attach(frame2, 1, row, 1, 1)

        self.fixed.put(self.table_left, 15, 15)

    def create_table_right(self):
        """Erstellt eine Tabelle mit 2 Spalten und 2 Reihen auf der rechten oberen Seite."""
        table = Gtk.Grid()

        data = [
            ("Infos", ""),
            ("Spielzeit", "n.V."),
            ("Anzahl Runden", "n.V.")
        ]

        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)
            label1.set_size_request(185, 25)
            label2.set_size_request(70, 25)
            if row == 0:
                label1.set_xalign(0.5)
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")
                frame1.get_style_context().add_class("red-text")
                table.attach(frame1, 0, row, 2, 1)
            else:
                label1.set_xalign(0.0)
                label1.set_margin_left(6)
                label2.set_xalign(1.0)
                label2.set_margin_right(6)
                label1.get_style_context().add_class("green-text")
                label2.get_style_context().add_class("green-text")
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell")
                frame2 = Gtk.Frame()
                frame2.add(label2)
                frame2.get_style_context().add_class("table-cell")
                table.attach(frame1, 0, row, 1, 1)
                table.attach(frame2, 1, row, 1, 1)

        self.fixed.put(table, 515, 15)

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
        """Startet den Timer im Poker-Interface."""
        GLib.timeout_add_seconds(1, self.update_timer)

    def update_timer(self):
        """Aktualisiert die Timer-Anzeige in der linken Tabelle."""
        if TimerData.is_running:
            minute = int(TimerData.minute) if TimerData.minute is not None else 0
            second = int(TimerData.second) if TimerData.second is not None else 0
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{minute:02}:{second:02}")
        return True

    async def listen_for_updates(self):
        """Empfängt Daten vom Server und aktualisiert das Interface."""
        uri = "ws://192.168.1.65:8765"  # Passe die Adresse ggf. an
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
