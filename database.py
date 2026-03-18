import sqlite3
import config
from config import get_db_path


class DochazkaDB:
    def __init__(self):
        self.db_path = get_db_path()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS dochazka 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             tyden INTEGER,
                             datum TEXT,
                             prichod TEXT,
                             odchod TEXT,
                             minut INTEGER)''')
            # Přidání sloupce obed, pokud neexistuje
            try:
                conn.execute(
                    "ALTER TABLE dochazka ADD COLUMN obed INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                pass

    # --- CRUD operace ---
    def insert(self, datum, prichod, odchod, obed, tyden):
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO dochazka (tyden, datum, prichod, odchod, minut, obed) VALUES (?, ?, ?, ?, ?, ?)",
                (tyden, datum, prichod, odchod, 0 if not odchod else max(
                    0, self._vypocti_minuty(prichod, odchod, obed)), obed)
            )
            return cursor.lastrowid

    def update(self, id, datum, prichod, odchod, obed, tyden):
        with self._connect() as conn:
            conn.execute(
                "UPDATE dochazka SET tyden=?, datum=?, prichod=?, odchod=?, minut=?, obed=? WHERE id=?",
                (tyden, datum, prichod, odchod, 0 if not odchod else max(
                    0, self._vypocti_minuty(prichod, odchod, obed)), obed, id)
            )

    def delete(self, id):
        with self._connect() as conn:
            conn.execute("DELETE FROM dochazka WHERE id=?", (id,))

    def fetch_by_id(self, id):
        with self._connect() as conn:
            return conn.execute("SELECT * FROM dochazka WHERE id=?", (id,)).fetchone()

    # --- Výběry podle kritérií ---
    def fetch_all(self):
        with self._connect() as conn:
            return conn.execute("SELECT * FROM dochazka ORDER BY datum DESC").fetchall()

    def fetch_by_week(self, tyden):
        with self._connect() as conn:
            return conn.execute("SELECT * FROM dochazka WHERE tyden=? ORDER BY datum DESC", (tyden,)).fetchall()

    def fetch_by_month(self, month_str):   # month_str = 'YYYY-MM'
        with self._connect() as conn:
            return conn.execute(
                "SELECT datum, prichod, odchod, minut, obed FROM dochazka WHERE substr(datum, 1, 7)=?",
                (month_str,)
            ).fetchall()

    def fetch_distinct_weeks(self):
        with self._connect() as conn:
            return [row[0] for row in conn.execute("SELECT DISTINCT tyden FROM dochazka ORDER BY tyden DESC").fetchall()]

    def fetch_months_for_export(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT DISTINCT substr(datum, 1, 4) as rok, substr(datum, 6, 2) as mesic "
                "FROM dochazka ORDER BY rok DESC, mesic DESC"
            ).fetchall()

    def fetch_for_export(self, months):
        placeholders = ','.join(['?' for _ in months])
        with self._connect() as conn:
            return conn.execute(
                f"SELECT datum, prichod, odchod FROM dochazka WHERE substr(datum, 1, 7) IN ({placeholders}) ORDER BY datum ASC",
                months
            ).fetchall()

    # --- Interní pomocná metoda ---
    def _vypocti_minuty(self, prichod, odchod, obed):
        from datetime import datetime
        from config import OBED_MINUT
        t1 = datetime.strptime(prichod, "%H:%M")
        t2 = datetime.strptime(odchod, "%H:%M")
        return int((t2 - t1).total_seconds() / 60) - (OBED_MINUT if obed else 0)

    def find_open_record(self):
        """Vrátí první (nejnovější) záznam, který nemá vyplněný odchod."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, datum, prichod, obed FROM dochazka "
                "WHERE odchod IS NULL OR odchod = '' "
                "ORDER BY datum DESC, id DESC LIMIT 1"
            )
            return cur.fetchone()

    def update_odchod(self, record_id, odchod):
        """Nastaví odchod u daného záznamu a přepočítá minuty."""
        with self._connect() as conn:
            # nejdřív získáme prichod a obed
            cur = conn.execute(
                "SELECT prichod, obed FROM dochazka WHERE id = ?",
                (record_id,)
            )
            row = cur.fetchone()
            if not row:
                return
            prichod, obed = row
            obed_bool = bool(obed)
            minuty = 0
            if odchod and prichod:
                from datetime import datetime
                try:
                    t1 = datetime.strptime(prichod, "%H:%M")
                    t2 = datetime.strptime(odchod, "%H:%M")
                    diff = int((t2 - t1).total_seconds() / 60)
                    if diff > 360 and obed_bool:
                        diff -= config.OBED_MINUT
                    minuty = max(0, diff)
                except:
                    minuty = 0
            conn.execute(
                "UPDATE dochazka SET odchod = ?, minut = ? WHERE id = ?",
                (odchod, minuty, record_id)
            )
