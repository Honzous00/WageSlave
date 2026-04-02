"""
WageSlave Systém — moderní desktopová aplikace (tkinter)
Verze 2.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import csv
import os
import sys

# Nastavit AppUserModelID co nejdrive - pred vytvorenim okna
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'WageSlave.App.1')
except Exception:
    pass

import config
config.load()
from database import WageSlaveDB
from calculator import week_analysis, month_balance
from utils import formatuj_minuty, cas_na_minuty, normalizuj_cas, set_dark_title_bar
from tray import TrayIcon
from eventlog import get_last_system_offline_time
import special_days
special_days.init_table()

# ─────────────────────────────────────────────────────────────────────────────
#  PALETA BAREV
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":        "#0d0f12",
    "surface":   "#13161b",
    "panel":     "#1a1e26",
    "border":    "#252b36",
    "border2":   "#2e3645",
    "text":      "#e2e8f0",
    "muted":     "#64748b",
    "accent":    "#3b82f6",
    "accent2":   "#60a5fa",
    "green":     "#22c55e",
    "red":       "#ef4444",
    "amber":     "#f59e0b",
    "white":     "#ffffff",
    "sidebar":   "#0f1218",
}

FONT_MONO  = ("Segoe UI", 10)
FONT_MONO_S = ("Segoe UI", 9)
FONT_MONO_L = ("Segoe UI", 12, "bold")
FONT_HERO  = ("Segoe UI", 42, "bold")
FONT_H1    = ("Segoe UI", 16, "bold")
FONT_H2    = ("Segoe UI", 12, "bold")
FONT_LABEL = ("Segoe UI", 8)
FONT_SMALL = ("Segoe UI", 8)


def get_week_number(date):
    return date.isocalendar()[1]


def day_name_cs(date):
    names = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
    return names[date.weekday()]


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

class DarkEntry(tk.Entry):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", C["bg"])
        kwargs.setdefault("fg", C["text"])
        kwargs.setdefault("insertbackground", C["accent"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("font", FONT_MONO)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", C["border2"])
        kwargs.setdefault("highlightcolor", C["accent"])
        super().__init__(parent, **kwargs)


class DarkButton(tk.Button):
    def __init__(self, parent, accent=False, danger=False, ghost=False, **kwargs):
        bg = C["accent"] if accent else C["red"] if danger else C["panel"]
        fg = C["white"] if (accent or danger) else (C["muted"] if ghost else C["text"])
        ab = C["accent2"] if accent else "#c0392b" if danger else C["border2"]
        kwargs.setdefault("bg", bg)
        kwargs.setdefault("fg", fg)
        kwargs.setdefault("activebackground", ab)
        kwargs.setdefault("activeforeground", C["white"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("font", FONT_MONO_S)
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("padx", 12)
        kwargs.setdefault("pady", 6)
        kwargs.setdefault("bd", 0)
        super().__init__(parent, **kwargs)
        self.bind("<Enter>", lambda e: self.config(bg=ab))
        self.bind("<Leave>", lambda e: self.config(bg=bg))


class Separator(tk.Frame):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", C["border"])
        kwargs.setdefault("height", 1)
        super().__init__(parent, **kwargs)


class SidebarButton(tk.Button):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", C["sidebar"])
        kwargs.setdefault("fg", C["muted"])
        kwargs.setdefault("activebackground", C["panel"])
        kwargs.setdefault("activeforeground", C["text"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("font", ("Segoe UI", 10))
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("anchor", "w")
        kwargs.setdefault("padx", 20)
        kwargs.setdefault("pady", 10)
        kwargs.setdefault("bd", 0)
        super().__init__(parent, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  EMOJI LABEL — barevné emoji přes Pillow bridge
# ─────────────────────────────────────────────────────────────────────────────

def _find_emoji_font(size):
    """Najde systémový barevný emoji font a vrátí PIL ImageFont."""
    from PIL import ImageFont
    candidates = [
        r"C:\Windows\Fonts\seguiemj.ttf",        # Windows — Segoe UI Emoji
        r"C:\Windows\Fonts\seguisym.ttf",         # Windows fallback
        "/System/Library/Fonts/Apple Color Emoji.ttc",  # macOS
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",  # Linux
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_emoji_image(text, size=18, bg=None):
    """Vykreslí emoji do PhotoImage přes Pillow. Vrátí (PhotoImage, width, height)."""
    try:
        from PIL import Image, ImageDraw, ImageTk
        font = _find_emoji_font(size)
        pad = 4
        canvas_size = size + pad * 2
        # Průhledné pozadí nebo barva dle bg
        if bg:
            r = int(bg[1:3], 16); g = int(bg[3:5], 16); b = int(bg[5:7], 16)
            img = Image.new("RGBA", (canvas_size, canvas_size), (r, g, b, 255))
        else:
            img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((canvas_size // 2, canvas_size // 2), text,
                  font=font, anchor="mm", embedded_color=True)
        return ImageTk.PhotoImage(img), canvas_size, canvas_size
    except Exception:
        return None, 0, 0


class EmojiLabel(tk.Label):
    """Label zobrazující barevné emoji přes Pillow. Parametry jako tk.Label."""
    def __init__(self, parent, emoji, size=18, **kwargs):
        bg_color = kwargs.get("bg", C["bg"])
        super().__init__(parent, **kwargs)
        photo, w, h = make_emoji_image(emoji, size=size, bg=bg_color)
        if photo:
            self._photo = photo   # nutné udržet referenci — jinak GC smaže
            self.config(image=photo, text="", width=w, height=h,
                        padx=0, pady=0, bd=0)
        else:
            self.config(text=emoji)


# ─────────────────────────────────────────────────────────────────────────────
#  LIVE BADGE (pulzující tečka)
# ─────────────────────────────────────────────────────────────────────────────

class LiveBadge(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["surface"], **kwargs)
        self.dot = tk.Label(self, text="●", fg=C["green"], bg=C["surface"],
                            font=("Segoe UI", 7))
        self.dot.pack(side="left", anchor="center")
        tk.Label(self, text="LIVE", fg=C["green"], bg=C["surface"],
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=(2, 0), anchor="center")
        self._blink_state = True
        self._blink()

    def _blink(self):
        self._blink_state = not self._blink_state
        self.dot.config(fg=C["green"] if self._blink_state else C["muted"])
        self.after(800, self._blink)


# ─────────────────────────────────────────────────────────────────────────────
#  PROGRESS BAR (custom canvas)
# ─────────────────────────────────────────────────────────────────────────────

class ProgressBar(tk.Canvas):
    def __init__(self, parent, height=8, **kwargs):
        kwargs.setdefault("bg", C["panel"])
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("height", height)
        super().__init__(parent, **kwargs)
        self._pct = 0
        self.bind("<Configure>", self._draw)

    def set(self, pct):
        self._pct = max(0, min(100, pct))
        self._draw()

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() or 200
        h = self.winfo_height() or 8
        r = h // 2
        # track
        self.create_rounded_rect(0, 0, w, h, r, fill=C["border"], outline="")
        # fill
        fw = int(w * self._pct / 100)
        if fw > r * 2:
            self.create_rounded_rect(0, 0, fw, h, r, fill=C["accent"], outline="")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        self.create_arc(x1, y1, x1 + 2*r, y1 + 2*r, start=90, extent=90, style="pieslice", **kwargs)
        self.create_arc(x2 - 2*r, y1, x2, y1 + 2*r, start=0, extent=90, style="pieslice", **kwargs)
        self.create_arc(x1, y2 - 2*r, x1 + 2*r, y2, start=180, extent=90, style="pieslice", **kwargs)
        self.create_arc(x2 - 2*r, y2 - 2*r, x2, y2, start=270, extent=90, style="pieslice", **kwargs)
        self.create_rectangle(x1 + r, y1, x2 - r, y2, **kwargs)
        self.create_rectangle(x1, y1 + r, x2, y2 - r, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  HLAVNÍ APLIKACE
# ─────────────────────────────────────────────────────────────────────────────

# Výchozí SVG logo (fallback pokud logo.svg neexistuje)
# Lze přepsat vlastním logo.svg ve složce vedle .exe nebo v AppData/WageSlave/
_DEFAULT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="45" fill="none" stroke="#3b82f6" stroke-width="6"/>
  <circle cx="50" cy="50" r="4" fill="#3b82f6"/>
  <line x1="50" y1="50" x2="50" y2="18" stroke="#3b82f6" stroke-width="5" stroke-linecap="round"/>
  <line x1="50" y1="50" x2="72" y2="62" stroke="#60a5fa" stroke-width="4" stroke-linecap="round"/>
  <circle cx="50" cy="12" r="3" fill="#60a5fa"/>
  <circle cx="50" cy="88" r="3" fill="#60a5fa"/>
  <circle cx="12" cy="50" r="3" fill="#60a5fa"/>
  <circle cx="88" cy="50" r="3" fill="#60a5fa"/>
</svg>"""


