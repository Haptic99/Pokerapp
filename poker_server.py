import asyncio
import websockets
import json
from data.timer_data import TimerData  # Timer-Daten
from data.blind_data import BlindData  # Blind-Daten

clients = set()  # Liste der verbundenen Clients

async def handle_client(websocket, path):
    """Verwaltet eine neue Client-Verbindung."""
    clients.add(websocket)
    print(f"✅ Neuer Client verbunden. {len(clients)} aktive Clients.")

    try:
        async for message in websocket:
            data = json.loads(message)

            if "command" in data:
                if data["command"] == "get_status":
                    await send_game_status(websocket)

                elif data["command"] == "update_blinds":
                    print(f"📢 Blinds geändert: {data['small_blind']} / {data['big_blind']}")
                    BlindData.small_blind = data["small_blind"]
                    BlindData.big_blind = data["big_blind"]
                    await broadcast_game_status()

                elif data["command"] == "update_timer":
                    print(f"⏳ Timer geändert: {data['minute']}:{data['second']} (Läuft: {data['is_running']})")
                    TimerData.minute = data["minute"]
                    TimerData.second = data["second"]
                    TimerData.is_running = data["is_running"]
                    await broadcast_game_status()

    except websockets.exceptions.ConnectionClosed:
        print("❌ Client hat die Verbindung getrennt.")
    finally:
        clients.discard(websocket)
        print(f"🔌 Client entfernt. {len(clients)} aktive Clients.")

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
    """Sendet den aktuellen Spielstatus an alle verbundenen Clients."""
    if clients:
        game_status = {
            "small_blind": BlindData.small_blind,
            "big_blind": BlindData.big_blind,
            "minute": TimerData.minute,
            "second": TimerData.second,
            "is_running": TimerData.is_running
        }

        # Senden an alle Clients
        disconnected_clients = set()
        for client in clients:
            try:
                await client.send(json.dumps(game_status))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)

        # Entferne inaktive Clients
        for client in disconnected_clients:
            clients.remove(client)
            print(f"❌ Entfernte inaktiven Client. {len(clients)} aktive Clients.")

async def server_heartbeat():
    """Pingt Clients regelmäßig, um Verbindungen zu überprüfen."""
    while True:
        await asyncio.sleep(10)  # Alle 10 Sekunden prüfen
        disconnected_clients = set()

        for client in clients:
            try:
                await client.ping()
            except:
                disconnected_clients.add(client)

        # Entferne inaktive Clients
        for client in disconnected_clients:
            clients.remove(client)
            print(f"❌ Ping fehlgeschlagen – Client entfernt. {len(clients)} aktive Clients.")

async def main():
    """Startet den WebSocket-Server."""
    server_instance = await websockets.serve(handle_client, "0.0.0.0", 8765)
    print("🚀 Poker-Server läuft auf Port 8765")

    # Starte den Heartbeat
    asyncio.create_task(server_heartbeat())

    await server_instance.wait_closed()

asyncio.run(main())
