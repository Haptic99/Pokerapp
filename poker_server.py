import asyncio
import websockets
import json
from data.timer_data import TimerData  # Timer-Daten
from data.blind_data import BlindData  # Blind-Daten

clients = set()

async def handle_client(websocket, path):  # <--- `path` hinzugefügt
    """Verwaltet eine neue Client-Verbindung."""
    clients.add(websocket)
    print("✅ Neuer Client verbunden.")

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
    """Sendet den aktuellen Spielstatus an alle verbundenen Clients."""
    if clients:
        game_status = {
            "small_blind": BlindData.small_blind,
            "big_blind": BlindData.big_blind,
            "minute": TimerData.minute,
            "second": TimerData.second,
            "is_running": TimerData.is_running
        }
        await asyncio.wait([client.send(json.dumps(game_status)) for client in clients])

async def main():
    server_instance = await websockets.serve(handle_client, "0.0.0.0", 8765)
    print("Poker-Server läuft auf Port 8765")
    await server_instance.wait_closed()

asyncio.run(main())
