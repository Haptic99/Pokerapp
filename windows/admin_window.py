import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from windows.blind_adjustment_window import BlindAdjustmentWindow
from windows.timer_setting_window import TimerSettingWindow
from data.blind_data import BlindData
from data.timer_data import TimerData

class AdminWindow(Gtk.Window):
    def __init__(self, poker_interface):
        super().__init__(title="Admin Panel")
        self.poker_interface = poker_interface  # Referenz auf das Poker-Interface speichern
        self.set_default_size(800, 480)

        # Setze das Admin-Fenster als untergeordnetes Fenster des Poker-Interfaces
        if self.poker_interface:
            self.set_transient_for(self.poker_interface)  

        self.set_modal(True)

        # Variable für Vollbildmodus initialisieren
        self.is_fullscreen_mode = False

        # Überprüfen, ob das Poker-Interface im Vollbildmodus ist
        if self.poker_interface and self.poker_interface.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)

        # Hintergrundbild setzen
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        # Gtk.Fixed verwenden, um die Widgets an festen Positionen zu platzieren
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Benutzeroberfläche erstellen
        self.create_ui()

        # Timer für Admin-Fenster starten
        self.start_admin_timer()

    def create_ui(self):
        # "Blinds anpassen" Button
        adjust_blinds_button = Gtk.Button(label="Blinds anpassen")
        adjust_blinds_button.set_size_request(165, 40)
        adjust_blinds_button.connect("clicked", self.open_blind_adjustment_window)
        adjust_blinds_button.connect("enter-notify-event", self.on_hover)  # Hover-Effekt starten
        adjust_blinds_button.connect("leave-notify-event", self.on_leave)  # Hover-Effekt beenden
        adjust_blinds_button.get_style_context().add_class("button-custom")
        self.fixed.put(adjust_blinds_button, 30, 20)  # Oben platzieren
        
        # "Blinds Zeiten" Button
        blinds_times_button = Gtk.Button(label="Blinds Zeiten")
        blinds_times_button.set_size_request(165, 40)
        blinds_times_button.connect("clicked", self.open_timer_setting_window)
        blinds_times_button.connect("enter-notify-event", self.on_hover)  # Hover-Effekt starten
        blinds_times_button.connect("leave-notify-event", self.on_leave)  # Hover-Effekt beenden
        blinds_times_button.get_style_context().add_class("button-custom")
        self.fixed.put(blinds_times_button, 30, 120)  # Position anpassen

        # Tabelle für Blinds erstellen
        self.create_blinds_table()

        # Tabelle für Timer erstellen
        self.create_timer_table()

        # "Zurück" Button unten rechts hinzufügen
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def create_blinds_table(self):
        """Erstellt eine Tabelle für die Blinds neben dem 'Blinds anpassen' Button."""
        self.blinds_table = Gtk.Grid()
        self.blinds_table.set_row_spacing(5)
        self.blinds_table.set_column_spacing(10)
        self.blinds_table.set_margin_top(10)
        self.blinds_table.set_margin_left(40)

        # Aktuelle Blind-Werte abrufen oder 'n.V.' setzen, wenn None
        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "n.V."
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "n.V."

        # Beispiel-Daten für die Tabelle
        data = [
            ("Small Blind", small_blind_value),
            ("Big Blind", big_blind_value),
        ]

        self.blind_labels = {}  # Speichert die Label-Widgets für späteres Update

        # Füge die Daten in die Tabelle ein
        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)

            # Größe der Spalten festlegen
            label1.set_size_request(150, 25)
            label2.set_size_request(70, 25)

            # Normale Zeilen (2 Spalten)
            label1.set_xalign(0.0)  # Linksbündig
            label1.set_margin_left(6)  # Fügt 6px am linken Rand hinzu
            label2.set_xalign(1.0)  # Rechtsbündig
            label2.set_margin_right(6)  # Fügt 6px am rechten Rand hinzu

            # CSS-Klassen zu den Labels hinzufügen
            label1.get_style_context().add_class("green-text")
            label2.get_style_context().add_class("green-text")

            # Labels speichern
            self.blind_labels[col1] = label2

            # Labels zur Tabelle hinzufügen und CSS-Klasse für Rahmen anwenden
            frame1 = Gtk.Frame()
            frame1.add(label1)
            frame1.get_style_context().add_class("table-cell")

            frame2 = Gtk.Frame()
            frame2.add(label2)
            frame2.get_style_context().add_class("table-cell")

            self.blinds_table.attach(frame1, 0, row, 1, 1)
            self.blinds_table.attach(frame2, 1, row, 1, 1)

        # Tabelle positionieren (neben dem 'Blinds anpassen' Button)
        self.fixed.put(self.blinds_table, 180, 6)

    def create_timer_table(self):
        """Erstellt eine Tabelle für den Timer."""
        self.timer_table = Gtk.Grid()
        self.timer_table.set_row_spacing(5)
        self.timer_table.set_column_spacing(10)
        self.timer_table.set_margin_top(10)
        self.timer_table.set_margin_left(40)

        # Aktuelle Timer-Werte abrufen oder "00:00" setzen, wenn None
        minute_value = TimerData.minute if TimerData.minute is not None else 0
        second_value = TimerData.second if TimerData.second is not None else 0
        
        # Aktuelle Startzeit-Werte abrufen oder "00:00" setzen, wenn None
        minute = TimerData.start_minute if TimerData.start_minute is not None else 0
        second = TimerData.start_second if TimerData.start_second is not None else 0

        # Umwandeln der Werte in Strings, bevor zfill aufgerufen wird
        minute_str = str(minute).zfill(2)
        second_str = str(second).zfill(2)
        minute_value_str = str(minute_value).zfill(2)
        second_value_str = str(second_value).zfill(2)

        # Beispiel-Daten für die Tabelle
        data = [
            ("Eingestellte Zeit", f"{minute_str}:{second_str}"),
            ("Momentane Zeit", f"{minute_value_str}:{second_value_str}"),
        ]

        self.timer_labels = {}  # Speichert die Label-Widgets für späteres Update

        # Füge die Daten in die Tabelle ein
        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)

            # Größe der Spalten festlegen
            label1.set_size_request(150, 25)
            label2.set_size_request(70, 25)

            # Normale Zeilen (2 Spalten)
            label1.set_xalign(0.0)  # Linksbündig
            label1.set_margin_left(6)  # Fügt 6px am linken Rand hinzu
            label2.set_xalign(1.0)  # Rechtsbündig
            label2.set_margin_right(6)  # Fügt 6px am rechten Rand hinzu

            # CSS-Klassen zu den Labels hinzufügen
            label1.get_style_context().add_class("green-text")
            label2.get_style_context().add_class("green-text")

            # Labels speichern
            self.timer_labels[col1] = label2

            # Labels zur Tabelle hinzufügen und CSS-Klasse für Rahmen anwenden
            frame1 = Gtk.Frame()
            frame1.add(label1)
            frame1.get_style_context().add_class("table-cell")

            frame2 = Gtk.Frame()
            frame2.add(label2)
            frame2.get_style_context().add_class("table-cell")

            self.timer_table.attach(frame1, 0, row, 1, 1)
            self.timer_table.attach(frame2, 1, row, 1, 1)

        # Tabelle positionieren
        self.fixed.put(self.timer_table, 180, 110)

    def update_all_timer_displays(self):
        """Aktualisiert den Timer-Status auf allen Bildschirmen."""
        minute = int(TimerData.minute) if TimerData.minute is not None else 0
        second = int(TimerData.second) if TimerData.second is not None else 0
        status_text = "►" if TimerData.is_running else "‖"

        # Timer im Poker-Interface aktualisieren
        if hasattr(self, "left_labels") and "Nächste Blinderhöhung" in self.left_labels:
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")

        # Timer im Admin-Window aktualisieren
        if hasattr(self, "timer_labels") and "Momentane Zeit" in self.timer_labels:
            self.timer_labels["Momentane Zeit"].set_text(f"{status_text} {minute:02}:{second:02}")


    def start_admin_timer(self):
        """Startet einen Timer, der jede Sekunde das Admin-Fenster aktualisiert."""
        GLib.timeout_add_seconds(1, self.update_admin_timer)

    def update_admin_timer(self):
        """Aktualisiert die Timer-Anzeige im Admin-Fenster."""
        if TimerData.is_running:  # Überprüfen, ob der Timer läuft
            start_minute = int(TimerData.start_minute) if TimerData.start_minute is not None else 0
            start_second = int(TimerData.start_second) if TimerData.start_second is not None else 0
            minute = int(TimerData.minute) if TimerData.minute is not None else 0
            second = int(TimerData.second) if TimerData.second is not None else 0

            # Timer-Labels aktualisieren
            self.timer_labels["Eingestellte Zeit"].set_text(f"{start_minute:02}:{start_second:02}")
            self.timer_labels["Momentane Zeit"].set_text(f"{minute:02}:{second:02}")

        return True  # Timer weiterlaufen lassen

    def open_blind_adjustment_window(self, widget):
        """Öffnet das Fenster zum Anpassen der Blinds."""
        blind_window = BlindAdjustmentWindow(self, self.on_blind_values_confirmed)
        blind_window.show_all()

    def open_timer_setting_window(self, widget):
        """Öffnet das Fenster zum Einstellen der Blind-Zeiten."""
        timer_window = TimerSettingWindow(self, self.on_timer_values_confirmed)
        timer_window.show_all()

    def on_blind_values_confirmed(self, small_blind, big_blind):
        """Verarbeitet die bestätigten Werte aus dem BlindAdjustmentWindow und aktualisiert das Poker-Interface."""
        print(f"Bestätigte Werte - Small Blind: {small_blind}, Big Blind: {big_blind}")

        # Blinds im Admin-Fenster aktualisieren
        self.update_blinds_table(small_blind, big_blind)

        # Blinds im Poker-Interface aktualisieren
        if self.poker_interface:
            self.poker_interface.update_blinds_in_table(small_blind, big_blind)


    def on_timer_values_confirmed(self, minute, second):
        """Verarbeitet die bestätigten Werte aus dem TimerSettingWindow."""
        print(f"Bestätigte Werte - Minuten: {minute}, Sekunden: {second}")
        self.update_timer_table(minute, second)

    def update_blinds_table(self, small_blind, big_blind):
        """Aktualisiert die Blind-Werte in der Tabelle."""
        self.blind_labels["Small Blind"].set_text(small_blind)
        self.blind_labels["Big Blind"].set_text(big_blind)

    def update_timer_table(self, minute, second):
        """Aktualisiert die Timer-Werte in der Tabelle."""
        self.timer_labels["Zeit"].set_text(minute.zfill(2) + ":" + second.zfill(2))

    def on_back_button_click(self, widget):
        self.close()

    def on_hover(self, widget, event):
        """Hover-Effekt starten und nach 0,5 Sekunden entfernen, solange der Mauszeiger über dem Button ist."""
        widget.get_style_context().add_class("hovered")

        if hasattr(self, 'hover_timer') and self.hover_timer:
            GLib.source_remove(self.hover_timer)

        self.hover_timer = GLib.timeout_add(500, self.remove_hover_effect, widget)

    def on_leave(self, widget, event):
        """Hover-Effekt entfernen, wenn die Maus den Button verlässt, nach 0,2 Sekunden."""
        if hasattr(self, 'hover_timer') and self.hover_timer:
            GLib.source_remove(self.hover_timer)

        self.hover_timer = GLib.timeout_add(200, self.remove_hover_effect, widget)

    def remove_hover_effect(self, widget):
        """Hover-Effekt entfernen."""
        widget.get_style_context().remove_class("hovered")
        self.hover_timer = None
        return False

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
            self.set_default_size(800, 480)
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True
