<p align="center">
  <img src="img/svg/money.svg" width="120" height="120" alt="WageSlave Logo">
</p>

<h1 align="center">WageSlave System</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Version-2.1.0-purple?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Privacy-Local_Only-green?style=for-the-badge" alt="Privacy">
  <img src="https://img.shields.io/badge/Cloud-None-blue?style=for-the-badge" alt="No Cloud">
</p>

<p align="center">
  <i>Moderní desktopová aplikace pro evidenci pracovní doby. Sleduj příchody, odchody, plnění týdenního fondu a měsíční bilanci – vše lokálně, bez cloudu.</i>
</p>

---

## Funkce

- **Automatický příchod** – při spuštění aplikace se zaznamená čas příchodu (odhadnutý z event logu systému)
- **Predikce odchodu** – live výpočet kdy musíš odejít, aby byl splněn týdenní fond hodin; pokud je pátek svátek nebo sick, automaticky přepočítá na předchozí pracovní den
- **Plánování výjimečných dnů** – záložka s měsíčním kalendářem pro zadávání státních svátků, dovolené a nemocenské; každý typ ovlivňuje fond a bilanci odlišně
- **Stažení státních svátků** – jedním klikem stáhne české svátky z veřejného API (date.nager.at) nebo použije vestavěný offline seznam (pevná data + Velikonoce)
- **Měsíční bilance** – přehled přesčasů a mínusů za aktuální měsíc se zohledněním výjimečných dnů
- **Systémový tray** – aplikace běží na pozadí, zavření okna ji neskryje, nekončí
- **Export CSV** – export záznamů za vybraný měsíc
- **Volba loga** – 6 variant ikon (purple, purple neon, money, money neon, slave, slave neon)
- **Automatické zálohy** – volitelná měsíční záloha DB a configu do AppData
- **Dark mode** – tmavé rozhraní včetně title baru

### Jak ovlivňují výjimečné dny fond a bilanci

| Typ            | Týdenní / měsíční fond | Hodiny v DB | Predikce odchodu          |
| -------------- | ---------------------- | ----------- | ------------------------- |
| Státní svátek  | Snížen o 8h            | Nezapisují  | Přesune na předchozí den  |
| Dovolená       | Zachován (8h splněno)  | 8h          | Pátek jako obvykle        |
| Nemocenská     | Snížen o 8h            | Nezapisují  | Přesune na předchozí den  |

### Varianty ikon

Aplikace nabízí 6 vizuálních stylů pro systémový tray a sidebar:

|                     Purple                      |                     Money                      |                     Slave                      |
| :---------------------------------------------: | :--------------------------------------------: | :--------------------------------------------: |
|   <img src="img/icon/purple.ico" width="32">    |   <img src="img/icon/money.ico" width="32">    |   <img src="img/icon/slave.ico" width="32">    |
|                 **Neon Purple**                 |                 **Neon Money**                 |                 **Neon Slave**                 |
| <img src="img/icon/purple_neon.ico" width="32"> | <img src="img/icon/money_neon.ico" width="32"> | <img src="img/icon/slave_neon.ico" width="32"> |

---

## Požadavky

- Windows 10 / 11
- Python 3.10+ (pouze pro spuštění skriptu, `.exe` verze Python nepotřebuje)

---

## Instalace a spuštění (skript)

```bash
# 1. Naklonuj nebo rozbal projekt
git clone https://github.com/Honzous00/WageSlave.git

# 2. Nainstaluj závislosti
pip install -r requirements.txt

# 3. Spusť aplikaci
py wageslave.pyw
```

---

## Build do .exe

```bash
build.bat
```

Výsledný soubor: `dist\WageSlave.exe`

Aplikace je zkompilována jako single-file executable – stačí zkopírovat `WageSlave.exe` kamkoliv, složka `img/` není potřeba (je součástí buildu).

---

## Struktura projektu

```
WageSlave/
├── wageslave.pyw       # Hlavní soubor aplikace
├── wageslave.spec      # PyInstaller konfigurace
├── build.bat           # Build skript
├── requirements.txt    # Python závislosti
│
├── config.py           # Konfigurace, AppData cesty
├── database.py         # SQLite vrstva (dochazka + special_days tabulky)
├── calculator.py       # Výpočty fondu, bilance, predikce
├── special_days.py     # Správa výjimečných dnů (svátky, dovolená, nemoc)
├── tray.py             # Systémový tray icon
├── utils.py            # Pomocné funkce (čas, formátování)
├── eventlog.py         # Čtení Windows event logu
│
└── img/
    ├── icon/           # .ico soubory (purple, money, slave + neon varianty)
    └── svg/            # .svg soubory (stejné varianty)
```

---

## Konfigurace

Nastavení se ukládají do `%APPDATA%\WageSlave\config.json` a jsou přístupná přímo v aplikaci přes záložku **Nastavení**.

| Parametr           | Výchozí | Popis                             |
| ------------------ | ------- | --------------------------------- |
| Týdenní fond hodin | 40      | Celkový počet hodin za týden      |
| Délka oběda        | 30 min  | Odečítá se po 6 hodinách práce    |
| Standardní příchod | 07:00   | Používá se pro predikci pátku     |
| Standardní odchod  | 15:30   | Cílový čas odchodu                |
| Složka databáze    | AppData | Lze přesměrovat na síťový disk    |
| Automatické zálohy | vypnuto | 1× měsíčně zazipuje DB + config   |
| Logo aplikace      | money   | Varianta ikony v sidebaru a trayi |

Databáze: `%APPDATA%\WageSlave\wageslave.db` (SQLite, dvě tabulky: `dochazka` + `special_days`)

Výjimečné dny (svátky, dovolená, nemocenská) se spravují přes záložku **Plánování** a ukládají se do tabulky `special_days` ve stejné databázi.

---

## Závislosti

| Balíček       | Účel                                                 |
| ------------- | ---------------------------------------------------- |
| `pillow`      | Načítání a resize ikon (.ico, .png), emoji rendering |
| `pystray`     | Systémový tray icon (Windows)                        |
| `pywin32`     | Windows event log, dark title bar                    |
| `resvg-py`    | SVG → PNG renderer (Rust binding, bez cairo)         |
| `pyinstaller` | Kompilace do .exe (pouze pro build)                  |

---

## Data a soukromí

Veškerá data jsou uložena **výhradně lokálně** v `%APPDATA%\WageSlave\`. Aplikace nevyužívá žádnou telemetrii ani cloudové služby.

Jediné volitelné síťové připojení: záložka **Plánování → Stáhnout svátky CZ** odešle jeden GET požadavek na `https://date.nager.at/api/v3/PublicHolidays/{rok}/CZ` pro stažení českých státních svátků. Akce je vždy iniciovaná uživatelem s potvrzovacím dialogem. Pokud API není dostupné, použije se vestavěný offline seznam.

---

## Verze

**v2.1.0** – 2026
