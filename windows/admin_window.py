import gi
import websockets
import json
import asyncio
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from windows.player_position_window import PlayerPositionWindow
from windows.blind_adjustment_window import BlindAdjustmentWindow
from windows.timer_setting_window import TimerSettingWindow
from data.blind_data import BlindData
from data.timer_data import TimerData
from data.game_time_data import GameTimeData


class AdminWindow(Gtk.Window):
    def __init__(self, poker_interface):
        super().__init__(title="Admin Panel")
        self.poker_interface = poker_interface  # Referenz auf das Poker-Interface speichern
        self.set_default_size(800, 480)

        # Spielerplatzierungsfenster-Referenz
        self.player_window = None
        self.persistent_websocket = None

        # Setze das Admin-Fenster als untergeordnetes Fenster des Poker-Interfaces
        if self.poker_interface:
            self.set_transient_for(self.poker_interface)  

        # Variable für Vollbildmodus initialisieren
        self.is_fullscreen_mode = False

        # Überprüfen, ob das Poker-Interface im Vollbildmodus ist
        if self.poker_interface and self.poker_interface.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)

        # Hintergrundbild setzen
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        # Gtk.Fixed verwenden, um die Widgets an festen Positionen zu platzieren
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # Benutzeroberfläche erstellen
        self.create_ui()

        # Starte einen Timer, der die Blind-Tabelle jede Sekunde aktualisiert
        GLib.timeout_add_seconds(1, self.update_blinds_table)

        # Timer für Admin-Fenster starten
        self.start_admin_timer()
        # ★ Hier starten wir auch den Spielzeit-Timer:
        self.start_game_time_timer()


    def create_ui(self):
        # "Blinds anpassen" Button
        adjust_blinds_button = Gtk.Button(label="Blinds anpassen")
        adjust_blinds_button.set_size_request(165, 40)
        adjust_blinds_button.connect("clicked", self.open_blind_adjustment_window)
        adjust_blinds_button.connect("enter-notify-event", self.on_hover)
        adjust_blinds_button.connect("leave-notify-event", self.on_leave)
        adjust_blinds_button.get_style_context().add_class("button-custom")
        self.fixed.put(adjust_blinds_button, 30, 20)
        
        # "Blinds Zeiten" Button
        blinds_times_button = Gtk.Button(label="Blinds Zeiten")
        blinds_times_button.set_size_request(165, 40)
        blinds_times_button.connect("clicked", self.open_timer_setting_window)
        blinds_times_button.connect("enter-notify-event", self.on_hover)
        blinds_times_button.connect("leave-notify-event", self.on_leave)
        blinds_times_button.get_style_context().add_class("button-custom")
        self.fixed.put(blinds_times_button, 30, 120)

        # Button "Spielzeit" (statt "Gesamtspielzeit")
        spielzeit_button = Gtk.Button(label="Spielzeit")
        spielzeit_button.set_size_request(165, 40)
        spielzeit_button.connect("clicked", self.open_total_game_time_window)
        spielzeit_button.get_style_context().add_class("button-custom")
        self.fixed.put(spielzeit_button, 30, 220)  # Position anpassen

        # "Spielerplatzierung" Button
        player_position_button = Gtk.Button(label="Spielerplatzierung")
        player_position_button.set_size_request(165, 40)
        player_position_button.connect("clicked", self.open_player_position_window)
        player_position_button.connect("enter-notify-event", self.on_hover)
        player_position_button.connect("leave-notify-event", self.on_leave)
        player_position_button.get_style_context().add_class("button-custom")
        self.fixed.put(player_position_button, 605, 20)

        # Tabelle für Blinds erstellen
        self.create_blinds_table()

        # Tabelle für Timer erstellen
        self.create_timer_table()
        
        # Tabelle für Spielzeit erstellen
        self.create_game_time_table()
        
        # "Zurück" Button unten rechts hinzufügen
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)


    def open_total_game_time_window(self, widget):
        # Öffnet das Gesamtspielzeit-Fenster mit einem Dummy-Callback
        total_time_window = __import__("windows.total_game_time_window", fromlist=["TotalGameTimeWindow"]).TotalGameTimeWindow(
            self, confirm_callback=lambda *args: None
        )
        total_time_window.show_all()

    def create_blinds_table(self):
        # (Unverändert – siehe ursprünglichen Code)
        self.blinds_table = Gtk.Grid()
        self.blinds_table.set_row_spacing(5)
        self.blinds_table.set_column_spacing(10)
        self.blinds_table.set_margin_top(10)
        self.blinds_table.set_margin_left(40)

        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "n.V."
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "n.V."

        data = [
            ("Small Blind", small_blind_value),
            ("Big Blind", big_blind_value),
        ]

        self.blind_labels = {}

        for row, (col1, col2) in enumerate(data):
            label1 = Gtk.Label(label=col1)
            label2 = Gtk.Label(label=col2)
            label1.set_size_request(150, 25)
            label2.set_size_request(70, 25)
            label1.set_xalign(0.0)
            label1.set_margin_left(6)
            label2.set_xalign(1.0)
            label2.set_margin_right(6)
            label1.get_style_context().add_class("green-text")
            label2.get_style_context().add_class("green-text")
            self.blind_labels[col1] = label2

            frame1 = Gtk.Frame()
            frame1.add(label1)
            frame1.get_style_context().add_class("table-cell")

            frame2 = Gtk.Frame()
            frame2.add(label2)
            frame2.get_style_context().add_class("table-cell")

            self.blinds_table.attach(frame1, 0, row, 1, 1)
            self.blinds_table.attach(frame2, 1, row, 1, 1)

        self.fixed.put(self.blinds_table, 180, 6)

    def create_game_time_table(self):
        from data.game_time_data import GameTimeData
        self.game_time_table = Gtk.Grid()
        self.game_time_table.set_row_spacing(5)
        self.game_time_table.set_column_spacing(10)
        self.game_time_table.set_margin_top(10)
        self.game_time_table.set_margin_left(40)

        # Hole die aktuelle Spielzeit
        game_minute = GameTimeData.minute if GameTimeData.minute is not None else 0
        game_second = GameTimeData.second if GameTimeData.second is not None else 0

        # Formatierung der Spielzeit
        game_time_str = f"{str(game_minute).zfill(2)}:{str(game_second).zfill(2)}"

        # Daten: Eine Zeile – Titel "Spielzeit" und der Zeitwert
        data = [
            ("Spielzeit", game_time_str),
        ]

        self.game_time_labels = {}

        for row, (title, time_str) in enumerate(data):
            label_title = Gtk.Label(label=title)
            label_time = Gtk.Label(label=time_str)
            label_title.set_size_request(150, 25)
            label_time.set_size_request(70, 25)
            label_title.set_xalign(0.0)
            label_title.set_margin_left(6)
            label_time.set_xalign(1.0)
            label_time.set_margin_right(6)
            label_title.get_style_context().add_class("green-text")
            label_time.get_style_context().add_class("green-text")
            
            # Speichere das Zeit-Label, damit es später aktualisiert werden kann
            self.game_time_labels[title] = label_time

            frame_title = Gtk.Frame()
            frame_title.add(label_title)
            frame_title.get_style_context().add_class("table-cell")

            frame_time = Gtk.Frame()
            frame_time.add(label_time)
            frame_time.get_style_context().add_class("table-cell")

            self.game_time_table.attach(frame_title, 0, row, 1, 1)
            self.game_time_table.attach(frame_time, 1, row, 1, 1)

        # Positioniere die Tabelle – hier als Beispiel bei (180, 224)
        self.fixed.put(self.game_time_table, 180, 224)

    async def send_start_timer(self, minute, second):
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
             "command": "start_timer",
             "minute": minute,
             "second": second,
             "is_running": True
        }
        try:
             async with websockets.connect(uri) as websocket:
                 await websocket.send(json.dumps(message))
                 print("Start Timer Update gesendet.")
        except Exception as e:
             print(f"Fehler beim Senden des Start-Timers: {e}")

    async def send_pause_timer(self, minute, second):
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
             "command": "pause_timer",
             "minute": minute,
             "second": second,
             "is_running": False
        }
        try:
             async with websockets.connect(uri) as websocket:
                 await websocket.send(json.dumps(message))
                 print("Pause Timer Update gesendet.")
        except Exception as e:
             print(f"Fehler beim Senden des Pause-Timers: {e}")

    async def send_stop_timer(self, minute, second):
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
             "command": "stop_timer",
             "minute": minute,
             "second": second,
             "is_running": False
        }
        try:
             async with websockets.connect(uri) as websocket:
                 await websocket.send(json.dumps(message))
                 print("Stop Timer Update gesendet.")
        except Exception as e:
             print(f"Fehler beim Senden des Stop-Timers: {e}")

    def create_timer_table(self):
        self.timer_table = Gtk.Grid()
        self.timer_table.set_row_spacing(5)
        self.timer_table.set_column_spacing(10)
        self.timer_table.set_margin_top(10)
        self.timer_table.set_margin_left(40)

        # Hole die eingestellte Zeit (Startzeit)
        set_minute = TimerData.start_minute if TimerData.start_minute is not None else 0
        set_second = TimerData.start_second if TimerData.start_second is not None else 0

        # Hole die momentane Zeit
        current_minute = TimerData.minute if TimerData.minute is not None else 0
        current_second = TimerData.second if TimerData.second is not None else 0

        # Formatierung der Zeiten
        set_time_str = f"{str(set_minute).zfill(2)}:{str(set_second).zfill(2)}"
        current_time_str = f"{str(current_minute).zfill(2)}:{str(current_second).zfill(2)}"

        # Daten: Erste Zeile: eingestellte Zeit, Zweite Zeile: momentane Zeit
        data = [
            ("Eingestellte Zeit", set_time_str),
            ("Momentane Zeit", current_time_str),
        ]

        self.timer_labels = {}

        for row, (title, time_str) in enumerate(data):
            label_title = Gtk.Label(label=title)
            label_time = Gtk.Label(label=time_str)
            label_title.set_size_request(150, 25)
            label_time.set_size_request(70, 25)
            label_title.set_xalign(0.0)
            label_title.set_margin_left(6)
            label_time.set_xalign(1.0)
            label_time.set_margin_right(6)
            label_title.get_style_context().add_class("green-text")
            label_time.get_style_context().add_class("green-text")
            
            # Speichere die Zeit-Labels in einem Dictionary, um sie später updaten zu können
            self.timer_labels[title] = label_time

            frame_title = Gtk.Frame()
            frame_title.add(label_title)
            frame_title.get_style_context().add_class("table-cell")

            frame_time = Gtk.Frame()
            frame_time.add(label_time)
            frame_time.get_style_context().add_class("table-cell")

            self.timer_table.attach(frame_title, 0, row, 1, 1)
            self.timer_table.attach(frame_time, 1, row, 1, 1)

        self.fixed.put(self.timer_table, 180, 110)



    def open_player_position_window(self, widget):
        """Öffnet das Spielerplatzierungsfenster und aktualisiert es mit Live-Daten vom Server."""
        if hasattr(self, "player_window") and self.player_window:
            self.player_window.present()
            return

        self.player_window = PlayerPositionWindow([])
        self.player_window.connect("destroy", self.on_player_window_closed)
        self.player_window.show_all()
        self.update_player_window()


    def on_player_window_closed(self, widget):
        print("Spielerplatzierungsfenster geschlossen.")
        self.player_window = None
        if hasattr(self, "update_timer_id") and self.update_timer_id is not None:
            GLib.source_remove(self.update_timer_id)
            print("⏱ Timer für Spielerplatzierungs-Updates gestoppt.")
            self.update_timer_id = None

        async def close_websocket():
            if self.persistent_websocket:
                try:
                    await self.persistent_websocket.close()
                    print("WebSocket-Verbindung geschlossen.")
                except Exception as e:
                    print(f"⚠ Fehler beim Schließen der WebSocket-Verbindung: {e}")
                finally:
                    self.persistent_websocket = None

        asyncio.run_coroutine_threadsafe(close_websocket(), self.poker_interface.loop)


    def open_blind_adjustment_window(self, widget):
        blind_window = BlindAdjustmentWindow(self, self.on_blind_values_confirmed)
        blind_window.show_all()


    def open_timer_setting_window(self, widget):
        timer_window = TimerSettingWindow(self, self.on_timer_values_confirmed)
        timer_window.show_all()


    def update_player_window(self):
        async def fetch_players():
            try:
                server_ip, server_port = self.poker_interface.server_address
                uri = f"ws://{server_ip}:{server_port}"

                if not self.persistent_websocket:
                    self.persistent_websocket = await websockets.connect(uri)
                    print(f"WebSocket-Verbindung hergestellt: {uri}")

                await self.persistent_websocket.send(json.dumps({"command": "get_status"}))
                message = await self.persistent_websocket.recv()
                data = json.loads(message)
                players = data.get("players", [])
                print(f"Spieler erhalten: {players}")
                GLib.idle_add(self.player_window.update_player_positions, players)

            except Exception as e:
                print(f"⚠ Fehler beim Abrufen der Spieler: {e}")
                if self.persistent_websocket:
                    await self.persistent_websocket.close()
                    self.persistent_websocket = None

        asyncio.run_coroutine_threadsafe(fetch_players(), self.poker_interface.loop)
        if self.player_window:
            self.update_timer_id = GLib.timeout_add_seconds(1, lambda: self.update_player_window() or False)
        return False

    def start_blinds_update(self):
        # Sende initial die Blind-Daten und wiederhole das Senden z. B. alle 5 Sekunden
        GLib.timeout_add_seconds(1, self.update_blinds)

    def start_blinds_update_table(self):
        # Sende initial die Blind-Daten und wiederhole das Senden z. B. alle 5 Sekunden
        GLib.timeout_add_seconds(1, self.update_blinds_table)

    def update_blinds(self):
        # Hier werden die aktuellen Blind-Daten an den Server gesendet
        asyncio.run_coroutine_threadsafe(
            self.send_update_blinds(BlindData.small_blind, BlindData.big_blind),
            self.poker_interface.loop
        )
        return True  # Damit der Timeout-Callback weiterläuft


    def start_admin_timer(self):
        GLib.timeout_add_seconds(1, self.update_admin_timer)

    def update_admin_timer(self):
        if TimerData.is_running:
            try:
                current_minute = int(TimerData.minute or 0)
                current_second = int(TimerData.second or 0)
                set_minute = int(TimerData.start_minute or 0)
                set_second = int(TimerData.start_second or 0)
            except Exception as e:
                print("Fehler beim Umwandeln der Timerwerte:", e)
                current_minute, current_second, set_minute, set_second = 0, 0, 0, 0

            if current_minute == 0 and current_second == 0:
                TimerData.is_running = False
            else:
                if current_second > 0:
                    current_second -= 1
                else:
                    current_minute -= 1
                    current_second = 59

            if hasattr(self, "timer_labels") and "Eingestellte Zeit" in self.timer_labels:
                new_set_time = f"{set_minute:02}:{set_second:02}"
                self.timer_labels["Eingestellte Zeit"].set_text(new_set_time)

            if hasattr(self, "timer_labels") and "Momentane Zeit" in self.timer_labels:
                new_time = f"{current_minute:02}:{current_second:02}"
                self.timer_labels["Momentane Zeit"].set_text(new_time)

            asyncio.run_coroutine_threadsafe(
                self.send_update_timer(current_minute, current_second, TimerData.is_running),
                self.poker_interface.loop
            )
        return True

    def start_game_time_timer(self):
        self.game_time_timer_id = GLib.timeout_add_seconds(1, self.update_game_time)

    def update_game_time(self):
        from data.game_time_data import GameTimeData
        # Nur hochzählen, wenn der Timer wirklich läuft:
        if GameTimeData.is_running:
            GameTimeData.second += 1
            if GameTimeData.second >= 60:
                GameTimeData.second = 0
                GameTimeData.minute += 1

        # Wähle das Symbol: "" wenn aktiv, ‖ wenn pausiert
        status_symbol = "" if GameTimeData.is_running else "‖"
        new_game_time = f"{status_symbol} {GameTimeData.minute:02}:{GameTimeData.second:02}"
        self.game_time_labels["Spielzeit"].set_text(new_game_time)

        asyncio.run_coroutine_threadsafe(
            self.send_update_game_time(GameTimeData.minute, GameTimeData.second),
            self.poker_interface.loop
        )
        return True



    async def send_update_game_time(self, minute, second):
        import websockets, json
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
            "command": "update_game_time",
            "game_time_minute": minute,
            "game_time_second": second,
            "is_running": GameTimeData.is_running
        }
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"Error sending game time update: {e}")

    def on_blind_values_confirmed(self, small_blind, big_blind):
        print(f"Bestätigte Werte - Small Blind: {small_blind}, Big Blind: {big_blind}")
        from data.blind_data import BlindData  # Sicherstellen, dass BlindData importiert ist
        BlindData.small_blind = small_blind
        BlindData.big_blind = big_blind
        # Sende die neuen Blind-Daten direkt an den Server
        asyncio.run_coroutine_threadsafe(
             self.send_update_blinds(small_blind, big_blind),
             self.poker_interface.loop
        )
    
    def on_timer_values_confirmed(self, minute, second):
        print(f"Bestätigte Timer-Werte - Minute: {minute}, Sekunde: {second}")
        TimerData.minute = minute
        TimerData.second = second
        TimerData.start_minute = minute
        TimerData.start_second = second
        TimerData.is_running = True

    async def send_update_blinds(self, small_blind, big_blind):
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        message = {
             "command": "update_blinds",
             "small_blind": small_blind,
             "big_blind": big_blind
        }
        try:
             async with websockets.connect(uri) as websocket:
                 await websocket.send(json.dumps(message))
                 print("Blind update sent.")
        except Exception as e:
             print(f"Fehler beim Senden der Blinds: {e}")


    async def send_update_timer(self, minute, second, is_running):
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        try:
            async with websockets.connect(uri) as websocket:
                message = {
                    "command": "update_timer",
                    "minute": minute,
                    "second": second,
                    "is_running": is_running
                }
                await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"⚠ Fehler beim Senden des Timers: {e}")

    def update_blinds_table(self):
        # Hole die aktuellen Werte – falls None, setze einen Standardwert
        small_blind_value = BlindData.small_blind if BlindData.small_blind is not None else "n.V."
        big_blind_value = BlindData.big_blind if BlindData.big_blind is not None else "n.V."
        # Aktualisiere die Labels, die du beim Erstellen der Blinds-Tabelle gespeichert hast
        if "Small Blind" in self.blind_labels:
            self.blind_labels["Small Blind"].set_text(small_blind_value)
        if "Big Blind" in self.blind_labels:
            self.blind_labels["Big Blind"].set_text(big_blind_value)
        return True  # Wichtig, damit der Timer weiterläuft



    def update_timer_table(self):
        set_minute = TimerData.start_minute if TimerData.start_minute is not None else 0
        set_second = TimerData.start_second if TimerData.start_second is not None else 0

        current_minute = TimerData.minute if TimerData.minute is not None else 0
        current_second = TimerData.second if TimerData.second is not None else 0

        set_time_str = f"{str(set_minute).zfill(2)}:{str(set_second).zfill(2)}"
        current_time_str = f"{str(current_minute).zfill(2)}:{str(current_second).zfill(2)}"

        if "Eingestellte Zeit" in self.timer_labels:
            self.timer_labels["Eingestellte Zeit"].set_text(set_time_str)
        if "Momentane Zeit" in self.timer_labels:
            self.timer_labels["Momentane Zeit"].set_text(current_time_str)

    def on_back_button_click(self, widget):
        self.close()

    def on_hover(self, widget, event):
        widget.get_style_context().add_class("hovered")
        if hasattr(self, 'hover_timer') and self.hover_timer:
            GLib.source_remove(self.hover_timer)
        self.hover_timer = GLib.timeout_add(500, self.remove_hover_effect, widget)

    def on_leave(self, widget, event):
        if hasattr(self, 'hover_timer') and self.hover_timer:
            GLib.source_remove(self.hover_timer)
        self.hover_timer = GLib.timeout_add(200, self.remove_hover_effect, widget)

    def remove_hover_effect(self, widget):
        widget.get_style_context().remove_class("hovered")
        self.hover_timer = None
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.set_default_size(800, 480)
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True

    def update_all_timer_displays(self):
            minute = int(TimerData.minute) if TimerData.minute is not None else 0
            second = int(TimerData.second) if TimerData.second is not None else 0
            status_text = "" if TimerData.is_running else "‖"

            if hasattr(self, "left_labels") and "Nächste Blinderhöhung" in self.left_labels:
                self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")

            if hasattr(self, "timer_labels") and "Momentane Zeit" in self.timer_labels:
                self.timer_labels["Momentane Zeit"].set_text(f"{status_text} {minute:02}:{second:02}")


if __name__ == "__main__":
    win = PokerInterface(is_admin=False)  # Normaler Client
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
