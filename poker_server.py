import asyncio
import websockets
import json
import socket
from zeroconf import Zeroconf, ServiceInfo
from data.timer_data import TimerData  # Timer-Daten
from data.blind_data import BlindData  # Blind-Daten
from data.game_time_data import GameTimeData

# Hole die lokale IP-Adresse
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

# Zeroconf-Dienstinformationen
service_type = "_poker._tcp.local."  # Service-Typ (eindeutiger Name)
service_name = "PokerServer._poker._tcp.local."  # Vollständiger Dienstname
port = 8765  # Der Port, auf dem der WebSocket-Server läuft

# Dienstinformationen für Zeroconf
info = ServiceInfo(
    service_type,
    service_name,
    addresses=[socket.inet_aton(local_ip)],
    port=port,
    properties={},
    server=f"{hostname}.local."
)

# Zeroconf initialisieren
zeroconf = Zeroconf()
print("Registriere den Zeroconf-Service...")
zeroconf.register_service(info)

clients = set()              # Liste der verbundenen Clients
connected_players = []       # Liste der Spielernamen (in Reihenfolge des Logins)


async def handle_client(websocket):
    """Verwaltet eine neue Client-Verbindung."""
    clients.add(websocket)
    print(f"✅ Neuer Client verbunden von {websocket.remote_address}")

    try:
        async for message in websocket:
            data = json.loads(message)

            # Verarbeitung von Join-/Leave-Aktionen
            if data.get("action") == "join":
                player_name = data.get("name", "Unbekannt")
                if player_name not in connected_players:
                    connected_players.append(player_name)
                    print(f"✅ Spieler hinzugefügt: {player_name}")
                    await broadcast_player_list()
            elif data.get("action") == "leave":
                player_name = data.get("name")
                if player_name and player_name in connected_players:
                    connected_players.remove(player_name)
                    print(f"❌ Spieler entfernt: {player_name}")
                    await broadcast_player_list()


            # Andere Kommandos werden verarbeitet
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
                elif data.get("command") == "update_game_time":
                    GameTimeData.minute = data["game_time_minute"]
                    GameTimeData.second = data["game_time_second"]
                    await broadcast_game_status()


    except websockets.exceptions.ConnectionClosed:
        print("❌ Client hat die Verbindung getrennt.")
    finally:
        # Entferne den Client aus der Clients-Menge
        clients.remove(websocket)
        # Optional: Falls ein Spielername noch in der Liste ist, könnte hier auch entfernt werden.
        # Da hier keine Zuordnung von WebSocket zu Spielernamen besteht, muss der Client selbst per "leave" die Entfernung vornehmen.


async def send_game_status(websocket):
    game_status = {
        "small_blind": BlindData.small_blind,
        "big_blind": BlindData.big_blind,
        "minute": TimerData.minute,
        "second": TimerData.second,
        "is_running": TimerData.is_running,
        "game_time_minute": GameTimeData.minute,
        "game_time_second": GameTimeData.second,
        "players": connected_players
    }
    await websocket.send(json.dumps(game_status))


async def broadcast_player_list():
    """Broadcastet die aktuelle Spielerliste an alle verbundenen Clients."""
    if clients:
        data = {
            "players": connected_players  # Liste der Spieler senden
        }
        print(f"Sende aktualisierte Spielerliste: {connected_players}")
        await asyncio.gather(*[client.send(json.dumps(data)) for client in clients])


async def broadcast_game_status():
    if clients:
        game_status = {
            "small_blind": BlindData.small_blind,
            "big_blind": BlindData.big_blind,
            "minute": TimerData.minute,
            "second": TimerData.second,
            "is_running": TimerData.is_running,
            "game_time_minute": GameTimeData.minute,   # <-- Hinzufügen
            "game_time_second": GameTimeData.second,   # <-- Hinzufügen
            "players": connected_players
        }
        print("Sende aktualisierten Spielstatus:", game_status)
        await asyncio.gather(*[client.send(json.dumps(game_status)) for client in clients])



async def main():
    """Startet den WebSocket-Server."""
    try:
        async with websockets.serve(handle_client, "0.0.0.0", port):
            print(f"Poker-Server läuft auf Port {port}")
            await asyncio.Future()  # Lässt den Server unbegrenzt laufen
    except Exception as e:
        print(f"❌ Fehler beim Starten des Servers: {e}")
    finally:
        # Zeroconf-Service deregistrieren
        print("Deregistere den Zeroconf-Service...")
        zeroconf.unregister_service(info)
        zeroconf.close()


if __name__ == "__main__":
    asyncio.run(main())  # Startet den Event-Loop
