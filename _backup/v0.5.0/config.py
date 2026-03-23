import os
import sys

TYDENNI_FOND_HODIN = 40
OBED_MINUT = 30
STANDARDNI_PRICHOD = "07:00"
STANDARDNI_ODCHOD = "15:30"

def get_db_path():
    """Vrátí absolutní cestu k databázovému souboru."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'dochazka.db')