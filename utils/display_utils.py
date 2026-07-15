from utils.helpers import format_timer_with_status
from data.timer_data import TimerData
from data.game_time_data import GameTimeData
from data.round_data import RoundData
from data.chip_data import ChipData

def update_client_display(instance, data):
    # Aktualisiere die Timer-Daten anhand der vom Server gesendeten Statuswerte
    TimerData.minute = data.get("blind_time_minute", TimerData.minute)
    TimerData.second = data.get("blind_time_second", TimerData.second)
    TimerData.is_running = data.get("timer_running", TimerData.is_running)
    
    # Setze konfigurierte Startzeit aus dem Server‑Status
    TimerData.start_minute = data.get("configured_blind_time_minute", TimerData.start_minute)
    TimerData.start_second = data.get("configured_blind_time_second", TimerData.start_second)

    # --- Aktualisiere GameTimeData mit Serverdaten ---
    if "game_time_minute" in data and "game_time_second" in data:
        GameTimeData.minute = data.get("game_time_minute", GameTimeData.minute)
        GameTimeData.second = data.get("game_time_second", GameTimeData.second)
        GameTimeData.is_running = data.get("game_time_running", GameTimeData.is_running)

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

        # --- Aktualisiere Spielzeit im TotalGameTimeWindow ---
        if hasattr(instance, "label_minute") and hasattr(instance, "label_second"):
            # Prüfe, ob wir uns im TotalGameTimeWindow befinden
            if hasattr(instance, "game_timer"):
                instance.label_minute.set_text(f"{game_minute:02}")
                instance.label_second.set_text(f"{game_second:02}")
                
                # Aktualisiere Buttons basierend auf game_running Status
                if hasattr(instance, "button_start") and hasattr(instance, "button_pause") and hasattr(instance, "button_stop"):
                    if game_running:
                        instance.button_start.set_sensitive(False)
                        instance.button_pause.set_sensitive(True)
                        instance.button_stop.set_sensitive(True)
                        # Eingabefelder deaktivieren
                        if hasattr(instance, "disable_input_fields"):
                            instance.disable_input_fields()
                    else:
                        # Nur aktivieren, wenn der Timer nicht pausiert ist
                        if not GameTimeData.is_paused:
                            instance.button_start.set_sensitive(True)
                            instance.button_pause.set_sensitive(False)
                            instance.button_stop.set_sensitive(False)
                            # Eingabefelder aktivieren
                            if hasattr(instance, "enable_input_fields"):
                                instance.enable_input_fields()

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

    # Aktualisiere Timer-Felder im Blind-Timer-Fenster
    if hasattr(instance, "label_minute") and hasattr(instance, "label_second"):
        # Prüfe, ob wir uns im TimerSettingWindow befinden (hat keinen game_timer)
        if not hasattr(instance, "game_timer"):
            instance.label_minute.set_text(f"{current_minute:02}")
            instance.label_second.set_text(f"{current_second:02}")

    if hasattr(instance, "timer_labels") and "Momentane Zeit" in instance.timer_labels:
        instance.timer_labels["Momentane Zeit"].set_text(current_time_str)
        
    # --- Aktualisiere Rundenzählung ---
    if "rounds_count" in data:
        rounds_count = data.get("rounds_count", 0)
        RoundData.count = rounds_count
        
        # Aktualisiere die Anzeige, falls das Label vorhanden ist
        if hasattr(instance, "info_labels") and "Anzahl Runden" in instance.info_labels:
            # Zeige '-' an, wenn Rundenzahl 0 ist, sonst zeige die Rundenzahl
            rounds_text = "-" if rounds_count == 0 else str(rounds_count)
            instance.info_labels["Anzahl Runden"].set_text(rounds_text)
    
    # --- Aktualisiere Chipwerte, falls vorhanden ---
    if "chip_values" in data:
        chip_values = data.get("chip_values", {})
        # Aktualisiere die lokalen ChipData.chf_values
        ChipData.chf_values.update(chip_values)
        
        # Falls wir uns im ChipValueWindow befinden, aktualisiere die Labels
        if hasattr(instance, "chf_labels") and isinstance(instance.chf_labels, dict):
            for chip_file, label in instance.chf_labels.items():
                chf_value = ChipData.chf_values.get(chip_file, 0.0)
                # Zeige "-" an, wenn Wert 0 ist
                chf_display = "-" if chf_value == 0.0 else f"CHF {chf_value:.2f}"
                label.set_text(chf_display)
