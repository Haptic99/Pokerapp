import asyncio
import websockets
import json
import threading
import gi
import socket

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from windows.poker_interface import PokerInterface  # Nutzt das gleiche Interface
from zeroconf import Zeroconf, ServiceBrowser

class MyListener:
    def __init__(self):
        self.server_address = None

    def remove_service(self, zeroconf, type, name):
        pass

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            addr = socket.inet_ntoa(info.addresses[0])
            print(f"Gefundener Server: {name} unter {addr}:{info.port}")
            self.server_address = (addr, info.port)

zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_poker._tcp.local.", listener)

# Warte eine gewisse Zeit, damit der Dienst gefunden wird
import time
time.sleep(5)

if listener.server_address:
    server_ip, server_port = listener.server_address
    print(f"Verbinde zu Server: {server_ip}:{server_port}")
    # Hier kannst du dann die Verbindung zum Server herstellen, z.B.:
    # asyncio.run_coroutine_threadsafe(self.listen_for_updates(), ...)

zeroconf.close()

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
        small_blind = data.get("small_blind", "n.V.")
        big_blind = data.get("big_blind", "n.V.")
        try:
            minute = int(data.get("minute") or 0)
            second = int(data.get("second") or 0)
        except Exception as e:
            print("Fehler bei der Umwandlung von minute/second:", e)
            minute, second = 0, 0


        print(is_running,e)
        status_text = "►" if data.get("is_running", False) else "‖"

        if hasattr(self, "left_labels"):
            # Aktualisiere auch die Blind-Labels, falls erwünscht
            if "Small Blind" in self.left_labels:
                self.left_labels["Small Blind"].set_text(small_blind)
            if "Big Blind" in self.left_labels:
                self.left_labels["Big Blind"].set_text(big_blind)
            # Aktualisiere das Timer-Label
            if "Nächste Blinderhöhung" in self.left_labels:
                new_text = f"{status_text} {minute:02}:{second:02}"
                print("Client: Aktualisiere Timer-Label auf:", new_text)
                self.left_labels["Nächste Blinderhöhung"].set_text(new_text)







if __name__ == "__main__":
    client = PokerClient()
    client.show_all()
    Gtk.main()
