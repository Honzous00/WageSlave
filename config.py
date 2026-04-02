import os
import sys
import json

# Vychozi hodnoty
TYDENNI_FOND_HODIN = 40
OBED_MINUT = 30
STANDARDNI_PRICHOD = "07:00"
STANDARDNI_ODCHOD  = "15:30"
DB_PATH_OVERRIDE   = ""   # prazdny = pouzij vychozi (AppData)
AUTO_BACKUP        = False
LOGO_VARIANTA      = "money"  # purple | purple_neon | money | money_neon | slave | slave_neon


def get_app_dir():
    """Vraci %APPDATA%/WageSlave, vytvori pokud neexistuje."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    d = os.path.join(appdata, "WageSlave_testing")
    os.makedirs(d, exist_ok=True)
    return d


def get_config_path():
    return os.path.join(get_app_dir(), "config.json")


def get_db_path():
    load()   # zajisti nacteni pred pouzitim
    if DB_PATH_OVERRIDE:
        return DB_PATH_OVERRIDE
    return os.path.join(get_app_dir(), "wageslave.db")


_loaded = False

def load():
    global TYDENNI_FOND_HODIN, OBED_MINUT, STANDARDNI_PRICHOD
    global STANDARDNI_ODCHOD, DB_PATH_OVERRIDE, AUTO_BACKUP, LOGO_VARIANTA, _loaded
    if _loaded:
        return
    _loaded = True
    path = get_config_path()
    if not os.path.exists(path):
        save()   # vytvor soubor s vychozimi hodnotami
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        TYDENNI_FOND_HODIN = d.get("tydenni_fond_hodin", TYDENNI_FOND_HODIN)
        OBED_MINUT         = d.get("obed_minut",         OBED_MINUT)
        STANDARDNI_PRICHOD = d.get("standardni_prichod", STANDARDNI_PRICHOD)
        STANDARDNI_ODCHOD  = d.get("standardni_odchod",  STANDARDNI_ODCHOD)
        DB_PATH_OVERRIDE   = d.get("db_path_override",   DB_PATH_OVERRIDE)
        AUTO_BACKUP        = d.get("auto_backup",         AUTO_BACKUP)
        LOGO_VARIANTA      = d.get("logo_varianta",       LOGO_VARIANTA)
    except Exception:
        pass


def save():
    path = get_config_path()
    d = {
        "tydenni_fond_hodin": TYDENNI_FOND_HODIN,
        "obed_minut":         OBED_MINUT,
        "standardni_prichod": STANDARDNI_PRICHOD,
        "standardni_odchod":  STANDARDNI_ODCHOD,
        "db_path_override":   DB_PATH_OVERRIDE,
        "auto_backup":        AUTO_BACKUP,
        "logo_varianta":      LOGO_VARIANTA,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
