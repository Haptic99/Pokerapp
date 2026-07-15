from gi.repository import Gtk
from windows.poker_interface import PokerInterface
from utils.display_utils import update_client_display
from utils.websocket_utils import WebSocketClient
import gi
gi.require_version('Gtk', '3.0')


class PokerClient(PokerInterface):
    """Der Poker-Client."""
    def __init__(self):
        super().__init__(is_admin=False)  # ✅ Client ist KEIN Admin

        # Entferne Admin-Button, falls vorhanden
        if hasattr(self, "fixed") and hasattr(self, "administration_button"):
            self.fixed.remove(self.administration_button)

        # WebSocket-Client initialisieren (findet Server automatisch via Zeroconf)
        self.ws_client = WebSocketClient(update_display_callback=self.update_display)

        # Starte den Netzwerk-Listener
        self.ws_client.start_async_loop()

        # Für Kompatibilität mit bestehendem Code
        self.server_address = self.ws_client.server_address
        self.loop = self.ws_client.loop
        self.uri = self.ws_client.uri

    def update_display(self, data):
        update_client_display(self, data)


# Statt eines asynchronen main()-Loops wird hier einfach der Client instanziert
if __name__ == '__main__':
    client = PokerClient()
    client.show_all()
    Gtk.main()
