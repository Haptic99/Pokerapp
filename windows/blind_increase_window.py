from gi.repository import Gtk, Gdk
from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.blind_data import BlindData
from data.timer_data import TimerData

import asyncio
import websockets
import json
import gi
gi.require_version('Gtk', '3.0')


class BlindIncreaseWindow(Gtk.Window):
    def __init__(self, parent, confirm_callback=None):
        super().__init__(title="Blind erhöhen?")
        self.parent = parent
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.confirm_callback = confirm_callback

        # Variable für Vollbildmodus initialisieren
        self.is_fullscreen_mode = False

        # Überprüfen, ob das Elternfenster im Vollbildmodus ist
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        # Hintergrundbild setzen
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        # Hauptcontainer erstellen
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Dialog-Komponenten erstellen
        self.create_dialog_components()

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)

    def create_dialog_components(self):
        # Aktuelle Blind-Werte abrufen
        current_small_blind = BlindData.small_blind if BlindData.small_blind is not None else "-"
        current_big_blind = BlindData.big_blind if BlindData.big_blind is not None else "-"

        # Berechne neue Blind-Werte (verdoppelt)
        try:
            new_small_blind = str(int(current_small_blind) * 2)
            new_big_blind = str(int(current_big_blind) * 2)
        except (ValueError, TypeError):
            new_small_blind = "-"
            new_big_blind = "-"

        # Rahmen für das Dialogfenster
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        frame.get_style_context().add_class("blind-increase-frame")

        # Hauptdialog-Box (Container für alles)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(30)
        main_box.set_margin_end(30)

        # Titel mit größerer Schrift
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold' foreground='#CDAD00'>Nächste Blinderhöhung</span>")
        title_label.get_style_context().add_class("dialog-text")
        title_label.set_margin_top(10)
        title_label.set_margin_bottom(20)
        main_box.pack_start(title_label, False, False, 0)

        # Blindwerte in einer Tabelle anzeigen
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(15)
        grid.set_halign(Gtk.Align.CENTER)
        grid.get_style_context().add_class("blinds-grid")

        # Beschriftungen
        current_blinds_label = Gtk.Label()
        current_blinds_label.set_markup("<span foreground='#9FB6CD'>Aktuelle Blinds:</span>")
        current_blinds_label.set_halign(Gtk.Align.START)

        new_blinds_label = Gtk.Label()
        new_blinds_label.set_markup("<span foreground='#9FB6CD'>Neue Blinds:</span>")
        new_blinds_label.set_halign(Gtk.Align.START)

        # Aktuelle Blinds
        current_value_label = Gtk.Label()
        current_value_label.set_markup(f"<span foreground='#9FB6CD'>{current_small_blind}/{current_big_blind}</span>")
        current_value_label.set_halign(Gtk.Align.END)

        # Neue Blinds - hervorgehoben
        new_value_label = Gtk.Label()
        new_value_label.set_markup(f"<span foreground='#FFFF00' weight='bold'>{new_small_blind}/{new_big_blind}</span>")
        new_value_label.get_style_context().add_class("highlight")
        new_value_label.set_halign(Gtk.Align.END)

        # Tabelle zusammenbauen
        grid.attach(current_blinds_label, 0, 0, 1, 1)
        grid.attach(current_value_label, 1, 0, 1, 1)
        grid.attach(new_blinds_label, 0, 1, 1, 1)
        grid.attach(new_value_label, 1, 1, 1, 1)

        # Grid zum Hauptbox hinzufügen
        main_box.pack_start(grid, False, False, 0)

        # Button-Box für die Aktionsbuttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)
        button_box.set_margin_bottom(10)

        # Buttons mit konsistentem Styling
        self.yes_button = Gtk.Button(label="Ja, Blinds erhöhen")
        self.yes_button.set_size_request(200, 50)
        self.yes_button.connect("clicked", self.on_yes_clicked)
        self.yes_button.get_style_context().add_class("button-custom")
        self.yes_button.get_style_context().add_class("yes-button")

        self.no_button = Gtk.Button(label="Nein, Blinds beibehalten")
        self.no_button.set_size_request(200, 50)
        self.no_button.connect("clicked", self.on_no_clicked)
        self.no_button.get_style_context().add_class("button-custom")
        self.no_button.get_style_context().add_class("no-button")

        button_box.pack_start(self.yes_button, False, False, 0)
        button_box.pack_start(self.no_button, False, False, 0)

        main_box.pack_start(button_box, False, False, 0)

        # Den Frame um die Hauptbox legen und alles dem Fixed-Container hinzufügen
        frame.add(main_box)
        self.fixed.put(frame, 150, 100)

    def on_yes_clicked(self, widget):
        """Verdoppelt die Blinds und startet den Timer neu."""
        # Aktuelle Blind-Werte
        current_small_blind = BlindData.small_blind
        current_big_blind = BlindData.big_blind

        # Verdoppelte Werte berechnen
        try:
            new_small_blind = str(int(current_small_blind) * 2)
            new_big_blind = str(int(current_big_blind) * 2)

            # Blind-Daten aktualisieren
            BlindData.small_blind = new_small_blind
            BlindData.big_blind = new_big_blind

            # Timer zurücksetzen und starten
            TimerData.is_running = True
            TimerData.is_paused = False
            TimerData.minute = TimerData.start_minute
            TimerData.second = TimerData.start_second

            # Server-Update senden
            self.send_updates(new_small_blind, new_big_blind, True)

        except (ValueError, TypeError) as e:
            print(f"Fehler beim Verdoppeln der Blinds: {e}")

        self.close()

    def on_no_clicked(self, widget):
        """Behält die aktuellen Blinds bei und setzt den Timer zurück, ohne ihn zu starten."""
        # Timer zurücksetzen aber nicht starten
        TimerData.is_running = False
        TimerData.is_paused = False
        TimerData.minute = TimerData.start_minute
        TimerData.second = TimerData.start_second

        # Server-Update senden (Timer-Update ohne Blind-Update)
        self.send_updates(None, None, False)

        self.close()

    def send_updates(self, small_blind, big_blind, start_timer):
        """Sendet die Updates an den Server."""
        # Suche nach dem event loop
        loop = None

        # Verschiedene Möglichkeiten durchgehen, wo der loop sein könnte
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'loop'):
            # Fall 1: Direkter Zugriff auf poker_interface (AdminWindow)
            loop = self.parent.poker_interface.loop
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'loop'):
            # Fall 2: Der Parent hat einen websocket client (TimerSettingWindow)
            loop = self.parent.ws_client.loop
        elif hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'poker_interface'):
            # Fall 3: Zugriff über parent.parent
            loop = self.parent.parent.poker_interface.loop
        else:
            print("ERROR: Konnte keinen asyncio loop finden!")
            return

        # Timer-Update senden
        asyncio.run_coroutine_threadsafe(
            self.send_update_timer(
                TimerData.start_minute,
                TimerData.start_second,
                start_timer
            ),
            loop
        )

        # Blinds-Update senden (nur wenn die Blinds erhöht werden sollen)
        if small_blind is not None and big_blind is not None:
            asyncio.run_coroutine_threadsafe(
                self.send_update_blinds(small_blind, big_blind),
                loop
            )

    async def send_update_timer(self, minute, second, is_running):
        """Sendet Timer-Updates an den Server."""
        # Determine server address
        server_address = None
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
            server_address = self.parent.poker_interface.server_address
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
            server_address = self.parent.ws_client.server_address

        if not server_address:
            print("ERROR: Konnte keine Server-Adresse finden!")
            return

        server_ip, server_port = server_address
        uri = f"ws://{server_ip}:{server_port}"

        try:
            async with websockets.connect(uri) as websocket:
                message = {
                    "command": "update_timer",
                    "minute": minute,
                    "second": second,
                    "is_running": is_running
                }
                await websocket.send(json.dumps(message))
                print(f"Timer Update gesendet: {minute}:{second}, running: {is_running}")
        except Exception as e:
            print(f"Fehler beim Senden des Timer-Updates: {e}")

    async def send_update_blinds(self, small_blind, big_blind):
        """Sendet Blind-Updates an den Server."""
        # Determine server address
        server_address = None
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
            server_address = self.parent.poker_interface.server_address
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
            server_address = self.parent.ws_client.server_address

        if not server_address:
            print("ERROR: Konnte keine Server-Adresse finden!")
            return

        server_ip, server_port = server_address
        uri = f"ws://{server_ip}:{server_port}"

        try:
            async with websockets.connect(uri) as websocket:
                message = {
                    "command": "update_blinds",
                    "small_blind": small_blind,
                    "big_blind": big_blind
                }
                await websocket.send(json.dumps(message))
                print(f"Blind Update gesendet: {small_blind}/{big_blind}")
        except Exception as e:
            print(f"Fehler beim Senden des Blind-Updates: {e}")

    def on_key_press(self, widget, event):
        """Keybindings für Escape und F11."""
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        """Schaltet zwischen Vollbild und Fenstergröße um."""
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True
