import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import sys
import csv
from datetime import datetime, timedelta

def get_db_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'dochazka.db')

TYDENNI_FOND_HODIN = 40
OBED_MINUT = 30
PATEK_PRIJEZD = "07:00"

def formatuj_minuty(celkem_minut):
    h = celkem_minut // 60
    m = celkem_minut % 60
    return f"{h}h {m:02d}m"

class PatecniVestec:
    def __init__(self, root):
        self.root = root
        self.root.title("Páteční Věštec v1.1")
        self.root.geometry("550x820")
        self.root.resizable(False, False)
        
        self.db_path = get_db_path()
        self.edit_id = None
        self.setup_db()
        
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- SEKCE ZADÁVÁNÍ ---
        input_group = ttk.LabelFrame(main_frame, text=" Záznam / Editace ", padding=10)
        input_group.pack(fill=tk.X, pady=5)

        # ... (pole pro Datum, Příchod, Odchod zůstávají stejná) ...
        ttk.Label(input_group, text="Datum:").grid(row=0, column=0, sticky=tk.W)
        self.ent_datum = ttk.Entry(input_group, width=15)
        self.ent_datum.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(input_group, text="Příchod:").grid(row=1, column=0, sticky=tk.W)
        self.ent_prichod = ttk.Entry(input_group, width=15)
        self.ent_prichod.grid(row=1, column=1, sticky=tk.W)
        ttk.Button(input_group, text="Teď", width=5, command=lambda: self.nastav_cas(self.ent_prichod)).grid(row=1, column=2, padx=5)

        ttk.Label(input_group, text="Odchod:").grid(row=2, column=0, sticky=tk.W)
        self.ent_odchod = ttk.Entry(input_group, width=15)
        self.ent_odchod.grid(row=2, column=1, sticky=tk.W)
        ttk.Button(input_group, text="Teď", width=5, command=lambda: self.nastav_cas(self.ent_odchod)).grid(row=2, column=2, padx=5)

        self.var_obed = tk.BooleanVar(value=True)
        self.chk_obed = ttk.Checkbutton(input_group, text="Odečíst 30 min oběd", variable=self.var_obed)
        self.chk_obed.grid(row=3, column=0, columnspan=2, pady=5, sticky=tk.W)

        btn_row = ttk.Frame(input_group)
        btn_row.grid(row=4, column=0, columnspan=3, pady=10, sticky=tk.EW)
        self.btn_ulozit = ttk.Button(btn_row, text="Uložit záznam", command=self.ulozit)
        self.btn_ulozit.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_row, text="Importovat Toggl CSV", command=self.import_toggl).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- FILTROVÁNÍ ---
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=5)
        ttk.Label(filter_frame, text="Zobrazit týden:").pack(side=tk.LEFT, padx=5)
        
        self.combo_tyden = ttk.Combobox(filter_frame, state="readonly", width=15)
        self.combo_tyden.pack(side=tk.LEFT, padx=5)
        self.combo_tyden.bind("<<ComboboxSelected>>", lambda e: self.obnovit_data())

        # --- HISTORIE ---
        history_group = ttk.LabelFrame(main_frame, text=" Historie záznamů ", padding=10)
        history_group.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(history_group, columns=("ID", "Týden", "Datum", "In", "Out", "Čistý"), show='headings', height=10)
        for col in [("ID", 30), ("Týden", 50), ("Datum", 90), ("In", 60), ("Out", 60), ("Čistý", 80)]:
            self.tree.heading(col[0], text=col[0])
            self.tree.column(col[0], width=col[1], anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.nacist_do_editace)

        ttk.Button(history_group, text="Smazat záznam", command=self.smazat).pack(fill=tk.X, pady=5)

        # --- ANALÝZA ---
        self.info_panel = ttk.LabelFrame(main_frame, text=" Analýza vybraného období ", padding=10)
        self.info_panel.pack(fill=tk.X, pady=5)
        self.lbl_patek = ttk.Label(self.info_panel, text="...", font=('Arial', 10, 'bold'), foreground="#1a73e8", justify=tk.CENTER)
        self.lbl_patek.pack()

        self.nacti_tydny_do_filtru()
        self.reset_form()
        self.obnovit_data()

    def setup_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS dochazka 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, tyden INTEGER, datum TEXT, prichod TEXT, odchod TEXT, minut INTEGER)''')
        conn.commit()
        conn.close()

    def nacti_tydny_do_filtru(self):
        conn = sqlite3.connect(self.db_path)
        tydny = conn.execute("SELECT DISTINCT tyden FROM dochazka ORDER BY tyden DESC").fetchall()
        conn.close()
        
        seznam = ["Aktuální týden", "Všechny záznamy"] + [str(t[0]) for t in tydny]
        self.combo_tyden['values'] = seznam
        self.combo_tyden.set("Aktuální týden")

    def import_toggl(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path: return
        try:
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                conn = sqlite3.connect(self.db_path)
                import_count = 0
                for row in reader:
                    datum = row['Start date']
                    prichod = row['Start time'][:5]
                    odchod = row['Stop time'][:5]
                    dt_obj = datetime.strptime(datum, "%Y-%m-%d")
                    tyden = dt_obj.isocalendar()[1]
                    t1 = datetime.strptime(prichod, "%H:%M")
                    t2 = datetime.strptime(odchod, "%H:%M")
                    minut = int((t2 - t1).total_seconds() / 60) - OBED_MINUT
                    check = conn.execute("SELECT id FROM dochazka WHERE datum=? AND prichod=?", (datum, prichod)).fetchone()
                    if not check:
                        conn.execute("INSERT INTO dochazka (tyden, datum, prichod, odchod, minut) VALUES (?, ?, ?, ?, ?)", 
                                     (tyden, datum, prichod, odchod, max(0, minut)))
                        import_count += 1
                conn.commit(); conn.close()
                self.nacti_tydny_do_filtru()
                self.obnovit_data()
                messagebox.showinfo("Hotovo", f"Importováno {import_count} nových záznamů.")
        except Exception as e:
            messagebox.showerror("Chyba importu", str(e))

    def reset_form(self):
        self.edit_id = None
        self.ent_datum.delete(0, tk.END); self.ent_datum.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.ent_prichod.delete(0, tk.END); self.ent_odchod.delete(0, tk.END)
        self.btn_ulozit.config(text="Uložit záznam")

    def nastav_cas(self, entry_field):
        entry_field.delete(0, tk.END); entry_field.insert(0, datetime.now().strftime("%H:%M"))

    def ulozit(self):
        d, p, o = self.ent_datum.get(), self.ent_prichod.get(), self.ent_odchod.get()
        if not p: return
        dt_obj = datetime.strptime(d, "%Y-%m-%d")
        tyden = dt_obj.isocalendar()[1]
        minut = 0
        if o:
            t1 = datetime.strptime(p, "%H:%M")
            t2 = datetime.strptime(o, "%H:%M")
            minut = int((t2 - t1).total_seconds() / 60) - (OBED_MINUT if self.var_obed.get() else 0)
        conn = sqlite3.connect(self.db_path)
        if self.edit_id:
            conn.execute("UPDATE dochazka SET tyden=?, datum=?, prichod=?, odchod=?, minut=? WHERE id=?", (tyden, d, p, o, max(0, minut), self.edit_id))
        else:
            conn.execute("INSERT INTO dochazka (tyden, datum, prichod, odchod, minut) VALUES (?, ?, ?, ?, ?)", (tyden, d, p, o, max(0, minut)))
        conn.commit(); conn.close()
        self.nacti_tydny_do_filtru()
        self.reset_form(); self.obnovit_data()

    def nacist_do_editace(self, event):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])['values']
        self.edit_id = item[0]
        self.ent_datum.delete(0, tk.END); self.ent_datum.insert(0, item[2])
        self.ent_prichod.delete(0, tk.END); self.ent_prichod.insert(0, item[3])
        self.ent_odchod.delete(0, tk.END); self.ent_odchod.insert(0, item[4] if "PRÁCI" not in str(item[4]) else "")
        self.btn_ulozit.config(text="Aktualizovat")

    def smazat(self):
        selected = self.tree.selection()
        if not selected: return
        id_db = self.tree.item(selected[0])['values'][0]
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM dochazka WHERE id=?", (id_db,))
        conn.commit(); conn.close()
        self.nacti_tydny_do_filtru(); self.reset_form(); self.obnovit_data()

    def obnovit_data(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        filtr = self.combo_tyden.get()
        dotaz = "SELECT * FROM dochazka"
        parametry = []

        if filtr == "Aktuální týden":
            dotaz += " WHERE tyden = ?"
            parametry.append(datetime.now().isocalendar()[1])
        elif filtr != "Všechny záznamy":
            dotaz += " WHERE tyden = ?"
            parametry.append(int(filtr))
        
        dotaz += " ORDER BY datum DESC, id DESC"
        
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(dotaz, parametry).fetchall()
        
        odpracovano = 0
        for r in rows:
            vals = list(r)
            vals[5] = formatuj_minuty(r[5]) if r[4] else "--"
            if not r[4]: vals[4] = ">> V PRÁCI <<"
            odpracovano += r[5]
            self.tree.insert('', tk.END, values=vals)
        conn.close()
        
        # Analýza pátku
        zbyva = (TYDENNI_FOND_HODIN * 60) - odpracovano
        if zbyva > 0:
            konec = datetime.strptime(PATEK_PRIJEZD, "%H:%M") + timedelta(minutes=zbyva + OBED_MINUT)
            msg = f"Období: {filtr}\nČistý čas: {formatuj_minuty(odpracovano)} | Zbývá: {formatuj_minuty(zbyva)}\nPáteční odchod (v {PATEK_PRIJEZD}): {konec.strftime('%H:%M')}"
        else:
            msg = f"Období: {filtr}\nFond splněn! 🎉 (Celkem: {formatuj_minuty(odpracovano)})"
        
        self.lbl_patek.config(text=msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = PatecniVestec(root)
    root.mainloop()