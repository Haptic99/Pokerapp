import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from data.game_time_data import GameTimeData

class TotalTimeSettingWindow(Gtk.Window):
    def __init__(self, parent, confirm_callback):
        super().__init__(title="Gesamt Spielzeit einstellen")
        self.parent = parent
        self.set_default_size(400, 300)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.confirm_callback = confirm_callback

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        self.add(vbox)

        # Große Eingabeanzeige (z. B. als Entry im Format MM:SS)
        self.time_entry = Gtk.Entry()
        self.time_entry.set_placeholder_text("MM:SS")
        vbox.pack_start(self.time_entry, False, False, 0)

        # Bestätigungsbutton
        confirm_button = Gtk.Button(label="Übernehmen")
        confirm_button.connect("clicked", self.on_confirm)
        vbox.pack_start(confirm_button, False, False, 0)

        # Abbrechen-Button
        cancel_button = Gtk.Button(label="Abbrechen")
        cancel_button.connect("clicked", lambda w: self.close())
        vbox.pack_start(cancel_button, False, False, 0)
    
		GameTimeData.minute = minute  # der übergebene Wert
		GameTimeData.second = second  # der übergebene Wert
		GameTimeData.is_running = True
    
    def on_confirm(self, widget):
        text = self.time_entry.get_text().strip()
        try:
            parts = text.split(":")
            minute = int(parts[0])
            second = int(parts[1])
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Ungültiges Format!"
            )
            dialog.run()
            dialog.destroy()
            return
        self.confirm_callback(minute, second)
        self.close()
