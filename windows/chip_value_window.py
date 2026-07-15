import gi
import os
import json
import asyncio
import websockets
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.chip_data import ChipData
from windows.chip_value_edit_overlay import ChipValueEditOverlay
from utils.websocket_utils import WebSocketClient
from utils.display_utils import update_client_display

class ChipValueWindow(Gtk.Window):
    """Fenster zur Anzeige und Bearbeitung der Chipwerte.
    Kann sowohl von normalen Clients (is_admin=False) als auch
    vom Admin-Panel (is_admin=True) aufgerufen werden."""
    
    def __init__(self, parent, is_admin=False):
        # Für Admin-Panel: "Chipwerte Verwaltung (Admin)"
        # Für normale Benutzer: "Chipwerte Übersicht"
        title = "Chipwerte Verwaltung (Admin)" if is_admin else "Chipwerte Übersicht"
        super().__init__(title=title)
        
        self.set_default_size(800, 480)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.parent = parent
        self.is_admin = is_admin  # Bestimmt, ob die Werte bearbeitet werden können

        # Variable für Vollbildmodus
        self.is_fullscreen_mode = False

        # Überprüfen, ob das Elternfenster im Vollbildmodus ist
        if hasattr(parent, 'is_fullscreen_mode') and parent.is_fullscreen_mode:
            self.fullscreen()
            self.is_fullscreen_mode = True

        # Hintergrundbild setzen
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.background_image_path = get_image_path("background_start.jpg")
        set_background_image(self.overlay, self.background_image_path)

        # Hauptcontainer erstellen
        self.fixed = Gtk.Fixed()
        self.overlay.add_overlay(self.fixed)

        # UI-Komponenten erstellen
        self.create_ui()

        # Keybindings für Vollbildmodus und Escape
        self.connect("key-press-event", self.on_key_press)
        
        # WebSocket-Client initialisieren (findet Server automatisch via Zeroconf)
        self.ws_client = WebSocketClient(update_display_callback=self.update_display)
        
        # Starte den Netzwerk-Listener
        self.ws_client.start_async_loop()
        
        # Status, um zu verfolgen, ob der Timer aktiv ist
        self.update_timer_active = False
        
        # Starte Timer für die lokale UI-Aktualisierung
        self.update_timer_id = GLib.timeout_add_seconds(1, self.periodic_update)
        self.update_timer_active = True
        
        # Signal für Fenster-Schließen, um Timer zu stoppen
        self.connect("destroy", self.on_window_destroy)

    def create_ui(self):
        # Titel mit angepasstem Text je nach Modus
        title_text = "Chipwerte Verwaltung (Admin)" if self.is_admin else "Chipwerte Übersicht"
        title_label = Gtk.Label()
        title_label.set_markup(f"<span size='x-large' weight='bold' foreground='#CDAD00'>{title_text}</span>")
        title_label.get_style_context().add_class("dialog-text")
        title_label.set_halign(Gtk.Align.CENTER)  # Zentriere den Titel horizontal
        self.fixed.put(title_label, 0, 20)
        title_label.set_size_request(800, -1)  # Setze eine feste Breite für den Titel
        
        # Container für das Grid (für bessere Zentrierung)
        grid_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        grid_container.set_halign(Gtk.Align.CENTER)  # Zentrierter Container
        grid_container.set_size_request(800, -1)  # Nutze volle Fensterbreite
        
        # Liste der Chip-Bilder sortiert nach Wert (aufsteigend)
        sorted_chips = sorted(ChipData.CHIPS.items(), key=lambda x: x[1])
        
        # Widgets für CHF-Werte speichern, um sie später aktualisieren zu können
        self.chf_labels = {}
        
        # WICHTIG: Berechne, wie viele Reihen wir haben werden
        column_count = 4
        chip_count = len(sorted_chips)
        full_rows = chip_count // column_count
        last_row_items = chip_count % column_count
        total_rows = full_rows + (1 if last_row_items > 0 else 0)
        
        # Erstelle für jede Reihe einen eigenen Container
        for row in range(total_rows):
            # Erstelle einen horizontalen Container für diese Reihe
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
            row_box.set_halign(Gtk.Align.CENTER)  # Zentriere die Reihe
            
            # Bestimme Start- und Endindex für diese Reihe
            start_idx = row * column_count
            # Für die letzte Reihe: nur die übrigen Items
            if row == full_rows and last_row_items > 0:
                end_idx = start_idx + last_row_items
            else:
                end_idx = start_idx + column_count
            
            # Füge Chips für diese Reihe hinzu
            for i in range(start_idx, min(end_idx, chip_count)):
                chip_file, chip_value = sorted_chips[i]
                
                # Container für den Chip und seine Werte
                chip_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                chip_box.set_margin_start(10)
                chip_box.set_margin_end(10)
                
                # Chip-Bild laden und anzeigen
                chip_path = os.path.join("Chips", chip_file)
                full_path = get_image_path(chip_path)
                
                if os.path.exists(full_path):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 100, 100, True)
                    chip_image = Gtk.Image.new_from_pixbuf(pixbuf)
                    chip_box.pack_start(chip_image, False, False, 0)
                
                # Chip-Wert anzeigen
                value_label = Gtk.Label(label=f"{chip_value} Chips")
                value_label.get_style_context().add_class("green-text")
                chip_box.pack_start(value_label, False, False, 0)
                
                # CHF-Wert anzeigen und ggf. editierbar machen
                chf_value = ChipData.chf_values.get(chip_file, 0.0)
                
                # CHF-Wert formatieren - Zeige "-" an, wenn Wert 0 ist
                chf_display = "-" if chf_value == 0.0 else f"CHF {chf_value:.2f}"
                chf_label = Gtk.Label(label=chf_display)
                chf_label.get_style_context().add_class("green-text")
                
                if self.is_admin:
                    # Admin-Modus: Button mit CHF-Wert
                    chf_button = Gtk.Button()
                    chf_button.add(chf_label)
                    chf_button.get_style_context().add_class("time-button")  # Stilwiederverwendung
                    chf_button.connect("clicked", self.on_chf_button_clicked, chip_file, chip_value)
                    chip_box.pack_start(chf_button, False, False, 0)
                else:
                    # Nicht-Admin-Modus: Nur Label
                    chip_box.pack_start(chf_label, False, False, 0)
                
                # CHF-Label-Referenz speichern
                self.chf_labels[chip_file] = chf_label
                
                # Zum Reihen-Container hinzufügen
                row_box.pack_start(chip_box, False, False, 0)
            
            # Füge die Reihe zum Hauptcontainer hinzu
            grid_container.pack_start(row_box, False, False, 10)
        
        # Container zum Fixed-Layout hinzufügen
        self.fixed.put(grid_container, 0, 80)
        
        # Status-Label hinzufügen für Aktualisierungsstatus
        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_valign(Gtk.Align.CENTER)
        self.status_label.set_size_request(400, 30)
        self.status_label.get_style_context().add_class("green-text")
        self.fixed.put(self.status_label, 20, 420)
        
        # "Schließen"-Button unten rechts
        back_button = Gtk.Button(label="Schliessen")
        back_button.set_size_request(100, 40)
        back_button.connect("clicked", self.on_back_button_click)
        back_button.get_style_context().add_class("button-custom")
        self.fixed.put(back_button, 658, 416)

    def update_chf_labels(self):
        """Aktualisiert alle CHF-Labels mit aktuellen Werten aus ChipData.chf_values."""
        for chip_file, label in self.chf_labels.items():
            chf_value = ChipData.chf_values.get(chip_file, 0.0)
            # Zeige "-" an, wenn Wert 0 ist
            chf_display = "-" if chf_value == 0.0 else f"CHF {chf_value:.2f}"
            label.set_text(chf_display)
        
        # Zeige Debug-Info an
        self.status_label.set_text(f"Aktualisiert: {len(self.chf_labels)} Chipwerte")

    def on_chf_button_clicked(self, button, chip_file, chip_value):
        """Öffnet das Overlay zum Bearbeiten des CHF-Werts."""
        if not self.is_admin:
            return  # Sicherheitscheck
            
        # Aktueller CHF-Wert des Chips
        current_chf = ChipData.chf_values.get(chip_file, 0.0)
        
        # Overlay erstellen
        edit_overlay = ChipValueEditOverlay(self, chip_file, chip_value, current_chf, self.on_chf_value_updated)
        edit_overlay.show_all()

    def on_chf_value_updated(self, chip_file, new_chf_value):
        """Callback zum Aktualisieren eines CHF-Werts."""
        # Neuen Wert setzen und alle anderen entsprechend aktualisieren
        ChipData.set_chf_value(chip_file, new_chf_value)
        
        # UI aktualisieren
        self.update_chf_labels()
        
        # Update an Server senden
        self.send_chip_values_to_server()

    def send_chip_values_to_server(self):
        """Sendet aktualisierte Chip-Werte an den Server."""
        # Event-Loop finden
        loop = None
        
        # Verschiedene mögliche Orte für die Loop überprüfen
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'loop'):
            loop = self.parent.poker_interface.loop
        elif hasattr(self.parent, 'loop'):
            loop = self.parent.loop
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'loop'):
            loop = self.parent.ws_client.loop
        
        if not loop:
            print("FEHLER: Konnte asyncio-Loop nicht finden!")
            self.status_label.set_text("Fehler: Konnte keine Verbindung zum Server herstellen")
            return
            
        # Update an Server senden
        asyncio.run_coroutine_threadsafe(
            self.send_chip_values_update(),
            loop
        )

    async def send_chip_values_update(self):
        """Sendet die aktualisierten Chip-Werte asynchron an den Server."""
        # Server-Adresse ermitteln
        server_address = None
        
        if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
            server_address = self.parent.poker_interface.server_address
        elif hasattr(self.parent, 'server_address'):
            server_address = self.parent.server_address
        elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
            server_address = self.parent.ws_client.server_address
        
        if not server_address:
            print("FEHLER: Konnte Server-Adresse nicht finden!")
            GLib.idle_add(lambda: self.status_label.set_text("Fehler: Keine Server-Adresse gefunden"))
            return
            
        server_ip, server_port = server_address
        uri = f"ws://{server_ip}:{server_port}"
        
        try:
            async with websockets.connect(uri) as websocket:
                message = {
                    "command": "update_chip_values",
                    "chip_values": ChipData.chf_values
                }
                await websocket.send(json.dumps(message))
                GLib.idle_add(lambda: self.status_label.set_text(f"Gesendet: Chip-Werte an {server_ip}:{server_port}"))
        except Exception as e:
            error_msg = f"Fehler beim Senden der Chip-Werte: {e}"
            print(error_msg)
            GLib.idle_add(lambda: self.status_label.set_text(error_msg))
    
    def periodic_update(self):
        """
        Aktualisiert die Anzeige regelmäßig basierend auf den aktuellen ChipData-Werten.
        Nutzt den bestehenden Aktualisierungsmechanismus statt direkter Server-Anfragen.
        """
        if not self.update_timer_active:
            return False  # Timer abbrechen, wenn nicht mehr aktiv
            
        # UI-Update direkt basierend auf den aktuellen ChipData-Werten
        self.update_chf_labels()
        
        # Status aktualisieren
        self.status_label.set_text("Auto-Update: Chipwerte aktualisiert")
        
        return True  # Damit der Timer weiterläuft
    
    def update_display(self, data):
        """
        Callback für den WebSocketClient. Wird aufgerufen, wenn neue Daten vom Server empfangen werden.
        Nutzt die gemeinsame update_client_display Funktion aus display_utils.
        """
        # Nutzt die gleiche Funktion wie alle anderen Fenster
        update_client_display(self, data)
        
        # Status aktualisieren, wenn Chipwerte empfangen wurden
        if "chip_values" in data:
            self.status_label.set_text(f"Server-Update: Chipwerte aktualisiert")
    
    def on_window_destroy(self, widget):
        """Wird aufgerufen, wenn das Fenster geschlossen wird."""
        # Timer deaktivieren
        self.update_timer_active = False
        
        # Timer entfernen, wenn er existiert
        if hasattr(self, "update_timer_id") and self.update_timer_id:
            GLib.source_remove(self.update_timer_id)
            self.update_timer_id = None

    def on_back_button_click(self, widget):
        """Schließt das Fenster."""
        self.close()

    def on_key_press(self, widget, event):
        """Keybindings für Escape und F11."""
        if event.keyval == Gdk.KEY_Escape:
            if self.is_fullscreen_mode:
                self.unfullscreen()
                self.is_fullscreen_mode = False
            else:
                self.close()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        """Schaltet zwischen Vollbild und Fenstergröße um."""
        if self.is_fullscreen_mode:
            self.unfullscreen()
            self.is_fullscreen_mode = False
        else:
            self.fullscreen()
            self.is_fullscreen_mode = True
