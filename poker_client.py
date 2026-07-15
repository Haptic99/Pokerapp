import asyncio
import websockets
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from windows.poker_interface import PokerInterface  # Nutzt das gleiche Interface

class PokerClient(PokerInterface):
    def __init__(self):
        super().__init__()

        # Entferne Admin-Button, falls vorhanden
        if hasattr(self, "fixed"):
            self.fixed.remove(self.admin_button)

        # Starte den Netzwerk-Listener
        asyncio.create_task(self.listen_for_updates())

    async def listen_for_updates(self):
        """Empfängt Daten vom Server und aktualisiert das Interface."""
        uri = "ws://SERVER_IP:8765"  # Ersetze SERVER_IP mit der echten IP
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"command": "get_status"}))
            async for message in websocket:
                data = json.loads(message)
                self.update_display(data)

    def update_display(self, data):
        """Aktualisiert die Anzeige basierend auf den Server-Daten."""
        small_blind = data.get("small_blind", "n.V.")
        big_blind = data.get("big_blind", "n.V.")
        minute = data.get("minute", 0)
        second = data.get("second", 0)
        status_text = "►" if data.get("is_running", False) else "‖"

        if hasattr(self, "left_labels") and "Nächste Blinderhöhung" in self.left_labels:
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")

if __name__ == "__main__":
    client = PokerClient()
    client.show_all()
    Gtk.main()
