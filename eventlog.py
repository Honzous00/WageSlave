import datetime
import time


def get_last_system_offline_time():
    try:
        import win32evtlog
    except ImportError:
        return None

    try:
        hand = win32evtlog.OpenEventLog(None, "System")
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        target_ids = {6006, 1074}
        max_read = 10000
        read_count = 0

        while read_count < max_read:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            if not events:
                break
            for event in events:
                read_count += 1
                if event.EventID in target_ids:
                    local_struct = event.TimeGenerated
                    dt = datetime.datetime.fromtimestamp(time.mktime(local_struct))
                    if dt > datetime.datetime.now() - datetime.timedelta(days=7):
                        return dt
            if read_count >= max_read:
                break
        return None
    except Exception:
        return None
