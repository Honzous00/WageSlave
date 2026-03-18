# dochazka.pyw  –  Premium UI Reconstruction
# Framework: CustomTkinter  |  Theme: Dark "Zinc" Dashboard
# ─────────────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import csv
from datetime import datetime, timedelta
import psutil
import threading
from collections import defaultdict

import customtkinter as ctk
from customtkinter import (CTk, CTkFrame, CTkLabel, CTkEntry,
                            CTkButton, CTkCheckBox, CTkComboBox,
                            CTkProgressBar, CTkFont)

import config
from utils import formatuj_minuty, cas_na_minuty, normalizuj_cas, set_dark_title_bar
from database import DochazkaDB
import calculator

try:
    from tray import TrayIcon
    TRAY_DOSTUPNY = True
except ImportError:
    TRAY_DOSTUPNY = False

# ── Appearance ────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Color Palette  (zinc + slate) ─────────────────────────────
BG           = "#09090b"   # root background
SIDEBAR      = "#111113"   # sidebar
CARD         = "#18181b"   # card / panel
CARD_DEEP    = "#101012"   # deeper card accent
BORDER       = "#27272a"   # glass border
ACCENT       = "#3b82f6"   # primary blue
ACCENT_HOVER = "#2563eb"
TEXT         = "#e2e8f0"   # primary text
SUB          = "#64748b"   # muted labels
GREEN_BG     = "#14291d"
GREEN_FG     = "#4ade80"
RED_FG       = "#f87171"
DARK_HOVER   = "#1f1f23"

# Fonts are initialised inside PatecniVestec.__init__() after CTk() is created.
# Module-level tuple used only for ttk (which accepts plain tuples).
FONT_TABLE = ("Segoe UI Variable", 10)


