"""
WageSlave — Správa výjimečných dnů (svátky, dovolená, nemoc)

Typy dnů:
  holiday  — státní svátek (fond zachován, den se počítá jako odpracovaný)
  vacation — dovolená     (fond zachován, den se počítá jako odpracovaný)
  sick     — nemocenská   (fond se sníží o tento den = 8h méně v týdnu/měsíci)
"""

import sqlite3
import config
from config import get_db_path


# ─────────────────────────────────────────────────────────────────────────────
#  TYPY A POPISKY
# ─────────────────────────────────────────────────────────────────────────────

TYPES = {
    "holiday":  "Státní svátek",
    "vacation": "Dovolená",
    "sick":     "Nemocenská",
}

TYPE_COLORS = {
    "holiday":  "#f59e0b",   # amber
    "vacation": "#22c55e",   # green
    "sick":     "#ef4444",   # red
}

TYPE_EMOJI = {
    "holiday":  "🎉",
    "vacation": "🏖",
    "sick":     "🤒",
}


# ─────────────────────────────────────────────────────────────────────────────
#  DB OPERACE
# ─────────────────────────────────────────────────────────────────────────────

def _connect():
    return sqlite3.connect(get_db_path())


def init_table():
    """Vytvoří tabulku special_days pokud neexistuje."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS special_days (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                datum   TEXT NOT NULL UNIQUE,
                typ     TEXT NOT NULL,
                poznamka TEXT DEFAULT ''
            )
        """)


def upsert(datum: str, typ: str, poznamka: str = "") -> bool:
    """Vloží nebo aktualizuje záznam. Vrátí True pokud OK."""
    if typ not in TYPES:
        return False
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO special_days (datum, typ, poznamka)
                VALUES (?, ?, ?)
                ON CONFLICT(datum) DO UPDATE SET typ=excluded.typ, poznamka=excluded.poznamka
            """, (datum, typ, poznamka))
        return True
    except Exception:
        return False


def delete(datum: str):
    """Smaže záznam pro dané datum."""
    with _connect() as conn:
        conn.execute("DELETE FROM special_days WHERE datum=?", (datum,))


def get(datum: str):
    """Vrátí (datum, typ, poznamka) nebo None."""
    with _connect() as conn:
        return conn.execute(
            "SELECT datum, typ, poznamka FROM special_days WHERE datum=?", (datum,)
        ).fetchone()


def get_type(datum: str) -> str | None:
    """Vrátí typ ('holiday'/'vacation'/'sick') nebo None."""
    row = get(datum)
    return row[1] if row else None


def fetch_month(month_str: str) -> list:
    """Vrátí všechny záznamy pro daný měsíc (YYYY-MM)."""
    with _connect() as conn:
        return conn.execute(
            "SELECT datum, typ, poznamka FROM special_days "
            "WHERE substr(datum,1,7)=? ORDER BY datum",
            (month_str,)
        ).fetchall()


def fetch_range(date_from: str, date_to: str) -> dict:
    """Vrátí dict {datum: (typ, poznamka)} pro dané rozmezí dat."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT datum, typ, poznamka FROM special_days "
            "WHERE datum>=? AND datum<=?",
            (date_from, date_to)
        ).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def fetch_year(year: int) -> dict:
    """Vrátí dict {datum: (typ, poznamka)} pro celý rok."""
    return fetch_range(f"{year}-01-01", f"{year}-12-31")


# ─────────────────────────────────────────────────────────────────────────────
#  STAŽENÍ SVÁTKŮ Z API (Czech public holidays — open data)
# ─────────────────────────────────────────────────────────────────────────────

# Pevně zakódované české státní svátky pro fallback (bez závislosti na síti)
_CS_HOLIDAYS_FIXED = {
    "01-01": "Nový rok / Den obnovy státu",
    "05-01": "Svátek práce",
    "05-08": "Den vítězství",
    "07-05": "Den slovanských věrozvěstů",
    "07-06": "Den upálení mistra Jana Husa",
    "09-28": "Den české státnosti",
    "10-28": "Den vzniku Československého státu",
    "11-17": "Den boje za svobodu a demokracii",
    "12-24": "Štědrý den",
    "12-25": "1. svátek vánoční",
    "12-26": "2. svátek vánoční",
}


