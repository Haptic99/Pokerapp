import os
import json
import asyncio
import websockets
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.chip_data import ChipData
from utils.websocket_utils import WebSocketClient
from utils.display_utils import update_client_display

class ChipValueWindow(Gtk.Window):
    """Fenster zur Anzeige und Bearbeitung der Chipwerte.
    Kann sowohl von normalen Clients (is_admin=False) als auch
    vom Admin-Panel (is_admin=True) aufgerufen werden."""

    def __init__(self, parent, is_admin=False):
        title = "Chipwerte Verwaltung (Admin)" if is_admin else "Chipwerte Übersicht"
        super().__init__(title=title)

        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.parent = parent
        self.is_admin = is_admin

        self.is_fullscreen_mode = False
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        self.create_ui()

        self.connect("key-press-event", self.on_key_press)
        self.ws_client = WebSocketClient(update_display_callback=self.update_display)
        self.ws_client.start_async_loop()

        self.update_timer_active = True
        self.update_timer_id = GLib.timeout_add_seconds(1, self.periodic_update)
        self.connect("destroy", self.on_window_destroy)
        
        self.edit_container = None
        self.current_edit_chip = None
        self.new_entry = True
        self.has_decimal = False

    def create_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_halign(Gtk.Align.CENTER)
        main_box.set_valign(Gtk.Align.CENTER)
        
        # Glass Panel for the whole UI
        glass_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        glass_panel.set_margin_top(5)
        glass_panel.set_margin_bottom(5)
        glass_panel.set_margin_left(20)
        glass_panel.set_margin_right(20)
        glass_panel.get_style_context().add_class("glass-panel")
        
        # Title
        title_text = "Chipwerte Verwaltung (Admin)" if self.is_admin else "Chipwerte Übersicht"
        title_label = Gtk.Label(label=title_text)
        title_label.get_style_context().add_class("time-title")
        glass_panel.pack_start(title_label, False, False, 5)
        
        # Container for the two rows
        rows_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_row.set_halign(Gtk.Align.CENTER)
        
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_row.set_halign(Gtk.Align.CENTER)
        
        self.chf_labels = {}
        sorted_chips = sorted(ChipData.CHIPS.items(), key=lambda x: x[1])
        
        for index, (chip_file, chip_value) in enumerate(sorted_chips):
            # Chip Card
            chip_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            chip_card.get_style_context().add_class("chip-card")
            chip_card.set_halign(Gtk.Align.CENTER)
            chip_card.set_size_request(160, -1)  # Erhöht auf 160px, da der 10000er Button sonst das Layout sprengt
            
            # Image
            chip_path = os.path.join("Chips", chip_file)
            full_path = get_image_path(chip_path)
            if os.path.exists(full_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 50, 50, True)
                chip_image = Gtk.Image.new_from_pixbuf(pixbuf)
                chip_card.pack_start(chip_image, False, False, 0)
                
            # Chip Value (in chips)
            val_label = Gtk.Label(label=f"{chip_value} Chips")
            val_label.get_style_context().add_class("chip-value-text")
            chip_card.pack_start(val_label, False, False, 0)
            
            # CHF Value
            chf_value = ChipData.chf_values.get(chip_file, 0.0)
            chf_display = "-" if chf_value == 0.0 else f"CHF {chf_value:.2f}"
            chf_label = Gtk.Label(label=chf_display)
            chf_label.get_style_context().add_class("chip-chf-text")
            self.chf_labels[chip_file] = chf_label
            
            if self.is_admin:
                btn_edit = Gtk.Button()
                btn_edit.add(chf_label)
                btn_edit.get_style_context().add_class("button-custom")
                btn_edit.connect("clicked", self.on_chf_button_clicked, chip_file, chip_value)
                chip_card.pack_start(btn_edit, False, False, 0)
            else:
                chip_card.pack_start(chf_label, False, False, 0)
                
            # 4 Chips in der ersten Reihe, 3 in der zweiten
            if index < 4:
                top_row.pack_start(chip_card, False, False, 0)
            else:
                bottom_row.pack_start(chip_card, False, False, 0)
                
        rows_container.pack_start(top_row, False, False, 0)
        rows_container.pack_start(bottom_row, False, False, 0)
        glass_panel.pack_start(rows_container, True, True, 0)
        
        # Status Label (nur ganz klein)
        self.status_label = Gtk.Label(label="")
        glass_panel.pack_start(self.status_label, False, False, 0)
        
        # Close button
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(120, 35)
        back_button.set_halign(Gtk.Align.CENTER)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        glass_panel.pack_start(back_button, False, False, 5)
        
        main_box.pack_start(glass_panel, False, False, 0)
        self.overlay.add_overlay(main_box)
        self.overlay.show_all()

    def update_chf_labels(self):
        for chip_file, label in self.chf_labels.items():
            chf_value = ChipData.chf_values.get(chip_file, 0.0)
            chf_display = "-" if chf_value == 0.0 else f"CHF {chf_value:.2f}"
            label.set_text(chf_display)

    def on_chf_button_clicked(self, button, chip_file, chip_value):
        if not self.is_admin:
            return

        self.current_edit_chip = chip_file
        current_chf = ChipData.chf_values.get(chip_file, 0.0)
        self.new_entry = True
        self.has_decimal = False

        self.edit_container = Gtk.EventBox()
        self.edit_container.set_name("edit_container")
        self.edit_container.set_halign(Gtk.Align.FILL)
        self.edit_container.set_valign(Gtk.Align.FILL)
        self.edit_container.get_style_context().add_class("dimmed-background")

        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)

        panel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        panel.set_margin_top(40)
        panel.set_margin_bottom(40)
        panel.set_margin_left(40)
        panel.set_margin_right(40)
        panel.get_style_context().add_class("glass-panel")

        # Left Side: Info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        info_box.set_valign(Gtk.Align.CENTER)
        
        title_lbl = Gtk.Label(label="Wert festlegen")
        title_lbl.get_style_context().add_class("time-title")
        info_box.pack_start(title_lbl, False, False, 0)

        chip_path = os.path.join("Chips", chip_file)
        full_path = get_image_path(chip_path)
        if os.path.exists(full_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 100, 100, True)
            chip_image = Gtk.Image.new_from_pixbuf(pixbuf)
            info_box.pack_start(chip_image, False, False, 10)

        val_label = Gtk.Label(label=f"Chipwert: {chip_value}")
        val_label.get_style_context().add_class("chip-value-text")
        info_box.pack_start(val_label, False, False, 0)

        chf_display = "0.00" if current_chf == 0.0 else f"{current_chf:.2f}"
        self.chf_entry_label = Gtk.Label(label=chf_display)
        self.chf_entry_label.get_style_context().add_class("time-value")
        
        chf_entry_btn = Gtk.Button()
        chf_entry_btn.add(self.chf_entry_label)
        chf_entry_btn.get_style_context().add_class("time-button")
        chf_entry_btn.connect("clicked", self.on_chf_entry_clicked)
        info_box.pack_start(chf_entry_btn, False, False, 10)

        panel.pack_start(info_box, False, False, 0)

        # Right Side: Numpad
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_valign(Gtk.Align.CENTER)

        buttons = [
            ('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
            ('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
            ('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
            ('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
            ('.', 0, 4), ('Abbrechen', 1, 4), ('Ok', 2, 4)
        ]

        for item in buttons:
            label = item[0]
            x, y = item[1], item[2]
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("numpad-button")
            btn.set_size_request(80, 60)

            if label == 'C':
                btn.connect("clicked", self.on_clear_clicked)
            elif label == '←':
                btn.connect("clicked", self.on_backspace_clicked)
            elif label == '.':
                btn.connect("clicked", self.on_decimal_clicked)
            elif label == 'Ok':
                btn.connect("clicked", self.on_ok_clicked)
                btn.get_style_context().add_class("numpad-button-ok")
            elif label == 'Abbrechen':
                btn.connect("clicked", self.on_cancel_edit_clicked)
            else:
                btn.connect("clicked", self.on_number_clicked)

            grid.attach(btn, x, y, 1, 1)

        panel.pack_start(grid, False, False, 20)
        center_box.pack_start(panel, False, False, 0)
        self.edit_container.add(center_box)

        self.overlay.add_overlay(self.edit_container)
        self.edit_container.show_all()

    def on_chf_entry_clicked(self, widget):
        self.chf_entry_label.get_style_context().add_class("time-selected")
        self.new_entry = True

    def on_number_clicked(self, button):
        digit = button.get_label()
        current_text = self.chf_entry_label.get_text()
        if self.new_entry:
            if digit == '0':
                new_text = "0."
                self.has_decimal = True
            else:
                new_text = digit
            self.new_entry = False
        else:
            new_text = current_text + digit
        self.chf_entry_label.set_text(new_text)

    def on_decimal_clicked(self, button):
        if self.has_decimal:
            return
        current_text = self.chf_entry_label.get_text()
        if self.new_entry:
            new_text = "0."
            self.new_entry = False
        else:
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
            self.chf_entry_label.set_text("0.00")
            self.new_entry = True
            self.has_decimal = False
        else:
            if current_text[-1] == '.':
                self.has_decimal = False
            new_text = current_text[:-1]
            self.chf_entry_label.set_text(new_text)

    def on_cancel_edit_clicked(self, button):
        if self.edit_container:
            self.edit_container.destroy()
            self.edit_container = None

    def on_ok_clicked(self, button):
        try:
            new_chf_value = float(self.chf_entry_label.get_text())
            if new_chf_value < 0:
                self.status_label.set_text("Fehler: Wert darf nicht negativ sein.")
                return

            ChipData.set_chf_value(self.current_edit_chip, new_chf_value)
            self.update_chf_labels()
            self.send_chip_values_to_server()
            
            if self.edit_container:
                self.edit_container.destroy()
                self.edit_container = None
        except ValueError:
            self.status_label.set_text("Fehler: Ungültige Zahl.")

    def send_chip_values_to_server(self):
        loop = None
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'loop'):
            loop = self.parent.poker_interface.loop
        elif hasattr(self.parent, 'loop'):
            loop = self.parent.loop
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'loop'):
            loop = self.parent.ws_client.loop

        if not loop:
            print("FEHLER: Konnte asyncio-Loop nicht finden!")
            self.status_label.set_text("Fehler: Konnte keine Verbindung zum Server herstellen")
            return

        asyncio.run_coroutine_threadsafe(self.send_chip_values_update(), loop)

    async def send_chip_values_update(self):
        server_address = None
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
            server_address = self.parent.poker_interface.server_address
        elif hasattr(self.parent, 'server_address'):
            server_address = self.parent.server_address
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
            server_address = self.parent.ws_client.server_address

        if not server_address:
            print("FEHLER: Konnte Server-Adresse nicht finden!")
            GLib.idle_add(lambda: self.status_label.set_text("Fehler: Keine Server-Adresse gefunden"))
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
                GLib.idle_add(lambda: self.status_label.set_text(f"Gesendet: Chip-Werte an {server_ip}:{server_port}"))
        except Exception as e:
            error_msg = f"Fehler beim Senden der Chip-Werte: {e}"
            print(error_msg)
            GLib.idle_add(lambda: self.status_label.set_text(error_msg))

    def periodic_update(self):
        if not self.update_timer_active:
            return False
        self.update_chf_labels()
        return True

    def update_display(self, data):
        update_client_display(self, data)

    def on_window_destroy(self, widget):
        self.update_timer_active = False
        if hasattr(self, "update_timer_id") and self.update_timer_id:
            GLib.source_remove(self.update_timer_id)
            self.update_timer_id = None

    def on_back_button_click(self, widget):
        self.close()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.edit_container:
                self.edit_container.destroy()
                self.edit_container = None
            elif self.is_fullscreen_mode:
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
