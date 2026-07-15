import gi
gi.require_version('Gtk', '3.0')
import asyncio
import json
import websockets
from gi.repository import Gtk, Gdk, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.game_time_data import GameTimeData
from utils.timer_controller import create_game_time_timer

class TotalGameTimeWindow(Gtk.Window):
    def __init__(self, parent, confirm_callback):
        super().__init__(title="Spielzeit einstellen")
        self.parent = parent  # Speichere parent als Instanzvariable!
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)

        self.timer_stopped = True

        # Variable für Vollbildmodus initialisieren
        self.is_fullscreen_mode = False
        if parent.is_fullscreen_mode:
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

        # Zellen für Minuten und Sekunden erstellen
        self.create_timer_cells()

        # NumPad erstellen
        self.create_numpad()

        # "Schließen" Button hinzufügen
        self.create_back_button()

        # Aktuelles Eingabefeld (Minuten oder Sekunden)
        self.current_time = None

        # Flag, um zu verfolgen, ob eine neue Eingabe begonnen wurde
        self.new_entry = False

        # Bestätigungs-Callback
        self.confirm_callback = confirm_callback

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)

        # Timer-Attribute
        self.timer_id = None
        self.is_running = False
        self.is_paused = False

        # Falls bereits ein Timer-Zustand vorliegt, diesen laden
        self.load_existing_timer_state()

        # TimerController initialisieren
        self.game_timer = create_game_time_timer(
                self, 
                {
                        "minute_label": self.label_minute,
                        "second_label": self.label_second,
                        "start_button": self.button_start,
                        "pause_button": self.button_pause,
                        "stop_button": self.button_stop,
                        "fields": [self.button_minute, self.button_second]
                }
        )
    
	# Buttons mit dem Controller verbinden
        self.button_start.connect("clicked", lambda w: self.game_timer.start_timer())
        self.button_pause.connect("clicked", lambda w: self.game_timer.pause_timer())
        self.button_stop.connect("clicked", lambda w: self.game_timer.stop_timer())

    def load_existing_timer_state(self):
        """Übernimmt den aktuellen Zustand des Timers, falls er läuft oder pausiert ist."""
        if GameTimeData.is_running or GameTimeData.is_paused:
            minute_value = GameTimeData.minute if GameTimeData.minute is not None else "00"
            second_value = GameTimeData.second if GameTimeData.second is not None else "00"
            self.label_minute.set_text(f"{int(minute_value):02}")
            self.label_second.set_text(f"{int(second_value):02}")
            self.disable_input_fields()
            if GameTimeData.is_running:
                self.is_running = True
                self.start_timer()
            elif GameTimeData.is_paused:
                self.button_pause.set_sensitive(False)
                self.button_start.set_sensitive(True)
                self.button_stop.set_sensitive(True)

    def create_timer_cells(self):
        # Container für die Zeit auf der linken Seite
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_homogeneous(False)
        self.fixed.put(vbox, 130, 100)

        # Minuten Titel
        label_minute_title = Gtk.Label(label="Minuten")
        label_minute_title.get_style_context().add_class("time-title")
        vbox.pack_start(label_minute_title, False, False, 5)

        # Minuten Wert
        self.label_minute = Gtk.Label(label="00")
        self.label_minute.get_style_context().add_class("time-value")
        self.button_minute = Gtk.Button()
        self.button_minute.add(self.label_minute)
        self.button_minute.get_style_context().add_class("time-button")
        self.button_minute.connect("clicked", self.on_time_click, "minute")
        vbox.pack_start(self.button_minute, False, False, 5)

        # Sekunden Titel
        label_second_title = Gtk.Label(label="Sekunden")
        label_second_title.get_style_context().add_class("time-title")
        vbox.pack_start(label_second_title, False, False, 5)

        # Sekunden Wert
        self.label_second = Gtk.Label(label="00")
        self.label_second.get_style_context().add_class("time-value")
        self.button_second = Gtk.Button()
        self.button_second.add(self.label_second)
        self.button_second.get_style_context().add_class("time-button")
        self.button_second.connect("clicked", self.on_time_click, "second")
        vbox.pack_start(self.button_second, False, False, 5)

    def create_numpad(self):
        # NumPad auf der rechten Seite
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        self.fixed.put(grid, 400, 50)

        buttons = [
            ('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
            ('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
            ('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
            ('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
            ('►', 0, 4), ('‖', 1, 4), ('■', 2, 4),
        ]

        for item in buttons:
            label = item[0]
            x = item[1]
            y = item[2]
            button = Gtk.Button(label=label)
            button.set_size_request(70, 70)
            button.get_style_context().add_class("numpad-button")
            if label == '►':
                button.connect("clicked", self.on_start_button_click)
                self.button_start = button
            elif label == '‖':
                button.connect("clicked", self.on_pause_button_click)
                self.button_pause = button
                self.button_pause.set_sensitive(False)
            elif label == '■':
                button.connect("clicked", self.on_stop_button_click)
                self.button_stop = button
                self.button_stop.set_sensitive(False)
            elif label == '←':
                button.connect("clicked", self.on_backspace_button_click)
            elif label == 'C':
                button.connect("clicked", self.on_numpad_button_click)
            else:
                button.connect("clicked", self.on_numpad_button_click)
            grid.attach(button, x, y, 1, 1)

    def on_pause_button_click(self, button):
        self.pause_timer()

    def on_stop_button_click(self, button):
        self.stop_timer()

    def create_back_button(self):
        back_button = Gtk.Button(label="Schließen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def on_back_button_click(self, widget):
        self.close()

    def stop_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.is_paused = False

        # Setze die Gesamtspielzeit zurück (GameTimeData)
        self.label_minute.set_text("00")
        self.label_second.set_text("00")
        from data.game_time_data import GameTimeData
        GameTimeData.minute = 0
        GameTimeData.second = 0
        GameTimeData.is_running = False
        GameTimeData.is_paused = False

        # Zusätzlich: Stoppe auch den Blinds-Timer (TimerData)
        from data.timer_data import TimerData
        TimerData.is_running = False
        TimerData.is_paused = False
        # Optional: Setze TimerData auf die ursprünglichen Startwerte zurück
        TimerData.minute = TimerData.start_minute if TimerData.start_minute is not None else 0
        TimerData.second = TimerData.start_second if TimerData.start_second is not None else 0

        self.enable_input_fields()
        self.button_start.set_sensitive(True)
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(False)
        self.timer_stopped = True

        # Sende beide Updates an den Server:
        asyncio.run_coroutine_threadsafe(
            self.send_final_timer_update(GameTimeData.minute, GameTimeData.second, GameTimeData.is_running),
            self.parent.poker_interface.loop
        )
        # Falls das Admin-Window bereits existiert, sende auch für TimerData:
        if hasattr(self.parent, 'send_update_timer'):
            asyncio.run_coroutine_threadsafe(
                self.parent.send_update_timer(TimerData.minute, TimerData.second, TimerData.is_running),
                self.parent.poker_interface.loop
            )

    async def send_final_game_time_update(self, minute, second, is_running):
        server_ip, server_port = self.parent.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
            "command": "update_game_time",
            "game_time_minute": minute,
            "game_time_second": second,
            "is_running": is_running
        }
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print("Final game time update sent.")
        except Exception as e:
            print(f"Error sending final game time update: {e}")



    def on_numpad_button_click(self, button):
        label_text = button.get_label()
        if self.current_time is None:
            return
        current_label = self.label_minute if self.current_time == "minute" else self.label_second
        current_text = current_label.get_text()
        if label_text == 'C':
            current_label.set_text('00')
            self.new_entry = True
            current_label.get_style_context().remove_class("error")
        else:
            if self.new_entry or current_text == '00':
                new_text = label_text
                self.new_entry = False
            else:
                new_text = current_text + label_text
            try:
                new_value = int(new_text)
                if self.current_time == "second" and new_value >= 60:
                    new_value = 59
                    new_text = '59'
                    self.new_entry = True
                    current_label.get_style_context().add_class("error")
                    GLib.timeout_add(500, self.remove_error_class, current_label)
                else:
                    current_label.get_style_context().remove_class("error")
            except ValueError:
                new_value = 0
                new_text = '00'
                self.new_entry = True
            current_label.set_text(f"{int(new_text):02}")

    def remove_error_class(self, label):
        label.get_style_context().remove_class("error")
        return False

    def on_backspace_button_click(self, button):
        if self.current_time is None:
            return
        current_label = self.label_minute if self.current_time == "minute" else self.label_second
        current_text = current_label.get_text()
        new_text = current_text[:-1] if len(current_text) > 1 else '0'
        if len(current_text) <= 1:
            self.new_entry = True
        current_label.set_text(f"{int(new_text):02}")

    def on_time_click(self, widget, time_type):
        self.current_time = time_type
        self.new_entry = True
        self.highlight_selected_timer()

    def highlight_selected_timer(self):
        if self.current_time == "minute":
            self.label_minute.get_style_context().add_class("time-selected")
            self.label_second.get_style_context().remove_class("time-selected")
        elif self.current_time == "second":
            self.label_second.get_style_context().add_class("time-selected")
            self.label_minute.get_style_context().remove_class("time-selected")

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True

    # Timer-Kontrollmethoden (hier für einen Timer, der hochzählt)
    def on_start_button_click(self, button):
        if not self.is_running:
            self.start_timer()

    def start_timer(self):
        if self.timer_stopped:
            minute = self.label_minute.get_text()
            second = self.label_second.get_text()
            GameTimeData.minute = int(minute)
            GameTimeData.second = int(second)
        self.is_running = True
        GameTimeData.is_running = True
        GameTimeData.is_paused = False
        self.timer_stopped = False
        self.disable_input_fields()
        self.remove_timer_focus()
        self.button_start.set_sensitive(False)
        self.button_pause.set_sensitive(True)
        self.button_stop.set_sensitive(True)
        self.timer_id = GLib.timeout_add_seconds(1, self.update_timer)

    def pause_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.is_paused = True
        from data.game_time_data import GameTimeData
        GameTimeData.is_running = False
        GameTimeData.is_paused = True

        self.button_start.set_sensitive(True)
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(True)

        # Sende sofort ein Update an den Server, dass der Timer pausiert ist.
        asyncio.run_coroutine_threadsafe(
            self.send_pause_update(GameTimeData.minute, GameTimeData.second, GameTimeData.is_running),
            self.parent.poker_interface.loop
        )
        print("Pause-Taste gedrückt, Status gesendet:", GameTimeData.is_running)

    def stop_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.is_paused = False

        # Setze die Gesamtspielzeit zurück (GameTimeData)
        self.label_minute.set_text("00")
        self.label_second.set_text("00")
        from data.game_time_data import GameTimeData
        GameTimeData.minute = 0
        GameTimeData.second = 0
        GameTimeData.is_running = False
        GameTimeData.is_paused = False

        self.enable_input_fields()
        self.button_start.set_sensitive(True)
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(False)
        self.timer_stopped = True

        # Sende das finale Update an den Server:
        asyncio.run_coroutine_threadsafe(
            self.send_final_timer_update(GameTimeData.minute, GameTimeData.second, GameTimeData.is_running),
            self.parent.poker_interface.loop
        )

        # (Optional) Aktualisiere auch die Anzeige im übergeordneten Fenster
        if hasattr(self.parent, 'update_all_timer_displays'):
            GLib.idle_add(self.parent.update_all_timer_displays)


    async def send_pause_update(self, minute, second, is_running):
        server_ip, server_port = self.parent.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
            "command": "update_game_time",
            "game_time_minute": minute,
            "game_time_second": second,
            "is_running": is_running
        }
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print("Pause update sent for game time.")
        except Exception as e:
            print(f"Error sending pause update: {e}")

    async def send_final_timer_update(self, minute, second, is_running):
        server_ip, server_port = self.parent.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
            "command": "update_game_time",
            "game_time_minute": minute,
            "game_time_second": second,
            "is_running": is_running
        }
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print("Final game time update sent.")
        except Exception as e:
            print(f"Error sending final game time update: {e}")


    def update_timer(self):
        minute = int(self.label_minute.get_text())
        second = int(self.label_second.get_text())
        # Hier wird die Zeit um 1 Sekunde erhöht
        second += 1
        if second >= 60:
            minute += 1
            second = 0
        self.label_minute.set_text(f"{minute:02}")
        self.label_second.set_text(f"{second:02}")
        GameTimeData.minute = minute
        GameTimeData.second = second
        return True

    def disable_input_fields(self):
        self.button_minute.set_sensitive(False)
        self.button_second.set_sensitive(False)
        self.button_minute.set_can_focus(False)
        self.button_second.set_can_focus(False)

    def enable_input_fields(self):
        self.button_minute.set_sensitive(True)
        self.button_second.set_sensitive(True)
        self.button_minute.set_can_focus(True)
        self.button_second.set_can_focus(True)

    def remove_timer_focus(self):
        self.fixed.grab_focus()
