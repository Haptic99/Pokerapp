from gi.repository import Gtk, Gdk, GdkPixbuf
from utils.resources import get_image_path
from data.blind_data import BlindData
from windows.admin_window import AdminWindow
from windows.poker_hands_window import PokerHandsWindow
from windows.chip_value_window import ChipValueWindow  # Import des normalen ChipValueWindow

import asyncio
import websockets
import json
import os
import threading
import gi
gi.require_version('Gtk', '3.0')


class PokerInterface(Gtk.Window):
    def __init__(self, is_admin=False):
        super().__init__(title="Poker Interface")
        self.set_default_size(800, 480)
        self.is_admin = is_admin  # Admin-Status speichern

        # Event-Loop für asynchrone WebSocket-Kommunikation
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()

        # Spielername (wird über den Namenseingabe-Bildschirm gesetzt)
        self.player_name = None

        # Hauptcontainer für das Interface
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.main_box)

        # Overlay für den Namenseingabe-Bildschirm und weitere Widgets
        self.overlay = Gtk.Overlay()
        self.main_box.pack_start(self.overlay, True, True, 0)

        # Hintergrundbild setzen
        self.background_image_path = get_image_path("background_start.jpg")
        self.set_background_image(self.background_image_path)

        # Fixed-Container für Buttons und Tabellen
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Buttons erstellen
        self.create_buttons()

        # Namenseingabe-Bildschirm erstellen (wird eingeblendet, solange kein Name vorhanden ist)
        self.create_welcome_screen()

        # Admin-Fenster-Referenz initialisieren
        self.admin_window = None

        # Vollbildmodus-Status (wichtig für Admin-Fenster)
        self.is_fullscreen_mode = True
        self.fullscreen()

        # Key-Press-Event verbinden
        self.connect("key-press-event", self.on_key_press)

        # CSS laden
        self.load_css()

        # Tabellen erstellen
        self.create_table_left()
        self.create_table_right()

    def create_welcome_screen(self):
        """Erstellt bzw. zeigt den Namenseingabe-Bildschirm.
        Dabei werden alle anderen Buttons deaktiviert, sodass nur die Namenseingabe möglich ist."""
        # Zuerst alle Buttons deaktivieren
        self.disable_buttons()

        # Falls bereits ein Bildschirm existiert, zerstören wir ihn
        if hasattr(self, "welcome_box") and self.welcome_box:
            self.welcome_box.destroy()

        self.welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.welcome_box.set_halign(Gtk.Align.CENTER)
        self.welcome_box.set_valign(Gtk.Align.CENTER)
        self.welcome_box.set_name("welcome_box")  # Für CSS

        # Begrüßungstext
        welcome_label = Gtk.Label(label="Willkommen! Bitte geben Sie Ihren Namen ein und klicken Sie auf Weiter.")
        self.welcome_box.pack_start(welcome_label, True, True, 0)

        # Eingabefeld für den Namen
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Name eingeben...")
        self.name_entry.connect("activate", self.on_name_entered)
        self.welcome_box.pack_start(self.name_entry, True, True, 0)

        # Button "Weiter" – speichert den Namen und entfernt den Bildschirm
        weiter_button = Gtk.Button(label="Weiter")
        weiter_button.connect("clicked", self.on_start_button_clicked)
        self.welcome_box.pack_start(weiter_button, True, True, 0)

        self.overlay.add_overlay(self.welcome_box)
        self.welcome_box.show_all()  # WICHTIG: Widget sichtbar machen

    def on_start_button_clicked(self, button):
        """Wird ausgeführt, wenn der Benutzer seinen Namen eingegeben hat."""
        name = self.name_entry.get_text().strip()
        if not name:
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Fehler: Kein Name eingegeben!"
            )
            error_dialog.format_secondary_text("Bitte geben Sie einen Namen ein und klicken Sie auf Weiter.")
            error_dialog.run()
            error_dialog.destroy()
            return

        self.player_name = name
        # Entferne den Namenseingabe-Bildschirm
        self.welcome_box.destroy()
        # In der Info-Tabelle wird nur der Name (in Fett und in Grau) angezeigt
        self.player_name_label.set_markup(f"<span foreground='#808080'><b>{name}</b></span>")
        # Sende den Join-Request an den Server
        asyncio.run_coroutine_threadsafe(self.ws_client.send_join_message(name), self.ws_client.loop)
        # Aktiviere alle Buttons (nun kann der Spieler interagieren)
        self.enable_buttons()

    def on_name_entered(self, _):
        """Bei Enter wird die gleiche Logik wie beim Klick auf 'Weiter' ausgeführt."""
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
            background_image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.overlay.add(background_image)
            self.overlay.set_overlay_pass_through(background_image, True)

    def disable_buttons(self):
        """Deaktiviert alle Buttons im Fixed-Container."""
        for child in self.fixed.get_children():
            if isinstance(child, Gtk.Button):
                child.set_sensitive(False)

    def enable_buttons(self):
        """Aktiviert alle Buttons im Fixed-Container."""
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

        # Falls Admin: Button "Administration"
        if self.is_admin:
            self.administration_button = Gtk.Button(label="Administration")
            self.administration_button.set_size_request(100, 40)
            self.administration_button.connect("clicked", self.button_administration_click)
            self.administration_button.get_style_context().add_class("button-custom")
            self.fixed.put(self.administration_button, 450, 416)

        # Button "Platz verlassen" – immer mit diesem Label
        self.leave_button = Gtk.Button(label="Platz verlassen")
        self.leave_button.set_size_request(120, 40)
        self.leave_button.get_style_context().add_class("button-custom")
        self.leave_button.connect("clicked", self.on_leave_button_clicked)
        # Dieser Button ist erst aktiv, wenn ein Name eingegeben wurde
        self.leave_button.set_sensitive(False)
        self.fixed.put(self.leave_button, 610, 416)

    def on_leave_button_clicked(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Platz verlassen bestätigen?"
        )
        dialog.format_secondary_text("Möchten Sie wirklich Ihren Platz verlassen?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            print("Platz wird verlassen.")
            # Speichere den aktuellen Namen in einer lokalen Variable
            name_to_leave = self.player_name
            # Sende den Leave-Request mit dem korrekten Namen an den Server
            asyncio.run_coroutine_threadsafe(self.ws_client.send_leave_message(name_to_leave), self.ws_client.loop)
            # Entferne den Namen aus der Info-Tabelle und lösche den gespeicherten Namen
            self.player_name_label.set_text("")
            self.player_name = None
            # Deaktiviere alle Buttons, sodass der Benutzer nur noch den Namenseingabe-Bildschirm verwenden kann
            self.disable_buttons()
            # Blende den Namenseingabe-Bildschirm erneut ein
            self.create_welcome_screen()
        else:
            # Falls abgebrochen, passiert nichts
            pass

    async def send_join_message(self):
        """Sendet eine Join-Nachricht mit dem Namen an den Server."""
        try:
            uri = "ws://localhost:8765"  # ggf. anpassen
            async with websockets.connect(uri) as websocket:
                message = {"action": "join", "name": self.player_name}
                await websocket.send(json.dumps(message))
                print("Join-Nachricht gesendet.")
        except Exception as e:
            print(f"Fehler beim Senden der Join-Nachricht: {e}")

    async def send_leave_message(self, name):
        """Sendet eine Leave-Nachricht mit dem übergebenen Namen an den Server."""
        try:
            uri = "ws://localhost:8765"  # ggf. anpassen
            async with websockets.connect(uri) as websocket:
                message = {"action": "leave", "name": name}
                await websocket.send(json.dumps(message))
                print("Leave-Nachricht gesendet.")
        except Exception as e:
            print(f"Fehler beim Senden der Leave-Nachricht: {e}")

    def button_chipwerte_click(self, widget):
        """Öffnet das Fenster für die Chipwerte (nur Anzeige, keine Bearbeitung)."""
        # Hier wurde die Methode geändert, um für alle Benutzer das gleiche Fenster zu öffnen (is_admin=False)
        chip_window = ChipValueWindow(self, is_admin=False)
        if self.is_fullscreen_mode:
            chip_window.fullscreen()
        chip_window.show_all()

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
        """Erstellt die linke Tabelle (z. B. Blinds und Timer)."""
        self.table_left = Gtk.Grid()
        self.table_left.get_style_context().add_class("glass-panel")

        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "-"
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "-"

        data = [
            ("Blinds", ""),
            ("Small Blind", small_blind_value),
            ("Big Blind", big_blind_value),
            ("Nächste Blinderhöhung", "-")
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
                frame1.get_style_context().add_class("table-cell-transparent")
                frame1.get_style_context().add_class("primary-text")
                self.table_left.attach(frame1, 0, row, 2, 1)
            else:
                label1.set_xalign(0.0)
                label1.set_margin_left(6)
                label2.set_xalign(1.0)
                label2.set_margin_right(6)
                label1.get_style_context().add_class("accent-text")
                label2.get_style_context().add_class("accent-text")
                self.left_labels[col1] = label2
                frame1 = Gtk.Frame()
                frame1.add(label1)
                frame1.get_style_context().add_class("table-cell-transparent")
                frame2 = Gtk.Frame()
                frame2.add(label2)
                frame2.get_style_context().add_class("table-cell-transparent")
                self.table_left.attach(frame1, 0, row, 1, 1)
                self.table_left.attach(frame2, 1, row, 1, 1)

        self.fixed.put(self.table_left, 15, 15)

    def create_table_right(self):
        table = Gtk.Grid()
        table.get_style_context().add_class("glass-panel")

        # Überschrift "Infos" über beide Spalten
        header_label = Gtk.Label(label="Infos")
        header_label.set_xalign(0.5)
        header_frame = Gtk.Frame()
        header_frame.add(header_label)
        header_frame.get_style_context().add_class("table-cell-transparent")
        header_frame.get_style_context().add_class("primary-text")
        table.attach(header_frame, 0, 0, 2, 1)

        # Zeile für den Spielernamen
        self.player_name_label = Gtk.Label(label="")
        self.player_name_label.set_xalign(0.5)
        name_frame = Gtk.Frame()
        name_frame.add(self.player_name_label)
        name_frame.get_style_context().add_class("table-cell-transparent")
        table.attach(name_frame, 0, 1, 2, 1)

        # Weitere Infos: Hier fügen wir "Spielzeit" hinzu
        data = [
            ("Spielzeit", "-"),
            ("Anzahl Runden", "-")
        ]
        self.info_labels = {}
        start_row = 2
        for i, (title, value) in enumerate(data):
            row = start_row + i
            label_title = Gtk.Label(label=title)
            label_time = Gtk.Label(label=value)
            label_title.set_size_request(185, 25)
            label_time.set_size_request(70, 25)
            label_title.set_xalign(0.0)
            label_title.set_margin_left(6)
            label_time.set_xalign(1.0)
            label_time.set_margin_right(6)
            label_title.get_style_context().add_class("accent-text")
            label_time.get_style_context().add_class("accent-text")
            self.info_labels[title] = label_time  # Speichern in einem Dictionary
            frame_title = Gtk.Frame()
            frame_title.add(label_title)
            frame_title.get_style_context().add_class("table-cell-transparent")
            frame_time = Gtk.Frame()
            frame_time.add(label_time)
            frame_time.get_style_context().add_class("table-cell-transparent")
            table.attach(frame_title, 0, row, 1, 1)
            table.attach(frame_time, 1, row, 1, 1)

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
