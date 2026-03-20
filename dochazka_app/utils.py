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
        if ':' in text:
            h, m = text.split(':', 1)
            h, m = int(h), int(m)
        else:
            h = int(text)
            m = 0
        if 0 <= h <= 23 and 0 <= m <= 59:
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
