import asyncio
import websockets
import json
import socket
from zeroconf import Zeroconf, ServiceInfo
from data.timer_data import TimerData  # Timer-Daten
from data.blind_data import BlindData  # Blind-Daten
from data.game_time_data import GameTimeData  # Spielzeit-Daten
from data.round_data import RoundData 

# Lokale IP-Adresse ermitteln
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

# Zeroconf-Dienstinformationen
service_type = "_poker._tcp.local."
service_name = "PokerServer._poker._tcp.local."
port = 8765  # Port, auf dem der WebSocket-Server läuft

info = ServiceInfo(
    service_type,
    service_name,
    addresses=[socket.inet_aton(local_ip)],
    port=port,
    properties={},
    server=f"{hostname}.local."
)

# Zeroconf initialisieren und Service registrieren
zeroconf = Zeroconf()
print("Registriere den Zeroconf-Service...")
zeroconf.register_service(info)

clients = set()           # Verbundene Clients
connected_players = []    # Liste der Spielernamen (Reihenfolge des Logins)

async def update_loop():
    while True:
        # Debug timer status - Handle None values with default of 0
        minute = "-" if TimerData.minute is None else TimerData.minute
        second = "-" if TimerData.second is None else TimerData.second
        current_minute = "-" if TimerData.start_minute is None else TimerData.start_minute
        current_second = "-" if TimerData.start_second is None else TimerData.start_second

        # If the blind timer is running, update it (countdown)
        if TimerData.is_running:
            if TimerData.minute == 0 and TimerData.second == 0:
                TimerData.is_running = False
                print(f"[DEBUG] Timer reached zero, stopping")
            else:
                if TimerData.second > 0:
                    TimerData.second -= 1
                else:
                    TimerData.minute -= 1
                    TimerData.second = 59

        # If game time is running, update it (count up)
        if GameTimeData.is_running:
            GameTimeData.second += 1
            if GameTimeData.second >= 60:
                GameTimeData.second = 0
                GameTimeData.minute += 1
            print(f"[DEBUG] Game time updated: {GameTimeData.minute:02}:{GameTimeData.second:02}")

        # Send aggregated status to all clients
        await broadcast_status()
        await asyncio.sleep(1)

async def handle_client(websocket):
    """
    Verwaltet neue Client-Verbindungen.
    Befehle wie "join", "start_timer" usw. aktualisieren den internen Status.
    Ein direkter Broadcast erfolgt hier nicht – stattdessen sorgt der update_loop einmal pro Sekunde für die Updates.
    """
    clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)

            # Verarbeitung von Join-/Leave-Aktionen
            if data.get("action") == "join":
                player_name = data.get("name", "Unbekannt")
                if player_name not in connected_players:
                    connected_players.append(player_name)
                    print(f"✅ Spieler hinzugefügt: {player_name}")
            elif data.get("action") == "leave":
                player_name = data.get("name")
                if player_name and player_name in connected_players:
                    connected_players.remove(player_name)
                    print(f"❌ Spieler entfernt: {player_name}")

            # Timer-/Blindbefehle: Aktualisiere den internen Zustand
            if data.get("command") == "start_timer":
                TimerData.minute = int(data.get("minute", 0))
                TimerData.second = int(data.get("second", 0))
                TimerData.start_minute = int(data.get("minute", 0))
                TimerData.start_second = int(data.get("second", 0))
                TimerData.is_running = True
                TimerData.is_paused = False
            elif data.get("command") == "pause_timer":
                TimerData.is_running = False
                TimerData.is_paused = True
            elif data.get("command") == "stop_timer":
                TimerData.is_running = False
                TimerData.is_paused = False
                TimerData.minute = TimerData.start_minute if TimerData.start_minute is not None else "-"
                TimerData.second = TimerData.start_second if TimerData.start_second is not None else "-"
            elif data.get("command") == "update_rounds":
                RoundData.count = data["rounds_count"]

            # Weitere Befehle zur Aktualisierung einzelner Datenfelder
            if "command" in data:
                if data["command"] == "get_status":
                    await send_status(websocket)
                elif data["command"] == "update_blinds":
                    BlindData.small_blind = data["small_blind"]
                    BlindData.big_blind = data["big_blind"]
                elif data["command"] == "update_timer":
                    if data["is_running"]:
                        if TimerData.is_paused:
                            # Timer wurde pausiert und jetzt nur fortgesetzt – eingestellte Zeit NICHT ändern
                            TimerData.is_running = True
                            TimerData.is_paused = False
                            TimerData.minute = data["minute"]
                            TimerData.second = data["second"]
                            # Eingestellte Zeit (start_minute/start_second) NICHT überschreiben!
                        else:
                            # Timer wird neu gestartet – eingestellte Zeit aktualisieren
                            TimerData.is_running = True
                            TimerData.is_paused = False
                            TimerData.minute = data["minute"]
                            TimerData.second = data["second"]
                            TimerData.start_minute = data["minute"]
                            TimerData.start_second = data["second"]
                    else:
                        if TimerData.is_running:
                            # Timer wurde gerade pausiert – keine Zeit überschreiben
                            TimerData.is_running = False
                            TimerData.is_paused = True
                        else:
                            # Timer explizit gestoppt (is_running=False, is_paused=False)
                            TimerData.is_running = False
                            TimerData.is_paused = False
                            TimerData.minute = TimerData.start_minute
                            TimerData.second = TimerData.start_second
                elif data["command"] == "update_game_time":
                    GameTimeData.minute = data["game_time_minute"]
                    GameTimeData.second = data["game_time_second"]
                    GameTimeData.is_running = data["is_running"]

    except websockets.exceptions.ConnectionClosed:
        print("❌ Client hat die Verbindung getrennt.")
    finally:
        clients.remove(websocket)

