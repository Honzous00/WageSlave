# eventlog.py
import datetime
import time

def get_last_system_offline_time():
    """
    Pokusí se přečíst Windows System Event Log a vrátí datetime posledního
    vypnutí/restartu (Event ID 6006 nebo 1074).
    Vrací datetime objekt v lokálním čase nebo None, pokud:
      - pywin32 není nainstalováno
      - log nelze přečíst
      - žádná relevantní událost nebyla nalezena
    """
    try:
        import win32evtlog
    except ImportError:
        return None  # pywin32 není k dispozici

    try:
        hand = win32evtlog.OpenEventLog(None, "System")
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        target_ids = {6006, 1074}  # 6006 – vypnutí logování, 1074 – iniciované vypnutí

        # Omezíme čtení na posledních cca 10 000 záznamů (pro výkon)
        max_read = 10000
        read_count = 0

        while read_count < max_read:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            if not events:
                break

            for event in events:
                read_count += 1
                if event.EventID in target_ids:
                    # TimeGenerated je struct_time v lokálním čase
                    local_struct = event.TimeGenerated
                    # převod na datetime
                    dt = datetime.datetime.fromtimestamp(time.mktime(local_struct))
                    # nepovinné omezení stáří – např. posledních 7 dní
                    if dt > datetime.datetime.now() - datetime.timedelta(days=7):
                        return dt
            # Pokud jsme nenašli nic ani v posledních ~10k záznamech, končíme
            if read_count >= max_read:
                break

        return None
    except Exception:
        return None