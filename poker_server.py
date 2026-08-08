import asyncio
import websockets
import json
import socket
import time
from zeroconf import Zeroconf, ServiceInfo
from data.timer_data import TimerData  # Timer-Daten
from data.blind_data import BlindData  # Blind-Daten
from data.game_time_data import GameTimeData  # Spielzeit-Daten
from data.round_data import RoundData
from data.chip_data import ChipData

try:
    from gpiozero import Button
except ImportError:
    Button = None

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Dummy-Verbindung (muss nicht existieren), um die LAN-IP herauszufinden
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

hostname = socket.gethostname()
local_ip = get_local_ip()

# Zeroconf-Dienstinformationen
service_type = "_poker._tcp.local."
service_name = f"PokerServer_{int(time.time())}._poker._tcp.local."
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
        # If the blind timer is running, update it (countdown)
        if TimerData.is_running:
            if TimerData.minute == 0 and TimerData.second == 0:
                TimerData.is_running = False
                print("[DEBUG] Timer reached zero, stopping")
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
                elif data["command"] == "update_blind_schedule":
                    BlindData.BLIND_SCHEDULE = data["schedule"]
                    BlindData.current_level_index = 0
                    RoundData.count = 1
                    if len(BlindData.BLIND_SCHEDULE) > 0:
                        sb, bb = BlindData.BLIND_SCHEDULE[0]
                        BlindData.small_blind = str(sb)
                        BlindData.big_blind = str(bb)
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
                elif data["command"] == "update_chip_values":
                    # Update the chip values in the ChipData class
                    for chip_file, chf_value in data.get("chip_values", {}).items():
                        if chip_file in ChipData.chf_values:
                            ChipData.chf_values[chip_file] = chf_value
                    print("Chip values updated.")

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
        "chip_values": ChipData.chf_values,
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


import time

last_button_press_time = 0

def advance_round_hardware():
    """Wird aufgerufen, wenn der physische Hardware-Button gedrückt wird."""
    global last_button_press_time
    
    # 3 Sekunden Cooldown (Delay), um versehentliche Doppel-Klicks zu ignorieren
    current_time = time.time()
    if current_time - last_button_press_time < 3.0:
        print("[HARDWARE] Button ignoriert (Cooldown aktiv).")
        return
        
    last_button_press_time = current_time
    
    print("[HARDWARE] Button gedrückt! Nächste Runde wird eingeleitet...")
    
    # 1. Runde erhöhen
    current_round = RoundData.count if RoundData.count is not None else 0
    RoundData.count = current_round + 1
    
    # 2. Blinds erhöhen
    BlindData.current_level_index += 1
    if BlindData.current_level_index >= len(BlindData.BLIND_SCHEDULE):
        BlindData.current_level_index = len(BlindData.BLIND_SCHEDULE) - 1 # Auf höchstem Level bleiben
        
    sb, bb = BlindData.BLIND_SCHEDULE[BlindData.current_level_index]
    BlindData.small_blind = str(sb)
    BlindData.big_blind = str(bb)
    
    # 3. Timer zurücksetzen und starten
    # Falls noch nie eine Zeit eingestellt wurde, Standardwert 15 Minuten setzen
    if TimerData.start_minute is None:
        TimerData.start_minute = 15
        TimerData.start_second = 0
        
    TimerData.minute = TimerData.start_minute
    TimerData.second = TimerData.start_second
    TimerData.is_running = True
    TimerData.is_paused = False


def setup_hardware_button():
    """Initialisiert den GPIO-Button, falls auf einem Raspberry Pi ausgeführt."""
    if Button is not None:
        try:
            # GPIO 21 (Pin 40 am Raspberry Pi)
            # bounce_time=0.05 (50ms) ist kurz genug für sofortige Reaktion,
            # aber lang genug, um elektrische Störsignale zu filtern.
            btn = Button(21, pull_up=True, bounce_time=0.05)
            btn.when_pressed = advance_round_hardware
            print("✅ Hardware-Button auf GPIO 21 initialisiert.")
            return btn
        except Exception as e:
            print(f"⚠ Konnte Hardware-Button nicht initialisieren: {e}")
    else:
        print("⚠ gpiozero nicht verfügbar (vermutlich Windows). Hardware-Button deaktiviert.")
    return None


async def main():
    hw_button = setup_hardware_button()
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
