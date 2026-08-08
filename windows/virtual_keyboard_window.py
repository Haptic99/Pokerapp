from gi.repository import Gtk, Gdk, GLib
from utils.helpers import set_background_image
from utils.resources import get_image_path
import gi
gi.require_version('Gtk', '3.0')

class VirtualKeyboardWindow(Gtk.Window):
    def __init__(self, parent, initial_text, confirm_callback):
        super().__init__(title="Tastatur")
        self.parent = parent
        self.confirm_callback = confirm_callback
        self.set_default_size(750, 400)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_decorated(False) # No title bar to make it look embedded
        
        self.is_fullscreen_mode = False
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True
        
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        
        set_background_image(self.overlay, get_image_path("background_start.jpg"))
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_left(20)
        vbox.set_margin_right(20)
        
        self.overlay.add_overlay(vbox)
        
        # Text display container with glass panel
        text_frame = Gtk.Frame()
        text_frame.get_style_context().add_class("glass-panel")
        
        self.entry_label = Gtk.Label(label=initial_text)
        self.entry_label.get_style_context().add_class("time-value")
        self.entry_label.set_margin_top(15)
        self.entry_label.set_margin_bottom(15)
        
        if not initial_text:
             self.entry_label.set_text(" ") # Prevent collapsing if empty
        
        text_frame.add(self.entry_label)
        vbox.pack_start(text_frame, False, False, 10)
        
        # Keyboard Grid
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(grid, True, True, 0)
        
        rows = [
            ['Q', 'W', 'E', 'R', 'T', 'Z', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Y', 'X', 'C', 'V', 'B', 'N', 'M']
        ]
        
        # Row 1
        for i, key in enumerate(rows[0]):
            btn = self.create_key(key)
            grid.attach(btn, i*2, 0, 2, 1)
            
        # Row 2 (offset)
        for i, key in enumerate(rows[1]):
            btn = self.create_key(key)
            grid.attach(btn, i*2 + 1, 1, 2, 1)
            
        # Row 3 (offset more)
        for i, key in enumerate(rows[2]):
            btn = self.create_key(key)
            grid.attach(btn, i*2 + 2, 2, 2, 1)
            
        # Bottom Row: Backspace, Space, Enter, Cancel
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.set_halign(Gtk.Align.CENTER)
        bottom_box.set_margin_top(15)
        vbox.pack_start(bottom_box, False, False, 0)
        
        btn_cancel = Gtk.Button(label="Abbrechen")
        btn_cancel.set_size_request(120, 50)
        btn_cancel.get_style_context().add_class("keyboard-button")
        btn_cancel.get_style_context().add_class("keyboard-button-special")
        btn_cancel.connect("clicked", lambda _: self.close())
        bottom_box.pack_start(btn_cancel, False, False, 0)
        
        btn_space = Gtk.Button(label="Leerzeichen")
        btn_space.set_size_request(250, 50)
        btn_space.get_style_context().add_class("keyboard-button")
        btn_space.connect("clicked", self.on_key_clicked, " ")
        bottom_box.pack_start(btn_space, False, False, 0)
        
        btn_backspace = Gtk.Button(label="⌫")
        btn_backspace.set_size_request(80, 50)
        btn_backspace.get_style_context().add_class("keyboard-button")
        btn_backspace.get_style_context().add_class("keyboard-button-special")
        btn_backspace.connect("clicked", self.on_backspace)
        bottom_box.pack_start(btn_backspace, False, False, 0)
        
        btn_enter = Gtk.Button(label="Fertig")
        btn_enter.set_size_request(120, 50)
        btn_enter.get_style_context().add_class("keyboard-button")
        btn_enter.get_style_context().add_class("numpad-button-ok")
        btn_enter.connect("clicked", self.on_enter)
        bottom_box.pack_start(btn_enter, False, False, 0)

    def create_key(self, char):
        btn = Gtk.Button(label=char)
        btn.set_size_request(60, 60)
        btn.get_style_context().add_class("keyboard-button")
        btn.connect("clicked", self.on_key_clicked, char)
        return btn
        
    def on_key_clicked(self, widget, char):
        current = self.entry_label.get_text()
        if current == " ":
             current = ""
        if len(current) < 20: # Max length
            self.entry_label.set_text(current + char)
            
    def on_backspace(self, widget):
        current = self.entry_label.get_text()
        if current == " ":
             return
        if len(current) > 0:
            new_text = current[:-1]
            self.entry_label.set_text(new_text if new_text else " ")
            
    def on_enter(self, widget):
        final_text = self.entry_label.get_text()
        if final_text == " ":
             final_text = ""
        self.confirm_callback(final_text)
        self.close()
