# utils/zeroconf_utils.py

import socket
from zeroconf import Zeroconf, ServiceBrowser

class MyListener:
    """Listener für Zeroconf, um den Poker-Server zu entdecken."""
    def __init__(self):
        self.server_address = None

    def remove_service(self, zeroconf, type, name):
        # Keine Aktion erforderlich, wenn ein Service entfernt wird
        pass

    def add_service(self, zeroconf, type, name):
        """Wird aufgerufen, wenn ein Dienst gefunden wird."""
        info = zeroconf.get_service_info(type, name)
        if info:
            addr = socket.inet_ntoa(info.addresses[0])
            self.server_address = (addr, info.port)

    def update_service(self, zeroconf, type, name):
        pass
