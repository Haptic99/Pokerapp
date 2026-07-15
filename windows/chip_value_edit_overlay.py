import gi
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path

class ChipValueEditOverlay(Gtk.Window):
    def __init__(self, parent, chip_file, chip_value, current_chf, update_callback):
        super().__init__(title="CHF Wert bearbeiten")
        self.set_default_size(800, 480)  # Vollständige Fenstergröße wie bei anderen Fenstern
        self.set_transient_for(parent)
        self.set_modal(True)
        
        self.chip_file = chip_file
        self.chip_value = chip_value
        self.current_chf = current_chf
        self.update_callback = update_callback
        
        # Flag für neue Eingabe
        self.new_entry = True
        self.has_decimal = False  # Flag um zu prüfen, ob bereits ein Dezimalpunkt eingegeben wurde
        
        # Variable für Vollbildmodus initialisieren
        self.is_fullscreen_mode = False

        # Überprüfen, ob das Elternfenster im Vollbildmodus ist
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True
        
        # Set background image (konsistent mit anderen Fenstern)
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        
        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)
        
        # Main container
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)
        
        # Create UI (in separaten Methoden für bessere Strukturierung)
        self.create_ui_components()
        
        # Key bindings für Escape und F11
        self.connect("key-press-event", self.on_key_press)

    def create_ui_components(self):
        # Titel oben in der Mitte (konsistent mit anderen Fenstern)
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold' foreground='#CDAD00'>CHF Wert festlegen</span>")
        title_label.get_style_context().add_class("dialog-text")
        self.fixed.put(title_label, 300, 20)
        
        # Chipwert links anzeigen (ähnlich wie Timer in anderen Fenstern)
        self.create_chip_info_area()
        
        # Numpad rechts in der Mitte (konsistent mit anderen Fenstern)
        self.create_numpad()
        
        # "Schließen" Button unten rechts (konsistent mit anderen Fenstern)
        self.create_back_button()

    def create_chip_info_area(self):
        # Container für die Chip-Informationen auf der linken Seite
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_homogeneous(False)
        self.fixed.put(vbox, 130, 100)  # Gleiche Position wie in anderen Fenstern
        
        # Chip-Bild anzeigen
        chip_path = os.path.join("Chips", self.chip_file)
        full_path = get_image_path(chip_path)
        
        if os.path.exists(full_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 120, 120, True)
            chip_image = Gtk.Image.new_from_pixbuf(pixbuf)
            vbox.pack_start(chip_image, False, False, 5)
        
        # Chip-Wert (in Chips) anzeigen
        value_label = Gtk.Label(label=f"Chipwert: {self.chip_value}")
        value_label.get_style_context().add_class("green-text")
        vbox.pack_start(value_label, False, False, 5)
        
        # CHF Wert Titel
        label_chf_title = Gtk.Label(label="CHF Wert")
        label_chf_title.get_style_context().add_class("time-title")  # Konsistentes Styling
        vbox.pack_start(label_chf_title, False, False, 5)
        
        # CHF Wert Eingabefeld (ähnlich wie Timer-Eingabe)
        chf_display = "0.00" if self.current_chf == 0.0 else f"{self.current_chf:.2f}"
        self.chf_entry_label = Gtk.Label(label=chf_display)
        self.chf_entry_label.get_style_context().add_class("time-value")  # Konsistentes Styling
        
        # Button um das Label, um Klicks zu erfassen
        self.chf_entry = Gtk.Button()
        self.chf_entry.add(self.chf_entry_label)
        self.chf_entry.get_style_context().add_class("time-button")  # Konsistentes Styling
        self.chf_entry.connect("clicked", self.on_chf_entry_clicked)
        vbox.pack_start(self.chf_entry, False, False, 5)

    def create_numpad(self):
        # NumPad auf der rechten Seite (konsistent mit anderen Fenstern)
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        self.fixed.put(grid, 400, 100)  # Position wie in anderen Fenstern
        
        # Numpad buttons
        buttons = [
            ('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
            ('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
            ('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
            ('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
            ('.', 0, 4), ('Ok', 1, 4, 2)  # OK-Button über 2 Spalten
        ]
        
        for item in buttons:
            label = item[0]
            x = item[1]
            y = item[2]
            width = 1
            if len(item) > 3:
                width = item[3]
                
            button = Gtk.Button(label=label)
            button.get_style_context().add_class("numpad-button")
            button.set_size_request(70 * width + (width-1) * 10, 60)  # Größe anpassen
            
            if label == 'C':
                button.connect("clicked", self.on_clear_clicked)
            elif label == '←':
                button.connect("clicked", self.on_backspace_clicked)
            elif label == '.':
                button.connect("clicked", self.on_decimal_clicked)
            elif label == 'Ok':
                button.connect("clicked", self.on_ok_clicked)
                button.get_style_context().add_class("numpad-button-ok")
            else:
                button.connect("clicked", self.on_number_clicked)
                
            grid.attach(button, x, y, width, 1)

    def create_back_button(self):
        # "Schließen" Button unten rechts (konsistent mit anderen Fenstern)
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_cancel_clicked)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def on_chf_entry_clicked(self, widget):
        # Visuelles Feedback, dass das Feld aktiv ist
        self.chf_entry_label.get_style_context().add_class("time-selected")
        self.new_entry = True

    def on_number_clicked(self, button):
        digit = button.get_label()
        current_text = self.chf_entry_label.get_text()
        
        if self.new_entry:
            # Bei neuer Eingabe, überschreibe Text
            if digit == '0':
                # Für 0 als erste Ziffer, setze "0."
                new_text = "0."
                self.has_decimal = True
            else:
                new_text = digit
            self.new_entry = False
        else:
            # Bei bestehender Eingabe, füge Ziffer hinzu
            new_text = current_text + digit
            
        # Update label
        self.chf_entry_label.set_text(new_text)

    def on_decimal_clicked(self, button):
        if self.has_decimal:
            return  # Dezimalpunkt existiert bereits
            
        current_text = self.chf_entry_label.get_text()
        
        if self.new_entry:
            # Beginne neue Eingabe mit Dezimalpunkt
            new_text = "0."
            self.new_entry = False
        else:
            # Füge Dezimalpunkt an bestehende Eingabe
            new_text = current_text + "."
            
        self.has_decimal = True
        self.chf_entry_label.set_text(new_text)

    def on_clear_clicked(self, button):
        self.chf_entry_label.set_text("0.00")
        self.new_entry = True
        self.has_decimal = False

    def on_backspace_clicked(self, button):
        current_text = self.chf_entry_label.get_text()
        
        if len(current_text) <= 1:
            # Wenn nur eine Ziffer übrig, setze auf 0
            self.chf_entry_label.set_text("0.00")
            self.new_entry = True
            self.has_decimal = False
        else:
            # Entferne letztes Zeichen
            if current_text[-1] == '.':
                self.has_decimal = False
            new_text = current_text[:-1]
            self.chf_entry_label.set_text(new_text)

    def on_cancel_clicked(self, button):
        self.close()

    def on_ok_clicked(self, button):
        try:
            # Parse und validiere CHF-Wert
            new_chf_value = float(self.chf_entry_label.get_text())
            if new_chf_value < 0:
                self.show_error_dialog("Ungültiger Wert", "CHF-Wert muss größer oder gleich 0 sein.")
                return
                
            # Rufe Callback mit neuem Wert auf
            self.update_callback(self.chip_file, new_chf_value)
            self.close()
        except ValueError:
            self.show_error_dialog("Eingabefehler", "Bitte geben Sie eine gültige Zahl ein.")

    def show_error_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

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
