import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from windows.poker_interface import PokerInterface

class PokerViewer(PokerInterface):
    def __init__(self):
        super().__init__()
        
        # Entferne den Admin-Button aus der Oberfläche
        if hasattr(self, "fixed"):
            self.fixed.remove(self.admin_button)  # Falls es eine Referenz gibt

        print("PokerViewer gestartet (kein Admin-Zugang)")
    
    def button_administration_click(self, widget):
        """Blockiert den Zugriff auf die Administration."""
        print("PokerViewer: Zugriff auf Administration nicht erlaubt.")

# Starte das PokerInterface als Viewer
if __name__ == "__main__":
    viewer = PokerViewer()
    viewer.show_all()
    Gtk.main()
