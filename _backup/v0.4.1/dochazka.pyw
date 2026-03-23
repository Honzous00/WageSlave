import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import sys
import csv
from datetime import datetime, timedelta
import psutil
import ctypes
from ctypes import wintypes

# --- KONFIGURACE ---
TYDENNI_FOND_HODIN = 40
OBED_MINUT = 30
STANDARDNI_PRICHOD = "07:00"
STANDARDNI_ODCHOD = "15:30"

def get_db_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'dochazka.db')

def formatuj_minuty(celkem_minut):
    h = celkem_minut // 60
    m = celkem_minut % 60
    return f"{h}h {m:02d}m"

def cas_na_minuty(cas_str):
    """Převede čas HH:MM na minuty od půlnoci"""
    if not cas_str:
        return 0
    try:
        t = datetime.strptime(cas_str, "%H:%M")
        return t.hour * 60 + t.minute
    except:
        return 0

def set_dark_title_bar(window):
    """Nastaví tmavé záhlaví okna na Windows 10/11"""
    try:
        window.update()
        HWND = wintypes.HWND(int(window.frame(), 16))
        dwmapi = ctypes.WinDLL('dwmapi')
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        use_dark_mode = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(HWND, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                     ctypes.byref(use_dark_mode), ctypes.sizeof(use_dark_mode))
    except Exception:
        pass

