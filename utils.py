from datetime import datetime
from tkinter import END


def formatuj_minuty(celkem_minut):
    h = celkem_minut // 60
    m = celkem_minut % 60
    return f"{h}h {m:02d}m"


def cas_na_minuty(cas_str):
    if not cas_str:
        return 0
    try:
        t = datetime.strptime(cas_str, "%H:%M")
        return t.hour * 60 + t.minute
    except Exception:
        return 0


def normalizuj_cas(entry):
    text = entry.get().strip()
    if not text:
        return
    try:
        h, m = None, None
        if ':' in text:
            parts = text.split(':', 1)
            h = int(parts[0])
            m = int(parts[1]) if parts[1] else 0
        elif len(text) <= 2:
            # e.g. "6" → 6:00, "14" → 14:00
            h = int(text)
            m = 0
        elif len(text) == 3:
            # e.g. "630" → 6:30
            h = int(text[0])
            m = int(text[1:])
        elif len(text) == 4:
            # e.g. "0630" → 6:30, "1430" → 14:30
            h = int(text[:2])
            m = int(text[2:])
        else:
            return
        if h is not None and m is not None and 0 <= h <= 23 and 0 <= m <= 59:
            entry.delete(0, END)
            entry.insert(0, f"{h:02d}:{m:02d}")
    except Exception:
        pass


def set_dark_title_bar(window):
    try:
        import ctypes
        from ctypes import wintypes
        window.update()
        HWND = wintypes.HWND(int(window.frame(), 16))
        dwmapi = ctypes.WinDLL('dwmapi')
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        use_dark_mode = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            HWND, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(use_dark_mode), ctypes.sizeof(use_dark_mode)
        )
    except Exception:
        pass