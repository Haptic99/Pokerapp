import asyncio
import websockets
import json

class PersistentWebSocketClient:
    def __init__(self, uri, loop):
        self.uri = uri
        self.loop = loop
        self.websocket = None
        self.queue = asyncio.Queue()
        self.connected = asyncio.Event()
        # Starte den Verbindungs-Loop als Task im übergebenen Event-Loop.
        self.loop.create_task(self.connect_loop())

    async def connect_loop(self):
        """Dauerhafter Verbindungs-Loop: Versucht stets, eine Verbindung aufzubauen und sendet Nachrichten aus der Queue."""
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    self.connected.set()
                    print(f"Persistente Verbindung hergestellt zu {self.uri}")
                    # Solange die Verbindung besteht, Nachrichten aus der Queue senden.
                    while True:
                        message = await self.queue.get()
                        await self.websocket.send(message)
            except Exception as e:
                self.connected.clear()
                print(f"Verbindung verloren, versuche erneut in 5 Sekunden... ({e})")
                await asyncio.sleep(5)

    async def send(self, message):
        """Legt eine Nachricht in die Queue, um sie über die persistente Verbindung zu senden."""
        await self.queue.put(message)

