import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.timer_data import TimerData

class TimerSettingWindow(Gtk.Window):
    def __init__(self, parent, confirm_callback):
        super().__init__(title="Timer einstellen")
        self.parent = parent  # ✅ Hier speichern wir parent als Instanzvariable!
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)

        # Variable für Vollbildmodus initialisieren
        self.is_fullscreen_mode = False

        # Überprüfen, ob das Elternfenster im Vollbildmodus ist
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

        # "Zurück" Button hinzufügen
        self.create_back_button()

        # Aktuelles Eingabefeld (Minuten oder Sekunden)
        self.current_time = None

        # Flag, um zu verfolgen, ob eine neue Eingabe begonnen wurde
        self.new_entry = False

        # Bestätigungs-Callback
        self.confirm_callback = confirm_callback

        # Variable zum Speichern des Vollbildstatus
        self.is_fullscreen_mode = False

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)

        # Timer-Attribute
        self.timer_id = None
        self.is_running = False
        self.is_paused = False

        # Wenn der Timer bereits läuft, übernimm die aktuellen Werte
        self.load_existing_timer_state()

    def load_existing_timer_state(self):
        """Übernimmt den aktuellen Zustand des Timers, falls er läuft."""
        if TimerData.is_running or TimerData.is_paused:
            # Timer läuft oder ist pausiert, setze die aktuellen Werte
            minute_value = TimerData.minute if TimerData.minute is not None else "00"
            second_value = TimerData.second if TimerData.second is not None else "00"
            self.label_minute.set_text(f"{int(minute_value):02}")
            self.label_second.set_text(f"{int(second_value):02}")

            # Timer-Felder deaktivieren, wenn der Timer läuft
            self.disable_input_fields()

            # Timer läuft weiter
            if TimerData.is_running:
                self.is_running = True
                self.start_timer()
            elif TimerData.is_paused:
                # Der Timer ist pausiert, aktiviere den Start-Button zum Fortsetzen
                self.button_pause.set_sensitive(False)
                self.button_start.set_sensitive(True)
                self.button_stop.set_sensitive(True)

    def create_timer_cells(self):
        # Container für die Zeit auf der linken Seite
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_homogeneous(False)
        self.fixed.put(vbox, 130, 100)  # Position anpassen

        # Minuten Titel
        label_minute_title = Gtk.Label(label="Minuten")
        label_minute_title.get_style_context().add_class("time-title")
        vbox.pack_start(label_minute_title, False, False, 5)

        # Minuten Wert
        self.label_minute = Gtk.Label(label="00")
        self.label_minute.get_style_context().add_class("time-value")

        # Button um das Label, um Klicks zu erfassen
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

        # Button um das Label, um Klicks zu erfassen
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
        self.fixed.put(grid, 400, 50)  # Position anpassen

        # Buttons erstellen
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
            button.set_size_request(70, 70)  # Größe anpassen
            button.get_style_context().add_class("numpad-button")

            if label == '►':
                button.connect("clicked", self.on_start_button_click)
                self.button_start = button  # Start-Button zuweisen
            elif label == '‖':
                button.connect("clicked", self.on_pause_button_click)
                self.button_pause = button  # Pause-Button zuweisen
                self.button_pause.set_sensitive(False)  # Anfangs deaktiviert
            elif label == '■':
                button.connect("clicked", self.on_stop_button_click)
                self.button_stop = button  # Stop-Button zuweisen
                self.button_stop.set_sensitive(False)  # Anfangs deaktiviert
            elif label == '←':
                button.connect("clicked", self.on_backspace_button_click)
            elif label == 'C':
                button.connect("clicked", self.on_numpad_button_click)
            else:
                button.connect("clicked", self.on_numpad_button_click)

            grid.attach(button, x, y, 1, 1)

    def create_back_button(self):
        # "Zurück" Button unten rechts hinzufügen
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def on_back_button_click(self, widget):
        self.close()

    def on_numpad_button_click(self, button):
        label_text = button.get_label()
        if self.current_time is None:
            return  # Kein Feld ausgewählt

        if self.current_time == "minute":
            current_label = self.label_minute
        else:
            current_label = self.label_second

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
                if new_value > 60:
                    new_value = 60
                    new_text = '60'
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
            return  # Kein Feld ausgewählt

        if self.current_time == "minute":
            current_label = self.label_minute
        else:
            current_label = self.label_second

        current_text = current_label.get_text()

        if len(current_text) > 1:
            new_text = current_text[:-1]
        else:
            new_text = '0'
            self.new_entry = True

        current_label.set_text(new_text)

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

    # Methoden für Timer-Kontrollen
    def on_start_button_click(self, button):
        if not self.is_running:
            self.start_timer()

    def start_timer(self):
        if not self.is_running:
            minute = self.label_minute.get_text()
            second = self.label_second.get_text()

            # Werte in TimerData speichern
            TimerData.minute = minute
            TimerData.second = second

            # Speichere die Startwerte, falls sie noch nicht gesetzt wurden
            if TimerData.start_minute is None and TimerData.start_second is None:
                TimerData.start_minute = minute
                TimerData.start_second = second

        self.is_running = True
        TimerData.is_running = True  # Timer läuft
        TimerData.is_paused = False  # Timer wird fortgesetzt

        self.disable_input_fields()
        self.button_start.set_sensitive(False)
        self.button_pause.set_sensitive(True)
        self.button_stop.set_sensitive(True)

        # Start the timer loop
        self.timer_id = GLib.timeout_add_seconds(1, self.update_timer)


    def pause_timer(self):
        """Pausiert den Timer im aktuellen Fenster und aktualisiert alle Bildschirme."""
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None

        self.is_running = False
        self.is_paused = True
        TimerData.is_running = False
        TimerData.is_paused = True

        # Buttons aktualisieren
        self.button_start.set_sensitive(True)
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(True)

        # Falls das Admin-Window oder Poker-Interface existiert, Timer-Status aktualisieren
        if self.parent:
            self.parent.update_all_timer_displays()



    def stop_timer(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
    
        # Setze die Zustände zurück
        self.is_running = False
        self.is_paused = False
        TimerData.is_running = False  # Timer in TimerData stoppen
        TimerData.is_paused = False  # Pausenstatus zurücksetzen

        # Setze die gespeicherten Startwerte wieder zurück
        self.label_minute.set_text(f"{int(TimerData.start_minute):02}")
        self.label_second.set_text(f"{int(TimerData.start_second):02}")

        # Aktualisiere auch die aktuellen Werte in TimerData, um sie mit den Startwerten zu synchronisieren
        TimerData.minute = TimerData.start_minute
        TimerData.second = TimerData.start_second

        # Reaktiviere die Eingabefelder für Minuten und Sekunden
        self.enable_input_fields()

        # Aktualisiere die Button-Zustände
        self.button_start.set_sensitive(True)
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(False)


    def on_pause_button_click(self, button):
        """Pausiert den Timer und aktualisiert alle Bildschirme."""
        self.pause_timer()  # Ruft die Methode auf, um den Timer im aktuellen Fenster zu pausieren

        # Falls das Admin-Window oder Poker-Interface existiert, Timer-Status synchronisieren
        if self.parent:
            self.parent.update_all_timer_displays()



    def on_stop_button_click(self, button):
        self.stop_timer()

    def update_timer(self):
        minute = int(self.label_minute.get_text())
        second = int(self.label_second.get_text())

        if second == 0:
            if minute == 0:
                self.timer_finished()
                return False
            else:
                minute -= 1
                second = 59
        else:
            second -= 1

        # Aktualisiere die Labels
        self.label_minute.set_text(str(f"{minute:02}"))
        self.label_second.set_text(str(f"{second:02}"))

        # Aktualisiere TimerData
        TimerData.minute = minute
        TimerData.second = second

        return True

    def timer_finished(self):
        self.is_running = False
        self.is_paused = False
        TimerData.is_running = False
        TimerData.is_paused = False
        self.button_start.set_label("Start")
        self.button_pause.set_sensitive(False)
        self.button_stop.set_sensitive(False)
        self.enable_input_fields()
        self.reset_timer_labels()

        # Optional: Benachrichtigung anzeigen
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Timer abgelaufen!",
        )
        dialog.format_secondary_text(
            "Die eingestellte Zeit ist abgelaufen."
        )
        dialog.run()
        dialog.destroy()

    def disable_input_fields(self):
        self.button_minute.set_sensitive(False)
        self.button_second.set_sensitive(False)

    def enable_input_fields(self):
        self.button_minute.set_sensitive(True)
        self.button_second.set_sensitive(True)

    def reset_timer_labels(self):
        # Reset to the initial time stored in TimerData
        minute = TimerData.minute if TimerData.minute is not None else "00"
        second = TimerData.second if TimerData.second is not None else "00"
        self.label_minute.set_text(f"{int(minute):02}")
        self.label_second.set_text(f"{int(second):02}")
