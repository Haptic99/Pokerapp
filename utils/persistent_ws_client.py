import asyncio
import websockets

class PersistentWebSocketClient:
    def __init__(self, url):
        self.url = url

    async def connect_loop(self):
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    print(f"Persistente Verbindung hergestellt zu {self.url}")
                    await self.handle_connection(ws)
            except Exception as e:
                print("Verbindung verloren, versuche erneut in 5 Sekunden...", e)
                # Sicherstellen, dass sleep im aktuellen Event Loop läuft
                await asyncio.sleep(5)

    async def handle_connection(self, ws):
        try:
            async for message in ws:
                # Bearbeite die eingehenden Nachrichten hier
                print("Nachricht erhalten:", message)
        except Exception as e:
            print("Fehler beim Verarbeiten der Nachricht:", e)
