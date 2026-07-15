# main.py

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from windows.poker_interface import PokerInterface

if __name__ == "__main__":
    win = PokerInterface()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