def _easter_monday(year: int) -> str:
    """Vrátí datum Velikonočního pondělí jako YYYY-MM-DD."""
    # Anonymous Gregorian algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day   = ((h + l - 7 * m + 114) % 31) + 1
    # Easter Sunday → +1 day = Monday
    import datetime
    easter_sun = datetime.date(year, month, day)
    easter_mon = easter_sun + datetime.timedelta(days=1)
    return easter_mon.strftime("%Y-%m-%d")


def get_fixed_holidays(year: int) -> dict:
    """Vrátí dict {datum: nazev} pro pevné české státní svátky + Velikonoční pondělí."""
    holidays = {}
    for mmdd, name in _CS_HOLIDAYS_FIXED.items():
        holidays[f"{year}-{mmdd}"] = name
    holidays[_easter_monday(year)] = "Velikonoční pondělí"
    return holidays


def import_holidays_from_api(year: int, overwrite: bool = False) -> tuple[int, int, str]:
    """
    Stáhne české státní svátky z veřejného API (data.mff.cuni.cz nebo fallback).
    Vrátí (pocet_pridanych, pocet_preskocen, chybova_zprava_nebo_prazdny_string).
    """
    import urllib.request
    import json

    data = None
    zdroj = "offline"

    # Ověřené API: https://date.nager.at/api/v3/PublicHolidays/{year}/CZ
    urls = [
        f"https://date.nager.at/api/v3/PublicHolidays/{year}/CZ",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WageSlave/2.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                zdroj = url
                break
        except Exception:
            continue

    if data is None:
        # Použij pevně zakódované
        holidays = get_fixed_holidays(year)
        zdroj = "offline (vestavěný seznam)"
    else:
        # Parsuj různé formáty
        holidays = _parse_api_response(data, year)

    pridano = 0
    preskoceno = 0
    for datum, name in holidays.items():
        existing = get(datum)
        if existing and not overwrite:
            preskoceno += 1
            continue
        ok = upsert(datum, "holiday", name)
        if ok:
            pridano += 1
        else:
            preskoceno += 1

    return pridano, preskoceno, f"Zdroj: {zdroj}"


def _parse_api_response(data, year: int) -> dict:
    """Parsuje různé formáty API odpovědí na dict {datum: name}.
    nager.at vrací: [{"date": "2026-01-01", "localName": "Nový rok", "name": "New Year's Day", ...}]
    """
    result = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # nager.at: 'date' + 'localName' (česky) nebo 'name' (anglicky)
                datum = item.get("date") or item.get("datum") or item.get("day")
                name  = (item.get("localName") or item.get("name") or
                         item.get("nazev") or item.get("title") or "Státní svátek")
                if datum:
                    datum = _normalize_date(datum, year)
                    if datum:
                        result[datum] = name
    elif isinstance(data, dict):
        for key, val in data.items():
            datum = _normalize_date(key, year)
            name  = val if isinstance(val, str) else (val.get("localName") or val.get("name", "Státní svátek") if isinstance(val, dict) else "Státní svátek")
            if datum:
                result[datum] = name
    # Fallback: pokud nic nezparsováno, použij pevné
    if not result:
        result = get_fixed_holidays(year)
    return result


def _normalize_date(s: str, year: int) -> str | None:
    """Zkusí normalizovat různé formáty data na YYYY-MM-DD."""
    import re
    s = str(s).strip()
    # Už správný formát
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # DD.MM.YYYY nebo DD.MM.
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.?(\d{4})?$", s)
    if m:
        d, mo, y = m.group(1), m.group(2), m.group(3) or str(year)
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    # MM-DD
    m = re.match(r"^(\d{2})-(\d{2})$", s)
    if m:
        return f"{year}-{m.group(1)}-{m.group(2)}"
    return None
