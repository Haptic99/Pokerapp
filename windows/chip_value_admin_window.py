import gi
import os
import json
import asyncio
import websockets
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.chip_data import ChipData

class ChipValueAdminWindow(Gtk.Window):
    """
    Spezielles Fenster für die Administration der Chipwerte.
    Dies ist ein separates Fenster, das nur vom Admin-Panel aus geöffnet werden kann
    und erlaubt das Bearbeiten der CHF-Werte für jeden Chip.
    """
    def __init__(self, parent):
        super().__init__(title="Chipwerte Verwaltung (Admin)")
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.parent = parent

        # Variable for fullscreen mode
        self.is_fullscreen_mode = False

        # Check if parent window is in fullscreen mode
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        # Set background image
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        # Main container
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Create UI components
        self.create_ui()

        # Key bindings for fullscreen mode and escape
        self.connect("key-press-event", self.on_key_press)

    def create_ui(self):
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold' foreground='#CDAD00'>Chipwerte Verwaltung (Admin)</span>")
        title_label.get_style_context().add_class("dialog-text")
        self.fixed.put(title_label, 250, 20)

        # Grid for the chips
        chip_grid = Gtk.Grid()
        chip_grid.set_row_spacing(20)
        chip_grid.set_column_spacing(30)
        self.fixed.put(chip_grid, 80, 80)

        # List of chip images sorted by value (ascending)
        sorted_chips = sorted(ChipData.CHIPS.items(), key=lambda x: x[1])

        # Store widgets for CHF values to update them later
        self.chf_labels = {}

        # Fill the grid with chips, 4 per row
        column_count = 4
        for i, (chip_file, chip_value) in enumerate(sorted_chips):
            row = i // column_count
            col = i % column_count
            
            # Container for the chip and its values
            chip_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            chip_box.set_halign(Gtk.Align.CENTER)
            
            # Load and display chip image
            chip_path = os.path.join("Chips", chip_file)
            full_path = get_image_path(chip_path)
            
            if os.path.exists(full_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 100, 100, True)
                chip_image = Gtk.Image.new_from_pixbuf(pixbuf)
                chip_box.pack_start(chip_image, False, False, 0)
            
            # Display chip value
            value_label = Gtk.Label(label=f"{chip_value} Chips")
            value_label.get_style_context().add_class("green-text")
            chip_box.pack_start(value_label, False, False, 0)
            
            # Make CHF value editable
            chf_value = ChipData.chf_values.get(chip_file, 0.0)
            chf_label = Gtk.Label(label=f"CHF {chf_value:.2f}")
            chf_label.get_style_context().add_class("green-text")
            
            # Button with CHF value
            chf_button = Gtk.Button()
            chf_button.add(chf_label)
            chf_button.get_style_context().add_class("time-button")  # Reuse style
            chf_button.connect("clicked", self.on_chf_button_clicked, chip_file, chip_value)
            chip_box.pack_start(chf_button, False, False, 0)
            
            # Store the CHF label reference
            self.chf_labels[chip_file] = chf_label
            
            # Add to grid
            chip_grid.attach(chip_box, col, row, 1, 1)

        # "Close" button in bottom right
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def update_chf_labels(self):
        """Updates all CHF labels with current values."""
        for chip_file, label in self.chf_labels.items():
            chf_value = ChipData.chf_values.get(chip_file, 0.0)
            label.set_text(f"CHF {chf_value:.2f}")

    def on_chf_button_clicked(self, button, chip_file, chip_value):
        """Opens the overlay to edit the CHF value."""
        # Current CHF value of the chip
        current_chf = ChipData.chf_values.get(chip_file, 0.0)
        
        # Create the overlay
        edit_overlay = ChipValueEditOverlay(self, chip_file, chip_value, current_chf, self.on_chf_value_updated)
        edit_overlay.show_all()

    def on_chf_value_updated(self, chip_file, new_chf_value):
        """Callback for updating a CHF value."""
        # Set the new value and update all others
        ChipData.set_chf_value(chip_file, new_chf_value)
        
        # Update UI
        self.update_chf_labels()
        
        # Send update to server
        self.send_chip_values_to_server()

    def send_chip_values_to_server(self):
        """Sends updated chip values to the server."""
        # Find the event loop
        loop = None
        
        # Check different possible locations for the loop
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'loop'):
            loop = self.parent.poker_interface.loop
        elif hasattr(self.parent, 'loop'):
            loop = self.parent.loop
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'loop'):
            loop = self.parent.ws_client.loop
        
        if not loop:
            print("ERROR: Could not find asyncio loop!")
            return
            
        # Send update to server
        asyncio.run_coroutine_threadsafe(
            self.send_chip_values_update(),
            loop
        )

    async def send_chip_values_update(self):
        """Sends the updated chip values asynchronously to the server."""
        # Determine server address
        server_address = None
        
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
            server_address = self.parent.poker_interface.server_address
        elif hasattr(self.parent, 'server_address'):
            server_address = self.parent.server_address
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
            server_address = self.parent.ws_client.server_address
        
        if not server_address:
            print("ERROR: Could not find server address!")
            return
            
        server_ip, server_port = server_address
        uri = f"ws://{server_ip}:{server_port}"
        
        try:
            async with websockets.connect(uri) as websocket:
                message = {
                    "command": "update_chip_values",
                    "chip_values": ChipData.chf_values
                }
                await websocket.send(json.dumps(message))
                print(f"Chip values update sent: {message}")
        except Exception as e:
            print(f"Error sending chip values: {e}")

    def on_back_button_click(self, widget):
        """Closes the window."""
        self.close()

    def on_key_press(self, widget, event):
        """Key bindings for Escape and F11."""
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        """Toggles between fullscreen and window size."""
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True

