# utils/websocket_utils.py

import asyncio
import websockets
import json
import threading
import time
from gi.repository import GLib
from zeroconf import Zeroconf, ServiceBrowser
from utils.zeroconf_utils import MyListener

class WebSocketClient:
    """Eine gemeinsame Klasse für WebSocket-Kommunikation in Poker-Clients."""
    
    def __init__(self, server_address=None, update_display_callback=None):
        """
        Initialisiert den WebSocket-Client.
        
        Args:
            server_address: Tuple (host, port) oder None
            update_display_callback: Callback-Funktion für UI-Updates
        """
        self.server_address = server_address
        self.update_display_callback = update_display_callback
        self.loop = None
        self.persistent_ws = None
        
        # Wenn keine Server-Adresse angegeben wurde, versuche via Zeroconf zu finden
        if not self.server_address:
            self.server_address = self.find_server_via_zeroconf()
            
        self.uri = (
            f"ws://{self.server_address[0]}:{self.server_address[1]}"
            if self.server_address
            else "ws://192.168.1.65:8765"
        )
    
    def start_async_loop(self):
        """Startet den asyncio-Eventloop in einem separaten Thread."""
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()
        # Starte die Routine zum Abhören von Updates vom Server
        asyncio.run_coroutine_threadsafe(self.listen_for_updates(), self.loop)
    
    def run_async_loop(self):
        """Führt den asyncio-Eventloop aus."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    async def listen_for_updates(self):
        """Empfängt regelmäßig Updates vom Server und aktualisiert das Interface."""
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print(f"Verbunden mit dem Server: {self.uri}")
                    await websocket.send(json.dumps({"command": "get_status"}))
                    async for message in websocket:
                        data = json.loads(message)
                        if self.update_display_callback:
                            # Update über GLib.idle_add, um den GTK-Hauptloop nicht zu blockieren
                            GLib.idle_add(self.update_display_callback, data)
            except Exception as e:
                print(f"⚠ Verbindung zum Server fehlgeschlagen: {e}")
                await asyncio.sleep(5)
    
    async def send_message(self, message_dict):
        """
        Sendet eine Nachricht an den Server.
        
        Args:
            message_dict: Dictionary mit der zu sendenden Nachricht
        """
        try:
            async with websockets.connect(self.uri) as websocket:
                await websocket.send(json.dumps(message_dict))
                print(f"Nachricht an Server gesendet: {message_dict}")
                return True
        except Exception as e:
            print(f"⚠ Fehler beim Senden einer Nachricht: {e}")
            return False
    
    async def send_join_message(self, player_name):
        """Sendet eine Join-Nachricht mit dem Namen an den Server."""
        message = {"action": "join", "name": player_name}
        return await self.send_message(message)
    
    async def send_leave_message(self, player_name):
        """Sendet eine Leave-Nachricht mit dem Namen an den Server."""
        message = {"action": "leave", "name": player_name}
        return await self.send_message(message)
    
    async def send_update_blinds(self, small_blind, big_blind):
        """Sendet aktualisierte Blind-Werte an den Server."""
        message = {
            "command": "update_blinds",
            "small_blind": small_blind,
            "big_blind": big_blind
        }
        return await self.send_message(message)
    
    async def send_update_timer(self, minute, second, is_running):
        """Sendet aktualisierte Timer-Werte an den Server."""
        message = {
            "command": "update_timer",
            "minute": minute,
            "second": second,
            "is_running": is_running
        }
        return await self.send_message(message)
    
    async def send_update_game_time(self, minute, second, is_running):
        """Sendet aktualisierte Spielzeit-Werte an den Server."""
        message = {
            "command": "update_game_time",
            "game_time_minute": minute,
            "game_time_second": second,
            "is_running": is_running
        }
        return await self.send_message(message)
    
    async def send_start_timer(self, minute, second):
        """Sendet den Befehl zum Starten des Timers an den Server."""
        message = {
            "command": "start_timer",
            "minute": minute,
            "second": second
        }
        return await self.send_message(message)
    
    async def send_pause_timer(self):
        """Sendet den Befehl zum Pausieren des Timers an den Server."""
        message = {
            "command": "pause_timer"
        }
        return await self.send_message(message)
    
    async def send_stop_timer(self):
        """Sendet den Befehl zum Stoppen des Timers an den Server."""
        message = {
            "command": "stop_timer"
        }
        return await self.send_message(message)
        
    def find_server_via_zeroconf(self):
        """Verwendet Zeroconf, um den Poker-Server zu finden."""
        zeroconf = Zeroconf()
        listener = MyListener()
        ServiceBrowser(zeroconf, "_poker._tcp.local.", listener)

        print("🔍 Suche nach dem Server...")
        time.sleep(5)  # Warte einige Sekunden, um Dienste zu entdecken
        zeroconf.close()

        if listener.server_address:
            print(f"✅ Server gefunden unter {listener.server_address}")
            return listener.server_address
        else:
            print("❌ Kein Server gefunden. Verwende eine Standard-Adresse.")
            return None  # Hier kann ein Fallback verwendet werden
