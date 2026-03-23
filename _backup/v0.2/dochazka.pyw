import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import sys
import csv
from datetime import datetime, timedelta
import psutil

# --- KONFIGURACE ---
TYDENNI_FOND_HODIN = 40
OBED_MINUT = 30
PATEK_PRIJEZD = "07:00"

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

class PatecniVestec:
    def __init__(self, root):
        self.root = root
        self.root.title("Páteční Věštec 2.0")
        self.root.geometry("660x950")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")
        
        self.db_path = get_db_path()
        self.edit_id = None
        self.last_estimate = ""  # pro kopírování
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
        success = "#28a745"
        warning = "#ffc107"
        danger = "#dc3545"

        # Obecné styly
        style.configure("TFrame", background=bg_dark)
        style.configure("TLabelframe", background=bg_dark, foreground=fg, bordercolor=bg_light)
        style.configure("TLabelframe.Label", background=bg_dark, foreground=accent, font=('Segoe UI', 11, 'bold'))
        
        style.configure("TLabel", background=bg_dark, foreground=fg, font=('Segoe UI', 10))
        style.configure("TButton", font=('Segoe UI', 10, 'bold'), borderwidth=0, padding=6)
        style.map("TButton",
                  background=[('active', accent_light), ('!active', accent)],
                  foreground=[('active', fg), ('!active', fg)])
        
        style.configure("TEntry", fieldbackground=bg_medium, foreground=fg, bordercolor=bg_light, padding=5)
        style.configure("TCheckbutton", background=bg_dark, foreground=fg, font=('Segoe UI', 10))
        style.map("TCheckbutton", background=[('active', bg_medium)])
        
        # Treeview
        style.configure("Treeview", background=bg_medium, fieldbackground=bg_medium, foreground=fg,
                        rowheight=34, borderwidth=0, font=('Segoe UI', 9))
        style.configure("Treeview.Heading", background=bg_light, foreground=fg,
                        font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map("Treeview", background=[('selected', accent)])
        
        # Progress bar
        style.configure("Accent.Horizontal.TProgressbar", background=accent, troughcolor=bg_medium, borderwidth=0, thickness=12)
        
        # Kombobox
        style.configure("TCombobox", fieldbackground=bg_medium, foreground=fg, bordercolor=bg_light)
        style.map("TCombobox", fieldbackground=[('readonly', bg_medium)])

    def create_widgets(self):
        # --- HEADER ---
        header_frame = tk.Frame(self.main_container, bg="#1a1a1a")
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title = tk.Label(header_frame, text="PÁTEČNÍ VĚŠTEC 2.0",
                         font=('Segoe UI Black', 24), bg="#1a1a1a", fg="#0078d4")
        title.pack(side=tk.LEFT)
        
        # Verze / malý popisek
        version = tk.Label(header_frame, text="high-end edice", font=('Segoe UI', 9),
                           bg="#1a1a1a", fg="#888")
        version.pack(side=tk.RIGHT, anchor='s')

        # --- ANALÝZA (horní karta) ---
        analysis_frame = ttk.LabelFrame(self.main_container, text=" ANALÝZA TÝDNE ", padding=15)
        analysis_frame.pack(fill=tk.X, pady=5)

        # První řádek: statistiky a progress bar
        stats_row = tk.Frame(analysis_frame, bg="#2d2d2d")
        stats_row.pack(fill=tk.X, pady=(0, 8))

        self.lbl_stats = tk.Label(stats_row, text="Načítám...", font=('Segoe UI', 11),
                                  bg="#2d2d2d", fg="white")
        self.lbl_stats.pack(side=tk.LEFT, padx=(0, 15))

        self.progress = ttk.Progressbar(stats_row, style="Accent.Horizontal.TProgressbar",
                                        orient='horizontal', length=200, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=5)

        self.lbl_percent = tk.Label(stats_row, text="0%", font=('Segoe UI', 10, 'bold'),
                                    bg="#2d2d2d", fg="#0078d4")
        self.lbl_percent.pack(side=tk.LEFT, padx=(5, 0))

        # Druhý řádek: velký odhad odchodu (klikatelný)
        estimate_frame = tk.Frame(analysis_frame, bg="#2d2d2d")
        estimate_frame.pack(fill=tk.X, pady=5)

        tk.Label(estimate_frame, text="🕒 Odhad odchodu v pátek:", font=('Segoe UI', 12),
                 bg="#2d2d2d", fg="#aaa").pack()

        self.lbl_patek = tk.Label(estimate_frame, text="--:--",
                                   font=('Segoe UI', 22, 'bold'), bg="#2d2d2d", fg="#0078d4",
                                   cursor="hand2")
        self.lbl_patek.pack()
        self.lbl_patek.bind("<Button-1>", self.copy_estimate)

        tk.Label(estimate_frame, text="(kliknutím zkopíruješ)", font=('Segoe UI', 8),
                 bg="#2d2d2d", fg="#888").pack()

        # --- VSTUPNÍ KARTA ---
        entry_frame = ttk.LabelFrame(self.main_container, text=" NOVÝ ZÁZNAM / EDITACE ", padding=12)
        entry_frame.pack(fill=tk.X, pady=10)

        # Mřížka pro vstupní pole
        grid_params = {'padx': 8, 'pady': 6, 'sticky': 'w'}

        ttk.Label(entry_frame, text="Datum:").grid(row=0, column=0, **grid_params)
        self.ent_datum = ttk.Entry(entry_frame, width=12)
        self.ent_datum.grid(row=0, column=1, **grid_params)

        ttk.Label(entry_frame, text="Příchod:").grid(row=1, column=0, **grid_params)
        self.ent_prichod = ttk.Entry(entry_frame, width=12)
        self.ent_prichod.grid(row=1, column=1, **grid_params)
        ttk.Button(entry_frame, text="⏱", width=3,
                   command=lambda: self.nastav_cas(self.ent_prichod)).grid(row=1, column=2, padx=5)

        ttk.Label(entry_frame, text="Odchod:").grid(row=2, column=0, **grid_params)
        self.ent_odchod = ttk.Entry(entry_frame, width=12)
        self.ent_odchod.grid(row=2, column=1, **grid_params)
        ttk.Button(entry_frame, text="⏱", width=3,
                   command=lambda: self.nastav_cas(self.ent_odchod)).grid(row=2, column=2, padx=5)

        self.var_obed = tk.BooleanVar(value=True)
        ttk.Checkbutton(entry_frame, text="Odečíst 30 minut oběd", variable=self.var_obed).grid(
            row=3, column=0, columnspan=3, pady=10, sticky='w')

        # Tlačítka akcí
        btn_container = tk.Frame(entry_frame, bg="#2d2d2d")
        btn_container.grid(row=4, column=0, columnspan=3, sticky='ew', pady=5)
        btn_container.columnconfigure(0, weight=1)
        btn_container.columnconfigure(1, weight=1)
        btn_container.columnconfigure(2, weight=1)

        self.btn_ulozit = ttk.Button(btn_container, text="💾 Uložit", command=self.ulozit)
        self.btn_ulozit.grid(row=0, column=0, sticky='ew', padx=2)

        ttk.Button(btn_container, text="🔄 Sync PC", command=self.check_boot_time_and_record).grid(
            row=0, column=1, sticky='ew', padx=2)
        ttk.Button(btn_container, text="📤 Export", command=self.export_pro_excel).grid(
            row=0, column=2, sticky='ew', padx=2)

        # --- HISTORIE ---
        history_frame = ttk.LabelFrame(self.main_container, text=" HISTORIE ", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Filtr týdnů
        filter_frame = tk.Frame(history_frame, bg="#2d2d2d")
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filter_frame, text="Týden:", background="#2d2d2d").pack(side=tk.LEFT, padx=5)
        self.combo_tyden = ttk.Combobox(filter_frame, state="readonly", width=22)
        self.combo_tyden.pack(side=tk.LEFT, padx=5)
        self.combo_tyden.bind("<<ComboboxSelected>>", lambda e: self.obnovit_data())

        # Tabulka se scrollbarem
        tree_frame = tk.Frame(history_frame, bg="#2d2d2d")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("ID", "Týden", "Datum", "Příchod", "Odchod", "Čistý čas")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)

        widths = {"ID": 30, "Týden": 50, "Datum": 90, "Příchod": 70, "Odchod": 100, "Čistý čas": 90}
        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=widths[col], anchor=tk.CENTER)

        # Střídavé barvy řádků
        self.tree.tag_configure('odd', background='#2d2d2d')
        self.tree.tag_configure('even', background='#353535')
        self.tree.tag_configure('working', foreground='#ffa500', font=('Segoe UI', 9, 'italic'))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.nacist_do_editace)

        # Tlačítko pro smazání
        ttk.Button(history_frame, text="🗑️ Smazat vybraný", command=self.smazat).pack(fill=tk.X, pady=(8, 0))

    # --- LOGIKA ---
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
        self.btn_ulozit.config(text="💾 Uložit")

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
        self.btn_ulozit.config(text="🔄 Aktualizovat")

    def obnovit_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        filtr = self.combo_tyden.get()
        dotaz = "SELECT * FROM dochazka"
        params = []
        if filtr == "Aktuální týden":
            dotaz += " WHERE tyden = ?"
            params.append(datetime.now().isocalendar()[1])
        elif filtr != "Všechny záznamy":
            dotaz += " WHERE tyden = ?"
            params.append(int(filtr))

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(dotaz + " ORDER BY datum DESC", params).fetchall()
        conn.close()

        odpracovano = 0
        ted = datetime.now()
        for idx, r in enumerate(rows):
            vals = list(r)
            tag = 'even' if idx % 2 == 0 else 'odd'
            if not r[4]:  # odchod je None
                vals[4] = "V PRÁCI"
                vals[5] = "--"
                tag = 'working'
                try:
                    p_dt = ted.replace(hour=datetime.strptime(r[3], "%H:%M").hour,
                                       minute=datetime.strptime(r[3], "%H:%M").minute)
                    if ted > p_dt:
                        diff = int((ted - p_dt).total_seconds() / 60)
                        if diff > 360:
                            diff -= OBED_MINUT
                        odpracovano += max(0, diff)
                except Exception:
                    pass
            else:
                vals[5] = formatuj_minuty(r[5])
                odpracovano += r[5]
            self.tree.insert('', tk.END, values=vals, tags=(tag,))

        # Analýza a progress bar
        celkem_minut = TYDENNI_FOND_HODIN * 60
        procenta = min(100, int((odpracovano / celkem_minut) * 100)) if celkem_minut else 0
        self.progress['value'] = procenta
        self.lbl_percent.config(text=f"{procenta}%")

        zbyva = celkem_minut - odpracovano
        dneska_v_tydnu = ted.weekday()
        dni_pred_patkem = max(0, 4 - dneska_v_tydnu - 1)
        zbyva_na_patek = zbyva - (dni_pred_patkem * 480)

        odchod_dt = datetime.strptime(PATEK_PRIJEZD, "%H:%M") + timedelta(minutes=max(0, zbyva_na_patek) + OBED_MINUT)
        if zbyva_na_patek < 1000 and odchod_dt.day == 1:
            cas_patek = odchod_dt.strftime('%H:%M')
        else:
            cas_patek = "🏃 NESTÍHÁŠ!"

        self.last_estimate = cas_patek
        self.lbl_patek.config(text=cas_patek)
        self.lbl_stats.config(text=f"Odpracováno: {formatuj_minuty(odpracovano)}  |  Zbývá: {formatuj_minuty(zbyva)}")

    def copy_estimate(self, event):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.last_estimate)
        # Dočasně změníme text na potvrzení
        original = self.lbl_patek.cget("text")
        self.lbl_patek.config(text="✅ Zkopírováno!")
        self.root.after(1500, lambda: self.lbl_patek.config(text=original))

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