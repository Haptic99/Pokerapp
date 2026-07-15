import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from windows.poker_interface import PokerInterface
from utils.display_utils import update_client_display
from utils.websocket_utils import WebSocketClient
from utils.helpers import format_timer_with_status
from data.timer_data import TimerData

class PokerAdminClient(PokerInterface):
    """Der Poker‑Admin‑Client."""
    def __init__(self):
        super().__init__(is_admin=True)  # Admin‑Client hat Admin‑Privilegien

        # WebSocket-Client initialisieren (findet Server automatisch via Zeroconf)
        self.ws_client = WebSocketClient(update_display_callback=self.update_display)
        
        # Starte den Netzwerk-Listener
        self.ws_client.start_async_loop()
        
        # Für Kompatibilität mit bestehendem Code
        self.server_address = self.ws_client.server_address
        self.loop = self.ws_client.loop
        self.uri = self.ws_client.uri

    def update_timer_table(self):
        if (TimerData.minute is None or (TimerData.minute == 0 and TimerData.second == 0)):
            current_time_str = "-"
        else:
            current_time_str = format_timer_with_status(TimerData.minute, TimerData.second, TimerData.is_running)

        if "Eingestellte Zeit" in self.timer_labels:
            self.timer_labels["Eingestellte Zeit"].set_text(set_time_str)
        if "Momentane Zeit" in self.timer_labels:
            self.timer_labels["Momentane Zeit"].set_text(current_time_str)

    def update_display(self, data):
        update_client_display(self, data)

    async def send_update_to_server(self, command, payload):
        """Diese Methode ist jetzt ein Wrapper für die WebSocketClient-Methoden."""
        if command == "update_blinds":
            await self.ws_client.send_update_blinds(payload["small_blind"], payload["big_blind"])
        elif command == "update_timer":
            await self.ws_client.send_update_timer(payload["minute"], payload["second"], payload["is_running"])
        elif command == "update_game_time":
            await self.ws_client.send_update_game_time(
                payload["game_time_minute"], 
                payload["game_time_second"], 
                payload["is_running"]
            )
        else:
            message = {"command": command, **payload}
            await self.ws_client.send_message(message)

# Am Ende des Dokuments: instanziere den Admin-Client und starte die GUI
if __name__ == '__main__':
    admin_client = PokerAdminClient()
    admin_client.show_all()
    Gtk.main()