def _get_logo_path():
    """Vrátí cestu k logu podle config.LOGO_VARIANTA.
    Hledá nejdřív .ico (nevyžaduje žádný renderer), pak .svg jako zálohu.
    """
    varianta = getattr(config, 'LOGO_VARIANTA', 'purple')
    root = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) \
        else os.path.dirname(sys.executable)

    candidates = [
        # .ico — přímá podpora přes Pillow, žádné závislosti
        os.path.join(root, 'img', 'icon', f"{varianta}.ico"),
        # .svg — záloha pokud je k dispozici renderer
        os.path.join(root, 'img', 'svg', f"{varianta}.svg"),
        # původní time.ico
        os.path.join(root, 'time.ico'),
    ]
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            candidates += [
                os.path.join(meipass, 'img', 'icon', f"{varianta}.ico"),
                os.path.join(meipass, 'img', 'svg', f"{varianta}.svg"),
                os.path.join(meipass, 'time.ico'),
            ]

    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def get_logo_photo(size=40):
    """Vrátí PhotoImage loga v požadované velikosti."""
    import io
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None

    path = _get_logo_path()
    if not path:
        return None

    ext = os.path.splitext(path)[1].lower()

    # .ico nebo .png — přímé načtení přes Pillow, žádné další závislosti
    if ext in ('.ico', '.png'):
        try:
            img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    # .svg — zkus resvg_py (Rust, žádné cairo)
    if ext == '.svg':
        try:
            import resvg_py
            with open(path, 'rb') as f:
                svg_src = f.read()
            png_bytes = resvg_py.svg_to_bytes(
                svg_string=svg_src.decode('utf-8', errors='replace'),
                width=size, height=size
            )
            img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            return ImageTk.PhotoImage(img)
        except ImportError:
            pass
        except Exception:
            pass

        # cairosvg záloha
        try:
            import cairosvg
            with open(path, 'rb') as f:
                svg_src = f.read()
            png_data = cairosvg.svg2png(bytestring=svg_src,
                                        output_width=size, output_height=size)
            img = Image.open(io.BytesIO(png_data)).convert("RGBA")
            return ImageTk.PhotoImage(img)
        except Exception:
            pass

    return None


def get_ico_path():
    """Vrati cestu k time.ico. Pokud je app zabalena v .exe (PyInstaller),
    extrahuje ikonu do %APPDATA%/WageSlave/ pod pevnym nazvem."""
    if getattr(sys, 'frozen', False):
        # Nejdriv zkus slozku vedle .exe
        exe_ico = os.path.join(os.path.dirname(sys.executable), 'time.ico')
        if os.path.exists(exe_ico):
            return exe_ico
        # Extrahuj z bundlu do %APPDATA%/WageSlave/time.ico (pevny nazev)
        bundle_ico = os.path.join(sys._MEIPASS, 'time.ico')
        if os.path.exists(bundle_ico):
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            app_dir = os.path.join(appdata, 'WageSlave')
            os.makedirs(app_dir, exist_ok=True)
            dest = os.path.join(app_dir, 'time.ico')
            if not os.path.exists(dest):
                import shutil
                shutil.copy2(bundle_ico, dest)
            return dest
        return None
    else:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'time.ico')
        return p if os.path.exists(p) else None


class WageSlaveApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = WageSlaveDB()
        self.tray = TrayIcon(self)

        self.selected_id = None
        self._toast_job = None
        self._autosave_job = None
        self._pages = {}

        self._setup_window()
        self._setup_styles()
        self._build_ui()

        set_dark_title_bar(self)
        self._auto_zapis_prichod()
        self._refresh()
        self.after(30_000, self._tick)
        self.after(500, self.tray.create)  # create tray after window is ready
        self.after(3_000, self._run_backup_if_due)

    # ── WINDOW SETUP ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("WageSlave")
        self.geometry("1120x740")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_icon()

    def _set_icon(self):
        # Použij variantu loga pokud existuje, jinak time.ico
        varianta = getattr(config, 'LOGO_VARIANTA', 'purple')
        root = os.path.dirname(os.path.abspath(__file__))
        variant_ico = os.path.join(root, 'img', 'icon', f"{varianta}.ico")
        ico_path = variant_ico if os.path.exists(variant_ico) else get_ico_path()
        if ico_path:
            try:
                self.iconbitmap(default=ico_path)
            except Exception:
                pass

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Treeview
        style.configure("Dark.Treeview",
            background=C["panel"],
            foreground=C["text"],
            fieldbackground=C["panel"],
            borderwidth=0,
            rowheight=28,
            font=FONT_MONO_S,
        )
        style.configure("Dark.Treeview.Heading",
            background=C["surface"],
            foreground=C["muted"],
            borderwidth=0,
            font=("Segoe UI", 8, "bold"),
            relief="flat",
        )
        style.map("Dark.Treeview",
            background=[("selected", C["accent"])],
            foreground=[("selected", C["white"])],
        )
        style.map("Dark.Treeview.Heading",
            background=[("active", C["border"])],
        )

        # Combobox
        style.configure("Dark.TCombobox",
            fieldbackground=C["bg"],
            background=C["bg"],
            foreground=C["text"],
            arrowcolor=C["muted"],
            borderwidth=1,
            relief="flat",
        )
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", C["bg"])],
            selectbackground=[("readonly", C["bg"])],
            selectforeground=[("readonly", C["text"])],
        )

        # Scrollbar
        style.configure("Dark.Vertical.TScrollbar",
            background=C["border"],
            troughcolor=C["panel"],
            borderwidth=0,
            arrowsize=12,
        )

        # Checkbutton
        style.configure("Dark.TCheckbutton",
            background=C["panel"],
            foreground=C["text"],
            font=FONT_MONO_S,
        )

    # ── BUILD UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Sidebar
        self._build_sidebar()

        # ── Main area
        self.main_frame = tk.Frame(self, bg=C["bg"])
        self.main_frame.pack(side="left", fill="both", expand=True)

        # Topbar
        self._build_topbar()

        # Content (notebook-like pages)
        self.content = tk.Frame(self.main_frame, bg=C["bg"])
        self.content.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_page_dashboard()
        self._build_page_history()
        self._build_page_planning()
        self._build_page_settings()

        self._show_page("dashboard")

    # ── SIDEBAR ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = tk.Frame(self, bg=C["sidebar"], width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo — jen text, zarovnaný do stejné šířky přes Canvas
        logo_frame = tk.Frame(self.sidebar, bg=C["sidebar"], pady=18)
        logo_frame.pack(fill="x")
        # Oba řádky stejně wide — použijeme Canvas s textem
        # Šířka sidebaru je 210px, padding 20px každá strana → 170px text area
        TEXT_W = 170
        for line, color in [("WAGESLAVE", C["accent"]), ("SYSTEM", C["text"])]:
            c = tk.Canvas(logo_frame, bg=C["sidebar"], width=TEXT_W, height=40,
                          highlightthickness=0, bd=0)
            c.pack(anchor="w", padx=20)
            c.create_text(0, 11, text=line, anchor="w",
                          fill=color, font=("Segoe UI", 20, "bold"))
        tk.Label(logo_frame, text="Evidence pracovní doby", bg=C["sidebar"],
                 fg=C["muted"], font=("Segoe UI", 8),
                 anchor="w", padx=20).pack(fill="x", pady=(4, 0))

        Separator(self.sidebar).pack(fill="x", padx=0)

        # Nav items
        nav_frame = tk.Frame(self.sidebar, bg=C["sidebar"])
        nav_frame.pack(fill="x", pady=8)

        self._nav_btns = {}
        nav_items = [
            ("dashboard", "  Dashboard"),
            ("history",   "  Historie"),
            ("planning",  "  Plánování"),
            ("settings",  "  Nastavení"),
        ]
        for key, txt in nav_items:
            # Wrapper frame simuluje chování SidebarButton
            row = tk.Frame(nav_frame, bg=C["sidebar"], cursor="hand2")
            row.pack(fill="x")
            txt_lbl = tk.Label(row, text=txt, bg=C["sidebar"], fg=C["muted"],
                               font=("Segoe UI", 10), anchor="w", cursor="hand2",
                               padx=20)
            txt_lbl.pack(side="left", fill="x", expand=True, pady=9)

            def _make_nav(row, txt_lbl, key=key):
                def on_enter(e):
                    if row.cget("bg") == C["sidebar"]:
                        row.config(bg=C["border"])
                        txt_lbl.config(bg=C["border"])
                def on_leave(e):
                    if row.cget("bg") == C["border"]:
                        row.config(bg=C["sidebar"])
                        txt_lbl.config(bg=C["sidebar"])
                def on_click(e):
                    self._show_page(key)
                for w in (row, txt_lbl):
                    w.bind("<Enter>", on_enter)
                    w.bind("<Leave>", on_leave)
                    w.bind("<Button-1>", on_click)

                class NavProxy:
                    def config(self_, bg=None, fg=None, **kw):
                        if bg:
                            row.config(bg=bg)
                            txt_lbl.config(bg=bg)
                        if fg:
                            txt_lbl.config(fg=fg)
                return NavProxy()

            self._nav_btns[key] = _make_nav(row, txt_lbl)

        # Bottom — brand logo + verze
        Separator(self.sidebar).pack(fill="x", side="bottom")
        bottom_frame = tk.Frame(self.sidebar, bg=C["sidebar"])
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=12)
        # Brand logo — šířka sidebaru 210px minus 2×20px padding = 170px
        self._brand_photo = get_logo_photo(size=170)
        if self._brand_photo:
            self._brand_logo_lbl = tk.Label(bottom_frame, image=self._brand_photo,
                     bg=C["sidebar"], bd=0)
            self._brand_logo_lbl.pack(anchor="w")
        else:
            self._brand_logo_lbl = EmojiLabel(bottom_frame, "🕐", size=32, bg=C["sidebar"])
            self._brand_logo_lbl.pack(anchor="w")
        tk.Label(bottom_frame, text="v2.0.0 · 2026", bg=C["sidebar"],
                 fg=C["muted"], font=("Segoe UI", 8),
                 anchor="w").pack(fill="x", pady=(4, 0))

    # ── TOPBAR ────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        tb = tk.Frame(self.main_frame, bg=C["surface"], height=52)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        Separator(tb).pack(side="bottom", fill="x")

        self.topbar_title = tk.Label(tb, text="Dashboard", bg=C["surface"],
                                     fg=C["text"], font=FONT_H2, anchor="w")
        self.topbar_title.pack(side="left", padx=20)

        # Right side: week badge + live badge
        right = tk.Frame(tb, bg=C["surface"])
        right.pack(side="right", padx=16)

        LiveBadge(right).pack(side="right", padx=(8, 0))

        self.week_badge = tk.Label(right, text="TÝ. 00 · 2025",
                                   bg=C["border"], fg=C["muted"],
                                   font=("Segoe UI", 8),
                                   padx=10, pady=4, relief="flat")
        self.week_badge.pack(side="right")

    # ── PAGE NAVIGATION ───────────────────────────────────────────────────────

    def _show_page(self, name):
        for key, frame in self._pages.items():
            frame.pack_forget()
        self._pages[name].pack(fill="both", expand=True)

        titles = {"dashboard": "Dashboard", "history": "Historie", "settings": "Nastavení", "planning": "Plánování"}
        self.topbar_title.config(text=titles.get(name, name))

        for key, btn in self._nav_btns.items():
            if key == name:
                btn.config(bg=C["panel"], fg=C["accent2"],
                           relief="flat")
            else:
                btn.config(bg=C["sidebar"], fg=C["muted"], relief="flat")

        if name == "history":
            self._refresh_history()
        elif name == "dashboard":
            self._refresh()
        elif name == "planning":
            self._refresh_planning()

    # ═════════════════════════════════════════════════════════════════════════
    #  DASHBOARD PAGE
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_dashboard(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["dashboard"] = page

        # Outer padding
        pad = tk.Frame(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=10)

        # ── ROW 1: Hero cards
        row1 = tk.Frame(pad, bg=C["bg"])
        row1.pack(fill="x", pady=(0, 8))

        self._build_pred_card(row1)
        self._build_progress_card(row1)

        # ── ROW 2: Stat cards
        row2 = tk.Frame(pad, bg=C["bg"])
        row2.pack(fill="x", pady=(0, 8))

        self.stat_celkem  = self._build_stat_card(row2, "🕐  CELKEM ODPRACOVÁNO", "--",      "tento týden")
        self.stat_zbyva   = self._build_stat_card(row2, "💼  ZBÝVÁ DOPRACOVAT",   "--",      "do splnění fondu")
        self.stat_bilance = self._build_stat_card(row2, "📅  MĚSÍČNÍ BILANCE",    "+0h 00m", "tento měsíc", last=True)

        # ── ROW 3: Form + Table
        row3 = tk.Frame(pad, bg=C["bg"])
        row3.pack(fill="both", expand=True)
        row3.bind("<Button-1>", lambda e: self._clear_form())
        pad.bind("<Button-1>", lambda e: self._clear_form())

        self._build_form_card(row3)
        self._build_table_card(row3)

    # ── PREDICTION CARD ───────────────────────────────────────────────────────

    def _build_pred_card(self, parent):
        card = tk.Frame(parent, bg=C["panel"], padx=24, pady=14)
        card.pack(side="left", fill="both", padx=(0, 10))

        # Top accent line (canvas trick)
        accent_bar = tk.Canvas(card, bg=C["panel"], height=3,
                               highlightthickness=0)
        accent_bar.pack(fill="x", pady=(0, 12))
        accent_bar.bind("<Configure>", lambda e: self._draw_gradient_bar(accent_bar))

        tk.Label(card, text="PREDIKCE ODCHODU", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x")

        self.pred_day_lbl = tk.Label(card, text="PÁTEK", bg=C["panel"],
                                     fg=C["accent2"], font=("Segoe UI", 9),
                                     anchor="w")
        self.pred_day_lbl.pack(fill="x", pady=(2, 0))

        self.pred_time_lbl = tk.Label(card, text="--:--", bg=C["panel"],
                                      fg=C["text"], font=FONT_HERO,
                                      anchor="w")
        self.pred_time_lbl.pack(fill="x")

        self.pred_sub_lbl = tk.Label(card, text="Výpočet...", bg=C["panel"],
                                     fg=C["muted"], font=("Segoe UI", 8),
                                     anchor="w")
        self.pred_sub_lbl.pack(fill="x")

    def _draw_gradient_bar(self, canvas):
        canvas.delete("all")
        w = canvas.winfo_width() or 200
        steps = 40
        for i in range(steps):
            x1 = int(w * i / steps)
            x2 = int(w * (i + 1) / steps)
            r = int(0x3b + (0x22 - 0x3b) * i / steps)
            g = int(0x82 + (0xc5 - 0x82) * i / steps)
            b = int(0xf6 + (0x5e - 0xf6) * i / steps)
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_rectangle(x1, 0, x2, 3, fill=color, outline="")

    # ── PROGRESS CARD ─────────────────────────────────────────────────────────

    def _build_progress_card(self, parent):
        card = tk.Frame(parent, bg=C["panel"], padx=24, pady=14)
        card.pack(side="left", fill="both", expand=True)

        # Header row
        header = tk.Frame(card, bg=C["panel"])
        header.pack(fill="x", pady=(0, 4))

        tk.Label(header, text="TÝDENNÍ FOND", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(side="left")

        self.prog_pct_lbl = tk.Label(header, text="0%", bg=C["panel"],
                                     fg=C["text"], font=("Segoe UI", 24, "bold"))
        self.prog_pct_lbl.pack(side="right")

        self.prog_bar = ProgressBar(card, height=8)
        self.prog_bar.pack(fill="x", pady=8)

        meta = tk.Frame(card, bg=C["panel"])
        meta.pack(fill="x")
        self.prog_done_lbl = tk.Label(meta, text="0h 00m odpracováno",
                                      bg=C["panel"], fg=C["muted"],
                                      font=FONT_SMALL, anchor="w")
        self.prog_done_lbl.pack(side="left")
        self.prog_left_lbl = tk.Label(meta, text="40h 00m zbývá",
                                      bg=C["panel"], fg=C["muted"],
                                      font=FONT_SMALL, anchor="e")
        self.prog_left_lbl.pack(side="right")

        # Week days mini
        self.week_days_frame = tk.Frame(card, bg=C["panel"])
        self.week_days_frame.pack(fill="x", pady=(12, 0))

    # ── STAT CARD ─────────────────────────────────────────────────────────────

    def _build_stat_card(self, parent, label, value, sub, last=False):
        card = tk.Frame(parent, bg=C["panel"], padx=20, pady=12)
        card.pack(side="left", fill="both", expand=True,
                  padx=(0, 0 if last else 10))

        lbl_row = tk.Frame(card, bg=C["panel"])
        lbl_row.pack(fill="x")
        # Odděl případné emoji (první znak) od zbytku textu
        if label and ord(label[0]) > 0x2FFF:
            EmojiLabel(lbl_row, label[0], size=13, bg=C["panel"]).pack(side="left")
            rest = label[1:].lstrip()
        else:
            rest = label
        tk.Label(lbl_row, text=rest, bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left")

        val_lbl = tk.Label(card, text=value, bg=C["panel"], fg=C["text"],
                           font=("Segoe UI", 22, "bold"), anchor="w")
        val_lbl.pack(fill="x", pady=(6, 2))

        tk.Label(card, text=sub, bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")
        return val_lbl

    # ── FORM CARD ─────────────────────────────────────────────────────────────

    def _build_form_card(self, parent):
        card = tk.Frame(parent, bg=C["panel"], padx=18, pady=14, width=340)
        card.pack(side="left", fill="both", padx=(0, 10))
        card.pack_propagate(False)
        self.form_card = card
        card.bind("<Button-1>", lambda e: self._clear_form())

        lbl_title = tk.Label(card, text="ZÁZNAM SMĚNY", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w")
        lbl_title.pack(fill="x")
        lbl_title.bind("<Button-1>", lambda e: self._clear_form())
        Separator(card).pack(fill="x", pady=8)

        # Datum
        tk.Label(card, text="DATUM", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 7), anchor="w").pack(fill="x")
        self.e_datum = DarkEntry(card)
        self.e_datum.pack(fill="x", pady=(3, 8), ipady=5)
        self.e_datum.insert(0, datetime.date.today().strftime("%Y-%m-%d"))

        # Příchod
        tk.Label(card, text="PŘÍCHOD", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 7), anchor="w").pack(fill="x")
        pr_row = tk.Frame(card, bg=C["panel"])
        pr_row.pack(fill="x", pady=(3, 8))
        pr_row.bind("<Button-1>", lambda e: self._clear_form())
        self.e_prichod = DarkEntry(pr_row, width=8)
        self.e_prichod.pack(side="left", ipady=5)
        self.e_prichod.bind("<FocusOut>", lambda e: normalizuj_cas(self.e_prichod))
        self.e_prichod.bind("<Return>", lambda e: normalizuj_cas(self.e_prichod))
        DarkButton(pr_row, text="NOW", accent=True,
                   command=lambda: self._set_now(self.e_prichod),
                   padx=8, pady=4).pack(side="left", padx=(6, 0))

        # Odchod
        tk.Label(card, text="ODCHOD", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 7), anchor="w").pack(fill="x")
        od_row = tk.Frame(card, bg=C["panel"])
        od_row.pack(fill="x", pady=(3, 8))
        od_row.bind("<Button-1>", lambda e: self._clear_form())
        self.e_odchod = DarkEntry(od_row, width=8)
        self.e_odchod.pack(side="left", ipady=5)
        self.e_odchod.bind("<FocusOut>", lambda e: normalizuj_cas(self.e_odchod))
        self.e_odchod.bind("<Return>", lambda e: normalizuj_cas(self.e_odchod))
        DarkButton(od_row, text="NOW", accent=True,
                   command=lambda: self._set_now(self.e_odchod),
                   padx=8, pady=4).pack(side="left", padx=(6, 0))

        # Oběd checkbox
        self.obed_var = tk.BooleanVar(value=True)
        obed_row = tk.Frame(card, bg=C["panel"])
        obed_row.pack(fill="x", pady=(0, 8))
        self.obed_cb = tk.Checkbutton(obed_row, text=f" Odečíst oběd ({config.OBED_MINUT} min)",
                            variable=self.obed_var,
                            bg=C["panel"], fg=C["muted"],
                            selectcolor=C["bg"],
                            activebackground=C["panel"],
                            activeforeground=C["text"],
                            font=FONT_MONO_S,
                            bd=0, highlightthickness=0,
                            cursor="hand2")
        self.obed_cb.pack(anchor="w")

        # Buttons — always at bottom
        btn_frame = tk.Frame(card, bg=C["panel"])
        btn_frame.pack(side="bottom", fill="x")

        self.save_btn = DarkButton(btn_frame, text="Uložit záznam",
                                   accent=True,
                                   command=self._save_record)
        self.save_btn.pack(fill="x")

        self.delete_btn = DarkButton(btn_frame, text="Smazat vybraný",
                                     danger=True,
                                     command=self._confirm_delete,
                                     state="disabled")
        self.delete_btn.pack(fill="x", pady=(4, 0))



    # ── TABLE CARD ────────────────────────────────────────────────────────────

    def _build_table_card(self, parent):
        card = tk.Frame(parent, bg=C["panel"], padx=16, pady=18)
        card.pack(side="left", fill="both", expand=True)

        # Toolbar
        toolbar = tk.Frame(card, bg=C["panel"])
        toolbar.pack(fill="x", pady=(0, 10))

        tk.Label(toolbar, text="ZÁZNAMY", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(side="left")

        # Week filter combobox
        self.week_filter_var = tk.StringVar(value="Vše")
        self.week_combo = ttk.Combobox(toolbar, textvariable=self.week_filter_var,
                                       style="Dark.TCombobox", width=14,
                                       state="readonly")
        self.week_combo.pack(side="right")
        self.week_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())

        # Treeview
        cols = ("id", "tyden", "datum", "prichod", "odchod", "minut")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 style="Dark.Treeview", selectmode="browse")

        heads = [("#", 40), ("Tý.", 40), ("Datum", 90), ("Příchod", 70),
                 ("Odchod", 70), ("Čistý čas", 90)]
        for (col, head_data), width in zip(zip(cols, heads), [h[1] for h in heads]):
            self.tree.heading(col, text=heads[cols.index(col)][0])
            self.tree.column(col, width=width, minwidth=width, anchor="center")

        scroll = ttk.Scrollbar(card, orient="vertical",
                               command=self.tree.yview,
                               style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.tag_configure("open", foreground=C["amber"])
        self.tree.tag_configure("even", background=C["surface"])
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._on_tree_click)

    # ═════════════════════════════════════════════════════════════════════════
    #  HISTORY PAGE
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_history(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["history"] = page

        pad = tk.Frame(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # Controls bar
        ctrl = tk.Frame(pad, bg=C["bg"])
        ctrl.pack(fill="x", pady=(0, 12))

        self.month_filter_var = tk.StringVar(value="Všechny měsíce")
        self.month_combo = ttk.Combobox(ctrl, textvariable=self.month_filter_var,
                                        style="Dark.TCombobox", width=18,
                                        state="readonly")
        self.month_combo.pack(side="left")
        self.month_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_history())

        DarkButton(ctrl, text="↓  Export CSV",
                   command=self._export_csv,
                   padx=14).pack(side="left", padx=10)

        self.hist_count_lbl = tk.Label(ctrl, text="0 záznamů",
                                       bg=C["bg"], fg=C["muted"],
                                       font=FONT_SMALL)
        self.hist_count_lbl.pack(side="right")

        # Table
        card = tk.Frame(pad, bg=C["panel"], padx=16, pady=16)
        card.pack(fill="both", expand=True)

        h_cols = ("id", "tyden", "datum", "den", "prichod", "odchod", "obed", "minut")
        self.hist_tree = ttk.Treeview(card, columns=h_cols, show="headings",
                                      style="Dark.Treeview", selectmode="browse")

        h_heads = [("#", 40), ("Tý.", 40), ("Datum", 95), ("Den", 40),
                   ("Příchod", 70), ("Odchod", 70), ("Ob.", 40), ("Čistý čas", 90)]
        for col, (head, w) in zip(h_cols, h_heads):
            self.hist_tree.heading(col, text=head)
            self.hist_tree.column(col, width=w, minwidth=w, anchor="center")

        h_scroll = ttk.Scrollbar(card, orient="vertical",
                                 command=self.hist_tree.yview,
                                 style="Dark.Vertical.TScrollbar")
        self.hist_tree.configure(yscrollcommand=h_scroll.set)
        self.hist_tree.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="right", fill="y")

        self.hist_tree.tag_configure("open", foreground=C["amber"])
        self.hist_tree.tag_configure("even", background=C["surface"])

    # ═════════════════════════════════════════════════════════════════════════
    #  PLANNING PAGE — Svátky / Dovolená / Nemocenská
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_planning(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["planning"] = page

        pad = tk.Frame(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Horní toolbar
        toolbar = tk.Frame(pad, bg=C["bg"])
        toolbar.pack(fill="x", pady=(0, 12))

        self._plan_month_var = tk.StringVar()
        self._plan_month_var.set(datetime.date.today().strftime("%Y-%m"))

        nav_l = DarkButton(toolbar, text="◀", ghost=True, padx=8, pady=4,
                           command=self._plan_prev_month)
        nav_l.pack(side="left")

        self._plan_month_lbl = tk.Label(toolbar, text="", bg=C["bg"],
                                        fg=C["text"], font=FONT_H2, width=16)
        self._plan_month_lbl.pack(side="left", padx=8)

        nav_r = DarkButton(toolbar, text="▶", ghost=True, padx=8, pady=4,
                           command=self._plan_next_month)
        nav_r.pack(side="left")

        DarkButton(toolbar, text="⬇  Stáhnout svátky CZ",
                   command=self._plan_import_holidays,
                   padx=12, pady=4).pack(side="right")

        # ── Dvousloupcový layout: kalendář + panel pro editaci
        body = tk.Frame(pad, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # Levý sloupec — kalendář
        cal_frame = tk.Frame(body, bg=C["panel"], padx=16, pady=16)
        cal_frame.pack(side="left", fill="both", expand=True)
        self._plan_cal_frame = cal_frame

        # Pravý sloupec — přidání záznamu
        right = tk.Frame(body, bg=C["bg"], width=280)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        # Karta přidání
        add_card = tk.Frame(right, bg=C["panel"], padx=18, pady=16)
        add_card.pack(fill="x")

        tk.Label(add_card, text="NOVÝ ZÁZNAM", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x")
        Separator(add_card).pack(fill="x", pady=8)

        tk.Label(add_card, text="DATUM", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 7), anchor="w").pack(fill="x")
        self._plan_datum = DarkEntry(add_card)
        self._plan_datum.pack(fill="x", pady=(3, 8), ipady=5)
        self._plan_datum.insert(0, datetime.date.today().strftime("%Y-%m-%d"))

        tk.Label(add_card, text="TYP", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 7), anchor="w").pack(fill="x")
        self._plan_typ_var = tk.StringVar(value="holiday")
        for key, label in special_days.TYPES.items():
            color = special_days.TYPE_COLORS[key]
            rb = tk.Radiobutton(
                add_card,
                text=f"  {special_days.TYPE_EMOJI[key]}  {label}",
                variable=self._plan_typ_var,
                value=key,
                bg=C["panel"], fg=C["text"],
                selectcolor=C["bg"],
                activebackground=C["panel"],
                activeforeground=color,
                font=FONT_MONO_S,
                bd=0, highlightthickness=0,
                cursor="hand2",
            )
            rb.pack(anchor="w", pady=2)

        tk.Label(add_card, text="POZNÁMKA (volitelné)", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 7), anchor="w").pack(fill="x", pady=(8, 0))
        self._plan_poznamka = DarkEntry(add_card)
        self._plan_poznamka.pack(fill="x", pady=(3, 8), ipady=4)

        DarkButton(add_card, text="Uložit", accent=True,
                   command=self._plan_save).pack(fill="x")
        DarkButton(add_card, text="Smazat vybraný den", danger=True,
                   command=self._plan_delete).pack(fill="x", pady=(4, 0))

        # Karta legenda
        leg_card = tk.Frame(right, bg=C["panel"], padx=18, pady=14)
        leg_card.pack(fill="x", pady=(12, 0))
        tk.Label(leg_card, text="LEGENDA", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x")
        Separator(leg_card).pack(fill="x", pady=6)
        legend_items = [
            ("holiday",  "Fond zachován, počítá se jako odpracovaný"),
            ("vacation", "Fond zachován, počítá se jako odpracovaný"),
            ("sick",     "Fond SNÍŽEN o 8h, den se nepočítá"),
        ]
        for typ, desc in legend_items:
            row = tk.Frame(leg_card, bg=C["panel"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{special_days.TYPE_EMOJI[typ]} {special_days.TYPES[typ]}",
                     bg=C["panel"], fg=special_days.TYPE_COLORS[typ],
                     font=FONT_MONO_S, anchor="w", width=16).pack(side="left")
            tk.Label(row, text=desc, bg=C["panel"], fg=C["muted"],
                     font=("Segoe UI", 7), anchor="w",
                     wraplength=180, justify="left").pack(side="left")

    def _plan_prev_month(self):
        y, m = map(int, self._plan_month_var.get().split("-"))
        m -= 1
        if m < 1:
            m = 12; y -= 1
        self._plan_month_var.set(f"{y}-{m:02d}")
        self._refresh_planning()

    def _plan_next_month(self):
        y, m = map(int, self._plan_month_var.get().split("-"))
        m += 1
        if m > 12:
            m = 1; y += 1
        self._plan_month_var.set(f"{y}-{m:02d}")
        self._refresh_planning()

    def _refresh_planning(self):
        import calendar as cal_mod
        month_str = self._plan_month_var.get()
        y, m = map(int, month_str.split("-"))

        mesice = ["Leden","Únor","Březen","Duben","Květen","Červen",
                  "Červenec","Srpen","Září","Říjen","Listopad","Prosinec"]
        self._plan_month_lbl.config(text=f"{mesice[m-1]} {y}")

        days_data = special_days.fetch_month(month_str)
        special_map = {r[0]: (r[1], r[2]) for r in days_data}

        # Vymaž obsah
        for w in self._plan_cal_frame.winfo_children():
            w.destroy()

        # Jeden grid frame — vše přes .grid(row, col)
        gf = tk.Frame(self._plan_cal_frame, bg=C["panel"])
        gf.pack(fill="both", expand=True)

        # 7 sloupců stejné šířky
        for col in range(7):
            gf.columnconfigure(col, weight=1, uniform="cal")

        # Hlavičky — řádek 0
        day_names = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
        for col, dn in enumerate(day_names):
            tk.Label(gf, text=dn, bg=C["panel"], fg=C["muted"],
                     font=("Segoe UI", 8, "bold"),
                     anchor="center", pady=6).grid(row=0, column=col, sticky="nsew")

        # Oddělovač — řádek 1
        sep = tk.Frame(gf, bg=C["border"], height=1)
        sep.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(0, 4))

        first_weekday, num_days = cal_mod.monthrange(y, m)
        today = datetime.date.today()

        for day_num in range(1, num_days + 1):
            abs_pos  = first_weekday + day_num - 1
            grid_row = 2 + abs_pos // 7
            grid_col = abs_pos % 7

            date_obj = datetime.date(y, m, day_num)
            date_str = date_obj.strftime("%Y-%m-%d")
            day_type = special_map.get(date_str, (None, ""))[0]
            is_weekend = date_obj.weekday() >= 5
            is_today   = (date_obj == today)

            if is_today:
                cell_bg = C["accent"]
                cell_fg = C["white"]
            elif day_type == "sick":
                cell_bg = "#3d1a1a"
                cell_fg = special_days.TYPE_COLORS["sick"]
            elif day_type == "holiday":
                cell_bg = "#3d2e0a"
                cell_fg = special_days.TYPE_COLORS["holiday"]
            elif day_type == "vacation":
                cell_bg = "#0d2e1a"
                cell_fg = special_days.TYPE_COLORS["vacation"]
            elif is_weekend:
                cell_bg = C["surface"]
                cell_fg = C["muted"]
            else:
                cell_bg = C["panel"]
                cell_fg = C["text"]

            emoji = special_days.TYPE_EMOJI.get(day_type, "") if day_type else ""
            label_text = f"{day_num}\n{emoji}" if emoji else str(day_num)

            cell = tk.Label(
                gf,
                text=label_text,
                bg=cell_bg, fg=cell_fg,
                font=("Segoe UI", 10),
                height=3,
                relief="flat",
                cursor="hand2" if not is_weekend else "arrow",
                anchor="center",
                justify="center",
            )
            cell.grid(row=grid_row, column=grid_col, sticky="nsew", padx=2, pady=2)

            if not is_weekend:
                def _on_click(e, ds=date_str):
                    self._plan_datum.delete(0, tk.END)
                    self._plan_datum.insert(0, ds)
                    existing = special_days.get(ds)
                    if existing:
                        self._plan_typ_var.set(existing[1])
                        self._plan_poznamka.delete(0, tk.END)
                        self._plan_poznamka.insert(0, existing[2] or "")
                    else:
                        self._plan_poznamka.delete(0, tk.END)
                cell.bind("<Button-1>", _on_click)
                orig_bg = cell_bg
                cell.bind("<Enter>", lambda e, w=cell: w.config(bg=C["border2"]))
                cell.bind("<Leave>", lambda e, w=cell, bg=orig_bg: w.config(bg=bg))
    def _plan_save(self):
        datum = self._plan_datum.get().strip()
        typ   = self._plan_typ_var.get()
        pozn  = self._plan_poznamka.get().strip()
        try:
            datetime.datetime.strptime(datum, "%Y-%m-%d")
        except ValueError:
            self._toast("Neplatný formát data (YYYY-MM-DD)", error=True)
            return
        ok = special_days.upsert(datum, typ, pozn)
        if ok:
            self._toast(f"Uloženo: {datum} → {special_days.TYPES.get(typ, typ)}")
            self._plan_month_var.set(datum[:7])
            self._refresh_planning()
            self._refresh_dashboard()
        else:
            self._toast("Chyba při ukládání", error=True)

    def _plan_delete(self):
        datum = self._plan_datum.get().strip()
        existing = special_days.get(datum)
        if not existing:
            self._toast(f"Pro {datum} není žádný záznam", error=True)
            return
        if messagebox.askyesno(
            "Smazat záznam",
            f"Smazat záznam pro {datum}?\n({special_days.TYPES.get(existing[1], existing[1])})",
            parent=self
        ):
            special_days.delete(datum)
            self._toast(f"Smazáno: {datum}")
            self._refresh_planning()
            self._refresh_dashboard()

    def _plan_import_holidays(self):
        dialog = tk.Toplevel(self)
        dialog.title("Stáhnout státní svátky")
        dialog.configure(bg=C["bg"])
        dialog.geometry("420x320")
        dialog.resizable(False, False)
        dialog.grab_set()
        set_dark_title_bar(dialog)

        tk.Label(dialog, text="Stáhnout české státní svátky",
                 bg=C["bg"], fg=C["text"], font=FONT_H2).pack(
            anchor="w", padx=24, pady=(20, 4))
        tk.Label(
            dialog,
            text="Aplikace se pokusí stáhnout svátky z veřejného API.\n"
                 "Pokud API není dostupné, použije vestavěný seznam svátků\n"
                 "(pevná data + Velikonoce).\n\n"
                 "Data budou uložena jako typ 'Státní svátek'.",
            bg=C["bg"], fg=C["muted"], font=("Segoe UI", 9),
            justify="left", wraplength=370
        ).pack(anchor="w", padx=24, pady=(0, 12))

        year_frame = tk.Frame(dialog, bg=C["bg"])
        year_frame.pack(anchor="w", padx=24, pady=(0, 8))
        tk.Label(year_frame, text="Rok:", bg=C["bg"], fg=C["text"],
                 font=FONT_MONO).pack(side="left", padx=(0, 8))
        year_var = tk.StringVar(value=str(datetime.date.today().year))
        DarkEntry(year_frame, width=8, justify="center",
                  textvariable=year_var).pack(side="left")

        overwrite_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            dialog,
            text="  Přepsat existující záznamy",
            variable=overwrite_var,
            bg=C["bg"], fg=C["muted"],
            selectcolor=C["panel"],
            activebackground=C["bg"],
            font=FONT_MONO_S, bd=0,
            highlightthickness=0, cursor="hand2"
        ).pack(anchor="w", padx=24, pady=(0, 10))

        result_lbl = tk.Label(dialog, text="", bg=C["bg"],
                              fg=C["muted"], font=("Segoe UI", 8),
                              wraplength=370, justify="left")
        result_lbl.pack(anchor="w", padx=24)

        btn_frame = tk.Frame(dialog, bg=C["bg"])
        btn_frame.pack(side="bottom", fill="x", padx=24, pady=16)

        def do_import():
            try:
                year = int(year_var.get())
            except ValueError:
                result_lbl.config(text="Neplatný rok.", fg=C["red"])
                return
            result_lbl.config(text="Stahování...", fg=C["muted"])
            dialog.update()
            try:
                pridano, preskoceno, zdroj = special_days.import_holidays_from_api(
                    year, overwrite=overwrite_var.get()
                )
                result_lbl.config(
                    text=f"✓ Přidáno: {pridano}, přeskočeno: {preskoceno}\n{zdroj}",
                    fg=C["green"]
                )
                self._refresh_planning()
                self._refresh_dashboard()
            except Exception as e:
                result_lbl.config(text=f"Chyba: {e}", fg=C["red"])

        DarkButton(btn_frame, text="⬇  Stáhnout", accent=True,
                   command=do_import).pack(side="left")
        DarkButton(btn_frame, text="Zavřít",
                   command=dialog.destroy).pack(side="right")

    # ═════════════════════════════════════════════════════════════════════════
    #  SETTINGS PAGE
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_settings(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["settings"] = page

        # Scrollovatelný canvas
        canvas = tk.Canvas(page, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(page, orient="vertical",
                                  command=canvas.yview,
                                  style="Dark.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        pad = tk.Frame(canvas, bg=C["bg"])
        pad_window = canvas.create_window((0, 0), window=pad, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(pad_window, width=e.width)

        pad.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Scroll myší
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Odváž scroll při opuštění stránky
        page.bind("<Unmap>", lambda e: canvas.unbind_all("<MouseWheel>"))
        page.bind("<Map>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))

        # Přidej vnitřní padding
        inner = tk.Frame(pad, bg=C["bg"])
        inner.pack(fill="both", expand=True, padx=20, pady=16)
        pad = inner  # zbytek kódu používá pad beze změny

        def section(title):
            tk.Label(pad, text=title, bg=C["bg"],
                     fg=C["text"], font=FONT_H2,
                     anchor="w").pack(fill="x", pady=(16, 4))
            Separator(pad).pack(fill="x", pady=(0, 8))

        def setting_row(label, desc, widget_fn):
            row = tk.Frame(pad, bg=C["panel"], padx=20, pady=14)
            row.pack(fill="x", pady=(0, 2))
            info = tk.Frame(row, bg=C["panel"])
            info.pack(side="left", fill="both", expand=True)
            tk.Label(info, text=label, bg=C["panel"], fg=C["text"],
                     font=FONT_MONO, anchor="w").pack(anchor="w")
            tk.Label(info, text=desc, bg=C["panel"], fg=C["muted"],
                     font=("Segoe UI", 8), anchor="w").pack(anchor="w")
            w = widget_fn(row)
            w.pack(side="right")
            return w

        section("Pracovní fond")

        def mk_fond(p):
            e = DarkEntry(p, width=8, justify="center")
            e.insert(0, str(config.TYDENNI_FOND_HODIN))
            e.bind("<KeyRelease>", self._schedule_apply)
            return e
        self.set_fond = setting_row("Týdenní fond hodin",
                                    "Celkový počet hodin za pracovní týden", mk_fond)

        def mk_obed(p):
            e = DarkEntry(p, width=8, justify="center")
            e.insert(0, str(config.OBED_MINUT))
            e.bind("<KeyRelease>", self._schedule_apply)
            return e
        self.set_obed = setting_row("Délka oběda (min)",
                                    "Počet minut odečtených za oběd", mk_obed)

        section("Standardní časy")

        def mk_prichod(p):
            e = DarkEntry(p, width=8, justify="center")
            e.insert(0, config.STANDARDNI_PRICHOD)
            e.bind("<KeyRelease>", self._schedule_apply)
            return e
        self.set_prichod = setting_row("Standardní příchod",
                                       "Výchozí čas příchodu", mk_prichod)

        def mk_odchod(p):
            e = DarkEntry(p, width=8, justify="center")
            e.insert(0, config.STANDARDNI_ODCHOD)
            e.bind("<KeyRelease>", self._schedule_apply)
            return e
        self.set_odchod = setting_row("Standardní odchod",
                                      "Výchozí čas odchodu", mk_odchod)

        section("Databáze")

        def mk_db_path(p):
            frame = tk.Frame(p, bg=C["panel"])
            e = DarkEntry(frame, width=32, justify="left")
            e.insert(0, config.DB_PATH_OVERRIDE)
            e.pack(side="left", padx=(0, 6))
            def browse():
                folder = filedialog.askdirectory(title="Zvolit složku pro databázi")
                if folder:
                    e.delete(0, "end")
                    e.insert(0, folder)
                    self._apply_db_folder(folder)
            DarkButton(frame, text="…", command=browse, padx=8, pady=4).pack(side="left")
            return frame
        self.set_db_path_frame = setting_row(
            "Složka databáze",
            "Výchozí: %APPDATA%\\WageSlave\\  (prázdné = výchozí)",
            mk_db_path
        )
        self.set_db_path = self.set_db_path_frame.winfo_children()[0]

        # Zálohy
        self.set_backup_var = tk.BooleanVar(value=config.AUTO_BACKUP)
        row_bak = tk.Frame(pad, bg=C["panel"], padx=20, pady=14)
        row_bak.pack(fill="x", pady=(0, 2))
        info_bak = tk.Frame(row_bak, bg=C["panel"])
        info_bak.pack(side="left", fill="both", expand=True)
        tk.Label(info_bak, text="Automatické zálohy", bg=C["panel"],
                 fg=C["text"], font=FONT_MONO, anchor="w").pack(anchor="w")
        tk.Label(info_bak, text="1× měsíčně zazipuje databázi a config do %APPDATA%\\WageSlave\\backup\\",
                 bg=C["panel"], fg=C["muted"], font=("Segoe UI", 8), anchor="w").pack(anchor="w")
        tk.Checkbutton(row_bak, variable=self.set_backup_var,
                       bg=C["panel"], activebackground=C["panel"],
                       selectcolor=C["accent"], bd=0, highlightthickness=0,
                       cursor="hand2", command=self._apply_settings).pack(side="right")

        section("Vzhled")

        LOGO_VARIANTY = [
            ("purple",      "Purple"),
            ("purple_neon", "Purple Neon"),
            ("money",       "Money"),
            ("money_neon",  "Money Neon"),
            ("slave",       "Slave"),
            ("slave_neon",  "Slave Neon"),
        ]

        def mk_logo(p):
            frame = tk.Frame(p, bg=C["panel"])
            self._logo_var = tk.StringVar(value=config.LOGO_VARIANTA)
            combo = ttk.Combobox(frame, textvariable=self._logo_var,
                                 values=[label for _, label in LOGO_VARIANTY],
                                 style="Dark.TCombobox", width=14, state="readonly")
            # Nastav aktuální hodnotu jako zobrazený label
            cur_key = config.LOGO_VARIANTA
            for key, label in LOGO_VARIANTY:
                if key == cur_key:
                    self._logo_var.set(label)
                    break
            combo.pack(side="left", padx=(0, 6))

            def on_logo_change(event=None):
                label = self._logo_var.get()
                for key, lbl in LOGO_VARIANTY:
                    if lbl == label:
                        config.LOGO_VARIANTA = key
                        break
                config.save()
                # Přenačti logo v sidebaru
                self._brand_photo = get_logo_photo(size=170)
                if self._brand_photo and hasattr(self, '_brand_logo_lbl'):
                    self._brand_logo_lbl.config(image=self._brand_photo)
                self._toast(f"Logo změněno: {label}")

            combo.bind("<<ComboboxSelected>>", on_logo_change)
            return frame

        setting_row("Logo aplikace",
                    "Ikona zobrazená v levém dolním rohu",
                    mk_logo)

        row_del = tk.Frame(pad, bg=C["panel"], padx=20, pady=14)
        row_del.pack(fill="x", pady=(0, 2))
        info_del = tk.Frame(row_del, bg=C["panel"])
        info_del.pack(side="left", fill="both", expand=True)
        tk.Label(info_del, text="Smazat všechna data", bg=C["panel"],
                 fg=C["text"], font=FONT_MONO, anchor="w").pack(anchor="w")
        tk.Label(info_del, text="Tato akce je nevratná", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 8), anchor="w").pack(anchor="w")
        DarkButton(row_del, text="Smazat vše", danger=True,
                   command=self._clear_all).pack(side="right")

    # ═════════════════════════════════════════════════════════════════════════
    #  DATA REFRESH
    # ═════════════════════════════════════════════════════════════════════════

    def _refresh(self):
        self._refresh_dashboard()
        self._refresh_table()

    def _refresh_dashboard(self):
        dnes = datetime.date.today()
        tyden = get_week_number(dnes)
        records = self.db.fetch_by_week(tyden)

        # Week badge
        self.week_badge.config(
            text=f"TÝ. {tyden:02d} · {dnes.year}"
        )

        # Week analysis
        ana = week_analysis(records, dnes)
        skutecne = ana['skutecne_celkem']
        zbyva    = ana['zbyva']
        procenta = ana['procenta']
        cas_p    = ana['cas_patek']
        otevrene = ana['otevrene_dnes']

        # Prediction — používá pred_label z kalkulátoru
        pred_label = ana.get('pred_label', 'Pá')   # např. "Pá", "Čt (pá – svátek)"
        pred_den   = ana.get('pred_den')            # date objekt

        # Horní řádek: je to dnes nebo jiný den?
        if pred_den == dnes:
            pred_day = "DNES"
        elif pred_den and pred_den.weekday() == 4:
            pred_day = "PÁTEK"
        else:
            # Předchozí pracovní den (čtvrtek atd.)
            pred_day = pred_label.split(" ")[0].upper() if pred_label else "PÁTEK"
        self.pred_day_lbl.config(text=pred_day)

        if cas_p == "Volno":
            self.pred_time_lbl.config(text="Volno", fg=C["green"])
            sub = f"Volno — {pred_label}"
        elif cas_p.startswith("Nyní ("):
            time_part = cas_p[6:-1]
            self.pred_time_lbl.config(text=time_part, fg=C["green"])
            self.pred_day_lbl.config(text="TEĎ →")
            sub = "Fond splněn, můžeš odejít"
        elif cas_p == "✓ Hotovo":
            self.pred_time_lbl.config(text="✓", fg=C["green"])
            sub = "Týdenní fond splněn!"
        elif cas_p == "NESTÍHÁŠ!":
            self.pred_time_lbl.config(text=cas_p, fg=C["red"])
            sub = "Fond nesplnitelný dnes"
        else:
            self.pred_time_lbl.config(text=cas_p, fg=C["text"])
            # Sub: "Plánovaný odchod v Čt (pá – svátek) · 40h fond"
            sub = f"Odchod: {pred_label}  ·  {config.TYDENNI_FOND_HODIN}h fond"
        self.pred_sub_lbl.config(text=sub)

        # Progress
        self.prog_pct_lbl.config(text=f"{procenta}%")
        self.prog_bar.set(procenta)
        self.prog_done_lbl.config(text=f"{formatuj_minuty(skutecne)} odpracováno")
        celkem_fond     = ana.get('celkem_fond', config.TYDENNI_FOND_HODIN * 60)
        reducing_count  = ana.get('fond_reducing_tyden', 0)
        fond_label      = f"{formatuj_minuty(zbyva)} zbývá"
        if reducing_count:
            fond_label += f"  (fond –{reducing_count}d)"
        self.prog_left_lbl.config(text=fond_label)

        # Week days mini display
        for w in self.week_days_frame.winfo_children():
            w.destroy()

        from collections import defaultdict
        denni = defaultdict(int)
        for r in records:
            denni[r[2]] += r[5] or 0

        start = dnes - datetime.timedelta(days=dnes.weekday())
        day_labels = ["Po", "Út", "St", "Čt", "Pá"]
        # Získej special days pro tento týden z výsledku week_analysis
        week_special = ana.get('special', {})
        for i, dl in enumerate(day_labels):
            d = start + datetime.timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            day_type = week_special.get(d)
            mins = denni.get(ds, 0)
            if day_type == "sick":
                txt = f"{dl}: 🤒"
                color = C["red"]
            elif day_type == "holiday":
                txt = f"{dl}: 🎉"
                color = C["amber"]
            elif day_type == "vacation":
                txt = f"{dl}: 🏖"
                color = C["green"]
            else:
                color = C["accent2"] if d == dnes else (C["text"] if d < dnes else C["muted"])
                txt = f"{dl}: {formatuj_minuty(mins)}" if mins else f"{dl}: --"
            tk.Label(self.week_days_frame, text=txt, bg=C["panel"],
                     fg=color, font=FONT_SMALL).pack(side="left", padx=(0, 16))

        # Stats
        self.stat_celkem.config(text=formatuj_minuty(skutecne))
        self.stat_zbyva.config(text=formatuj_minuty(zbyva))

        # Month balance
        month_str = dnes.strftime("%Y-%m")
        month_recs = self.db.fetch_by_month(month_str)
        bil = month_balance(month_recs, dnes)
        sign = "+" if bil >= 0 else ""
        self.stat_bilance.config(
            text=f"{sign}{formatuj_minuty(abs(bil))}",
            fg=C["green"] if bil > 0 else (C["red"] if bil < 0 else C["text"])
        )

    def _refresh_table(self):
        # Update week filter combobox
        weeks = self.db.fetch_distinct_weeks()
        options = ["Vše"] + [f"Týden {w}" for w in weeks]
        self.week_combo["values"] = options
        cur = self.week_filter_var.get()

        # On first load (still "Vše" default), auto-select current week if available
        if cur == "Vše" and not hasattr(self, '_table_initialized'):
            self._table_initialized = True
            current_week = get_week_number(datetime.date.today())
            current_week_str = f"Týden {current_week}"
            if current_week_str in options:
                self.week_filter_var.set(current_week_str)
                cur = current_week_str
            elif weeks:
                # Fall back to most recent week
                latest = f"Týden {weeks[0]}"
                self.week_filter_var.set(latest)
                cur = latest

        if cur not in options:
            self.week_filter_var.set("Vše")
            cur = "Vše"

        # Fetch data
        sel = self.week_filter_var.get()
        if sel == "Vše":
            data = self.db.fetch_all()
        else:
            w = int(sel.split()[-1])
            data = self.db.fetch_by_week(w)

        # Populate tree
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(data):
            # r: id, tyden, datum, prichod, odchod, minut, obed
            odchod_txt = r[4] if r[4] else "---"
            minut_txt  = formatuj_minuty(r[5]) if r[5] else "--"
            tag = "open" if not r[4] else ("even" if i % 2 else "")
            iid = self.tree.insert("", "end",
                iid=str(r[0]),
                values=(f"#{r[0]}", r[1], r[2], r[3] or "--",
                        odchod_txt, minut_txt),
                tags=(tag,)
            )

        # Re-select if still exists
        if self.selected_id:
            try:
                self.tree.selection_set(str(self.selected_id))
                self.tree.see(str(self.selected_id))
            except Exception:
                self._clear_form()

    def _refresh_history(self):
        months = self.db.fetch_months_for_export()
        month_strs = [f"{r[0]}-{r[1]}" for r in months]
        options = ["Všechny měsíce"] + month_strs
        self.month_combo["values"] = options
        cur = self.month_filter_var.get()
        if cur not in options:
            self.month_filter_var.set("Všechny měsíce")

        sel = self.month_filter_var.get()
        if sel == "Všechny měsíce":
            data = self.db.fetch_all()
        else:
            data = []
            all_data = self.db.fetch_all()
            data = [r for r in all_data if r[2].startswith(sel)]

        self.hist_count_lbl.config(text=f"{len(data)} záznamů")
        self.hist_tree.delete(*self.hist_tree.get_children())
        for i, r in enumerate(sorted(data, key=lambda x: x[2], reverse=True)):
            d = datetime.datetime.strptime(r[2], "%Y-%m-%d").date()
            tag = "open" if not r[4] else ("even" if i % 2 else "")
            self.hist_tree.insert("", "end",
                values=(f"#{r[0]}", r[1], r[2], day_name_cs(d),
                        r[3] or "--", r[4] or "---",
                        "✓" if r[6] else "–",
                        formatuj_minuty(r[5]) if r[5] else "--"),
                tags=(tag,)
            )

    # ═════════════════════════════════════════════════════════════════════════
    #  FORM OPERATIONS
    # ═════════════════════════════════════════════════════════════════════════

    def _set_now(self, entry):
        entry.delete(0, tk.END)
        entry.insert(0, datetime.datetime.now().strftime("%H:%M"))

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        self.selected_id = int(iid)
        rec = self.db.fetch_by_id(self.selected_id)
        if not rec:
            return
        # r: id, tyden, datum, prichod, odchod, minut, obed
        self.e_datum.delete(0, tk.END)
        self.e_datum.insert(0, rec[2])
        self.e_prichod.delete(0, tk.END)
        self.e_prichod.insert(0, rec[3] or "")
        self.e_odchod.delete(0, tk.END)
        self.e_odchod.insert(0, rec[4] or "")
        self.obed_var.set(bool(rec[6]))
        self.save_btn.config(text="Aktualizovat")
        self.delete_btn.config(state="normal")

    def _on_tree_click(self, event):
        """Deselect when clicking on empty area of the treeview."""
        if not self.tree.identify_row(event.y):
            self._clear_form()

    def _clear_form(self):
        self.selected_id = None
        self.e_datum.delete(0, tk.END)
        self.e_datum.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.e_prichod.delete(0, tk.END)
        self.e_odchod.delete(0, tk.END)
        self.obed_var.set(True)
        self.save_btn.config(text="Uložit záznam")
        self.delete_btn.config(state="disabled")
        self.tree.selection_remove(self.tree.selection())

    def _save_record(self):
        datum   = self.e_datum.get().strip()
        prichod = self.e_prichod.get().strip()
        odchod  = self.e_odchod.get().strip() or None
        obed    = 1 if self.obed_var.get() else 0

        if not datum or not prichod:
            self._toast("Vyplňte datum a čas příchodu", error=True)
            return

        try:
            datetime.datetime.strptime(datum, "%Y-%m-%d")
        except ValueError:
            self._toast("Neplatný formát data (YYYY-MM-DD)", error=True)
            return

        tyden = get_week_number(datetime.datetime.strptime(datum, "%Y-%m-%d").date())

        if self.selected_id is not None:
            self.db.update(self.selected_id, datum, prichod, odchod, obed, tyden)
            self._toast("Záznam aktualizován")
        else:
            self.db.insert(datum, prichod, odchod, obed, tyden)
            self._toast("Záznam uložen")

        self._clear_form()
        self._refresh()

    def _confirm_delete(self):
        if self.selected_id is None:
            return
        rec = self.db.fetch_by_id(self.selected_id)
        if not rec:
            return
        if messagebox.askyesno(
            "Smazat záznam",
            f"Opravdu smazat záznam #{rec[0]}?\n{rec[2]} · {rec[3]} → {rec[4] or '---'}\n\nTuto akci nelze vrátit.",
            parent=self
        ):
            self.db.delete(self.selected_id)
            self._clear_form()
            self._refresh()
            self._toast("Záznam smazán")

    # ═════════════════════════════════════════════════════════════════════════
    #  EXPORT
    # ═════════════════════════════════════════════════════════════════════════

    def _export_csv(self):
        months_raw = self.db.fetch_months_for_export()
        if not months_raw:
            self._toast("Žádná data k exportu", error=True)
            return

        # Dialog for month selection
        dialog = tk.Toplevel(self)
        dialog.title("Export CSV")
        dialog.configure(bg=C["bg"])
        dialog.geometry("340x320")
        dialog.resizable(False, False)
        dialog.grab_set()
        set_dark_title_bar(dialog)

        tk.Label(dialog, text="Vyberte měsíce pro export:",
                 bg=C["bg"], fg=C["text"], font=FONT_MONO).pack(
            anchor="w", padx=20, pady=(16, 8))

        list_frame = tk.Frame(dialog, bg=C["bg"])
        list_frame.pack(fill="both", expand=True, padx=20)

        vars_ = []
        for rok, mesic in months_raw:
            v = tk.BooleanVar(value=True)
            vars_.append((v, f"{rok}-{mesic}"))
            cb = tk.Checkbutton(list_frame, text=f"{rok}-{mesic}",
                                variable=v, bg=C["bg"], fg=C["text"],
                                selectcolor=C["accent"],
                                activebackground=C["bg"],
                                font=FONT_MONO_S, bd=0,
                                highlightthickness=0, cursor="hand2")
            cb.pack(anchor="w", pady=2)

        def do_export():
            selected = [m for v, m in vars_ if v.get()]
            if not selected:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV soubory", "*.csv"), ("Všechny soubory", "*.*")],
                initialfile=f"dochazka_export.csv",
                parent=dialog
            )
            if not path:
                return
            data = self.db.fetch_for_export(selected)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Datum", "Den", "Příchod", "Odchod"])
                for row in data:
                    d = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
                    w.writerow([row[0], day_name_cs(d), row[1], row[2] or ""])
            dialog.destroy()
            self._toast(f"Exportováno {len(data)} záznamů")

        DarkButton(dialog, text="↓  Exportovat CSV", accent=True,
                   command=do_export).pack(padx=20, pady=14, fill="x")

    # ═════════════════════════════════════════════════════════════════════════
    #  SETTINGS
    # ═════════════════════════════════════════════════════════════════════════

    def _apply_settings(self, event=None):
        try:
            config.TYDENNI_FOND_HODIN = int(self.set_fond.get())
        except ValueError:
            pass
        try:
            config.OBED_MINUT = int(self.set_obed.get())
        except ValueError:
            pass
        p = self.set_prichod.get().strip()
        if p:
            config.STANDARDNI_PRICHOD = p
        o = self.set_odchod.get().strip()
        if o:
            config.STANDARDNI_ODCHOD = o
        db_p = self.set_db_path.get().strip() if hasattr(self, "set_db_path") else ""
        # Pokud zadali složku (ne celou cestu k souboru), doplň název souboru
        if db_p and not db_p.endswith(".db"):
            db_p = os.path.join(db_p, "wageslave.db")
        config.DB_PATH_OVERRIDE = db_p
        config.AUTO_BACKUP = bool(self.set_backup_var.get()) if hasattr(self, "set_backup_var") else False
        config.save()
        # Aktualizuj text oběd checkboxu
        if hasattr(self, "obed_cb"):
            self.obed_cb.config(text=f" Odečíst oběd ({config.OBED_MINUT} min)")
        self._refresh_dashboard()
        self._toast("Nastavení uloženo")

    def _schedule_apply(self, event=None):
        """Debounced autosave — uloží 800 ms po posledním stisku klávesy."""
        if hasattr(self, "_autosave_job") and self._autosave_job:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(800, self._apply_settings)

    def _clear_all(self):
        if messagebox.askyesno(
            "Smazat všechna data",
            "Opravdu smazat VŠECHNA data z databáze?\n\nTuto akci nelze vrátit!",
            parent=self
        ):
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("DELETE FROM dochazka")
            self._clear_form()
            self._refresh()
            self._toast("Všechna data smazána")

    # ═════════════════════════════════════════════════════════════════════════
    #  AUTOMATICKÝ PŘÍCHOD / ODCHOD
    # ═════════════════════════════════════════════════════════════════════════

    def _auto_zapis_prichod(self):
        dnes = datetime.date.today()
        if dnes.weekday() >= 5:  # víkend
            return
        dnes_str = dnes.strftime("%Y-%m-%d")
        tyden = get_week_number(dnes)

        # Zjistit, zda dnes už existuje záznam
        all_today = [r for r in self.db.fetch_by_week(tyden) if r[2] == dnes_str]
        if all_today:
            return  # už máme záznam pro dnešek

        # Auto-příchod: zkusit načíst čas posledního zapnutí z event logu
        prichod_time = None
        try:
            # Jednoduché přiblížení: příchod = teď (při spuštění aplikace)
            prichod_time = datetime.datetime.now().strftime("%H:%M")
            # Zkusit event log pro přesnější čas
            offline_dt = get_last_system_offline_time()
            if offline_dt:
                # Odhadnout příchod jako čas posledního zapnutí
                boot_str = offline_dt.strftime("%H:%M")
                p_min = cas_na_minuty(boot_str)
                if 300 <= p_min <= 720:  # 5:00–12:00 = rozumný příchod
                    prichod_time = boot_str
        except Exception:
            pass

        if prichod_time:
            self.db.insert(dnes_str, prichod_time, None, 1, tyden)
            self.after(500, lambda: self._toast(
                f"Auto-příchod zaznamenán: {prichod_time}", error=False
            ))

    # ═════════════════════════════════════════════════════════════════════════
    #  TRAY / CLOSE
    # ═════════════════════════════════════════════════════════════════════════

    def _apply_db_folder(self, folder):
        """Uloží novou složku DB do configu a restartuje aplikaci."""
        import shutil
        db_file = os.path.join(folder, "wageslave.db")
        # Sestav novou cestu
        config.DB_PATH_OVERRIDE = db_file
        config.save()
        # Informovat uživatele a restartovat
        if os.path.exists(db_file):
            msg = f"Nalezena existující databáze v:\n{db_file}\n\nAplikace se restartuje pro načtení nové databáze."
        else:
            msg = f"Databáze bude vytvořena v:\n{db_file}\n\nAplikace se restartuje."
        messagebox.showinfo("Změna databáze", msg, parent=self)
        self._restart()

    def _restart(self):
        """Restartuje aplikaci."""
        self.tray.stop()
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        self.destroy()

    def _run_backup_if_due(self):
        """Jednou měsíčně zazipuje DB a config do AppData/WageSlave/backup/."""
        if not config.AUTO_BACKUP:
            return
        import zipfile, calendar
        app_dir   = config.get_app_dir()
        backup_dir = os.path.join(app_dir, "backup")
        os.makedirs(backup_dir, exist_ok=True)

        # Zjistit, zda záloha pro tento měsíc už existuje
        now = datetime.datetime.now()
        stamp = now.strftime("%Y-%m")
        marker = os.path.join(backup_dir, f"backup_{stamp}.done")
        if os.path.exists(marker):
            return   # záloha pro tento měsíc hotova

        zip_path = os.path.join(backup_dir, f"wageslave_backup_{stamp}.zip")
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                db = config.get_db_path()
                if os.path.exists(db):
                    zf.write(db, "wageslave.db")
                cfg = config.get_config_path()
                if os.path.exists(cfg):
                    zf.write(cfg, "config.json")
            # Zapsat marker
            with open(marker, "w") as f:
                f.write(now.isoformat())
            self._toast(f"Záloha vytvořena: backup_{stamp}.zip")
        except Exception as e:
            self._toast(f"Záloha selhala: {e}", error=True)

    def zobraz_okno(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def ukoncit_aplikaci(self, icon=None, item=None):
        # Auto-odchod při ukončení
        open_rec = self.db.find_open_record()
        if open_rec:
            now_str = datetime.datetime.now().strftime("%H:%M")
            self.db.update_odchod(open_rec[0], now_str)
        self.tray.stop()
        self.after(0, self.destroy)

    def _on_close(self):
        # Minimize to tray instead of closing
        self.withdraw()
        self.tray.hide_window()

    # ═════════════════════════════════════════════════════════════════════════
    #  TICK (live refresh)
    # ═════════════════════════════════════════════════════════════════════════

    def _tick(self):
        self._refresh_dashboard()
        self.after(30_000, self._tick)

    # ═════════════════════════════════════════════════════════════════════════
    #  TOAST
    # ═════════════════════════════════════════════════════════════════════════

    def _toast(self, msg, error=False):
        if hasattr(self, "_toast_win") and self._toast_win.winfo_exists():
            self._toast_win.destroy()

        tw = tk.Toplevel(self)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.configure(bg=C["panel"])

        # Position bottom-right of main window
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() - 320
        y = self.winfo_y() + self.winfo_height() - 70
        tw.geometry(f"300x44+{x}+{y}")

        bar_color = C["red"] if error else C["green"]
        tk.Frame(tw, bg=bar_color, width=4).pack(side="left", fill="y")
        tk.Label(tw, text=msg, bg=C["panel"], fg=C["text"],
                 font=FONT_MONO_S, padx=12, pady=12).pack(side="left")

        self._toast_win = tw
        tw.after(2600, lambda: tw.destroy() if tw.winfo_exists() else None)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = WageSlaveApp()
    app.mainloop()
