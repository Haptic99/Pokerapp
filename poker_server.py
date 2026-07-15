import asyncio
import websockets
import json
import socket
from zeroconf import Zeroconf, ServiceInfo
from data.timer_data import TimerData
from data.blind_data import BlindData

# Hole die lokale IP-Adresse
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

service_type = "_poker._tcp.local."  # Service-Typ (wähle einen eindeutigen Namen)
service_name = "PokerServer._poker._tcp.local."  # Vollständiger Dienstname
port = 8765  # Der Port, auf dem dein WebSocket-Server läuft

info = ServiceInfo(
    service_type,
    service_name,
    addresses=[socket.inet_aton(local_ip)],
    port=port,
    properties={},
    server=f"{hostname}.local."
)

zeroconf = Zeroconf()
print("Registriere den Service...")
zeroconf.register_service(info)

try:
    # Hier startet dein Server, z. B. asyncio.run(main())
    pass
finally:
    zeroconf.unregister_service(info)
    zeroconf.close()

clients = set()

async def handle_client(websocket):
    """Verwaltet eine neue Client-Verbindung."""
    clients.add(websocket)
    print(f"✅ Neuer Client verbunden von {websocket.remote_address}")

    try:
        async for message in websocket:
            data = json.loads(message)

            if "command" in data:
                if data["command"] == "get_status":
                    await send_game_status(websocket)
                elif data["command"] == "update_blinds":
                    BlindData.small_blind = data["small_blind"]
                    BlindData.big_blind = data["big_blind"]
                    await broadcast_game_status()
                elif data["command"] == "update_timer":
                    TimerData.minute = data["minute"]
                    TimerData.second = data["second"]
                    TimerData.is_running = data["is_running"]
                    await broadcast_game_status()

    except websockets.exceptions.ConnectionClosed:
        print("❌ Client hat die Verbindung getrennt.")
    finally:
        clients.remove(websocket)

async def send_game_status(websocket):
    """Sendet den aktuellen Spielstatus an einen einzelnen Client."""
    game_status = {
        "small_blind": BlindData.small_blind,
        "big_blind": BlindData.big_blind,
        "minute": TimerData.minute,
        "second": TimerData.second,
        "is_running": TimerData.is_running
    }
    await websocket.send(json.dumps(game_status))

async def broadcast_game_status():
    if clients:
        game_status = {
            "small_blind": BlindData.small_blind,
            "big_blind": BlindData.big_blind,
            "minute": TimerData.minute,
            "second": TimerData.second,
            "is_running": TimerData.is_running
        }
        print("Broadcasting game status:", game_status)  # Debug-Ausgabe
        await asyncio.gather(*[client.send(json.dumps(game_status)) for client in clients])



async def main():
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        print("Poker-Server läuft auf Port 8765")
        await asyncio.Future()  # Lässt den Server unbegrenzt laufen

if __name__ == "__main__":
    asyncio.run(main())  # Startet den Event-Loop
