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
        self.is_fullscreen_mode = False
        
        self.parent_poker_interface = parent

        if parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        self.confirm_callback = confirm_callback
        
        # State - initialisiere mit dem aktuell aktiven Small Blind
        current_sb = BlindData.small_blind if BlindData.small_blind else "5"
        try:
            float(current_sb)
            self.current_start_blind = str(current_sb)
        except ValueError:
            self.current_start_blind = "5"
            
        self.strategies = {
            "Standard-Turnier": self.generate_standard_schedule,
            "Immer Verdoppeln": self.generate_doubling_schedule
        }
        self.current_strategy = "Standard-Turnier"
        self.generated_schedule = []

        self.create_left_panel()
        self.create_right_panel()

        self.connect("key-press-event", self.on_key_press)
        
        # Initiale Generierung
        self.regenerate_schedule()

    def create_left_panel(self):
        # Strategie Auswahl
        lbl_strategy = Gtk.Label(label="Strategie:")
        lbl_strategy.get_style_context().add_class("time-title")
        self.fixed.put(lbl_strategy, 30, 20)

        self.combo_strategy = Gtk.ComboBoxText()
        for strategy in self.strategies.keys():
            self.combo_strategy.append_text(strategy)
        self.combo_strategy.set_active(0)
        self.combo_strategy.connect("changed", self.on_strategy_changed)
        self.combo_strategy.set_size_request(220, 40)
        # Dropdown im Button-Look stylen
        self.combo_strategy.get_style_context().add_class("button-custom")
        self.fixed.put(self.combo_strategy, 30, 50)

        # Start Blind Eingabe
        lbl_start = Gtk.Label(label="Start Small Blind:")
        lbl_start.get_style_context().add_class("time-title")
        self.fixed.put(lbl_start, 30, 110)

        self.label_start_blind = Gtk.Label(label=self.current_start_blind)
        self.label_start_blind.get_style_context().add_class("time-value")
        self.label_start_blind.get_style_context().add_class("time-selected")
        
        btn_start_blind = Gtk.Button()
        btn_start_blind.add(self.label_start_blind)
        btn_start_blind.get_style_context().add_class("time-button")
        btn_start_blind.set_size_request(220, 50)
        self.fixed.put(btn_start_blind, 30, 140)

        # Numpad (kleiner)
        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        self.fixed.put(grid, 30, 210)

        buttons = [
            ('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
            ('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
            ('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
            ('.', 0, 3), ('0', 1, 3), ('←', 2, 3),
            ('C', 0, 4, 3) # Clear-Button über die gesamte Breite
        ]

        for item in buttons:
            if len(item) == 4:
                label, x, y, width = item
            else:
                label, x, y = item
                width = 1
                
            button = Gtk.Button(label=label)
            # Berechne Breite basierend auf Spalten-Span
            btn_width = 70 * width + 5 * (width - 1)
            button.set_size_request(btn_width, 50)
            button.get_style_context().add_class("numpad-button")
            
            if label == 'C':
                button.connect("clicked", self.on_numpad_clear)
            elif label == '←':
                button.connect("clicked", self.on_numpad_backspace)
            elif label == '.':
                button.connect("clicked", self.on_numpad_dot)
            else:
                button.connect("clicked", self.on_numpad_number, label)
                
            grid.attach(button, x, y, width, 1)

    def create_right_panel(self):
        # Vorschau-Titel
        lbl_preview = Gtk.Label(label="Turnier-Fahrplan:")
        lbl_preview.get_style_context().add_class("time-title")
        self.fixed.put(lbl_preview, 300, 20)

        # TreeView für Tabelle
        self.liststore = Gtk.ListStore(str, str, str) # Level, SB, BB
        self.treeview = Gtk.TreeView(model=self.liststore)
        
        for i, column_title in enumerate(["Runde", "Small Blind", "Big Blind"]):
            renderer = Gtk.CellRendererText()
            renderer.set_property("font", "Arial 16")
            renderer.set_property("foreground", "white")
            
            # Die Beträge (Index 1 und 2) rechtsbündig ausrichten
            if i > 0:
                renderer.set_property("xalign", 1.0)
                
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            # Damit die Ausrichtung auch im Header optisch passt, wenn möglich
            if i > 0:
                column.set_alignment(1.0)
                
            column.set_min_width(140)
            self.treeview.append_column(column)

        # Touch/Drag-Scrolling manuell implementieren
        self.treeview.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                                 Gdk.EventMask.BUTTON_RELEASE_MASK |
                                 Gdk.EventMask.POINTER_MOTION_MASK)
        self.treeview.connect("button-press-event", self.on_treeview_button_press)
        self.treeview.connect("button-release-event", self.on_treeview_button_release)
        self.treeview.connect("motion-notify-event", self.on_treeview_motion)
        
        self.drag_start_y = None
        self.drag_start_vadj = None

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_size_request(460, 330)
        # Versteckt den Scrollbalken komplett (EXTERNAL bedeutet: wir steuern es manuell)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        self.scroll.add(self.treeview)
        
        # Dunkler Hintergrund für die Liste im Glas-Look
        self.scroll.get_style_context().add_class("glass-panel") 
        self.fixed.put(self.scroll, 300, 50)

        # Buttons
        btn_apply = Gtk.Button(label="Plan übernehmen")
        btn_apply.set_size_request(200, 45)
        btn_apply.connect("clicked", self.on_apply_clicked)
        btn_apply.get_style_context().add_class("button-custom")
        self.fixed.put(btn_apply, 300, 400)

        btn_close = Gtk.Button(label="Schliessen")
        btn_close.set_size_request(150, 45)
        btn_close.connect("clicked", lambda w: self.close())
        btn_close.get_style_context().add_class("button-custom")
        self.fixed.put(btn_close, 610, 400)

    # --- Logic ---

    def on_treeview_button_press(self, widget, event):
        if event.button == 1:  # Linker Mausklick / Touch
            self.drag_start_y = event.y_root
            self.drag_start_vadj = self.scroll.get_vadjustment().get_value()
        return False

    def on_treeview_button_release(self, widget, event):
        if event.button == 1:
            self.drag_start_y = None
        return False

    def on_treeview_motion(self, widget, event):
        if self.drag_start_y is not None:
            # Distanz berechnen (wie weit der Finger gewischt wurde)
            dy = self.drag_start_y - event.y_root
            vadj = self.scroll.get_vadjustment()
            # Scrollbalken-Wert anpassen (Tabelle nach oben/unten verschieben)
            vadj.set_value(self.drag_start_vadj + dy)
            return True # Event konsumieren, damit beim Wischen keine Zeilen markiert werden
        return False

    def on_strategy_changed(self, combo):
        self.current_strategy = combo.get_active_text()
        self.regenerate_schedule()

    def on_numpad_number(self, button, digit):
        new_value_str = ""
        if self.current_start_blind == "0":
            new_value_str = digit
        else:
            new_value_str = self.current_start_blind + digit
            
        # Überprüfen auf maximal 2 Dezimalstellen
        if "." in new_value_str:
            parts = new_value_str.split(".")
            if len(parts) > 1 and len(parts[1]) > 2:
                return # Ignoriere die Eingabe, da schon 2 Dezimalstellen
                
        # Überprüfen auf Maximalwert 100'000
        try:
            val = float(new_value_str)
            if val > 100000.0:
                return # Ignoriere die Eingabe, da zu hoch
        except ValueError:
            return
            
        self.current_start_blind = new_value_str
        self.update_start_blind_display()
        self.regenerate_schedule()

    def on_numpad_dot(self, button):
        if "." not in self.current_start_blind:
            if not self.current_start_blind:
                self.current_start_blind = "0."
            else:
                self.current_start_blind += "."
            self.update_start_blind_display()
            self.regenerate_schedule()

    def on_numpad_clear(self, button):
        self.current_start_blind = ""
        self.update_start_blind_display()
        self.regenerate_schedule()

    def on_numpad_backspace(self, button):
        if len(self.current_start_blind) > 1:
            self.current_start_blind = self.current_start_blind[:-1]
        else:
            self.current_start_blind = ""
        self.update_start_blind_display()
        self.regenerate_schedule()

    def update_start_blind_display(self):
        # Zeige den String exakt so an, wie er getippt wurde (verhindert 00 und behält den Punkt)
        self.label_start_blind.set_text(self.current_start_blind)

    # --- Generators ---

    def _format_blind(self, value):
        """Formatiert einen Blind-Wert sauber (entfernt unnötige Nachkommastellen)."""
        # Auf 2 Nachkommastellen runden
        val = round(float(value), 2)
        if val.is_integer():
            return str(int(val))
        return str(val)

    def regenerate_schedule(self):
        try:
            start_sb = float(self.current_start_blind)
        except ValueError:
            start_sb = 0.0
            
        if start_sb == 0.0:
            self.generated_schedule = []
        else:
            generator = self.strategies.get(self.current_strategy, self.generate_standard_schedule)
            self.generated_schedule = generator(start_sb)
            
        self.update_preview_list()

    def generate_doubling_schedule(self, start_sb):
        schedule = []
        sb = start_sb
        for _ in range(20):
            bb = sb * 2
            schedule.append((self._format_blind(sb), self._format_blind(bb)))
            sb = bb
        return schedule

    def generate_standard_schedule(self, start_sb):
        multipliers = [1, 2, 3, 4, 5, 10, 15, 20, 40, 60, 80, 100, 150, 200, 300, 400, 500, 800, 1000, 2000]
        schedule = []
        for m in multipliers:
            sb = start_sb * m
            bb = sb * 2
            schedule.append((self._format_blind(sb), self._format_blind(bb)))
        return schedule

    def update_preview_list(self):
        self.liststore.clear()
        for i, (sb, bb) in enumerate(self.generated_schedule):
            self.liststore.append([f"Runde {i+1}", str(sb), str(bb)])

    # --- Actions ---

    def on_apply_clicked(self, button):
        if not self.generated_schedule:
            return
            
        # Sende den Plan direkt über den WebSocket an den Server!
        import asyncio
        asyncio.run_coroutine_threadsafe(
            self.parent_poker_interface.ws_client.send_update_blind_schedule(self.generated_schedule), 
            self.parent_poker_interface.ws_client.loop
        )
        
        # Auf dem Client manuell auch für den Fall der Fälle den confirm callback feuern
        sb, bb = self.generated_schedule[0]
        if self.confirm_callback:
            self.confirm_callback(str(sb), str(bb))
            
        self.close()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.fullscreen()
                self.is_fullscreen_mode = True
