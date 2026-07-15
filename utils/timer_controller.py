# utils/timer_controller.py

import gi
import asyncio
import websockets
import json
from gi.repository import GLib, Gtk

from data.timer_data import TimerData
from data.game_time_data import GameTimeData

class TimerController:
    """
    Zentrale Klasse zur Verwaltung aller Timer-Funktionen im Poker-Spiel.
    Unterstützt sowohl den Blinds-Timer (Countdown) als auch die Spielzeit (Countup).
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
        
        # Timer-Status
        self.timer_id = None
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
                
            # Timer starten
            self.start_timer_loop()

    def start_timer(self):
        """Startet den Timer."""
        if not self.is_running:
            minute = 0
            second = 0
            
            # UI-Werte abrufen, falls verfügbar
            if self.ui_elements and "minute_label" in self.ui_elements and "second_label" in self.ui_elements:
                minute = int(self.ui_elements["minute_label"].get_text())
                second = int(self.ui_elements["second_label"].get_text())
                
            if self.timer_type == "blind_timer":
                TimerData.minute = minute
                TimerData.second = second
                
                # Speichere die Anfangswerte für Reset
                if self.timer_stopped:
                    TimerData.start_minute = minute
                    TimerData.start_second = second
                
                TimerData.is_running = True
                TimerData.is_paused = False
            else:  # game_time
                if self.timer_stopped:
                    GameTimeData.minute = minute
                    GameTimeData.second = second
                
                GameTimeData.is_running = True
                GameTimeData.is_paused = False
            
            # Timer-Status aktualisieren
            self.is_running = True
            self.is_paused = False
            self.timer_stopped = False
            
            # UI aktualisieren
            self.update_ui_for_running_timer()
            
            # Timer-Schleife starten
            self.start_timer_loop()
            
            # Server-Update senden
            self.send_server_update(minute, second, True)

    def start_timer_loop(self):
        """Startet die Timer-Schleife auf Basis des Timer-Typs."""
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            
        if self.timer_type == "blind_timer":
            self.timer_id = GLib.timeout_add_seconds(1, self.update_countdown_timer)
        else:  # game_time
            self.timer_id = GLib.timeout_add_seconds(1, self.update_countup_timer)

    def pause_timer(self):
        """Pausiert den Timer."""
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            
        self.is_running = False
        self.is_paused = True
        
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
        """Stoppt den Timer vollständig und setzt ihn zurück."""
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            
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

    def update_countdown_timer(self):
        """Aktualisiert den Countdown-Timer (für Blinds)."""
        minute = TimerData.minute if TimerData.minute is not None else 0
        second = TimerData.second if TimerData.second is not None else 0
        
        # Zeit reduzieren
        if second > 0:
            second -= 1
        else:
            if minute > 0:
                minute -= 1
                second = 59
            else:
                # Timer ist abgelaufen
                self.is_running = False
                self.timer_id = None
                self.update_ui_for_paused_timer()
                return False
        
        # Timer-Daten aktualisieren
        TimerData.minute = minute
        TimerData.second = second
        
        # UI aktualisieren, falls vorhanden
        if self.ui_elements and "minute_label" in self.ui_elements and "second_label" in self.ui_elements:
            self.ui_elements["minute_label"].set_text(f"{minute:02}")
            self.ui_elements["second_label"].set_text(f"{second:02}")
        
        # Status für alle Clients synchronisieren (optional)
        self.send_server_update(minute, second, True)
        
        return True  # Wichtig, damit der Timer weiterläuft

    def update_countup_timer(self):
        """Aktualisiert den Countup-Timer (für Spielzeit)."""
        minute = GameTimeData.minute if GameTimeData.minute is not None else 0
        second = GameTimeData.second if GameTimeData.second is not None else 0
        
        # Zeit erhöhen
        second += 1
        if second >= 60:
            minute += 1
            second = 0
        
        # Timer-Daten aktualisieren
        GameTimeData.minute = minute
        GameTimeData.second = second
        
        # UI aktualisieren, falls vorhanden
        if self.ui_elements and "minute_label" in self.ui_elements and "second_label" in self.ui_elements:
            self.ui_elements["minute_label"].set_text(f"{minute:02}")
            self.ui_elements["second_label"].set_text(f"{second:02}")
        
        # Status für alle Clients synchronisieren (optional)
        self.send_server_update(minute, second, True)
        
        return True  # Wichtig, damit der Timer weiterläuft

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
        """Sendet ein Timer-Update an den Server."""
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'loop'):
            if self.timer_type == "blind_timer":
                asyncio.run_coroutine_threadsafe(
                    self.send_update_timer(minute, second, is_running),
                    self.parent.poker_interface.loop
                )
            else:  # game_time
                asyncio.run_coroutine_threadsafe(
                    self.send_update_game_time(minute, second, is_running),
                    self.parent.poker_interface.loop
                )

    async def send_update_timer(self, minute, second, is_running):
        """Sendet ein Update für den Blinds-Timer an den Server."""
        try:
            server_ip, server_port = self.parent.poker_interface.server_address
            uri = f"ws://{server_ip}:{server_port}"
            message = {
                "command": "update_timer",
                "minute": minute,
                "second": second,
                "is_running": is_running
            }
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print("Timer update sent.")
        except Exception as e:
            print(f"Error sending timer update: {e}")

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
