# data/blind_data.py

class BlindData:
    small_blind = None
    big_blind = None
    
    # Standard-Fahrplan für Poker-Blinds (Small Blind, Big Blind)
    BLIND_SCHEDULE = [
        (5, 10),
        (10, 20),
        (15, 30),
        (20, 40),
        (25, 50),
        (50, 100),
        (75, 150),
        (100, 200),
        (200, 400),
        (500, 1000)
    ]
    
    # Aktuelle Stufe im Fahrplan (-1 = manuell gesetzt oder Spiel nicht gestartet)
    current_level_index = -1
