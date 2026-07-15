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

        self.set_modal(True)

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

        # Timer für Admin-Fenster starten
        self.start_admin_timer()





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

        # "Spielerplatzierung" Button
        player_position_button = Gtk.Button(label="Spielerplatzierung")
        player_position_button.set_size_request(165, 40)
        player_position_button.connect("clicked", self.open_player_position_window)
        self.add(player_position_button)
        self.fixed.put(player_position_button, 30, 220)

        # Tabelle für Blinds erstellen
        self.create_blinds_table()

        # Tabelle für Timer erstellen
        self.create_timer_table()

        # "Zurück" Button unten rechts hinzufügen
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def open_player_position_window(self, widget):
        """Öffnet das Spielerplatzierungsfenster und aktualisiert es mit Live-Daten."""
        if self.player_window:
            self.player_window.present()
            return

        self.player_window = PlayerPositionWindow([])
        self.player_window.connect("destroy", self.on_player_window_closed)
        self.player_window.show_all()

        self.update_player_window()

    def on_player_window_closed(self, widget):
        """Behandelt das Schließen des Spielerplatzierungsfensters."""
        print("Spielerplatzierungsfenster geschlossen.")
        self.player_window = None

        # Entferne den Timer, wenn er noch läuft
        if hasattr(self, "update_timer_id") and self.update_timer_id is not None:
            GLib.source_remove(self.update_timer_id)
            print("⏱ Timer für Spielerplatzierungs-Updates gestoppt.")
            self.update_timer_id = None

        # Schließe die WebSocket-Verbindung
        async def close_websocket():
            if self.persistent_websocket:
                try:
                    await self.persistent_websocket.close()
                    print("🌐 WebSocket-Verbindung geschlossen.")
                except Exception as e:
                    print(f"⚠ Fehler beim Schließen der WebSocket-Verbindung: {e}")
                finally:
                    self.persistent_websocket = None

        asyncio.run_coroutine_threadsafe(close_websocket(), self.poker_interface.loop)


    def update_player_window(self):
        """Aktualisiert die Spielerplatzierung mit den Live-Daten vom Server."""
        async def fetch_players():
            try:
                server_ip, server_port = self.poker_interface.server_address
                uri = f"ws://{server_ip}:{server_port}"

                if not self.persistent_websocket:
                    self.persistent_websocket = await websockets.connect(uri)
                    print(f"🌐 WebSocket-Verbindung hergestellt: {uri}")

                # Spielerliste vom Server abrufen
                await self.persistent_websocket.send(json.dumps({"command": "get_status"}))
                message = await self.persistent_websocket.recv()
                data = json.loads(message)
                players = data.get("players", [])
                print(f"🔄 Spieler erhalten: {players}")

                # Spielerplätze im Fenster aktualisieren
                GLib.idle_add(self.player_window.update_player_positions, players)

            except Exception as e:
                print(f"⚠ Fehler beim Abrufen der Spieler: {e}")
                if self.persistent_websocket:
                    await self.persistent_websocket.close()
                    self.persistent_websocket = None

        # Starte den asynchronen Abruf
        asyncio.run_coroutine_threadsafe(fetch_players(), self.poker_interface.loop)

        # Wiederhole das Update alle 5 Sekunden, solange das Fenster offen ist
        if self.player_window:
            self.update_timer_id = GLib.timeout_add_seconds(
                5, lambda: self.update_player_window() or False
            )
        return False  # Timer nicht erneut ausführen





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

    def create_timer_table(self):
        # (Unverändert – siehe ursprünglichen Code)
        self.timer_table = Gtk.Grid()
        self.timer_table.set_row_spacing(5)
        self.timer_table.set_column_spacing(10)
        self.timer_table.set_margin_top(10)
        self.timer_table.set_margin_left(40)

        minute_value = TimerData.minute if TimerData.minute is not None else 0
        second_value = TimerData.second if TimerData.second is not None else 0
        minute = TimerData.start_minute if TimerData.start_minute is not None else 0
        second = TimerData.start_second if TimerData.start_second is not None else 0

        minute_str = str(minute).zfill(2)
        second_str = str(second).zfill(2)
        minute_value_str = str(minute_value).zfill(2)
        second_value_str = str(second_value).zfill(2)

        data = [
            ("Eingestellte Zeit", f"{minute_str}:{second_str}"),
            ("Momentane Zeit", f"{minute_value_str}:{second_value_str}"),
        ]

        self.timer_labels = {}

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
            self.timer_labels[col1] = label2

            frame1 = Gtk.Frame()
            frame1.add(label1)
            frame1.get_style_context().add_class("table-cell")

            frame2 = Gtk.Frame()
            frame2.add(label2)
            frame2.get_style_context().add_class("table-cell")

            self.timer_table.attach(frame1, 0, row, 1, 1)
            self.timer_table.attach(frame2, 1, row, 1, 1)

        self.fixed.put(self.timer_table, 180, 110)

    def update_all_timer_displays(self):
        minute = int(TimerData.minute) if TimerData.minute is not None else 0
        second = int(TimerData.second) if TimerData.second is not None else 0
        status_text = "►" if TimerData.is_running else "‖"

        if hasattr(self, "left_labels") and "Nächste Blinderhöhung" in self.left_labels:
            self.left_labels["Nächste Blinderhöhung"].set_text(f"{status_text} {minute:02}:{second:02}")

        if hasattr(self, "timer_labels") and "Momentane Zeit" in self.timer_labels:
            self.timer_labels["Momentane Zeit"].set_text(f"{status_text} {minute:02}:{second:02}")

    def start_admin_timer(self):
        GLib.timeout_add_seconds(1, self.update_admin_timer)

    def update_admin_timer(self):
        if TimerData.is_running:
            # Hole aktuelle Timer-Werte, setze None-Fallback auf 0
            try:
                current_minute = int(TimerData.minute or 0)
                current_second = int(TimerData.second or 0)
            except Exception as e:
                print("Fehler beim Umwandeln der Timerwerte:", e)
                current_minute, current_second = 0, 0

            # Countdown-Logik
            if current_minute == 0 and current_second == 0:
                # Timer ist abgelaufen – stoppe den Timer
                TimerData.is_running = False
            else:
                if current_second > 0:
                    current_second -= 1
                else:
                    # current_second == 0, aber current_minute > 0
                    current_minute -= 1
                    current_second = 59

            # Aktualisiere die globalen TimerData-Werte
            TimerData.minute = current_minute
            TimerData.second = current_second

            # Aktualisiere die Anzeige im Admin-Fenster
            if hasattr(self, "timer_labels") and "Momentane Zeit" in self.timer_labels:
                new_time = f"{current_minute:02}:{current_second:02}"
                self.timer_labels["Momentane Zeit"].set_text(new_time)

            # Sende den neuen Timerwert an den Server, sodass dieser broadcastet
            asyncio.run_coroutine_threadsafe(
                self.send_update_timer(current_minute, current_second, TimerData.is_running),  # 🔥 Aufruf über self
                self.poker_interface.loop
            )

        # Diese Methode wird jede Sekunde aufgerufen
        return True



    def open_blind_adjustment_window(self, widget):
        blind_window = BlindAdjustmentWindow(self, self.on_blind_values_confirmed)
        blind_window.show_all()

    def open_timer_setting_window(self, widget):
        timer_window = TimerSettingWindow(self, self.on_timer_values_confirmed)
        timer_window.show_all()

    def on_blind_values_confirmed(self, small_blind, big_blind):
        print(f"Bestätigte Werte - Small Blind: {small_blind}, Big Blind: {big_blind}")
        self.update_blinds_table(small_blind, big_blind)
        if self.poker_interface:
            self.poker_interface.update_blinds_in_table(small_blind, big_blind)
        asyncio.run_coroutine_threadsafe(
            self.send_update_blinds(small_blind, big_blind),
            self.poker_interface.loop
        )

    def on_timer_values_confirmed(self, minute, second):
        print(f"Bestätigte Timer-Werte - Minute: {minute}, Sekunde: {second}")
        # Setze die globalen Timer-Daten auf die neuen Werte:
        TimerData.minute = minute
        TimerData.second = second
        TimerData.start_minute = minute
        TimerData.start_second = second
        TimerData.is_running = True

    async def send_update_blinds(self, small_blind, big_blind):
        # Dynamisch ermittelte Server-IP und Port verwenden
        server_ip, server_port = self.poker_interface.server_address
        uri = f"ws://{server_ip}:{server_port}"
        try:
            async with websockets.connect(uri) as websocket:
                message = {
                    "command": "update_blinds",
                    "small_blind": small_blind,
                    "big_blind": big_blind
                }
                await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"⚠ Fehler beim Senden der Blinds: {e}")

    async def send_update_timer(self, minute, second, is_running):
        # Dynamisch ermittelte Server-IP und Port verwenden
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

    def update_blinds_table(self, small_blind, big_blind):
        self.blind_labels["Small Blind"].set_text(small_blind)
        self.blind_labels["Big Blind"].set_text(big_blind)

    def update_timer_table(self, minute, second):
        self.timer_labels["Zeit"].set_text(minute.zfill(2) + ":" + second.zfill(2))

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


if __name__ == "__main__":
    win = PokerInterface(is_admin=False)  # Normaler Client
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
