# utils/display_utils.py

from utils.helpers import format_timer_with_status

def update_client_display(instance, data):
    """
    Aktualisiert die Anzeige eines Poker-Clients basierend auf Serverdaten.
    Diese Funktion wird von beiden Client-Typen verwendet.
    
    Args:
        instance: Die Client-Instanz (PokerClient oder PokerAdminClient)
        data: Die Daten vom Server
    """
    # Aktualisiere Blinds
    small_blind = data.get("small_blind") or "n.V."
    big_blind = data.get("big_blind") or "n.V."
    try:
        blind_minute = int(data.get("blind_time_minute") or 0)
        blind_second = int(data.get("blind_time_second") or 0)
        timer_running = data.get("timer_running", False)
    except Exception as e:
        print("Fehler bei der Umwandlung der Blind-Timer Werte:", e)
        blind_minute, blind_second = 0, 0
        timer_running = False

    if hasattr(instance, "left_labels"):
        if "Small Blind" in instance.left_labels:
            instance.left_labels["Small Blind"].set_text(small_blind)
        if "Big Blind" in instance.left_labels:
            instance.left_labels["Big Blind"].set_text(big_blind)
        if "Nächste Blinderhöhung" in instance.left_labels:
            timer_text = format_timer_with_status(blind_minute, blind_second, timer_running)
            instance.left_labels["Nächste Blinderhöhung"].set_text(timer_text)

    # Aktualisiere Spielzeit
    if "game_time_minute" in data and "game_time_second" in data:
        try:
            game_minute = int(data.get("game_time_minute") or 0)
            game_second = int(data.get("game_time_second") or 0)
            game_running = data.get("game_time_running", False)
        except Exception as e:
            print("Fehler bei der Umwandlung der Spielzeit:", e)
            game_minute, game_second = 0, 0
            game_running = False

        if hasattr(instance, "info_labels") and "Spielzeit" in instance.info_labels:
            game_time_text = format_timer_with_status(game_minute, game_second, game_running)
            instance.info_labels["Spielzeit"].set_text(game_time_text)
