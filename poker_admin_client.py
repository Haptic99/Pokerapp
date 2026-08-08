"""
Poker Admin Client Module.

This module implements the administrator client for the poker application.
It provides an interface with admin privileges to manage the poker game,
including features like setting blinds, managing timers, and monitoring players.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from windows.poker_interface import PokerInterface
from utils.display_utils import update_client_display
from utils.websocket_utils import WebSocketClient


class PokerAdminClient(PokerInterface):
    """The Poker Admin Client.

    Extends the basic PokerInterface with administrative capabilities,
    allowing for full control over the poker game settings and management.
    """
    def __init__(self):
        super().__init__(is_admin=True)  # Admin client has admin privileges

        # Initialize WebSocket client (automatically finds server via Zeroconf)
        self.ws_client = WebSocketClient(update_display_callback=self.update_display)

        # Start the network listener
        self.ws_client.start_async_loop()

        # For compatibility with existing code
        self.server_address = self.ws_client.server_address
        self.loop = self.ws_client.loop
        self.uri = self.ws_client.uri

    def update_display(self, data):
        """Update the display with data received from the server.

        This method is called when new data is received from the server
        via the WebSocket connection. It updates all UI elements with
        the current game state.

        Args:
            data: Dictionary containing the current game state data
                 from the server, including blinds, timer values,
                 player information, etc.
        """
        update_client_display(self, data)


# At the end of the document: instantiate the Admin Client and start the GUI
if __name__ == '__main__':
    admin_client = PokerAdminClient()
    admin_client.show_all()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("\nPoker Admin Client wurde beendet.")
