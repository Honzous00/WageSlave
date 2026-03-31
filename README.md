<p align="center">
  <img src="img/svg/money.svg" width="120" height="120" alt="WageSlave Logo">
</p>

<h1 align="center">WageSlave System</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Version-2.0.0-purple?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Privacy-Local_Only-green?style=for-the-badge" alt="Privacy">
</p>

<p align="center">
  <i>Moderní desktopová aplikace pro evidenci pracovní doby. Sleduj příchody, odchody, plnění týdenního fondu a měsíční bilanci – vše lokálně, bez cloudu.</i>
</p>

---

## Funkce

- **Automatický příchod** – při spuštění aplikace se zaznamená čas příchodu (odhadnutý z event logu systému)
- **Predikce odchodu** – live výpočet kdy musíš odejít, aby byl splněn týdenní fond hodin
- **Měsíční bilance** – přehled přesčasů a mínusů za aktuální měsíc
- **Systémový tray** – aplikace běží na pozadí, zavření okna ji neskryje, nekončí
- **Export CSV** – export záznamů za vybraný měsíc
- **Volba loga** – 6 variant ikon (purple, purple neon, money, money neon, slave, slave neon)
- **Automatické zálohy** – volitelná měsíční záloha DB a configu do AppData
- **Dark mode** – tmavé rozhraní včetně title baru

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
├── database.py         # SQLite vrstva
├── calculator.py       # Výpočty fondu, bilance, predikce
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

Databáze: `%APPDATA%\WageSlave\wageslave.db` (SQLite)

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

Veškerá data jsou uložena **výhradně lokálně** v `%APPDATA%\WageSlave\`. Aplikace nevyužívá žádné síťové připojení, telemetrii ani cloudové služby.

---

## Verze

**v2.0.0** – 2026
