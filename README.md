# Docházkový systém v2.0

Moderní desktopová aplikace pro evidenci pracovní doby.

## Instalace

1. Ujistěte se, že máte Python 3.9+
2. Nainstalujte závislosti:
   ```
   pip install -r requirements.txt
   ```
3. Spusťte aplikaci:
   ```
   pythonw dochazka.pyw
   ```
   nebo poklikejte na `dochazka.pyw`

## Volitelné (auto-příchod z Event Logu)

Pro automatické rozpoznání času příchodu ze systémových logů:
```
pip install pywin32
```

## Soubory

| Soubor | Popis |
|--------|-------|
| `dochazka.pyw` | Hlavní aplikace |
| `config.py` | Konfigurace (fond, oběd, časy) |
| `database.py` | SQLite databáze |
| `calculator.py` | Výpočty týdne a měsíce |
| `utils.py` | Pomocné funkce |
| `tray.py` | Systémový tray |
| `eventlog.py` | Windows Event Log |
| `dochazka.db` | Databáze (vytvořena automaticky) |
