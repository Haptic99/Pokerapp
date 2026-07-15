import gi
from gi.repository import Gtk, Gdk, GLib
from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.game_time_data import GameTimeData

class TotalGameTimeWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="Spielzeit")
        self.parent = parent
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        
        # Falls das übergeordnete Fenster im Vollbildmodus ist:
        self.is_fullscreen_mode = parent.is_fullscreen_mode
        if self.is_fullscreen_mode:
            self.fullscreen()
        
        # Startwerte (hochzählender Timer)
        self.total_minute = 0
        self.total_second = 0
        self.is_running = False
        self.timer_id = None
        
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)
        
        # Große Anzeige – hier wird der Text weiß angezeigt
        self.time_label = Gtk.Label(label="00:00")
        self.time_label.set_name("total-time-label")
        self.time_label.set_markup("<span font='60' foreground='white'>00:00</span>")
        self.time_label.get_style_context().add_class("bright-text")
        self.overlay.add_overlay(self.time_label)
        self.time_label.set_halign(Gtk.Align.CENTER)
        self.time_label.set_valign(Gtk.Align.CENTER)
        
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Buttons erstellen
        self.start_button = Gtk.Button(label="►")
        self.start_button.set_size_request(65, 40)
        self.start_button.get_style_context().add_class("button-custom-spielzeit")
        self.start_button.connect("clicked", self.on_start)
        self.fixed.put(self.start_button, 150, 416)

        self.pause_button = Gtk.Button(label="‖")
        self.pause_button.set_size_request(65, 40)
        self.pause_button.get_style_context().add_class("button-custom-spielzeit")
        self.pause_button.connect("clicked", self.on_pause)
        self.fixed.put(self.pause_button, 235, 416)

        self.stop_button = Gtk.Button(label="■")
        self.stop_button.set_size_request(65, 40)
        self.stop_button.get_style_context().add_class("button-custom-spielzeit")
        self.stop_button.connect("clicked", self.on_stop)
        self.fixed.put(self.stop_button, 320, 416)

        self.set_time_button = Gtk.Button(label="Zeit einstellen")
        self.set_time_button.get_style_context().add_class("button-custom")
        self.set_time_button.connect("clicked", self.on_set_time)
        self.fixed.put(self.set_time_button, 460, 416)

        # Neuer Schliessen-Button rechts unten, analog zum Admin-Fenster:
        close_button = Gtk.Button(label="Schliessen")
        close_button.set_size_request(100, 40)
        close_button.connect("clicked", lambda w: self.close())
        close_button.get_style_context().add_class("button-custom")
        self.fixed.put(close_button, 658, 416)

        self.pause_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        
        self.connect("key-press-event", self.on_key_press)
    
    def on_start(self, widget):
        if not self.is_running:
            self.is_running = True
            # Übertrage den aktuellen lokalen Timer in GameTimeData
            GameTimeData.minute = self.total_minute
            GameTimeData.second = self.total_second
            GameTimeData.is_running = True
            self.start_timer()
            self.start_button.set_sensitive(False)
            self.pause_button.set_sensitive(True)
            self.stop_button.set_sensitive(True)
    
    def on_pause(self, widget):
        if self.is_running:
            self.is_running = False
            if self.timer_id:
                GLib.source_remove(self.timer_id)
                self.timer_id = None
            self.start_button.set_sensitive(True)
            self.pause_button.set_sensitive(False)
            # Setze GameTimeData.is_running auf False
            GameTimeData.is_running = False
    
    def on_stop(self, widget):
        self.is_running = False
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.total_minute = 0
        self.total_second = 0
        self.update_time_label()
        self.start_button.set_sensitive(True)
        self.pause_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        # Setze auch GameTimeData zurück
        GameTimeData.minute = 0
        GameTimeData.second = 0
        GameTimeData.is_running = False
    
    def on_set_time(self, widget):
        from windows.total_time_setting_window import TotalTimeSettingWindow
        self.time_setting_window = TotalTimeSettingWindow(self, self.on_time_set)
        self.time_setting_window.show_all()
    
    def on_time_set(self, minute, second):
        self.total_minute = minute
        self.total_second = second
        self.update_time_label()
        if hasattr(self, "time_setting_window"):
            self.time_setting_window.close()
    
    def start_timer(self):
        self.timer_id = GLib.timeout_add_seconds(1, self.update_timer)
    
    def update_timer(self):
        self.total_second += 1
        if self.total_second >= 60:
            self.total_second = 0
            self.total_minute += 1
        self.update_time_label()
        # Übertrage die aktuellen Werte in GameTimeData,
        # damit diese global (und via Serverbroadcast) sichtbar sind.
        GameTimeData.minute = self.total_minute
        GameTimeData.second = self.total_second
        return True
    
    def update_time_label(self):
        self.time_label.set_markup(
            f"<span font='60' foreground='white'>{self.total_minute:02}:{self.total_second:02}</span>"
        )
    
    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
    
    # Optional: Weitere Methoden zum Pausieren und Stoppen können hier ergänzt werden.
    
if __name__ == "__main__":
    win = TotalGameTimeWindow(None)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
