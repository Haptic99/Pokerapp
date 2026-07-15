import gi
import websockets
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from windows.poker_interface import PokerInterface

if __name__ == "__main__":
    win = PokerInterface(is_admin=True)
    # Falls du hier etwas basierend auf dem Admin-Status tun möchtest:
    if not win.is_admin:
        # Zum Beispiel: win.listen_for_updates() starten
        pass
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
