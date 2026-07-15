import asyncio
import websockets
import json
import socket
import threading
import gi
from zeroconf import Zeroconf, ServiceBrowser

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from windows.poker_interface import PokerInterface
from utils.zeroconf_utils import MyListener
from utils.persistent_ws_client import PersistentWebSocketClient

class PokerAdminClient(PokerInterface):
    """Der Poker-Admin-Client."""
    def __init__(self):
        super().__init__(is_admin=True)  # ✅ Admin-Client hat Admin-Privilegien

        # Zeroconf-Diensterkennung starten
        self.server_address = self.find_server_via_zeroconf()

        # Starte den Netzwerk-Listener in eigenem Thread
        self.start_async_loop()
    
        self.uri = f"ws://{self.server_address[0]}:{self.server_address[1]}" if self.server_address else "ws://192.168.1.65:8765"
        self.persistent_ws = PersistentWebSocketClient(self.uri, self.loop)


    def find_server_via_zeroconf(self):
        """Verwendet Zeroconf, um den Poker-Server zu finden."""
        zeroconf = Zeroconf()
        listener = MyListener()
        browser = ServiceBrowser(zeroconf, "_poker._tcp.local.", listener)

        print("🔍 Suche nach dem Server...")
        import time
        time.sleep(5)  # Warte einige Sekunden, um Dienste zu entdecken
        zeroconf.close()

        if listener.server_address:
            print(f"✅ Server gefunden unter {listener.server_address}")
            return listener.server_address
        else:
            print("❌ Kein Server gefunden. Verwende eine Standard-Adresse.")
            return None  # Es kann ein Fallback verwendet werden

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
        if self.server_address:
            uri = f"ws://{self.server_address[0]}:{self.server_address[1]}"
        else:
            # Fallback, wenn kein Server gefunden wurde
            uri = "ws://192.168.1.65:8765"

        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    print(f"Verbunden mit dem Server: {uri}")
                    await websocket.send(json.dumps({"command": "get_status"}))
                    async for message in websocket:
                        data = json.loads(message)
                        GLib.idle_add(self.update_display, data)
            except Exception as e:
                print(f"⚠ Verbindung zum Server fehlgeschlagen: {e}")
                await asyncio.sleep(5)  # 5 Sekunden warten, dann erneut versuchen

    def update_display(self, data):
        # Blind-Daten
        small_blind = data.get("small_blind") or "n.V."
        big_blind = data.get("big_blind") or "n.V."
        
        try:
            blind_minute = int(data.get("blind_time_minute") or 0)
            blind_second = int(data.get("blind_time_second") or 0)
            timer_running = data.get("timer_running", False)
        except Exception as e:
            print("Fehler bei der Umwandlung der Blind-Timer Werte:", e)
            blind_minute, blind_second = 0, 0
            timer_running = False
        
        status_text = "" if timer_running else "‖"
        
        if hasattr(self, "left_labels"):
            if "Small Blind" in self.left_labels:
                self.left_labels["Small Blind"].set_text(small_blind)
            if "Big Blind" in self.left_labels:
                self.left_labels["Big Blind"].set_text(big_blind)
            if "Nächste Blinderhöhung" in self.left_labels:
                new_text = f"{status_text} {blind_minute:02}:{blind_second:02}"
                self.left_labels["Nächste Blinderhöhung"].set_text(new_text)
        
        # Spielzeit aktualisieren:
        if "game_time_minute" in data and "game_time_second" in data:
            try:
                from data.game_time_data import GameTimeData
                game_minute = int(data.get("game_time_minute") or 0)
                game_second = int(data.get("game_time_second") or 0)
                game_running = data.get("game_time_running", False)
            except Exception as e:
                print("Fehler bei der Umwandlung der Spielzeit:", e)
                game_minute, game_second = 0, 0
                game_running = False
            
            status_game = "" if game_running else "‖"
            if hasattr(self, "info_labels") and "Spielzeit" in self.info_labels:
                new_game_time = f"{status_game} {game_minute:02}:{game_second:02}"
                self.info_labels["Spielzeit"].set_text(new_game_time)





    async def send_update_to_server(self, command, payload):
        message = json.dumps({"command": command, **payload})
        try:
            await self.persistent_ws.send(message)
            print(f"Update an Server gesendet: {command}, {payload}")
        except Exception as e:
            print(f"⚠ Fehler beim Senden eines Updates: {e}")




if __name__ == "__main__":
    admin_client = PokerAdminClient()
    admin_client.show_all()
    Gtk.main()
