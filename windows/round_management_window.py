# windows/round_management_window.py

import gi
import asyncio
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from utils.helpers import set_background_image
from utils.resources import get_image_path
from data.round_data import RoundData

class RoundManagementWindow(Gtk.Window):
	def __init__(self, parent, confirm_callback=None):
		super().__init__(title="Runden-Verwaltung")
		self.parent = parent
		self.set_default_size(800, 480)
		self.set_transient_for(parent)
		self.set_modal(True)
		self.confirm_callback = confirm_callback

		# Variable für Vollbildmodus initialisieren
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
		
		# Liste für Numpad-Buttons initialisieren
		self.numpad_buttons = []
		
		# Flag für neue Eingabe
		self.new_entry = True
		
		# Temporärer Rundenwert (wird erst nach OK gesendet)
		self.temp_rounds_count = 1 if RoundData.count == 0 else RoundData.count

		# UI-Komponenten erstellen
		self.create_ui_components()

		# Keybindings für Vollbildmodus und Escape
		self.connect("key-press-event", self.on_key_press)

	def create_ui_components(self):
		# Titel oben in der Mitte
		title_label = Gtk.Label()
		title_label.set_markup("<span size='x-large' weight='bold' foreground='#CDAD00'>Runden-Verwaltung</span>")
		title_label.get_style_context().add_class("dialog-text")
		self.fixed.put(title_label, 300, 20)
		
		# Aktuelle Rundenanzahl oben links
		rounds_label = Gtk.Label(label="Aktuelle Rundenanzahl:")
		rounds_label.get_style_context().add_class("green-text")
		self.fixed.put(rounds_label, 100, 80)
		
		# Runden-Anzeigefeld (groß)
		self.rounds_display = Gtk.Label()
		# Vorwähle 1 wenn RoundData.count 0 ist, sonst verwende vorhandenen Wert
		display_value = "1" if RoundData.count == 0 else str(RoundData.count)
		self.rounds_display.set_markup(f"<span size='xx-large' weight='bold'>{display_value}</span>")
		self.rounds_display.get_style_context().add_class("green-text")
		self.rounds_display.get_style_context().add_class("large-text")
		self.fixed.put(self.rounds_display, 150, 120)
		
		# Runden-Eingabefeld (ähnlich wie im Timer Window)
		self.rounds_entry = Gtk.Button()
		self.rounds_entry_label = Gtk.Label(label=display_value)
		self.rounds_entry_label.get_style_context().add_class("time-value")
		self.rounds_entry.add(self.rounds_entry_label)
		self.rounds_entry.get_style_context().add_class("time-button")
		self.rounds_entry.set_size_request(100, 60)
		self.rounds_entry.connect("clicked", self.on_rounds_entry_clicked)
		self.fixed.put(self.rounds_entry, 150, 120)
		
		# NumPad auf der rechten Seite
		self.create_numpad()
		
		# "Schließen" Button unten rechts
		close_button = Gtk.Button(label="Schließen")
		close_button.set_size_request(100, 40)
		close_button.connect("clicked", self.on_close_button_clicked)
		close_button.get_style_context().add_class("button-custom")
		self.fixed.put(close_button, 658, 416)

	def create_numpad(self):
		# NumPad auf der rechten Seite ähnlich wie beim TimerSettingWindow
		grid = Gtk.Grid()
		grid.set_row_spacing(10)
		grid.set_column_spacing(10)
		self.fixed.put(grid, 400, 80)

		# Buttons erstellen: Ziffern 1-9, C, 0, Backspace, und Aktionstasten
		buttons = [
			('1', 0, 0), ('2', 1, 0), ('3', 2, 0),
			('4', 0, 1), ('5', 1, 1), ('6', 2, 1),
			('7', 0, 2), ('8', 1, 2), ('9', 2, 2),
			('C', 0, 3), ('0', 1, 3), ('←', 2, 3),
			('-1', 0, 4), ('Ok', 1, 4, 2), # Ok-Button über 2 Spalten
		]

		for item in buttons:
			label = item[0]
			x = item[1]
			y = item[2]
			
			width = 1
			if len(item) > 3:
				width = item[3]
				
			if label == 'Ok':
				button = Gtk.Button(label=label)
				button.connect("clicked", self.on_ok_button_clicked)
				button.get_style_context().add_class("numpad-button")
				button.get_style_context().add_class("numpad-button-ok")
			elif label == '-1':
				button = Gtk.Button(label=label)
				button.connect("clicked", self.on_decrement_rounds)
			elif label == '←':
				button = Gtk.Button(label=label)
				button.connect("clicked", self.on_backspace_button_click)
			elif label == 'C':
				button = Gtk.Button(label=label)
				button.connect("clicked", self.on_clear_button_click)
			else:
				button = Gtk.Button(label=label)
				button.connect("clicked", self.on_numpad_button_click)
			
			button.set_size_request(70 * width, 60)
			button.get_style_context().add_class("numpad-button")
			grid.attach(button, x, y, width, 1)
			self.numpad_buttons.append(button)

	def on_ok_button_clicked(self, widget):
		"""Bestätigt die Rundenwahl und sendet Updates."""
		# Rundenwert von der UI übernehmen
		rounds_value = self.temp_rounds_count
		
		# RoundData aktualisieren
		RoundData.count = rounds_value
		
		# Server-Update senden
		self.send_round_update()
		
		# Callback für UI-Updates
		if self.confirm_callback:
			self.confirm_callback(rounds_value)

	def on_rounds_entry_clicked(self, widget):
		self.new_entry = True
		self.rounds_entry_label.get_style_context().add_class("selected")

	def on_numpad_button_click(self, button):
		label_text = button.get_label()
		current_text = self.rounds_entry_label.get_text()
		
		if self.new_entry or current_text == '0':
			new_text = label_text
			self.new_entry = False
		else:
			new_text = current_text + label_text
		
		# Aktualisiere das Anzeige-Label
		self.rounds_entry_label.set_text(new_text)
		self.rounds_display.set_markup(f"<span size='xx-large' weight='bold'>{new_text}</span>")
		
		# Aktualisiere den temporären Rundenzähler
		try:
			new_count = int(new_text)
			if new_count < 0:
				new_count = 0
				new_text = '0'
				self.rounds_entry_label.set_text(new_text)
				self.rounds_display.set_markup(f"<span size='xx-large' weight='bold'>{new_text}</span>")
			
			self.temp_rounds_count = new_count
			
		except ValueError:
			# Wenn keine gültige Zahl eingegeben wurde
			self.rounds_entry_label.set_text(str(self.temp_rounds_count))
	
	def on_clear_button_click(self, button):
		self.rounds_entry_label.set_text('0')
		self.rounds_display.set_markup("<span size='xx-large' weight='bold'>0</span>")
		self.temp_rounds_count = 0
		self.new_entry = True
	
	def on_backspace_button_click(self, button):
		current_text = self.rounds_entry_label.get_text()
		
		if len(current_text) > 1:
			new_text = current_text[:-1]
		else:
			new_text = '0'
			self.new_entry = True
		
		self.rounds_entry_label.set_text(new_text)
		self.rounds_display.set_markup(f"<span size='xx-large' weight='bold'>{new_text}</span>")
		
		# Aktualisiere den temporären Rundenzähler
		try:
			self.temp_rounds_count = int(new_text)
		except ValueError:
			# Wenn keine gültige Zahl eingegeben wurde
			self.rounds_entry_label.set_text(str(self.temp_rounds_count))

	def on_decrement_rounds(self, widget):
		"""Verringert die Rundenanzahl um 1, aber nicht unter 0."""
		if self.temp_rounds_count > 0:
			self.temp_rounds_count -= 1
			self.rounds_entry_label.set_text(str(self.temp_rounds_count))
			self.rounds_display.set_markup(f"<span size='xx-large' weight='bold'>{self.temp_rounds_count}</span>")

	def send_round_update(self):
		"""Sendet die aktualisierte Rundenanzahl an den Server."""
		# Suche nach dem event loop
		loop = None
		
		# Verschiedene Möglichkeiten durchgehen, wo der loop sein könnte
		if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'loop'):
			loop = self.parent.poker_interface.loop
		elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'loop'):
			loop = self.parent.ws_client.loop
		else:
			print("ERROR: Konnte keinen asyncio loop finden!")
			return
		
		# Update an den Server senden
		asyncio.run_coroutine_threadsafe(
			self.send_update_rounds(),
			loop
		)

	async def send_update_rounds(self):
		"""Sendet ein Update der Rundenanzahl an den Server."""
		import websockets
		import json
		
		# Server-Adresse ermitteln
		server_address = None
		if hasattr(self.parent, 'poker_interface') and hasattr(self.parent.poker_interface, 'server_address'):
			server_address = self.parent.poker_interface.server_address
		elif hasattr(self.parent, 'ws_client') and hasattr(self.parent.ws_client, 'server_address'):
			server_address = self.parent.ws_client.server_address
		
		if not server_address:
			print("ERROR: Konnte keine Server-Adresse finden!")
			return
		
		server_ip, server_port = server_address
		uri = f"ws://{server_ip}:{server_port}"
		
		try:
			async with websockets.connect(uri) as websocket:
				message = {
					"command": "update_rounds",
					"rounds_count": RoundData.count
				}
				await websocket.send(json.dumps(message))
				print(f"Rundenupdate gesendet: Anzahl={RoundData.count}")
		except Exception as e:
			print(f"Fehler beim Senden des Rundenupdate: {e}")

	def on_close_button_clicked(self, widget):
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
