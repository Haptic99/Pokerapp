import asyncio
import websockets
import json
import threading
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from windows.poker_interface import PokerInterface  # Nutzt das gleiche Interface

class PokerClient(PokerInterface):
    def __init__(self):
        super().__init__(is_admin=False)  # ✅ Client ist KEIN Admin

        # Entferne Admin-Button, falls vorhanden
        if hasattr(self, "fixed") and hasattr(self, "administration_button"):
            self.fixed.remove(self.administration_button)

        # Starte den Netzwerk-Listener in eigenem Thread
        self.start_async_loop()

    def start_async_loop(self):
        """Startet den asyncio-Eventloop in einem separaten Thread."""
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.listen_for_updates(), self.loop)

    def run_async_loop(self):
        """Führt den asyncio-Eventloop aus."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def listen_for_updates(self):
        """Empfängt Daten vom Server und aktualisiert das Interface."""
        uri = "ws://192.168.1.65:8765"  # Server-IP anpassen

        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    await websocket.send(json.dumps({"command": "get_status"}))
                    async for message in websocket:
                        data = json.loads(message)
                        GLib.idle_add(self.update_display, data)
            except Exception as e:
                print(f"⚠ Verbindung zum Server fehlgeschlagen: {e}")
                await asyncio.sleep(5)  # 5 Sekunden warten, dann erneut versuchen

    def update_display(self, data):
        print("update_display aufgerufen mit:", data)
        try:
            minute = int(data.get("minute") or 0)
            second = int(data.get("second") or 0)
        except Exception as e:
            print("Fehler bei der Umwandlung von minute/second:", e)
            minute, second = 0, 0

        if hasattr(self, "left_labels"):
            if "Small Blind" in self.left_labels:
                self.left_labels["Small Blind"].set_text(f"{data.get('small_blind', 'n.V.')}")
            if "Big Blind" in self.left_labels:
                self.left_labels["Big Blind"].set_text(f"{data.get('big_blind', 'n.V.')}")




if __name__ == "__main__":
    client = PokerClient()
    client.show_all()
    Gtk.main()
