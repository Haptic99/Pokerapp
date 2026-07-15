# windows/blind_adjustment_window.py

from gi.repository import Gtk, Gdk, GLib
from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.blind_data import BlindData

import gi
gi.require_version('Gtk', '3.0')


class BlindAdjustmentWindow(Gtk.Window):
    def __init__(self, parent, confirm_callback):
        super().__init__(title="Blinds anpassen")
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

        # Liste für Numpad-Buttons
        self.numpad_buttons = []

        # Zellen für Small Blind und Big Blind erstellen
        self.create_blind_cells()

        # NumPad erstellen
        self.create_numpad()

        # "Zurück" Button hinzufügen
        self.create_back_button()

        # Aktuelles Eingabefeld (Small Blind oder Big Blind)
        self.current_blind = None

        # Flag, um zu verfolgen, ob eine neue Eingabe begonnen wurde
        self.new_entry = False

        # Bestätigungs-Callback
        self.confirm_callback = confirm_callback

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)

    def create_blind_cells(self):
        # Container für die Blinds auf der linken Seite
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_homogeneous(False)
        self.fixed.put(vbox, 130, 100)  # Position anpassen

        # Small Blind Titel
        label_small_title = Gtk.Label(label="Small Blind")
        label_small_title.get_style_context().add_class("time-title")  # Verwende time-title wie im TimerSettingWindow
        vbox.pack_start(label_small_title, False, False, 5)

        # Aktuelle Blind-Werte abrufen oder '00' setzen, wenn None
        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "0"
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "0"

        # Versuche, als Integer zu konvertieren und formatieren
        try:
            small_blind_text = f"{int(small_blind_value):02}"
        except (ValueError, TypeError):
            small_blind_text = "00"

        try:
            big_blind_text = f"{int(big_blind_value):02}"
        except (ValueError, TypeError):
            big_blind_text = "00"

        # Small Blind Wert
        self.label_small_blind = Gtk.Label(label=small_blind_text)
        self.label_small_blind.get_style_context().add_class("time-value")  # Verwende time-value statt blind-value

        # Button um das Label, um Klicks zu erfassen
        self.button_small_blind = Gtk.Button()
        self.button_small_blind.add(self.label_small_blind)
        self.button_small_blind.get_style_context().add_class("time-button")  # Verwende time-button statt blind-button
        self.button_small_blind.connect("clicked", self.on_blind_click, "small")
        vbox.pack_start(self.button_small_blind, False, False, 5)

        # Big Blind Titel
        label_big_title = Gtk.Label(label="Big Blind")
        label_big_title.get_style_context().add_class("time-title")  # Verwende time-title wie im TimerSettingWindow
        vbox.pack_start(label_big_title, False, False, 5)

        # Big Blind Wert
        self.label_big_blind = Gtk.Label(label=big_blind_text)
        self.label_big_blind.get_style_context().add_class("time-value")  # Verwende time-value statt blind-value

        # Button um das Label, um Klicks zu erfassen
        self.button_big_blind = Gtk.Button()
        self.button_big_blind.add(self.label_big_blind)
        self.button_big_blind.get_style_context().add_class("time-button")  # Verwende time-button statt blind-button
        self.button_big_blind.connect("clicked", self.on_blind_click, "big")
        vbox.pack_start(self.button_big_blind, False, False, 5)

    def create_numpad(self):
        # NumPad auf der rechten Seite
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        self.fixed.put(grid, 400, 50)  # Position anpassen

        # Erstellen der Buttons
        buttons = [
            ('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
            ('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
            ('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
            ('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
            ('Ok', 0, 4, 3)  # 'Ok' Button über drei Spalten
        ]

        for item in buttons:
            label = item[0]
            x = item[1]
            y = item[2]
            if len(item) == 4:
                width = item[3]
                height = 1
            else:
                width = 1
                height = 1

            button = Gtk.Button(label=label)
            button.set_size_request(70 * width + 10 * (width - 1), 70)  # Größe anpassen
            button.get_style_context().add_class("numpad-button")

            # Spezielle Behandlung für den 'Ok' Button
            if label == 'Ok':
                button.connect("clicked", self.on_ok_button_click)
            elif label == '←':
                button.connect("clicked", self.on_backspace_button_click)
            else:
                button.connect("clicked", self.on_numpad_button_click)

            grid.attach(button, x, y, width, height)
            # Füge den Button zur Liste hinzu
            self.numpad_buttons.append(button)

    def create_back_button(self):
        # "Schliessen" Button unten rechts hinzufügen
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def on_back_button_click(self, widget):
        self.close()

    def on_numpad_button_click(self, button):
        label_text = button.get_label()
        if self.current_blind is None:
            return  # Kein Feld ausgewählt

        if self.current_blind == "small":
            current_label = self.label_small_blind
        else:
            current_label = self.label_big_blind

        current_text = current_label.get_text()

        if label_text == 'C':
            # Label auf '00' setzen
            current_label.set_text('00')
            current_label.get_style_context().remove_class("error")
            self.new_entry = True  # Neue Eingabe beginnen
        else:
            if self.new_entry or current_text == '00':
                # Wenn neue Eingabe oder aktueller Text '00' ist, überschreiben
                new_text = label_text
                self.new_entry = False  # Nach der ersten Eingabe auf False setzen
            else:
                # An bestehenden Wert anhängen
                new_text = current_text + label_text

            try:
                # Prüfen, ob die Eingabe zu groß ist
                new_value = int(new_text)
                if new_value > 9999:  # Maximalwert für Blinds festlegen
                    new_value = 9999
                    new_text = '9999'
                    self.new_entry = True
                    current_label.get_style_context().add_class("error")
                    GLib.timeout_add(500, self.remove_error_class, current_label)
                else:
                    current_label.get_style_context().remove_class("error")
            except ValueError:
                new_value = 0
                new_text = '00'
                self.new_entry = True

            # Aktualisiere den Wert mit führenden Nullen für einstellige Zahlen
            current_label.set_text(f"{int(new_text):02}")

            # Blind-Kopplung: Wenn Small Blind geändert wird, aktualisiere Big Blind
            if self.current_blind == "small":
                small_value = int(new_text)
                # Big Blind ist doppelter Small Blind
                self.label_big_blind.set_text(f"{small_value * 2:02}")

    def remove_error_class(self, label):
        """Entfernt die Fehlerklasse nach einer kurzen Zeit."""
        label.get_style_context().remove_class("error")
        return False

    def on_ok_button_click(self, button):
        # Werte in BlindData speichern
        self.confirm_values()

        # Fokus entfernen
        self.remove_blind_focus()

    def on_backspace_button_click(self, button):
        if self.current_blind is None:
            return  # Kein Feld ausgewählt

        if self.current_blind == "small":
            current_label = self.label_small_blind
        else:
            current_label = self.label_big_blind

        current_text = current_label.get_text()

        # Entferne das letzte Zeichen
        if len(current_text) > 1:
            new_text = current_text[:-1]
            if len(new_text) == 1:  # Wenn nur noch eine Ziffer übrig ist
                new_text = f"0{new_text}"  # Führende Null hinzufügen
        else:
            new_text = '00'
            self.new_entry = True  # Neue Eingabe beginnen

        current_label.set_text(new_text)

        # Blind-Kopplung: Wenn Small Blind geändert wird, aktualisiere Big Blind
        if self.current_blind == "small":
            try:
                small_value = int(new_text)
                self.label_big_blind.set_text(f"{small_value * 2:02}")
            except ValueError:
                pass

    def confirm_values(self):
        small_blind = self.label_small_blind.get_text()
        big_blind = self.label_big_blind.get_text()

        # Entferne führende Nullen für BlindData
        small_blind = str(int(small_blind))
        big_blind = str(int(big_blind))

        # Werte in BlindData speichern
        BlindData.small_blind = small_blind
        BlindData.big_blind = big_blind

        # Callback aufrufen, wenn vorhanden
        if self.confirm_callback:
            self.confirm_callback(small_blind, big_blind)

    def on_blind_click(self, widget, blind_type):
        # Setze das aktuelle Eingabefeld
        self.current_blind = blind_type
        # Setze die Flag für neue Eingabe
        self.new_entry = True
        # Visuelles Feedback hinzufügen
        self.highlight_selected_blind()

    def highlight_selected_blind(self):
        # CSS-Klassen zum Hervorheben hinzufügen oder entfernen, verwende time-selected statt blind-selected
        if self.current_blind == "small":
            self.label_small_blind.get_style_context().add_class("time-selected")
            self.label_big_blind.get_style_context().remove_class("time-selected")
        elif self.current_blind == "big":
            self.label_big_blind.get_style_context().add_class("time-selected")
            self.label_small_blind.get_style_context().remove_class("time-selected")

    def remove_blind_focus(self):
        """Entfernt den Fokus von allen Eingabefeldern."""
        # Option 1: Fokus auf ein nicht-interaktives Element setzen
        self.fixed.grab_focus()

        # Option 2: Deselektiere die aktuelle Auswahl
        self.current_blind = None

        # Ausgewählte Blindfelder visuell deselektieren
        self.label_small_blind.get_style_context().remove_class("time-selected")
        self.label_big_blind.get_style_context().remove_class("time-selected")

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