async def send_status(websocket):
    """
    Sendet an einen einzelnen Client den aggregierten Status.
    Dies wird für z. B. get_status-Anfragen verwendet.
    """
    status = {
        "small_blind": BlindData.small_blind,
        "big_blind": BlindData.big_blind,
        "blind_time_minute": TimerData.minute,
        "blind_time_second": TimerData.second,
        "configured_blind_time_minute": TimerData.start_minute,
        "configured_blind_time_second": TimerData.start_second,
        "timer_running": TimerData.is_running,
        "game_time_minute": GameTimeData.minute,
        "game_time_second": GameTimeData.second,
        "game_time_running": GameTimeData.is_running,
        "players": connected_players
    }
    await websocket.send(json.dumps(status))

async def broadcast_status():
    """
    Sendet den aggregierten Status an alle verbundenen Clients.
    Hier werden alle Datenfelder zusammengeführt.
    """
    
    if not clients:
        return
    
    status = {
        "small_blind": BlindData.small_blind,
        "big_blind": BlindData.big_blind,
        "blind_time_minute": TimerData.minute,
        "blind_time_second": TimerData.second,
        "configured_blind_time_minute": TimerData.start_minute,
        "configured_blind_time_second": TimerData.start_second,
        "timer_running": TimerData.is_running,
        "game_time_minute": GameTimeData.minute,
        "game_time_second": GameTimeData.second,
        "game_time_running": GameTimeData.is_running,
        "players": connected_players,
        "rounds_count": RoundData.count,
    }
    
    # Eine Kopie des clients-Sets erstellen, um sicher über die ursprünglichen Clients zu iterieren
    clients_copy = clients.copy()
    to_remove = set()
    
    for client in clients_copy:
        try:
            await client.send(json.dumps(status))
        except websockets.exceptions.ConnectionClosed:
            to_remove.add(client)

    # Erst nach der Iteration die zu entfernenden Clients tatsächlich entfernen
    for client in to_remove:
        if client in clients:  # Sicherheitscheck, falls der Client bereits entfernt wurde
            clients.remove(client)

async def main():
    try:
        async with websockets.serve(handle_client, "0.0.0.0", port):
            print(f"Poker-Server läuft auf Port {port}")
            # Starte den aggregierten Update-Loop
            asyncio.create_task(update_loop())
            await asyncio.Future()  # Hält den Server am Laufen
    except Exception as e:
        print(f"❌ Fehler beim Starten des Servers: {e}")
    finally:
        # Zeroconf-Deregistrierung und -Schließung
        zeroconf.unregister_service(info)
        zeroconf.close()

if __name__ == "__main__":
    asyncio.run(main())
