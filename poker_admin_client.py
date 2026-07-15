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


class MyListener:
    """Listener für Zeroconf, um den Poker-Server zu entdecken."""
    def __init__(self):
        self.server_address = None

    def remove_service(self, zeroconf, type, name):
        pass  # Keine Aktion erforderlich, wenn ein Service entfernt wird

    def add_service(self, zeroconf, type, name):
        """Wird aufgerufen, wenn ein Dienst gefunden wird."""
        info = zeroconf.get_service_info(type, name)
        if info:
            addr = socket.inet_ntoa(info.addresses[0])
            print(f"Gefundener Server: {name} unter {addr}:{info.port}")
            self.server_address = (addr, info.port)


class PokerAdminClient(PokerInterface):
    """Der Poker-Admin-Client."""
    def __init__(self):
        super().__init__(is_admin=True)  # ✅ Admin-Client hat Admin-Privilegien

        # Zeroconf-Diensterkennung starten
        self.server_address = self.find_server_via_zeroconf()

        # Starte den Netzwerk-Listener in eigenem Thread
        self.start_async_loop()

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
                    print(f"🔗 Verbunden mit dem Server: {uri}")
                    await websocket.send(json.dumps({"command": "get_status"}))
                    async for message in websocket:
                        data = json.loads(message)
                        GLib.idle_add(self.update_display, data)
            except Exception as e:
                print(f"⚠ Verbindung zum Server fehlgeschlagen: {e}")
                await asyncio.sleep(5)  # 5 Sekunden warten, dann erneut versuchen

    def update_display(self, data):
        """Aktualisiert die Anzeige basierend auf den empfangenen Daten."""
        small_blind = data.get("small_blind", "n.V.")
        big_blind = data.get("big_blind", "n.V.")
        try:
            minute = int(data.get("minute") or 0)
            second = int(data.get("second") or 0)
        except Exception as e:
            print("Fehler bei der Umwandlung von minute/second:", e)
            minute, second = 0, 0

        status_text = "►" if data.get("is_running", False) else "‖"

        if hasattr(self, "left_labels"):
            # Aktualisiere die Small Blind und Big Blind Labels
            if "Small Blind" in self.left_labels:
                self.left_labels["Small Blind"].set_text(small_blind)
            if "Big Blind" in self.left_labels:
                self.left_labels["Big Blind"].set_text(big_blind)
            # Aktualisiere das Timer-Label
            if "Nächste Blinderhöhung" in self.left_labels:
                new_text = f"{status_text} {minute:02}:{second:02}"
                print("Admin-Client: Aktualisiere Timer-Label auf:", new_text)
                self.left_labels["Nächste Blinderhöhung"].set_text(new_text)

    async def send_update_to_server(self, command, payload):
        """Sendet eine Aktualisierung (z. B. Blinds oder Timer) an den Server."""
        if self.server_address:
            uri = f"ws://{self.server_address[0]}:{self.server_address[1]}"
        else:
            uri = "ws://192.168.1.65:8765"  # Fallback-Adresse

        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({"command": command, **payload}))
                print(f"🔄 Update an Server gesendet: {command}, {payload}")
        except Exception as e:
            print(f"⚠ Fehler beim Senden eines Updates: {e}")


if __name__ == "__main__":
    admin_client = PokerAdminClient()
    admin_client.show_all()
    Gtk.main()
