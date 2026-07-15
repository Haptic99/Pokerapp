# utils/timer_controller.py

import asyncio
import websockets
import json

from data.timer_data import TimerData
from data.game_time_data import GameTimeData

class TimerController:
    """
    Zentrale Klasse zur Verwaltung aller Timer-Funktionen im Poker-Spiel.
    Unterstützt sowohl den Blinds-Timer (Countdown) als auch die Spielzeit (Countup).
    Diese Klasse dient als Schnittstelle zwischen den UI-Komponenten und dem Server.
    """

    def __init__(self, parent, timer_type, ui_elements=None):
        """
        Initialisiert einen Timer-Controller.
        
        Args:
            parent: Das übergeordnete Fenster, das den Timer verwendet
            timer_type: "blind_timer" oder "game_time"
            ui_elements: Dictionary mit UI-Elementen {"minute_label", "second_label", "start_button", 
                                                     "pause_button", "stop_button", "fields"}
        """
        self.parent = parent
        self.timer_type = timer_type  # "blind_timer" oder "game_time"
        self.ui_elements = ui_elements or {}
        
        # Timer-Status (nur für die lokale UI-Steuerung)
        self.is_running = False
        self.is_paused = False
        self.timer_stopped = True
        
        # Initial-Zustand aus den globalen Daten laden
        self.load_initial_state()

    def load_initial_state(self):
        """Lädt den aktuellen Timer-Zustand aus den globalen Daten."""
        if self.timer_type == "blind_timer":
            self.is_running = TimerData.is_running
            self.is_paused = TimerData.is_paused
            
            if self.ui_elements and "minute_label" in self.ui_elements and "second_label" in self.ui_elements:
                minute = TimerData.minute if TimerData.minute is not None else 0
                second = TimerData.second if TimerData.second is not None else 0
                self.ui_elements["minute_label"].set_text(f"{int(minute):02}")
                self.ui_elements["second_label"].set_text(f"{int(second):02}")
                
        elif self.timer_type == "game_time":
            self.is_running = GameTimeData.is_running
            self.is_paused = GameTimeData.is_paused
            
            if self.ui_elements and "minute_label" in self.ui_elements and "second_label" in self.ui_elements:
                minute = GameTimeData.minute if GameTimeData.minute is not None else 0
                second = GameTimeData.second if GameTimeData.second is not None else 0
                self.ui_elements["minute_label"].set_text(f"{int(minute):02}")
                self.ui_elements["second_label"].set_text(f"{int(second):02}")
        
        # UI-Status aktualisieren, wenn Timer läuft
        if self.is_running and self.ui_elements:
            self.disable_input_fields()
            
            if "start_button" in self.ui_elements:
                self.ui_elements["start_button"].set_sensitive(False)
            if "pause_button" in self.ui_elements:
                self.ui_elements["pause_button"].set_sensitive(True)
            if "stop_button" in self.ui_elements:
                self.ui_elements["stop_button"].set_sensitive(True)

    def start_timer(self):
        print("Start Timer wurde aktiviert")
        """
        Starts the timer by sending a command to the server.
        Also updates local UI components.
        """
        # Get values from UI elements
        minute = 0
        second = 0
        if self.ui_elements and "minute_label" in self.ui_elements and "second_label" in self.ui_elements:
            minute = int(self.ui_elements["minute_label"].get_text())
            second = int(self.ui_elements["second_label"].get_text())
        
        print(f"[DEBUG] Starting timer with values - minute: {minute}, second: {second}")
        
        # Verify we're not starting a timer at 0:00
        if minute == 0 and second == 0:
            print("[ERROR] Cannot start timer at 0:00 - please set a valid time first")
            return
        
        # Update local status
        self.is_running = True
        self.is_paused = False
        self.timer_stopped = False
        
        # Update UI
        self.update_ui_for_running_timer()
        
        # Send server update with explicit values, not relying on TimerData
        self.send_server_update(minute, second, True)

    def pause_timer(self):
        print("Pause Timer wurde aktiviert")
        
        """Pausiert den Timer."""
        self.is_running = False
        self.is_paused = True
        
        minute = 0
        second = 0
        
        if self.timer_type == "blind_timer":
            TimerData.is_running = False
            TimerData.is_paused = True
            
            # UI-Status für pause aktualisieren
            minute = TimerData.minute if TimerData.minute is not None else 0
            second = TimerData.second if TimerData.second is not None else 0
        else:  # game_time
            GameTimeData.is_running = False
            GameTimeData.is_paused = True
            
            # UI-Status für pause aktualisieren
            minute = GameTimeData.minute if GameTimeData.minute is not None else 0
            second = GameTimeData.second if GameTimeData.second is not None else 0
        
        # UI aktualisieren
        self.update_ui_for_paused_timer()
        
        # Server-Update senden
        self.send_server_update(minute, second, False)

    def stop_timer(self):
        print("Stop Timer wurde aktiviert")
        """Stoppt den Timer vollständig und setzt ihn zurück."""
        self.is_running = False
        self.is_paused = False
        self.timer_stopped = True
        
        minute = 0
        second = 0
        
        if self.timer_type == "blind_timer":
            # Setze auf die ursprünglichen Startwerte zurück
            minute = TimerData.start_minute if TimerData.start_minute is not None else 0
            second = TimerData.start_second if TimerData.start_second is not None else 0
            
            TimerData.minute = minute
            TimerData.second = second
            TimerData.is_running = False
            TimerData.is_paused = False
        else:  # game_time
            # Setze die Spielzeit auf 0 zurück
            GameTimeData.minute = 0
            GameTimeData.second = 0
            GameTimeData.is_running = False
            GameTimeData.is_paused = False
            
            minute = 0
            second = 0
        
        # UI aktualisieren
        self.update_ui_for_stopped_timer(minute, second)
        
        # Server-Update senden
        self.send_server_update(minute, second, False)

    def update_ui_for_running_timer(self):
        """Aktualisiert die UI für einen laufenden Timer."""
        if not self.ui_elements:
            return
            
        # Eingabefelder deaktivieren
        self.disable_input_fields()
        
        # Buttons aktualisieren
        if "start_button" in self.ui_elements:
            self.ui_elements["start_button"].set_sensitive(False)
        if "pause_button" in self.ui_elements:
            self.ui_elements["pause_button"].set_sensitive(True)
        if "stop_button" in self.ui_elements:
            self.ui_elements["stop_button"].set_sensitive(True)

    def update_ui_for_paused_timer(self):
        """Aktualisiert die UI für einen pausierten Timer."""
        if not self.ui_elements:
            return
            
        # Buttons aktualisieren
        if "start_button" in self.ui_elements:
            self.ui_elements["start_button"].set_sensitive(True)
        if "pause_button" in self.ui_elements:
            self.ui_elements["pause_button"].set_sensitive(False)
        if "stop_button" in self.ui_elements:
            self.ui_elements["stop_button"].set_sensitive(True)

    def update_ui_for_stopped_timer(self, minute, second):
        """Aktualisiert die UI für einen gestoppten Timer."""
        if not self.ui_elements:
            return
            
        # Eingabefelder reaktivieren
        self.enable_input_fields()
        
        # Labels aktualisieren
        if "minute_label" in self.ui_elements:
            self.ui_elements["minute_label"].set_text(f"{minute:02}")
        if "second_label" in self.ui_elements:
            self.ui_elements["second_label"].set_text(f"{second:02}")
        
        # Buttons aktualisieren
        if "start_button" in self.ui_elements:
            self.ui_elements["start_button"].set_sensitive(True)
        if "pause_button" in self.ui_elements:
            self.ui_elements["pause_button"].set_sensitive(False)
        if "stop_button" in self.ui_elements:
            self.ui_elements["stop_button"].set_sensitive(False)

    def disable_input_fields(self):
        """Deaktiviert die Eingabefelder für den Timer."""
        if "fields" in self.ui_elements:
            for field in self.ui_elements["fields"]:
                field.set_sensitive(False)
                field.set_can_focus(False)

    def enable_input_fields(self):
        """Aktiviert die Eingabefelder für den Timer."""
        if "fields" in self.ui_elements:
            for field in self.ui_elements["fields"]:
                field.set_sensitive(True)
                field.set_can_focus(True)

    def send_server_update(self, minute, second, is_running):
        """Sends a timer update to the server."""
        # Wenn das nicht funktioniert, versuche es über parent.parent
        if hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'poker_interface'):
            if self.timer_type == "blind_timer":
                asyncio.run_coroutine_threadsafe(
                    self.send_update_timer(minute, second, is_running),
                    self.parent.parent.poker_interface.loop
                )
            else:  # game_time
                asyncio.run_coroutine_threadsafe(
                    self.send_update_game_time(minute, second, is_running),
                    self.parent.parent.poker_interface.loop
                )

    async def send_update_timer(self, minute, second, is_running):
        """Sends an update for the blinds timer to the server."""
        try:
            # Try to get server address from different possible paths
            server_address = None
            if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
                server_address = self.parent.poker_interface.server_address
            elif hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'poker_interface'):
                server_address = self.parent.parent.poker_interface.server_address
            elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
                server_address = self.parent.ws_client.server_address
            
            if not server_address:
                print(f"[ERROR] Could not find server address for timer update")
                return
                
            server_ip, server_port = server_address
            uri = f"ws://{server_ip}:{server_port}"
            
            print(f"[DEBUG] Sending timer update to {uri}: min={minute}, sec={second}, running={is_running}")
            
            message = {
                "command": "update_timer",
                "minute": minute,
                "second": second,
                "is_running": is_running
            }
            
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print(f"[DEBUG] Timer update sent successfully: {message}")
                
        except Exception as e:
            print(f"[ERROR] Failed to send timer update: {e}")

    async def send_update_game_time(self, minute, second, is_running):
        """Sendet ein Update für die Spielzeit an den Server."""
        try:
            server_ip, server_port = self.parent.poker_interface.server_address
            uri = f"ws://{server_ip}:{server_port}"
            message = {
                "command": "update_game_time",
                "game_time_minute": minute,
                "game_time_second": second,
                "is_running": is_running
            }
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print("Game time update sent.")
        except Exception as e:
            print(f"Error sending game time update: {e}")

# Convenience-Funktionen, um Timer von außen zu erstellen
def create_blind_timer(parent, ui_elements=None):
    """Erstellt einen Blinds-Timer."""
    return TimerController(parent, "blind_timer", ui_elements)

def create_game_time_timer(parent, ui_elements=None):
    """Erstellt einen Spielzeit-Timer."""
    return TimerController(parent, "game_time", ui_elements)
