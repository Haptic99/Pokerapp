from gi.repository import Gtk, Gdk, GdkPixbuf
from utils.resources import get_image_path
from data.blind_data import BlindData
from windows.admin_window import AdminWindow
from windows.poker_hands_window import PokerHandsWindow
from windows.chip_value_window import ChipValueWindow  # Import des normalen ChipValueWindow
from windows.virtual_keyboard_window import VirtualKeyboardWindow

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

        # Dynamisches Haupt-Layout für Tabellen und Buttons
        self.main_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        self.tables_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.tables_hbox.set_margin_top(15)
        self.tables_hbox.set_margin_left(15)
        self.tables_hbox.set_margin_right(15)
        
        self.buttons_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.buttons_hbox.set_margin_bottom(24)
        self.buttons_hbox.set_margin_left(15)
        self.buttons_hbox.set_margin_right(15)
        
        self.main_layout.pack_start(self.tables_hbox, False, False, 0)
        
        spacer_main = Gtk.Label()
        self.main_layout.pack_start(spacer_main, True, True, 0)
        
        self.main_layout.pack_end(self.buttons_hbox, False, False, 0)
        
        self.overlay.add_overlay(self.main_layout)

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
        """Erstellt bzw. zeigt den Namenseingabe-Bildschirm."""
        # Zuerst alle Buttons deaktivieren
        self.disable_buttons()

        # Falls bereits ein Bildschirm existiert, zerstören wir ihn
        if hasattr(self, "welcome_container") and self.welcome_container:
            self.welcome_container.destroy()

        # Vollbild-Container, der den Hintergrund abdunkelt
        self.welcome_container = Gtk.EventBox()
        self.welcome_container.set_name("welcome_container")
        self.welcome_container.set_halign(Gtk.Align.FILL)
        self.welcome_container.set_valign(Gtk.Align.FILL)
        
        # Zentrierungs-Box
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        self.welcome_container.add(center_box)

        self.welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.welcome_box.set_name("welcome_box")  # Für CSS

        # Begrüßungstext
        welcome_label = Gtk.Label(label="Willkommen! Klicken Sie unten, um dem Tisch beizutreten.")
        self.welcome_box.pack_start(welcome_label, True, True, 0)

        # "Platz nehmen" Button, der direkt die Tastatur öffnet
        self.name_button = Gtk.Button(label="Platz nehmen")
        self.name_button.get_style_context().add_class("button-custom")
        self.name_button.set_size_request(200, 50)
        self.name_button.connect("clicked", self.open_virtual_keyboard)
        self.welcome_box.pack_start(self.name_button, True, True, 0)

        center_box.pack_start(self.welcome_box, True, True, 0)

        self.overlay.add_overlay(self.welcome_container)
        self.welcome_container.show_all()  # WICHTIG: Widget sichtbar machen

    def open_virtual_keyboard(self, button):
        import socket
        current_text = button.get_label()
        if current_text == "Platz nehmen":
            # Für Testzwecke: Den Hostnamen des Raspberry Pis als Standard eintragen
            current_text = socket.gethostname()
        kbd = VirtualKeyboardWindow(self, current_text, self.on_keyboard_confirm)
        kbd.show_all()

    def on_keyboard_confirm(self, name):
        name = name.strip()
        if not name:
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Fehler: Kein Name eingegeben!"
            )
            error_dialog.format_secondary_text("Bitte geben Sie einen Namen ein, um Platz zu nehmen.")
            error_dialog.run()
            error_dialog.destroy()
            self.name_button.set_label("Platz nehmen")
            return

        # Anmeldung erfolgreich: Namen speichern, Bildschirm schließen und fortfahren
        self.player_name = name
        self.welcome_container.destroy()
        
        # In der Info-Tabelle wird nur der Name (in Fett und in Grau) angezeigt
        self.player_name_label.set_markup(f"<span foreground='#808080'><b>{name}</b></span>")
        
        # Sende den Join-Request an den Server
        import asyncio
        asyncio.run_coroutine_threadsafe(self.ws_client.send_join_message(name), self.ws_client.loop)
        
        # Aktiviere alle Buttons (nun kann der Spieler interagieren)
        self.enable_buttons()

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

    def _set_buttons_sensitive(self, container, sensitive):
        for child in container.get_children():
            if isinstance(child, Gtk.Button):
                child.set_sensitive(sensitive)
            elif hasattr(child, 'get_children'):
                self._set_buttons_sensitive(child, sensitive)

    def disable_buttons(self):
        """Deaktiviert alle Buttons im Container."""
        if hasattr(self, 'buttons_hbox'):
            self._set_buttons_sensitive(self.buttons_hbox, False)

    def enable_buttons(self):
        """Aktiviert alle Buttons im Container."""
        if hasattr(self, 'buttons_hbox'):
            self._set_buttons_sensitive(self.buttons_hbox, True)

    def create_buttons(self):
        left_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=35)
        
        # Button: Chipwerte
        chipwerte_button = Gtk.Button(label="Chipwerte")
        chipwerte_button.set_size_request(100, 40)
        chipwerte_button.connect("clicked", self.button_chipwerte_click)
        chipwerte_button.get_style_context().add_class("button-custom")
        left_buttons.pack_start(chipwerte_button, False, False, 0)

        # Button: Poker Hands
        poker_hands_button = Gtk.Button(label="Poker Hands")
        poker_hands_button.set_size_request(100, 40)
        poker_hands_button.connect("clicked", self.button_poker_hands_click)
        poker_hands_button.get_style_context().add_class("button-custom")
        left_buttons.pack_start(poker_hands_button, False, False, 0)
        
        self.buttons_hbox.pack_start(left_buttons, False, False, 0)

        # Spacer in der Mitte
        spacer = Gtk.Label()
        self.buttons_hbox.pack_start(spacer, True, True, 0)

        right_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=35)

        # Falls Admin: Button "Administration"
        if self.is_admin:
            self.administration_button = Gtk.Button(label="Administration")
            self.administration_button.set_size_request(100, 40)
            self.administration_button.connect("clicked", self.button_administration_click)
            self.administration_button.get_style_context().add_class("button-custom")
            right_buttons.pack_start(self.administration_button, False, False, 0)

        # Button "Platz verlassen" – immer mit diesem Label
        self.leave_button = Gtk.Button(label="Platz verlassen")
        self.leave_button.set_size_request(120, 40)
        self.leave_button.get_style_context().add_class("button-custom")
        self.leave_button.connect("clicked", self.on_leave_button_clicked)
        # Dieser Button ist erst aktiv, wenn ein Name eingegeben wurde
        self.leave_button.set_sensitive(False)
        right_buttons.pack_start(self.leave_button, False, False, 0)
        
        self.buttons_hbox.pack_start(right_buttons, False, False, 0)

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

        self.tables_hbox.pack_start(self.table_left, False, False, 0)

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

        # Spacer in die Mitte, um die rechte Tabelle an den Rand zu pushen
        spacer = Gtk.Label()
        self.tables_hbox.pack_start(spacer, True, True, 0)
        self.tables_hbox.pack_start(table, False, False, 0)

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
