from utils.helpers import format_timer_with_status

def update_client_display(instance, data):
    # --- Aktualisiere Blinds ---
    small_blind = data.get("small_blind") or "-"
    big_blind = data.get("big_blind") or "-"
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

    # --- Aktualisiere Spielzeit ---
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

    # --- Aktualisiere konfigurierten Timer (Eingestellte Zeit) ---
    if "configured_blind_time_minute" in data and "configured_blind_time_second" in data:
        configured_minute_raw = data.get("configured_blind_time_minute")
        configured_second_raw = data.get("configured_blind_time_second")
        if configured_minute_raw is None or configured_second_raw is None:
            set_time_str = "-"
        else:
            try:
                configured_minute = int(configured_minute_raw)
                configured_second = int(configured_second_raw)
                set_time_str = f"{configured_minute:02}:{configured_second:02}"
            except Exception as e:
                print("Fehler bei der Umwandlung der konfigurierten Timer-Werte:", e)
                set_time_str = "-"
        if hasattr(instance, "timer_labels") and "Eingestellte Zeit" in instance.timer_labels:
            instance.timer_labels["Eingestellte Zeit"].set_text(set_time_str)

    # --- Aktualisiere aktuelle Timer-Werte (Momentane Zeit) nur wenn der Timer läuft ---
    try:
        current_minute = int(data.get("blind_time_minute") or 0)
        current_second = int(data.get("blind_time_second") or 0)
        timer_running = data.get("timer_running", False)
    except Exception as e:
        print("Fehler bei der Umwandlung der aktuellen Timer-Werte:", e)
        current_minute, current_second = 0, 0
        timer_running = False

    current_time_str = format_timer_with_status(current_minute, current_second, timer_running)
    if timer_running:
        if hasattr(instance, "label_minute") and hasattr(instance, "label_second"):
            instance.label_minute.set_text(f"{current_minute:02}")
            instance.label_second.set_text(f"{current_second:02}")
        elif hasattr(instance, "timer_labels") and "Momentane Zeit" in instance.timer_labels:
            instance.timer_labels["Momentane Zeit"].set_text(current_time_str)