# ══════════════════════════════════════════════════════════════
class PatecniVestec:
    def __init__(self, root: CTk):
        self.root = root
        self.root.title("Páteční Věštec")
        self.root.geometry("1000x650")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG)

        if sys.platform == "win32":
            set_dark_title_bar(root)

        # ── Fonts (must be created AFTER CTk root exists)
        global FONT_TITLE, FONT_HERO, FONT_HERO_SM, FONT_VALUE
        global FONT_LABEL, FONT_CAPTION, FONT_NAV, FONT_TAG
        FONT_TITLE   = CTkFont(family="Segoe UI Variable", size=28, weight="bold")
        FONT_HERO    = CTkFont(family="Segoe UI Variable", size=64, weight="bold")
        FONT_HERO_SM = CTkFont(family="Segoe UI Variable", size=20, weight="bold")
        FONT_VALUE   = CTkFont(family="Segoe UI Variable", size=22, weight="bold")
        FONT_LABEL   = CTkFont(family="Segoe UI Variable", size=11, weight="normal")
        FONT_CAPTION = CTkFont(family="Segoe UI Variable", size=10, weight="normal")
        FONT_NAV     = CTkFont(family="Segoe UI Variable", size=13, weight="normal")
        FONT_TAG     = CTkFont(family="Segoe UI Variable", size=10, weight="bold")

        self.db      = DochazkaDB()
        self.edit_id = None

        # Root grid: sidebar | main
        self.root.grid_columnconfigure(0, weight=0, minsize=210)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._build_ui()
        self.nacti_tydny_do_filtru()
        self.reset_form()
        self.obnovit_data()
        self.periodicka_aktualizace()
        self.root.after(2000, self.check_unfinished_shift)

        if TRAY_DOSTUPNY:
            self.tray = TrayIcon(self)
            self.tray.create()
            self.root.protocol("WM_DELETE_WINDOW", self.minimalizuj_do_tray)
        else:
            self.root.protocol("WM_DELETE_WINDOW", self.root.quit)

        self.root.after(1000, self.check_boot_time_and_record)

    # ─────────────────────────────────────────────────────────
    # TOP-LEVEL BUILD
    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        self.create_sidebar()
        self.create_main()

    # ─────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────
    def create_sidebar(self):
        self.sidebar = CTkFrame(
            self.root,
            width=210,
            fg_color=SIDEBAR,
            border_width=1,
            border_color=BORDER,
            corner_radius=16
        )
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(5, weight=1)   # spacer row

        # ── Logo / title
        logo_frame = CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(28, 32))

        CTkLabel(
            logo_frame, text="Páteční", font=FONT_TITLE,
            text_color=TEXT, justify="left", anchor="w"
        ).pack(fill="x")
        CTkLabel(
            logo_frame, text="Věštec",
            font=CTkFont(family="Segoe UI Variable", size=28, weight="normal"),
            text_color=ACCENT, justify="left", anchor="w"
        ).pack(fill="x")

        # thin divider
        CTkFrame(self.sidebar, fg_color=BORDER, height=1, corner_radius=0
                 ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        # ── Nav section label
        CTkLabel(
            self.sidebar, text="PŘEHLED",
            font=FONT_CAPTION, text_color=SUB, anchor="w"
        ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 6))

        # ── Nav buttons
        nav_frame = CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=0)

        self._nav_btn(nav_frame, "⬛  Dashboard",  active=True)
        self._nav_btn(nav_frame, "📋  Historie",   active=False)
        self._nav_btn(nav_frame, "⚙️  Nastavení",  active=False)

        # spacer
        CTkFrame(self.sidebar, fg_color="transparent").grid(row=5, column=0, sticky="nsew")

        # ── Bottom buttons
        CTkFrame(self.sidebar, fg_color=BORDER, height=1, corner_radius=0
                 ).grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 8))

        bottom = CTkFrame(self.sidebar, fg_color="transparent")
        bottom.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 16))

        self._nav_btn(bottom, "↑  Export",  cmd=self.export_s_vyberem_mesicu)
        self._nav_btn(bottom, "↻  Obnovit", cmd=self.obnovit_data)

    def _nav_btn(self, parent, text, active=False, cmd=None):
        btn = CTkButton(
            parent, text=text,
            font=FONT_NAV,
            anchor="w",
            fg_color=ACCENT if active else "transparent",
            text_color=TEXT if active else SUB,
            hover_color=ACCENT_HOVER if active else DARK_HOVER,
            height=36, corner_radius=8,
            command=cmd if cmd else lambda: None
        )
        btn.pack(fill="x", pady=2, padx=0)
        return btn

    # ─────────────────────────────────────────────────────────
    # MAIN AREA
    # ─────────────────────────────────────────────────────────
    def create_main(self):
        self.main = CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.main.grid_rowconfigure(2, weight=1)   # history expands
        self.main.grid_columnconfigure(0, weight=1)

        self.create_topbar()
        self.create_hero_row()
        self.create_content_row()

    # ── Top bar (date + status dot)
    def create_topbar(self):
        bar = CTkFrame(self.main, fg_color="transparent", height=36)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.lbl_date = CTkLabel(
            bar, text=datetime.now().strftime("%A, %-d. %B %Y")
                       if sys.platform != "win32"
                       else datetime.now().strftime("%A, %d. %B %Y"),
            font=FONT_LABEL, text_color=SUB
        )
        self.lbl_date.pack(side="left")

        # live "●" dot
        self.lbl_live = CTkLabel(
            bar, text="● LIVE",
            font=CTkFont(family="Segoe UI Variable", size=10, weight="bold"),
            text_color=GREEN_FG
        )
        self.lbl_live.pack(side="right")

    # ── Hero row: big clock + 3 stat cards
    def create_hero_row(self):
        row = CTkFrame(self.main, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        row.grid_columnconfigure(0, weight=0)   # hero card – fixed
        row.grid_columnconfigure(1, weight=1)   # stats – expand

        # ── Hero card
        self.hero_card = CTkFrame(
            row, fg_color=CARD,
            border_width=1, border_color=BORDER,
            corner_radius=16
        )
        self.hero_card.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        # tiny label above the big time
        CTkLabel(
            self.hero_card, text="ODCHOD V PÁTEK",
            font=FONT_CAPTION, text_color=SUB
        ).pack(padx=28, pady=(20, 0), anchor="w")

        self.hero_label = CTkLabel(
            self.hero_card, text="--:--",
            font=FONT_HERO, text_color=TEXT
        )
        self.hero_label.pack(padx=28, pady=(0, 4))

        # progress bar inside hero
        self.progress = CTkProgressBar(
            self.hero_card,
            height=4, corner_radius=2,
            fg_color=BORDER, progress_color=ACCENT
        )
        self.progress.pack(fill="x", padx=28, pady=(0, 4))
        self.progress.set(0)

        self.lbl_percent = CTkLabel(
            self.hero_card, text="0 %",
            font=CTkFont(family="Segoe UI Variable", size=11, weight="bold"),
            text_color=ACCENT
        )
        self.lbl_percent.pack(padx=28, pady=(0, 20), anchor="e")

        # ── 3 stat cards (right of hero)
        stats_grid = CTkFrame(row, fg_color="transparent")
        stats_grid.grid(row=0, column=1, sticky="nsew")
        for i in range(3):
            stats_grid.grid_columnconfigure(i, weight=1, uniform="sc")
        stats_grid.grid_rowconfigure(0, weight=1)

        self._stat_card(stats_grid, "ODPRACOVÁNO", "--", 0, icon="⏱")
        self._stat_card(stats_grid, "ZBÝVÁ",       "--", 1, icon="⏳")
        self._stat_card(stats_grid, "BILANCE",     "--", 2, icon="⚖")

    def _stat_card(self, parent, label, value, col, icon=""):
        card = CTkFrame(
            parent, fg_color=CARD,
            border_width=1, border_color=BORDER,
            corner_radius=16
        )
        card.grid(row=0, column=col, sticky="nsew", padx=5, pady=0)
        card.grid_rowconfigure(0, weight=1)

        inner = CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=22, pady=22)

        # icon + label row
        top = CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        CTkLabel(top, text=icon, font=FONT_LABEL, text_color=SUB).pack(side="left")
        CTkLabel(top, text=f"  {label}", font=FONT_CAPTION, text_color=SUB).pack(side="left")

        val_lbl = CTkLabel(
            inner, text=value,
            font=FONT_VALUE, text_color=TEXT, anchor="w"
        )
        val_lbl.pack(fill="x", pady=(8, 0))

        # store ref by label key (normalised)
        key = label.lower().replace(" ", "_")
        setattr(self, f"stat_{key}_value", val_lbl)
        return card

    # ── Content row: form card  |  history card
    def create_content_row(self):
        row = CTkFrame(self.main, fg_color="transparent")
        row.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        row.grid_columnconfigure(0, weight=1)
        row.grid_rowconfigure(0, weight=0)
        row.grid_rowconfigure(1, weight=1)

        self.create_form_card(row)
        self.create_history_card(row)

    # ─────────────────────────────────────────────────────────
    # FORM CARD
    # ─────────────────────────────────────────────────────────
    def create_form_card(self, parent):
        card = CTkFrame(
            parent, fg_color=CARD,
            border_width=1, border_color=BORDER,
            corner_radius=16
        )
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # header row
        hdr = CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=22, pady=(16, 12))

        CTkLabel(
            hdr, text="EDITACE DNE",
            font=CTkFont(family="Segoe UI Variable", size=11, weight="bold"),
            text_color=ACCENT
        ).pack(side="left")

        self.btn_ulozit = CTkButton(
            hdr, text="ULOŽIT ZÁZNAM",
            font=CTkFont(family="Segoe UI Variable", size=11, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            height=30, corner_radius=8,
            command=self.ulozit
        )
        self.btn_ulozit.pack(side="right")

        # input row
        inputs = CTkFrame(card, fg_color="transparent")
        inputs.pack(fill="x", padx=22, pady=(0, 16))

        # Datum
        self.ent_datum = self._field_group(inputs, "DATUM", 110)

        # Příchod + TEĎ
        prichod_wrap = CTkFrame(inputs, fg_color="transparent")
        prichod_wrap.pack(side="left", padx=(0, 20))
        CTkLabel(prichod_wrap, text="PŘÍCHOD", font=FONT_CAPTION,
                 text_color=SUB).pack(anchor="w")
        prichod_row = CTkFrame(prichod_wrap, fg_color="transparent")
        prichod_row.pack()
        self.ent_prichod = CTkEntry(
            prichod_row, width=78, height=32,
            fg_color=CARD_DEEP, border_width=1, border_color=BORDER,
            text_color=TEXT, corner_radius=8
        )
        self.ent_prichod.pack(side="left")
        self.ent_prichod.bind("<FocusOut>", lambda e: normalizuj_cas(self.ent_prichod))
        self._ted_btn(prichod_row, self.ent_prichod)

        # Odchod + TEĎ
        odchod_wrap = CTkFrame(inputs, fg_color="transparent")
        odchod_wrap.pack(side="left", padx=(0, 20))
        CTkLabel(odchod_wrap, text="ODCHOD", font=FONT_CAPTION,
                 text_color=SUB).pack(anchor="w")
        odchod_row = CTkFrame(odchod_wrap, fg_color="transparent")
        odchod_row.pack()
        self.ent_odchod = CTkEntry(
            odchod_row, width=78, height=32,
            fg_color=CARD_DEEP, border_width=1, border_color=BORDER,
            text_color=TEXT, corner_radius=8
        )
        self.ent_odchod.pack(side="left")
        self.ent_odchod.bind("<FocusOut>", lambda e: normalizuj_cas(self.ent_odchod))
        self._ted_btn(odchod_row, self.ent_odchod)

        # Oběd checkbox
        self.var_obed = tk.BooleanVar(value=True)
        self.obed_check = CTkCheckBox(
            inputs, text="Oběd",
            variable=self.var_obed,
            font=FONT_LABEL, text_color=SUB,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=BORDER, checkmark_color=TEXT
        )
        self.obed_check.pack(side="left", pady=(14, 0))

    def _field_group(self, parent, label, width):
        wrap = CTkFrame(parent, fg_color="transparent")
        wrap.pack(side="left", padx=(0, 20))
        CTkLabel(wrap, text=label, font=FONT_CAPTION, text_color=SUB).pack(anchor="w")
        ent = CTkEntry(
            wrap, width=width, height=32,
            fg_color=CARD_DEEP, border_width=1, border_color=BORDER,
            text_color=TEXT, corner_radius=8
        )
        ent.pack()
        return ent

    def _ted_btn(self, parent, target):
        CTkButton(
            parent, text="NOW",
            width=36, height=32,
            font=CTkFont(family="Segoe UI Variable", size=9, weight="bold"),
            fg_color="#1c1c21", hover_color=DARK_HOVER,
            text_color=SUB, corner_radius=6,
            command=lambda: self.nastav_cas(target)
        ).pack(side="left", padx=(4, 0))

    # ─────────────────────────────────────────────────────────
    # HISTORY CARD  (table)
    # ─────────────────────────────────────────────────────────
    def create_history_card(self, parent):
        card = CTkFrame(
            parent, fg_color=CARD,
            border_width=1, border_color=BORDER,
            corner_radius=16
        )
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        # ── card header
        hdr = CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 10))

        CTkLabel(
            hdr, text="ZÁZNAMY",
            font=CTkFont(family="Segoe UI Variable", size=11, weight="bold"),
            text_color=ACCENT
        ).pack(side="left")

        # right-side controls
        ctrl = CTkFrame(hdr, fg_color="transparent")
        ctrl.pack(side="right")

        CTkLabel(ctrl, text="Týden", font=FONT_CAPTION, text_color=SUB
                 ).pack(side="left", padx=(0, 6))

        self.combo_tyden = CTkComboBox(
            ctrl,
            values=["Aktuální týden", "Všechny záznamy"],
            width=154, height=28,
            font=FONT_LABEL,
            fg_color=CARD_DEEP, border_color=BORDER,
            button_color=CARD_DEEP, button_hover_color=DARK_HOVER,
            dropdown_fg_color=CARD_DEEP, dropdown_hover_color=DARK_HOVER,
            text_color=TEXT
        )
        self.combo_tyden.pack(side="left")
        self.combo_tyden.set("Aktuální týden")
        self.combo_tyden.bind("<<ComboboxSelected>>", lambda e: self.obnovit_data())

        CTkButton(
            ctrl, text="SMAZAT",
            font=CTkFont(family="Segoe UI Variable", size=10, weight="bold"),
            width=72, height=28,
            fg_color="transparent", text_color=RED_FG,
            hover_color="#2a1515", corner_radius=6,
            command=self.smazat
        ).pack(side="left", padx=(10, 0))

        # ── Treeview
        tree_wrap = CTkFrame(card, fg_color="transparent")
        tree_wrap.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("PV.Treeview",
            background=CARD, fieldbackground=CARD,
            foreground=TEXT, rowheight=38,
            borderwidth=0, font=FONT_TABLE
        )
        style.configure("PV.Treeview.Heading",
            background="#1c1c21", foreground=SUB,
            font=("Segoe UI Variable", 9, "bold"),
            borderwidth=0, relief="flat", padding=(0, 6)
        )
        style.map("PV.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#ffffff")]
        )
        style.layout("PV.Treeview", [
            ("PV.Treeview.treearea", {"sticky": "nsew"})
        ])

        columns = ("ID", "Týden", "Datum", "Příchod", "Odchod", "Čistý čas")
        self.tree = ttk.Treeview(
            tree_wrap, columns=columns, show="headings",
            style="PV.Treeview", height=7
        )

        col_w = {"ID": 0, "Týden": 52, "Datum": 96, "Příchod": 72,
                 "Odchod": 110, "Čistý čas": 90}
        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=col_w[col], anchor="center",
                             minwidth=col_w[col])

        self.tree.column("ID", stretch=False)

        self.tree.tag_configure("odd",     background=CARD)
        self.tree.tag_configure("even",    background="#141417")
        self.tree.tag_configure("working", background=GREEN_BG,
                                foreground=GREEN_FG,
                                font=("Segoe UI Variable", 10, "bold"))

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>",          self.nacist_do_editace)
        self.tree.bind("<ButtonRelease-1>", self.zrusit_vyber_pri_kliknuti_mimo)

    # ═════════════════════════════════════════════════════════
    # BUSINESS LOGIC  (unchanged from original)
    # ═════════════════════════════════════════════════════════

    def minimalizuj_do_tray(self):
        self.root.withdraw()
        if TRAY_DOSTUPNY:
            self.tray.hide_window()

    def zobraz_okno(self):
        self.root.deiconify()
        if TRAY_DOSTUPNY:
            self.tray.show_window()

    def ukoncit_aplikaci(self):
        if TRAY_DOSTUPNY:
            self.tray.stop()
        self.root.quit()
        sys.exit(0)

    def nacti_tydny_do_filtru(self):
        tydny = self.db.fetch_distinct_weeks()
        self.combo_tyden.configure(
            values=["Aktuální týden", "Všechny záznamy"] + [str(t) for t in tydny]
        )

    def reset_form(self):
        self.edit_id = None
        self.ent_datum.delete(0, tk.END)
        self.ent_datum.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.ent_prichod.delete(0, tk.END)
        self.ent_odchod.delete(0, tk.END)
        self.btn_ulozit.configure(text="ULOŽIT ZÁZNAM")

    def nastav_cas(self, entry_field):
        entry_field.delete(0, tk.END)
        entry_field.insert(0, datetime.now().strftime("%H:%M"))

    def ulozit(self):
        d = self.ent_datum.get()
        p = self.ent_prichod.get()
        o = self.ent_odchod.get() or None
        obed = 1 if self.var_obed.get() else 0
        try:
            dt_obj = datetime.strptime(d, "%Y-%m-%d")
            tyden  = dt_obj.isocalendar()[1]
            if self.edit_id:
                self.db.update(self.edit_id, d, p, o, obed, tyden)
            else:
                self.db.insert(d, p, o, obed, tyden)
            self.nacti_tydny_do_filtru()
            self.reset_form()
            self.obnovit_data()
        except Exception:
            messagebox.showerror("Chyba", "Špatný formát času nebo data!")

    def smazat(self):
        sel = self.tree.selection()
        if not sel:
            return
        id_db = self.tree.item(sel[0])["values"][0]
        self.db.delete(id_db)
        self.obnovit_data()

    def nacist_do_editace(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item   = self.tree.item(sel[0])["values"]
        self.edit_id = item[0]
        zaznam = self.db.fetch_by_id(self.edit_id)
        if zaznam:
            self.ent_datum.delete(0, tk.END);  self.ent_datum.insert(0,  zaznam[2])
            self.ent_prichod.delete(0, tk.END);self.ent_prichod.insert(0, zaznam[3])
            self.ent_odchod.delete(0, tk.END)
            if zaznam[4]:
                self.ent_odchod.insert(0, zaznam[4])
            self.var_obed.set(bool(zaznam[6]))
            self.btn_ulozit.configure(text="AKTUALIZOVAT")

    def zrusit_vyber_pri_kliknuti_mimo(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "nothing":
            self.tree.selection_remove(self.tree.selection())
            self.reset_form()

    def periodicka_aktualizace(self):
        self.obnovit_data()
        self.root.after(60000, self.periodicka_aktualizace)

    def obnovit_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        filtr = self.combo_tyden.get()
        dnes  = datetime.now().date()

        if filtr == "Aktuální týden":
            hledany_tyden = dnes.isocalendar()[1]
            rows          = self.db.fetch_by_week(hledany_tyden)
            vsechny_tyden = rows
        elif filtr == "Všechny záznamy":
            rows          = self.db.fetch_all()
            vsechny_tyden = []
        else:
            hledany_tyden = int(filtr)
            rows          = self.db.fetch_by_week(hledany_tyden)
            vsechny_tyden = rows

        for idx, r in enumerate(rows):
            vals = list(r)
            tag  = "even" if idx % 2 == 0 else "odd"
            if not r[4]:
                vals[4] = "V PRÁCI"
                vals[5] = "--"
                tag     = "working"
            else:
                vals[5] = formatuj_minuty(r[5])
            self.tree.insert("", tk.END, values=vals, tags=(tag,))

        if filtr == "Aktuální týden" and vsechny_tyden:
            wd = calculator.week_analysis(vsechny_tyden, dnes)
            self.hero_label.configure(text=wd["cas_patek"])
            self.progress.set(wd["procenta"] / 100)
            self.lbl_percent.configure(text=f"{wd['procenta']} %")
            self.stat_odpracováno_value.configure(text=formatuj_minuty(wd["skutecne_celkem"]))
            self.stat_zbývá_value.configure(text=formatuj_minuty(wd["zbyva"]))

            mesic_str  = dnes.strftime("%Y-%m")
            mesic_data = self.db.fetch_by_month(mesic_str)
            balance    = calculator.month_balance(mesic_data, dnes)
            sign       = "+" if balance >= 0 else ""
            self.stat_bilance_value.configure(
                text=f"{sign}{formatuj_minuty(abs(balance))}",
                text_color=GREEN_FG if balance >= 0 else RED_FG
            )
        else:
            self.hero_label.configure(text="--:--")
            self.progress.set(0)
            self.lbl_percent.configure(text="0 %")
            self.stat_odpracováno_value.configure(text="--")
            self.stat_zbývá_value.configure(text="--")
            self.stat_bilance_value.configure(text="--", text_color=TEXT)

    def check_boot_time_and_record(self):
        try:
            boot_dt = datetime.fromtimestamp(psutil.boot_time())
            dnes, cas = boot_dt.strftime("%Y-%m-%d"), boot_dt.strftime("%H:%M")
            with self.db._connect() as conn:
                exists = conn.execute(
                    "SELECT id FROM dochazka WHERE datum=?", (dnes,)
                ).fetchone()
            if not exists:
                self.ent_datum.delete(0, tk.END);  self.ent_datum.insert(0, dnes)
                self.ent_prichod.delete(0, tk.END);self.ent_prichod.insert(0, cas)
                self.ulozit()
                messagebox.showinfo("Auto-zápis", f"Start PC detekován v {cas}")
            else:
                self.obnovit_data()
        except Exception:
            pass

    def export_s_vyberem_mesicu(self):
        rows = self.db.fetch_months_for_export()
        if not rows:
            messagebox.showinfo("Info", "Databáze neobsahuje žádné záznamy.")
            return

        data = {}
        for rok, mesic in rows:
            data.setdefault(rok, []).append(mesic)

        nazvy = ["Leden","Únor","Březen","Duben","Květen","Červen",
                 "Červenec","Srpen","Září","Říjen","Listopad","Prosinec"]

        top = ctk.CTkToplevel(self.root)
        top.title("Export měsíců")
        top.geometry("340x460")
        top.resizable(False, False)
        if sys.platform == "win32":
            set_dark_title_bar(top)

        mf = CTkFrame(top, fg_color=BG, corner_radius=0)
        mf.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(mf, bg=BG, highlightthickness=0)
        sb     = tk.Scrollbar(mf, orient="vertical", command=canvas.yview)
        sf     = tk.Frame(canvas, bg=BG)
        sf.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.export_vars = {}
        for rok, mesice in data.items():
            CTkLabel(sf, text=rok, font=FONT_VALUE,
                     text_color=ACCENT, anchor="w"
                     ).pack(fill="x", pady=(10, 2))
            for m in mesice:
                mframe = tk.Frame(sf, bg=BG)
                mframe.pack(fill="x", padx=20)
                var = tk.BooleanVar()
                self.export_vars[(rok, m)] = var
                tk.Checkbutton(
                    mframe, text=nazvy[int(m)-1], variable=var,
                    bg=BG, fg=TEXT, selectcolor=BG, font=FONT_TABLE, anchor="w"
                ).pack(side="left")

        bf = tk.Frame(mf, bg=BG)
        bf.pack(fill="x", pady=(10, 0))

        def select_all():
            for v in self.export_vars.values():
                v.set(True)

        def do_export():
            chosen = [f"{r}-{m}" for (r, m), v in self.export_vars.items() if v.get()]
            if not chosen:
                messagebox.showwarning("Varování", "Není vybrán žádný měsíc.")
                return
            self.proved_export(chosen)
            top.destroy()

        for txt, cmd in [("Vybrat vše", select_all),
                          ("Exportovat", do_export),
                          ("Storno",     top.destroy)]:
            CTkButton(bf, text=txt, command=cmd,
                      fg_color=ACCENT if txt == "Exportovat" else "transparent",
                      hover_color=ACCENT_HOVER if txt == "Exportovat" else DARK_HOVER
                      ).pack(side="left", padx=5)

    def proved_export(self, mesice):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Uložit CSV jako"
        )
        if not path:
            return
        try:
            data = self.db.fetch_for_export(mesice)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Datum", "Příchod", "Odchod"])
                w.writerows(data)
            messagebox.showinfo("Hotovo", f"Export {len(data)} záznamů proběhl úspěšně!")
        except Exception as e:
            messagebox.showerror("Chyba", str(e))

    def check_unfinished_shift(self):
        try:
            from eventlog import get_last_system_offline_time
        except ImportError:
            return

        open_rec = self.db.find_open_record()
        if not open_rec:
            return
        rec_id, datum, prichod, obed = open_rec
        if not prichod:
            return
        offline_dt = get_last_system_offline_time()
        if not offline_dt:
            return
        try:
            prichod_dt = datetime.strptime(f"{datum} {prichod}", "%Y-%m-%d %H:%M")
        except Exception:
            return

        now = datetime.now()
        if prichod_dt < offline_dt <= now:
            offline_str = offline_dt.strftime("%H:%M")
            self.db.update_odchod(rec_id, offline_str)
            self.obnovit_data()
            messagebox.showinfo(
                "Automatické doplnění",
                f"Poslední směna nebyla ukončena.\n"
                f"Čas odchodu doplněn ze systému: {offline_str}"
            )


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        root = ctk.CTk()
        app  = PatecniVestec(root)
        root.mainloop()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Stiskni Enter pro ukončení…")