class ChipValueEditOverlay(Gtk.Window):
    def __init__(self, parent, chip_file, chip_value, current_chf, update_callback):
        super().__init__(title="CHF Wert bearbeiten")
        self.set_default_size(400, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        
        self.chip_file = chip_file
        self.chip_value = chip_value
        self.current_chf = current_chf
        self.update_callback = update_callback
        
        # Flag for new input
        self.new_entry = True
        
        # Set background image
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        
        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)
        
        # Main container
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)
        
        # Create UI
        self.create_ui()
        
        # Key bindings for Escape
        self.connect("key-press-event", self.on_key_press)

    def create_ui(self):
        # Main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        vbox.set_margin_top(30)
        vbox.set_margin_bottom(30)
        vbox.set_margin_start(30)
        vbox.set_margin_end(30)
        self.fixed.put(vbox, 60, 30)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<span size='large' weight='bold' foreground='#CDAD00'>CHF Wert festlegen</span>")
        vbox.pack_start(title_label, False, False, 0)
        
        # Chip image
        chip_path = os.path.join("Chips", self.chip_file)
        full_path = get_image_path(chip_path)
        
        if os.path.exists(full_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 120, 120, True)
            chip_image = Gtk.Image.new_from_pixbuf(pixbuf)
            vbox.pack_start(chip_image, False, False, 0)
        
        # Display chip value
        value_label = Gtk.Label(label=f"Chipwert: {self.chip_value}")
        value_label.get_style_context().add_class("green-text")
        vbox.pack_start(value_label, False, False, 0)
        
        # CHF value input field
        chf_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        chf_label = Gtk.Label(label="CHF:")
        chf_label.get_style_context().add_class("green-text")
        chf_box.pack_start(chf_label, False, False, 0)
        
        self.chf_entry_label = Gtk.Label(label=f"{self.current_chf:.2f}")
        self.chf_entry_label.get_style_context().add_class("time-value")
        self.chf_entry = Gtk.Button()
        self.chf_entry.add(self.chf_entry_label)
        self.chf_entry.get_style_context().add_class("time-button")
        chf_box.pack_start(self.chf_entry, True, True, 0)
        
        vbox.pack_start(chf_box, False, False, 0)
        
        # Create numpad
        self.create_numpad(vbox)
        
        # Buttons: Cancel and OK
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        button_box.set_halign(Gtk.Align.CENTER)
        
        cancel_button = Gtk.Button(label="Abbrechen")
        cancel_button.set_size_request(120, 40)
        cancel_button.connect("clicked", self.on_cancel_clicked)
        cancel_button.get_style_context().add_class("button-custom")
        button_box.pack_start(cancel_button, False, False, 0)
        
        ok_button = Gtk.Button(label="OK")
        ok_button.set_size_request(120, 40)
        ok_button.connect("clicked", self.on_ok_clicked)
        ok_button.get_style_context().add_class("button-custom")
        button_box.pack_start(ok_button, False, False, 0)
        
        vbox.pack_start(button_box, False, False, 0)

    def create_numpad(self, container):
        # Grid for numpad
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        
        # Numpad buttons
        buttons = [
            ('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
            ('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
            ('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
            ('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
            ('.', 0, 4, 3)  # Decimal point over 3 columns
        ]
        
        self.has_decimal = False  # Flag to check if decimal point is already entered
        
        for item in buttons:
            label = item[0]
            x = item[1]
            y = item[2]
            width = 1
            if len(item) > 3:
                width = item[3]
                
            button = Gtk.Button(label=label)
            button.get_style_context().add_class("numpad-button")
            button.set_size_request(70, 50)
            
            if label == 'C':
                button.connect("clicked", self.on_clear_clicked)
            elif label == '←':
                button.connect("clicked", self.on_backspace_clicked)
            elif label == '.':
                button.connect("clicked", self.on_decimal_clicked)
            else:
                button.connect("clicked", self.on_number_clicked)
                
            grid.attach(button, x, y, width, 1)
            
        container.pack_start(grid, False, False, 0)

    def on_number_clicked(self, button):
        digit = button.get_label()
        current_text = self.chf_entry_label.get_text()
        
        if self.new_entry:
            # If new input, overwrite text
            if digit == '0':
                # For 0 as first digit, set "0."
                new_text = "0."
                self.has_decimal = True
            else:
                new_text = digit
            self.new_entry = False
        else:
            # For existing input, append digit
            new_text = current_text + digit
            
        # Update label
        self.chf_entry_label.set_text(new_text)

    def on_decimal_clicked(self, button):
        if self.has_decimal:
            return  # Decimal point already exists
            
        current_text = self.chf_entry_label.get_text()
        
        if self.new_entry:
            # Start new input with decimal
            new_text = "0."
            self.new_entry = False
        else:
            # Append decimal to existing input
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
            # If only one digit left, reset to 0
            self.chf_entry_label.set_text("0.00")
            self.new_entry = True
            self.has_decimal = False
        else:
            # Remove last character
            if current_text[-1] == '.':
                self.has_decimal = False
            new_text = current_text[:-1]
            self.chf_entry_label.set_text(new_text)

    def on_cancel_clicked(self, button):
        self.close()

    def on_ok_clicked(self, button):
        try:
            # Parse and validate CHF value
            new_chf_value = float(self.chf_entry_label.get_text())
            if new_chf_value <= 0:
                self.show_error_dialog("Invalid value", "CHF value must be greater than 0.")
                return
                
            # Call callback with new value
            self.update_callback(self.chip_file, new_chf_value)
            self.close()
        except ValueError:
            self.show_error_dialog("Input error", "Please enter a valid number.")

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
        """Key binding for Escape."""
        if event.keyval == Gdk.KEY_Escape:
            self.close()
