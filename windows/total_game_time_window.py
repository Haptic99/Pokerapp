import gi
gi.require_version('Gtk', '3.0')
import asyncio
from gi.repository import Gtk, Gdk, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.game_time_data import GameTimeData
from data.timer_data import TimerData
from utils.timer_controller import create_game_time_timer
from utils.websocket_utils import WebSocketClient
from utils.display_utils import update_client_display

class TotalGameTimeWindow(Gtk.Window):
    def __init__(self, parent, confirm_callback):
        super().__init__(title="Spielzeit einstellen")
        self.parent = parent  # Speichere parent als Instanzvariable!
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)

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

        # Liste für Numpad-Buttons
        self.numpad_buttons = []

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

        # TimerController initialisieren - zentrale Timer-Steuerung
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
        self.button_start.connect("clicked", self.on_start_button_clicked)
        self.button_pause.connect("clicked", lambda _: self.game_timer.pause_timer())
        self.button_stop.connect("clicked", self.on_stop_button_clicked)

        # WebSocket-Client initialisieren (findet Server automatisch via Zeroconf)
        self.ws_client = WebSocketClient(update_display_callback=self.update_display)
        
        # Starte den Netzwerk-Listener
        self.ws_client.start_async_loop()

        # Aktualisiere die Anzeige jede Sekunde
        GLib.timeout_add_seconds(1, self.update_timer_display)

        # Wenn Timer bereits läuft, UI entsprechend anpassen
        if GameTimeData.is_running:
            self.disable_input_fields()
            for btn in self.numpad_buttons:
                btn.set_sensitive(False)
            self.button_start.set_sensitive(False)
            self.button_pause.set_sensitive(True)
            self.button_stop.set_sensitive(True)

    def update_display(self, data):
        """
        Aktualisiert die Anzeige basierend auf Serverdaten
        """
        update_client_display(self, data)
        
        # Aktualisiere die UI basierend auf dem Spielzeit-Status vom Server
        game_running = data.get("game_time_running", False)
        
        if game_running:
            # Timer läuft
            self.disable_input_fields()
            for btn in self.numpad_buttons:
                btn.set_sensitive(False)
            self.button_start.set_sensitive(False)
            self.button_pause.set_sensitive(True)
            self.button_stop.set_sensitive(True)
        elif GameTimeData.is_paused:
            # Timer ist pausiert
            self.disable_input_fields()
            for btn in self.numpad_buttons:
                btn.set_sensitive(False)
            self.button_start.set_sensitive(True)
            self.button_pause.set_sensitive(False)
            self.button_stop.set_sensitive(True)
        else:
            # Timer ist gestoppt
            self.enable_input_fields()
            for btn in self.numpad_buttons:
                btn.set_sensitive(True)
            self.button_start.set_sensitive(True)
            self.button_pause.set_sensitive(False)
            self.button_stop.set_sensitive(False)

    def update_timer_display(self):
        """
        Aktualisiert die Anzeige des Timers basierend auf den aktuellen GameTimeData-Werten.
        """
        if GameTimeData.is_running:
            minute = GameTimeData.minute if GameTimeData.minute is not None else 0
            second = GameTimeData.second if GameTimeData.second is not None else 0
            
            # Setze die Labels, aber nur wenn sie existieren und ein Label enthaltens
            if hasattr(self, "label_minute"):
                self.label_minute.set_text(f"{int(minute):02}")
            if hasattr(self, "label_second"):
                self.label_second.set_text(f"{int(second):02}")
        
        return True  # Damit der GLib-Timeout-Callback fortgesetzt wird

    def create_timer_cells(self):
        # Container für die Zeit auf der linken Seite
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_homogeneous(False)
        self.fixed.put(vbox, 130, 100)

        # Minuten Titel
        label_minute_title = Gtk.Label(label="Minuten")
        label_minute_title.get_style_context().add_class("time-title")
        vbox.pack_start(label_minute_title, False, False, 5)

        # Aktuelle Minute aus GameTimeData verwenden oder 0
        current_minute = GameTimeData.minute if GameTimeData.minute is not None else 0
        
        # Minuten Wert
        self.label_minute = Gtk.Label(label=f"{current_minute:02}")
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

        # Aktuelle Sekunde aus GameTimeData verwenden oder 0
        current_second = GameTimeData.second if GameTimeData.second is not None else 0
        
        # Sekunden Wert
        self.label_second = Gtk.Label(label=f"{current_second:02}")
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
                self.button_start = button
            elif label == '‖':
                self.button_pause = button
                self.button_pause.set_sensitive(False)
            elif label == '■':
                self.button_stop = button
                self.button_stop.set_sensitive(False)
            elif label == '←':
                button.connect("clicked", self.on_backspace_button_click)
            elif label == 'C':
                button.connect("clicked", self.on_numpad_button_click)
            else:
                button.connect("clicked", self.on_numpad_button_click)
            grid.attach(button, x, y, 1, 1)
            self.numpad_buttons.append(button)

    def create_back_button(self):
        back_button = Gtk.Button(label="Schließen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def on_back_button_click(self, widget):
        self.close()

    def on_start_button_clicked(self, button):
        # Timer starten mit dem Controller
        self.game_timer.start_timer()
        
        # NEUE FUNKTIONALITÄT: NumPad deaktivieren
        for btn in self.numpad_buttons:
            btn.set_sensitive(False)
        
        # NEUE FUNKTIONALITÄT: Eingabefelder deaktivieren
        self.disable_input_fields()
        
        # NEUE FUNKTIONALITÄT: Fokus explizit entfernen
        self.remove_timer_focus()
        
        # NEUE FUNKTIONALITÄT: Start deaktivieren, Pause und Stop aktivieren
        self.button_start.set_sensitive(False)
        self.button_pause.set_sensitive(True)
        self.button_stop.set_sensitive(True)

    def on_stop_button_clicked(self, button):
        """
        Erweiterter Stop-Button, der auch den Blinds-Timer zurücksetzt
        """
        # Zuerst den Spielzeit-Timer mit dem Controller stoppen
        self.game_timer.stop_timer()

        # Zusätzlich: Stoppe auch den Blinds-Timer (TimerData)
        TimerData.is_running = False
        TimerData.is_paused = False
        # Optional: Setze TimerData auf die ursprünglichen Startwerte zurück
        TimerData.minute = TimerData.start_minute if TimerData.start_minute is not None else "-"
        TimerData.second = TimerData.start_second if TimerData.start_second is not None else "-"

        # Falls das Admin-Window bereits existiert, sende auch für TimerData:
        if hasattr(self.parent, 'send_update_timer'):
            asyncio.run_coroutine_threadsafe(
                self.parent.send_update_timer(TimerData.minute, TimerData.second, TimerData.is_running),
                self.parent.poker_interface.loop
            )

        # NEUE FUNKTIONALITÄT: Aktiviere alle NumPad-Buttons wieder
        for btn in self.numpad_buttons:
            btn.set_sensitive(True)
            
        # NEUE FUNKTIONALITÄT: Aktiviere die Eingabefelder
        self.enable_input_fields()
        
        # NEUE FUNKTIONALITÄT: Start aktivieren, Pause und Stop deaktivieren
        self.button_start.set_sensitive(True)
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(False)

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
        self.current_time = None
        self.label_minute.get_style_context().remove_class("time-selected")
        self.label_second.get_style_context().remove_class("time-selected")