class PatecniVestec:
    def __init__(self, root):
        self.root = root
        self.root.title("Páteční Věštec 2.0")
        self.root.geometry("680x940")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")
        
        # Nastavíme tmavý title bar (pouze Windows)
        if sys.platform == "win32":
            set_dark_title_bar(root)
        
        self.db_path = get_db_path()
        self.edit_id = None
        self.setup_db()
        self.apply_styles()
        
        # Hlavní kontejner s paddingem
        self.main_container = tk.Frame(root, bg="#1a1a1a", padx=20, pady=20)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.create_widgets()
        
        self.nacti_tydny_do_filtru()
        self.reset_form()
        self.obnovit_data()
        
        # Start automatiky
        self.root.after(1000, self.check_boot_time_and_record)

    def apply_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Barvy
        bg_dark = "#1a1a1a"
        bg_medium = "#2d2d2d"
        bg_light = "#3c3c3c"
        fg = "#ffffff"
        accent = "#0078d4"
        accent_light = "#2b88d8"

        # Font
        default_font = ('Segoe UI', 10)

        # Obecné styly
        style.configure("TFrame", background=bg_dark)
        style.configure("TLabelframe", background=bg_dark, foreground=fg, bordercolor=bg_light)
        style.configure("TLabelframe.Label", background=bg_dark, foreground=accent, font=('Segoe UI', 11, 'bold'))
        
        style.configure("TLabel", background=bg_dark, foreground=fg, font=default_font)
        style.configure("TButton", font=('Segoe UI', 10, 'bold'), borderwidth=0, padding=6)
        style.map("TButton",
                  background=[('active', accent_light), ('!active', accent)],
                  foreground=[('active', fg), ('!active', fg)])
        
        style.configure("TEntry", fieldbackground=bg_medium, foreground=fg, bordercolor=bg_light, padding=5, font=default_font)
        style.configure("TCheckbutton", background=bg_dark, foreground=fg, font=default_font)
        style.map("TCheckbutton", background=[('active', bg_medium)])
        
        # Treeview
        style.configure("Treeview", background=bg_medium, fieldbackground=bg_medium, foreground=fg,
                        rowheight=34, borderwidth=0, font=default_font)
        style.configure("Treeview.Heading", background=bg_light, foreground=fg,
                        font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map("Treeview", background=[('selected', accent)])
        
        # Progress bar
        style.configure("Accent.Horizontal.TProgressbar", background=accent, troughcolor=bg_medium, borderwidth=0, thickness=12)
        
        # Kombobox
        style.configure("TCombobox", fieldbackground=bg_medium, foreground=fg, bordercolor=bg_light, font=default_font)
        style.map("TCombobox", fieldbackground=[('readonly', bg_medium)])

        # Malá tlačítka v headeru
        style.configure("Header.TButton", font=('Segoe UI', 9), padding=4)

    def create_widgets(self):
        # --- HEADER s tlačítky vpravo ---
        header_frame = tk.Frame(self.main_container, bg="#1a1a1a")
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title = tk.Label(header_frame, text="PÁTEČNÍ VĚŠTEC 2.0",
                         font=('Segoe UI Black', 24), bg="#1a1a1a", fg="#0078d4")
        title.pack(side=tk.LEFT)
        
        right_buttons = tk.Frame(header_frame, bg="#1a1a1a")
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="SYNC PC", style="Header.TButton",
                  command=self.check_boot_time_and_record).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_buttons, text="EXPORT CSV", style="Header.TButton",
                  command=self.export_pro_excel).pack(side=tk.LEFT, padx=2)

        # --- ANALÝZA (horní karta) ---
        analysis_frame = ttk.LabelFrame(self.main_container, text=" ANALÝZA TÝDNE ", padding=15)
        analysis_frame.pack(fill=tk.X, pady=5)

        progress_row = tk.Frame(analysis_frame, bg="#2d2d2d")
        progress_row.pack(fill=tk.X, pady=(0, 10))

        self.lbl_stats = tk.Label(progress_row, text="Odpracováno: 0h 00m", font=('Segoe UI', 11),
                                  bg="#2d2d2d", fg="white")
        self.lbl_stats.pack(side=tk.LEFT, padx=(0, 15))

        self.progress = ttk.Progressbar(progress_row, style="Accent.Horizontal.TProgressbar",
                                        orient='horizontal', length=200, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=5)

        self.lbl_percent = tk.Label(progress_row, text="0%", font=('Segoe UI', 10, 'bold'),
                                    bg="#2d2d2d", fg="#0078d4", width=5)
        self.lbl_percent.pack(side=tk.LEFT)

        remaining_row = tk.Frame(analysis_frame, bg="#2d2d2d")
        remaining_row.pack(fill=tk.X, pady=(0, 10))
        
        self.lbl_remaining = tk.Label(remaining_row, text="Zbývá: 40h 00m", font=('Segoe UI', 11),
                                      bg="#2d2d2d", fg="#ffc107")
        self.lbl_remaining.pack()

        estimate_frame = tk.Frame(analysis_frame, bg="#2d2d2d")
        estimate_frame.pack(fill=tk.X, pady=5)

        tk.Label(estimate_frame, text="Odhad odchodu v pátek:", font=('Segoe UI', 12),
                 bg="#2d2d2d", fg="#aaa").pack()

        self.lbl_patek = tk.Label(estimate_frame, text="--:--",
                                   font=('Segoe UI', 26, 'bold'), bg="#2d2d2d", fg="#0078d4")
        self.lbl_patek.pack()

        # --- NOVÁ SEKCE ZÁZNAM (Horizontální Layout) ---
        entry_card = ttk.LabelFrame(self.main_container, text=" EDITACE DNE ", padding=15)
        entry_card.pack(fill=tk.X, pady=10)

        # Hlavní kontejner pro vstupy (aby byly vedle sebe)
        input_row = tk.Frame(entry_card, bg="#2d2d2d")
        input_row.pack(fill=tk.X)

        # 1. DATUM
        date_group = tk.Frame(input_row, bg="#2d2d2d")
        date_group.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(date_group, text="DATUM", font=('Segoe UI', 7, 'bold'), bg="#2d2d2d", fg="#888").pack(anchor="w")
        self.ent_datum = ttk.Entry(date_group, width=12)
        self.ent_datum.pack(pady=(2, 0))

        # 2. PŘÍCHOD + TEĎ
        in_group = tk.Frame(input_row, bg="#2d2d2d")
        in_group.pack(side=tk.LEFT, padx=10)
        tk.Label(in_group, text="PŘÍCHOD", font=('Segoe UI', 7, 'bold'), bg="#2d2d2d", fg="#888").pack(anchor="w")
        in_ctrls = tk.Frame(in_group, bg="#2d2d2d")
        in_ctrls.pack(pady=(2, 0))
        self.ent_prichod = ttk.Entry(in_ctrls, width=7)
        self.ent_prichod.pack(side=tk.LEFT)
        ttk.Button(in_ctrls, text="TEĎ", width=4, style="Header.TButton",
                   command=lambda: self.nastav_cas(self.ent_prichod)).pack(side=tk.LEFT, padx=4)

        # 3. ODCHOD + TEĎ
        out_group = tk.Frame(input_row, bg="#2d2d2d")
        out_group.pack(side=tk.LEFT, padx=10)
        tk.Label(out_group, text="ODCHOD", font=('Segoe UI', 7, 'bold'), bg="#2d2d2d", fg="#888").pack(anchor="w")
        out_ctrls = tk.Frame(out_group, bg="#2d2d2d")
        out_ctrls.pack(pady=(2, 0))
        self.ent_odchod = ttk.Entry(out_ctrls, width=7)
        self.ent_odchod.pack(side=tk.LEFT)
        ttk.Button(out_ctrls, text="TEĎ", width=4, style="Header.TButton",
                   command=lambda: self.nastav_cas(self.ent_odchod)).pack(side=tk.LEFT, padx=4)

        # 4. OBĚD + TLAČÍTKO ULOŽIT (vpravo)
        action_group = tk.Frame(input_row, bg="#2d2d2d")
        action_group.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Odsazení, aby tlačítko sedělo na lince s poli
        tk.Label(action_group, text="", font=('Segoe UI', 7), bg="#2d2d2d").pack() 
        
        btn_container = tk.Frame(action_group, bg="#2d2d2d")
        btn_container.pack(pady=(2, 0))
        
        self.var_obed = tk.BooleanVar(value=True)
        ttk.Checkbutton(btn_container, text="Oběd", variable=self.var_obed).pack(side=tk.LEFT, padx=10)
        
        self.btn_ulozit = ttk.Button(btn_container, text="ULOŽIT DATA", width=15, command=self.ulozit)
        self.btn_ulozit.pack(side=tk.LEFT)

        # --- HISTORIE ---
        history_frame = ttk.LabelFrame(self.main_container, text=" HISTORIE ", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        filter_toolbar = tk.Frame(history_frame, bg="#2d2d2d")
        filter_toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(filter_toolbar, text="Týden:", background="#2d2d2d").pack(side=tk.LEFT, padx=5)
        self.combo_tyden = ttk.Combobox(filter_toolbar, state="readonly", width=20)
        self.combo_tyden.pack(side=tk.LEFT, padx=5)
        self.combo_tyden.bind("<<ComboboxSelected>>", lambda e: self.obnovit_data())

        ttk.Button(filter_toolbar, text="SMAZAT VYBRANÝ", 
                  command=self.smazat).pack(side=tk.RIGHT, padx=5)

        tree_frame = tk.Frame(history_frame, bg="#2d2d2d")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("ID", "Týden", "Datum", "Příchod", "Odchod", "Čistý čas")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)

        widths = {"ID": 30, "Týden": 50, "Datum": 90, "Příchod": 70, "Odchod": 100, "Čistý čas": 90}
        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=widths[col], anchor=tk.CENTER)

        self.tree.tag_configure('odd', background='#2d2d2d')
        self.tree.tag_configure('even', background='#353535')
        self.tree.tag_configure('working', foreground='#ffa500', font=('Segoe UI', 9, 'italic'))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.nacist_do_editace)

    # --- LOGIKA (beze změn) ---
    def setup_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS dochazka 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, tyden INTEGER, datum TEXT, prichod TEXT, odchod TEXT, minut INTEGER)''')
        conn.commit()
        conn.close()

    def check_boot_time_and_record(self):
        try:
            boot_dt = datetime.fromtimestamp(psutil.boot_time())
            dnes, cas = boot_dt.strftime("%Y-%m-%d"), boot_dt.strftime("%H:%M")
            conn = sqlite3.connect(self.db_path)
            check = conn.execute("SELECT id FROM dochazka WHERE datum=?", (dnes,)).fetchone()
            conn.close()
            if not check:
                self.ent_datum.delete(0, tk.END)
                self.ent_datum.insert(0, dnes)
                self.ent_prichod.delete(0, tk.END)
                self.ent_prichod.insert(0, cas)
                self.ulozit()
                messagebox.showinfo("Auto-zápis", f"Start PC detekován v {cas}")
            else:
                self.obnovit_data()
        except Exception:
            pass

    def nacti_tydny_do_filtru(self):
        conn = sqlite3.connect(self.db_path)
        tydny = conn.execute("SELECT DISTINCT tyden FROM dochazka ORDER BY tyden DESC").fetchall()
        conn.close()
        self.combo_tyden['values'] = ["Aktuální týden", "Všechny záznamy"] + [str(t[0]) for t in tydny]
        self.combo_tyden.set("Aktuální týden")

    def reset_form(self):
        self.edit_id = None
        self.ent_datum.delete(0, tk.END)
        self.ent_datum.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.ent_prichod.delete(0, tk.END)
        self.ent_odchod.delete(0, tk.END)
        self.btn_ulozit.config(text="ULOŽIT ZÁZNAM")

    def nastav_cas(self, entry_field):
        entry_field.delete(0, tk.END)
        entry_field.insert(0, datetime.now().strftime("%H:%M"))

    def ulozit(self):
        d, p, o = self.ent_datum.get(), self.ent_prichod.get(), self.ent_odchod.get()
        if not p:
            return
        try:
            dt_obj = datetime.strptime(d, "%Y-%m-%d")
            tyden = dt_obj.isocalendar()[1]
            minut = 0
            if o:
                t1 = datetime.strptime(p, "%H:%M")
                t2 = datetime.strptime(o, "%H:%M")
                minut = int((t2 - t1).total_seconds() / 60) - (OBED_MINUT if self.var_obed.get() else 0)
            conn = sqlite3.connect(self.db_path)
            if self.edit_id:
                conn.execute("UPDATE dochazka SET tyden=?, datum=?, prichod=?, odchod=?, minut=? WHERE id=?",
                             (tyden, d, p, o, max(0, minut), self.edit_id))
            else:
                conn.execute("INSERT INTO dochazka (tyden, datum, prichod, odchod, minut) VALUES (?, ?, ?, ?, ?)",
                             (tyden, d, p, o, max(0, minut)))
            conn.commit()
            conn.close()
            self.nacti_tydny_do_filtru()
            self.reset_form()
            self.obnovit_data()
        except Exception:
            messagebox.showerror("Chyba", "Špatný formát času nebo data!")

    def smazat(self):
        sel = self.tree.selection()
        if not sel:
            return
        id_db = self.tree.item(sel[0])['values'][0]
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM dochazka WHERE id=?", (id_db,))
        conn.commit()
        conn.close()
        self.obnovit_data()

    def nacist_do_editace(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])['values']
        self.edit_id = item[0]
        self.ent_datum.delete(0, tk.END)
        self.ent_datum.insert(0, item[2])
        self.ent_prichod.delete(0, tk.END)
        self.ent_prichod.insert(0, item[3])
        odchod = item[4] if "V PRÁCI" not in str(item[4]) else ""
        self.ent_odchod.delete(0, tk.END)
        self.ent_odchod.insert(0, odchod)
        self.btn_ulozit.config(text="AKTUALIZOVAT")

    def vypocitej_idealni_odpracovano(self, tyden, datum_v_tydnu):
        """
        Spočítá, kolik by mělo být ideálně odpracováno k danému dni v týdnu
        (pondělí až čtvrtek: 7:00-15:30 = 8h, pátek se počítá zvlášť)
        """
        if datum_v_tydnu >= 4:  # pátek nebo víkend - pro výpočet do pátku bereme jen Po-Čt
            return 4 * 480  # 4 dny * 8 hodin = 32 hodin
        else:
            return (datum_v_tydnu + 1) * 480  # Po: 1 den, Út: 2 dny, atd.

    def obnovit_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        filtr = self.combo_tyden.get()
        
        # Určení týdne pro dotaz
        if filtr == "Aktuální týden":
            hledany_tyden = datetime.now().isocalendar()[1]
            dotaz = "SELECT * FROM dochazka WHERE tyden = ? ORDER BY datum DESC"
            params = [hledany_tyden]
        elif filtr == "Všechny záznamy":
            dotaz = "SELECT * FROM dochazka ORDER BY datum DESC"
            params = []
        else:
            hledany_tyden = int(filtr)
            dotaz = "SELECT * FROM dochazka WHERE tyden = ? ORDER BY datum DESC"
            params = [hledany_tyden]

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(dotaz, params).fetchall()
        
        # Načteme všechny záznamy pro aktuální týden (pokud je filtr)
        if filtr == "Aktuální týden":
            vsechny_tyden = conn.execute("SELECT * FROM dochazka WHERE tyden = ?", [hledany_tyden]).fetchall()
        else:
            vsechny_tyden = rows if params else []
        
        conn.close()

        # Zobrazení tabulky
        ted = datetime.now()
        for idx, r in enumerate(rows):
            vals = list(r)
            tag = 'even' if idx % 2 == 0 else 'odd'
            if not r[4]:  # odchod je None
                vals[4] = "V PRÁCI"
                vals[5] = "--"
                tag = 'working'
            else:
                vals[5] = formatuj_minuty(r[5])
            self.tree.insert('', tk.END, values=vals, tags=(tag,))

        # --- VÝPOČET ODHADU OCHODU V PÁTEK ---
        if filtr == "Aktuální týden":
            dny_v_tydnu = {}
            for r in vsechny_tyden:
                datum = datetime.strptime(r[2], "%Y-%m-%d")
                den_v_tydnu = datum.weekday()
                dny_v_tydnu[den_v_tydnu] = {'prichod': r[3], 'odchod': r[4], 'minut': r[5]}

            # 1. Čas z dokončených dnů (mimo dnešek)
            minuty_minule_dny = sum(r[5] for r in vsechny_tyden if r[4] and datetime.strptime(r[2], "%Y-%m-%d").date() != ted.date())
            
            # 2. Čas z dneška (pokud probíhá nebo je hotov)
            minuty_dnes = 0
            dnes_v_tydnu = ted.weekday()
            realny_prichod_dnes = "07:00" # fallback

            if dnes_v_tydnu in dny_v_tydnu:
                realny_prichod_dnes = dny_v_tydnu[dnes_v_tydnu]['prichod']
                if dny_v_tydnu[dnes_v_tydnu]['odchod']: # Dnes už zavřeno
                    minuty_dnes = dny_v_tydnu[dnes_v_tydnu]['minut']
                else: # Právě v práci
                    try:
                        p_dt = ted.replace(hour=datetime.strptime(realny_prichod_dnes, "%H:%M").hour,
                                           minute=datetime.strptime(realny_prichod_dnes, "%H:%M").minute)
                        if ted > p_dt:
                            diff = int((ted - p_dt).total_seconds() / 60)
                            if diff > 360: diff -= OBED_MINUT
                            minuty_dnes = max(0, diff)
                    except: pass

            skutecne_odpracovano = minuty_minule_dny + minuty_dnes
            
            # 3. Výpočet odhadu pro pátek
            celkem_fond = TYDENNI_FOND_HODIN * 60
            
            if dnes_v_tydnu == 4: # Je pátek
                # Kolik mi zbývalo ráno, než jsem přišel?
                zbyvalo_rano = celkem_fond - minuty_minule_dny
                # Odchod = dnešní příchod + to co zbývalo + oběd
                odchod_minuty = cas_na_minuty(realny_prichod_dnes) + zbyvalo_rano + OBED_MINUT
            else:
                # Je Po-Čt, počítáme ideální odchod na budoucí pátek
                ideal_k_dnes = self.vypocitej_idealni_odpracovano(hledany_tyden, dnes_v_tydnu)
                rozdil = skutecne_odpracovano - ideal_k_dnes
                patkovy_fond = 480 - rozdil
                odchod_minuty = cas_na_minuty("07:00") + patkovy_fond + OBED_MINUT

            # Formátování výsledku
            if dnes_v_tydnu == 4 and dny_v_tydnu.get(4, {}).get('odchod'):
                cas_patek = f"✓ {dny_v_tydnu[4]['odchod']}"
            elif odchod_minuty < 24*60:
                cas_patek = f"{int(odchod_minuty // 60):02d}:{int(odchod_minuty % 60):02d}"
            else:
                cas_patek = "NESTÍHÁŠ!"

            self.lbl_patek.config(text=cas_patek)
            
            # Progress bar a statistiky
            procenta = min(100, int((skutecne_odpracovano / celkem_fond) * 100))
            self.progress['value'] = procenta
            self.lbl_percent.config(text=f"{procenta}%")
            self.lbl_stats.config(text=f"Odpracováno: {formatuj_minuty(skutecne_odpracovano)}")
            self.lbl_remaining.config(text=f"Zbývá: {formatuj_minuty(max(0, celkem_fond - skutecne_odpracovano))}")
        else:
            # Nejsme v aktuálním týdnu, jen zobrazíme základní info
            self.lbl_patek.config(text="--:--")
            self.lbl_stats.config(text="Odpracováno: --")
            self.lbl_remaining.config(text="Zbývá: --")
            self.progress['value'] = 0
            self.lbl_percent.config(text="0%")

    def export_pro_excel(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not file_path:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            data = conn.execute("SELECT datum, prichod, odchod FROM dochazka ORDER BY datum ASC").fetchall()
            conn.close()
            with open(file_path, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Datum", "Příchod", "Odchod"])
                writer.writerows(data)
            messagebox.showinfo("Hotovo", "Export proběhl úspěšně!")
        except Exception as e:
            messagebox.showerror("Chyba", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = PatecniVestec(root)
    root.mainloop()