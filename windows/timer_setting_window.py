import gi
gi.require_version('Gtk', '3.0')
import asyncio
import websockets
import json
from gi.repository import Gtk, Gdk, GLib
from utils.helpers import set_background_image, format_timer_with_status
from utils.resources import get_image_path
from data.timer_data import TimerData
from utils.timer_controller import create_blind_timer
from utils.websocket_utils import WebSocketClient
from utils.display_utils import update_client_display


class TimerSettingWindow(Gtk.Window):
	def __init__(self, parent, confirm_callback):
		super().__init__(title="Timer einstellen")
		self.parent = parent  # Hier speichern wir parent als Instanzvariable
		self.set_default_size(800, 480)
		self.set_transient_for(parent)
		self.set_modal(True)

		# Variable für Vollbildmodus initialisieren
		self.is_fullscreen_mode = False

		# Überprüfen, ob das Elternfenster im Vollbildmodus ist
		if parent.is_fullscreen_mode:
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

		self.numpad_buttons = []

		# Zellen für Minuten und Sekunden erstellen
		self.create_timer_cells()

		# NumPad erstellen
		self.create_numpad()

		# Wenn Timer läuft oder pausiert ist: NumPad **und** Zeit‑Felder deaktivieren
		if TimerData.is_running or TimerData.is_paused:
			for btn in self.numpad_buttons:
				btn.set_sensitive(False)
			self.button_minute.set_sensitive(False)
			self.button_second.set_sensitive(False)
			self.button_start.set_sensitive(False)
			self.button_pause.set_sensitive(True)
			self.button_stop.set_sensitive(True)

		# "Zurück" Button hinzufügen
		self.create_back_button()

		# Aktuelles Eingabefeld (Minuten oder Sekunden)
		self.current_time = None

		# Flag, um zu verfolgen, ob eine neue Eingabe begonnen wurde
		self.new_entry = False

		# Bestätigungs-Callback
		self.confirm_callback = confirm_callback

		# Keybindings für Vollbildmodus und Escape
		self.connect("key-press-event", self.on_key_press)

		# TimerController initialisieren - zentrale Timer-Steuerung
		self.blind_timer = create_blind_timer(
			self, 
			{
				"minute_label": self.label_minute,
				"second_label": self.label_second,
				"start_button": self.button_start,
				"pause_button": self.button_pause,
				"stop_button": self.button_stop,
				"fields": [self.button_minute, self.button_second]
			}
		)

		# Buttons mit dem Controller verbinden
		self.button_start.connect("clicked", self.on_start_clicked)
		self.button_pause.connect("clicked", lambda _: self.blind_timer.pause_timer())
		self.button_stop.connect("clicked", self.on_stop_clicked)

		# WebSocket-Client initialisieren (findet Server automatisch via Zeroconf)
		self.ws_client = WebSocketClient(update_display_callback=self.update_display)
        
		# Starte den Netzwerk-Listener
		self.ws_client.start_async_loop()
		
		# In deiner __init__-Methode, nachdem die Timer-Felder (z. B. self.label_minute und self.label_second) angelegt wurden:
		GLib.timeout_add_seconds(1, self.update_timer_fields)

	def on_start_clicked(self, _):
		# Timer (neu) starten — nur bei NEUEM Start die konfigurierte Zeit überschreiben
		if TimerData.is_paused:
			# Resume: keine Änderung der Startzeit
			self.blind_timer.start_timer()
		else:
			minute = int(self.label_minute.get_text())
			second = int(self.label_second.get_text())
			self.confirm_callback(minute, second)
			self.blind_timer.start_timer()

		# NumPad deaktivieren
		for btn in self.numpad_buttons:
			btn.set_sensitive(False)

		# Nur Pause & Stop aktivieren
		self.button_pause.set_sensitive(True)
		self.button_stop.set_sensitive(True)

	def on_stop_clicked(self, _):
		# Blinds‑Timer stoppen
		self.blind_timer.stop_timer()

		# Alle NumPad‑Buttons wieder aktivieren
		for btn in self.numpad_buttons:
			btn.set_sensitive(True)

		# Pause und Stop bleiben deaktiviert
		self.button_pause.set_sensitive(False)
		self.button_stop.set_sensitive(False)

	def update_timer_fields(self):
		# Nur aktualisieren, wenn der Timer tatsächlich läuft
		if TimerData.is_running:
			minute = TimerData.minute if TimerData.minute is not None else 0
			second = TimerData.second if TimerData.second is not None else 0
			self.label_minute.set_text(f"{int(minute):02}")
			self.label_second.set_text(f"{int(second):02}")
		
		return True  # Damit der GLib-Callback fortlaufend aufgerufen wird

	def update_display(self, data):
		# data enthält den Serverstatus, inklusive "timer_running"
		timer_running = data.get("timer_running", False)
		if timer_running:
			self.button_start.set_sensitive(False)
			self.button_pause.set_sensitive(True)
			self.button_stop.set_sensitive(True)
		elif TimerData.is_paused:
			# Timer ist pausiert → Stop bleibt aktiv
			self.button_start.set_sensitive(True)
			self.button_pause.set_sensitive(False)
			self.button_stop.set_sensitive(True)
		else:
			# Timer ist gestoppt → Stop deaktivieren
			self.button_start.set_sensitive(True)
			self.button_pause.set_sensitive(False)
			self.button_stop.set_sensitive(False)

	def create_timer_cells(self):
		# Container für die Zeit auf der linken Seite
		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
		vbox.set_homogeneous(False)
		self.fixed.put(vbox, 130, 100)  # Position anpassen

		# Minuten Titel
		label_minute_title = Gtk.Label(label="Minuten")
		label_minute_title.get_style_context().add_class("time-title")
		vbox.pack_start(label_minute_title, False, False, 5)

		# Minuten Wert
		if not TimerData.is_running:
			self.label_minute = Gtk.Label(label="00")
		else:
			self.label_minute = Gtk.Label(label=f"{TimerData.minute:02}")
			minute = int(TimerData.minute) if TimerData.minute is not None else "-"
			second = int(TimerData.second) if TimerData.second is not None else "-"
			timer_text = format_timer_with_status(minute, second, TimerData.is_running)
			print(timer_text)
		self.label_minute.get_style_context().add_class("time-value")

		# Button um das Label, um Klicks zu erfassen
		self.button_minute = Gtk.Button()
		self.button_minute.add(self.label_minute)
		self.button_minute.get_style_context().add_class("time-button")
		self.button_minute.connect("clicked", self.on_time_click, "minute")
		vbox.pack_start(self.button_minute, False, False, 5)

		# Sekunden Titel
		label_second_title = Gtk.Label(label="Sekunden")
		label_second_title.get_style_context().add_class("time-title")
		vbox.pack_start(label_second_title, False, False, 5)

		# Sekunden Wert
		if not TimerData.is_running:
			self.label_second = Gtk.Label(label="00")
		else:
			self.label_second = Gtk.Label(label=f"{TimerData.second:02}")
		self.label_second.get_style_context().add_class("time-value")

		# Button um das Label, um Klicks zu erfassen
		self.button_second = Gtk.Button()
		self.button_second.add(self.label_second)
		self.button_second.get_style_context().add_class("time-button")
		self.button_second.connect("clicked", self.on_time_click, "second")
		vbox.pack_start(self.button_second, False, False, 5)

	def create_numpad(self):
		# NumPad auf der rechten Seite
		grid = Gtk.Grid()
		grid.set_row_spacing(10)
		grid.set_column_spacing(10)
		self.fixed.put(grid, 400, 50)  # Position anpassen

		# Buttons erstellen
		buttons = [
			('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
			('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
			('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
			('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
			('►', 0, 4), ('‖', 1, 4), ('■', 2, 4),
		]

		for item in buttons:
			label = item[0]
			x = item[1]
			y = item[2]

			button = Gtk.Button(label=label)
			button.set_size_request(70, 70)  # Größe anpassen
			button.get_style_context().add_class("numpad-button")

			if label == '►':
				# Für Start-Button wird jetzt der TimerController verwendet
				self.button_start = button
			elif label == '‖':
				# Für Pause-Button wird jetzt der TimerController verwendet
				self.button_pause = button
				self.button_pause.set_sensitive(False)  # Anfangs deaktiviert
			elif label == '■':
				# Für Stop-Button wird jetzt der TimerController verwendet
				self.button_stop = button
				self.button_stop.set_sensitive(False)  # Anfangs deaktiviert
			elif label == '←':
				button.connect("clicked", self.on_backspace_button_click)
			elif label == 'C':
				button.connect("clicked", self.on_numpad_button_click)
			else:
				button.connect("clicked", self.on_numpad_button_click)

			grid.attach(button, x, y, 1, 1)
			self.numpad_buttons.append(button)

	def create_back_button(self):
		# "Zurück" Button unten rechts hinzufügen
		back_button = Gtk.Button(label="Schliessen")
		back_button.set_size_request(100, 40)
		back_button.connect("clicked", self.on_back_button_click)
		back_button.get_style_context().add_class("button-custom")
		self.fixed.put(back_button, 658, 416)

	def on_back_button_click(self, widget):
		self.close()

	def on_numpad_button_click(self, button):
		label_text = button.get_label()
		if self.current_time is None:
			return  # Kein Feld ausgewählt

		if self.current_time == "minute":
			current_label = self.label_minute
		else:
			current_label = self.label_second

		current_text = current_label.get_text()

		if label_text == 'C':
			current_label.set_text('00')
			self.new_entry = True
			current_label.get_style_context().remove_class("error")
		else:
			if self.new_entry or current_text == '00':
				new_text = label_text
				self.new_entry = False
			else:
				new_text = current_text + label_text

			try:
				new_value = int(new_text)
				if new_value > 60:
					new_value = 60
					new_text = '60'
					self.new_entry = True
					current_label.get_style_context().add_class("error")
					GLib.timeout_add(500, self.remove_error_class, current_label)
				else:
					current_label.get_style_context().remove_class("error")
			except ValueError:
				new_value = 0
				new_text = '00'
				self.new_entry = True

			current_label.set_text(f"{int(new_text):02}")

	def remove_error_class(self, label):
		label.get_style_context().remove_class("error")
		return False

	def on_backspace_button_click(self, button):
		if self.current_time is None:
			return  # Kein Feld ausgewählt

		if self.current_time == "minute":
			current_label = self.label_minute
		else:
			current_label = self.label_second

		current_text = current_label.get_text()

		if len(current_text) > 1:
			new_text = current_text[:-1]
		else:
			new_text = '0'
			self.new_entry = True

		current_label.set_text(new_text)

	def on_time_click(self, widget, time_type):
		self.current_time = time_type
		self.new_entry = True
		self.highlight_selected_timer()
		

	def highlight_selected_timer(self):
		if self.current_time == "minute":
			self.label_minute.get_style_context().add_class("time-selected")
			self.label_second.get_style_context().remove_class("time-selected")
		elif self.current_time == "second":
			self.label_second.get_style_context().add_class("time-selected")
			self.label_minute.get_style_context().remove_class("time-selected")

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
			self.is_fullscreen_mode = False
		else:
			self.fullscreen()
			self.is_fullscreen_mode = True

	def disable_input_fields(self):
		"""Deaktiviert die Eingabefelder und entfernt deren Fokus."""
		self.button_minute.set_sensitive(False)
		self.button_second.set_sensitive(False)
		self.button_minute.set_can_focus(False)
		self.button_second.set_can_focus(False)

	def enable_input_fields(self):
		"""Aktiviert die Eingabefelder und erlaubt den Fokus."""
		self.button_minute.set_sensitive(True)
		self.button_second.set_sensitive(True)
		self.button_minute.set_can_focus(True)
		self.button_second.set_can_focus(True)
