from datetime import datetime, timedelta
from collections import defaultdict
import config
from utils import cas_na_minuty


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: načti výjimečné dny pro rozsah
# ─────────────────────────────────────────────────────────────────────────────

def _load_special_days(date_from, date_to) -> dict:
    """Vrátí dict {datetime.date: typ} pro dané rozmezí."""
    try:
        import special_days
        raw = special_days.fetch_range(
            date_from.strftime("%Y-%m-%d"),
            date_to.strftime("%Y-%m-%d")
        )
        result = {}
        for datum_str, (typ, _) in raw.items():
            try:
                result[datetime.strptime(datum_str, "%Y-%m-%d").date()] = typ
            except ValueError:
                pass
        return result
    except Exception:
        return {}


def _load_special_day_note(date_obj) -> str:
    """Vrátí poznámku / název svátku pro dané datum, nebo prázdný string."""
    try:
        import special_days
        row = special_days.get(date_obj.strftime("%Y-%m-%d"))
        return row[2] if row and row[2] else ""
    except Exception:
        return ""


# Typy dnů, které snižují fond (nepíší se hodiny do DB)
FOND_REDUCING = ("sick", "holiday")
# Typy dnů, které zachovávají fond a přičítají hodiny (dovolená)
FOND_KEEPING  = ("vacation",)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: najdi předchozí pracovní den (zpětně přeskočí volné dny)
# ─────────────────────────────────────────────────────────────────────────────

def _najdi_predchozi_pracovni_den(od_dne, special, start_of_week):
    """
    Vrátí (date, label_str) pro nejbližší předchozí pracovní den
    který není volno (sick/holiday). Hledá jen v rámci aktuálního týdne.
    label_str je např. 'Čt' nebo 'St'.
    """
    den_names = {0: "Po", 1: "Út", 2: "St", 3: "Čt", 4: "Pá"}
    den = od_dne - timedelta(days=1)
    while den >= start_of_week:
        if den.weekday() < 5:  # pracovní den
            typ = special.get(den)
            if typ not in FOND_REDUCING:
                return den, den_names.get(den.weekday(), "")
        den -= timedelta(days=1)
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
#  TÝDENNÍ ANALÝZA
# ─────────────────────────────────────────────────────────────────────────────

def week_analysis(records, current_date):
    denni_zaznamy = defaultdict(list)
    for r in records:
        datum = datetime.strptime(r[2], "%Y-%m-%d").date()
        denni_zaznamy[datum].append(r)

    start_of_week = current_date - timedelta(days=current_date.weekday())
    days = [start_of_week + timedelta(days=i) for i in range(5)]

    # Načti výjimečné dny pro celý týden
    special = _load_special_days(start_of_week, start_of_week + timedelta(days=4))

    skutecne_celkem = 0
    planovane_do_dneska = 0
    otevrene_dnes = None
    ted = datetime.now()

    # Fond snižují: sick + holiday
    fond_reducing_tyden = sum(1 for d in days if special.get(d) in FOND_REDUCING)
    celkem_fond = max(0, config.TYDENNI_FOND_HODIN * 60 - fond_reducing_tyden * 8 * 60)

    for den in days:
        day_type = special.get(den)

        if day_type in FOND_REDUCING:
            # Sick nebo svátek: fond snížen výše, hodiny se nepřičítají, přeskočíme
            continue

        if day_type in FOND_KEEPING:
            # Dovolená: fond zachován, počítá se jako plný den (jen do current_date)
            if den <= current_date:
                skutecne_celkem += 8 * 60
                planovane_do_dneska += 8 * 60
            continue

        # Standardní pracovní den
        if den in denni_zaznamy:
            zaznamy_dne = denni_zaznamy[den]
            celkem_minut_den = 0
            ma_otevreny = False
            otevreny_zaznam = None

            for z in zaznamy_dne:
                if z[4]:
                    celkem_minut_den += z[5]
                else:
                    ma_otevreny = True
                    otevreny_zaznam = z

            if den < current_date:
                skutecne_celkem += celkem_minut_den
                planovane_do_dneska += celkem_minut_den
            elif den == current_date:
                skutecne_celkem += celkem_minut_den
                planovane_do_dneska += celkem_minut_den

                if ma_otevreny:
                    otevrene_dnes = otevreny_zaznam
                    prichod = otevrene_dnes[3]
                    obed = otevrene_dnes[6]

                    if prichod:
                        p_dt = datetime.combine(den, datetime.strptime(prichod, "%H:%M").time())
                        if ted > p_dt:
                            diff = int((ted - p_dt).total_seconds() / 60)
                            if diff > 360 and obed:
                                diff -= config.OBED_MINUT
                            skutecne_celkem += max(0, diff)

                    if prichod:
                        plan = (cas_na_minuty(config.STANDARDNI_ODCHOD) - cas_na_minuty(prichod)) \
                               - (config.OBED_MINUT if obed else 0)
                        planovane_do_dneska += max(0, plan)
        else:
            if den == current_date:
                planovane_do_dneska += 8 * 60

    zbyva = max(0, celkem_fond - skutecne_celkem)
    procenta = min(100, int((skutecne_celkem / celkem_fond) * 100)) if celkem_fond else 100

    dnes_v_tydnu = current_date.weekday()
    dnes_typ = special.get(current_date)

    # Ideální fond do dneška: bez fond-reducing dnů do dneška
    reducing_do_dneska = sum(
        1 for i in range(dnes_v_tydnu + 1)
        if special.get(start_of_week + timedelta(days=i)) in FOND_REDUCING
    )
    ideal_k_dnes = (dnes_v_tydnu + 1 - reducing_do_dneska) * 8 * 60
    rozdil = planovane_do_dneska - ideal_k_dnes

    # ── Sestavení výsledku predikce odchodu ───────────────────────────────────
    # cas_patek: HH:MM / "Nyní (HH:MM)" / "✓ Hotovo" / "NESTÍHÁŠ!" / "Volno"
    # pred_den:  date objekt — kdy predikujeme odchod (pátek nebo předchozí pracovní den)
    # pred_label: textový popis ("Pá", "Čt (svátek)", "St (nemocenská)" …)

    patek = start_of_week + timedelta(days=4)
    patek_typ = special.get(patek)

    def _spocitej_odchod_pro_den(cil_den, otevreny, rozdil_minut):
        """Vypočte čas odchodu pro zadaný den (pátek nebo náhradní)."""
        patkovy_fond = max(0, 8 * 60 - rozdil_minut)
        if otevreny and otevreny[3] and cil_den == current_date:
            prichod_str = otevreny[3]
        else:
            prichod_str = config.STANDARDNI_PRICHOD
        odchod_min = cas_na_minuty(prichod_str) + patkovy_fond
        if patkovy_fond > 360:
            odchod_min += config.OBED_MINUT
        if odchod_min < 24 * 60:
            return f"{int(odchod_min // 60):02d}:{int(odchod_min % 60):02d}"
        return "NESTÍHÁŠ!"

    den_names = {0: "Po", 1: "Út", 2: "St", 3: "Čt", 4: "Pá"}
    typ_labels = {"holiday": "svátek", "sick": "nemocenská", "vacation": "dovolená"}

    if dnes_v_tydnu == 4:
        # ── Dnes je pátek ─────────────────────────────────────────────────────
        if dnes_typ in FOND_REDUCING:
            # Dnes je pátek a je volno → hledej předchozí pracovní den
            nahradni_den, nahradni_lbl = _najdi_predchozi_pracovni_den(current_date, special, start_of_week)
            if nahradni_den:
                typ_popis = typ_labels.get(dnes_typ, "volno")
                pred_label = f"{nahradni_lbl} (pá – {typ_popis})"
                cas_patek = _spocitej_odchod_pro_den(nahradni_den, otevrene_dnes, rozdil)
                pred_den = nahradni_den
            else:
                cas_patek = "Volno"
                pred_den = patek
                pred_label = "Pá"
        elif dnes_typ in FOND_KEEPING:
            cas_patek = "Volno"
            pred_den = patek
            pred_label = "Pá (dovolená)"
        elif otevrene_dnes is None:
            cas_patek = "✓ Hotovo"
            pred_den = patek
            pred_label = "Pá"
        else:
            prichod = otevrene_dnes[3]
            obed = otevrene_dnes[6]
            pred_den = patek
            pred_label = "Pá"
            if prichod:
                prichod_min = cas_na_minuty(prichod)
                odchod_min = prichod_min + zbyva + (config.OBED_MINUT if obed else 0)
                now_min = ted.hour * 60 + ted.minute
                odchod_min = max(odchod_min, now_min)
                if odchod_min < 24 * 60:
                    if zbyva == 0:
                        cas_patek = f"Nyní ({int(odchod_min // 60):02d}:{int(odchod_min % 60):02d})"
                    else:
                        cas_patek = f"{int(odchod_min // 60):02d}:{int(odchod_min % 60):02d}"
                else:
                    cas_patek = "NESTÍHÁŠ!"
            else:
                cas_patek = "--:--"
    else:
        # ── Nejsme v pátek ────────────────────────────────────────────────────
        if patek_typ in FOND_REDUCING:
            # Pátek je volno (svátek/sick) → hledej předchozí pracovní den od pátku
            nahradni_den, nahradni_lbl = _najdi_predchozi_pracovni_den(patek, special, start_of_week)
            if nahradni_den and nahradni_den >= current_date:
                # Náhradní den je ještě v budoucnosti (nebo dnes)
                typ_popis = typ_labels.get(patek_typ, "volno")
                pred_label = f"{nahradni_lbl} (pá – {typ_popis})"
                cas_patek = _spocitej_odchod_pro_den(nahradni_den, otevrene_dnes, rozdil)
                pred_den = nahradni_den
            elif nahradni_den and nahradni_den < current_date:
                # Náhradní den už proběhl — fond by měl být splněn
                cas_patek = "✓ Hotovo"
                pred_den = nahradni_den
                typ_popis = typ_labels.get(patek_typ, "volno")
                pred_label = f"{nahradni_lbl} (pá – {typ_popis})"
            else:
                cas_patek = "Volno"
                pred_den = patek
                pred_label = "Pá"
        elif patek_typ in FOND_KEEPING:
            # Pátek je dovolená → predikujeme normálně (fond zachován)
            pred_den = patek
            pred_label = "Pá (dovolená)"
            cas_patek = _spocitej_odchod_pro_den(patek, otevrene_dnes, rozdil)
        elif dnes_typ in FOND_REDUCING:
            # Dnes je volno, pátek je normální → predikce pátku standardně
            pred_den = patek
            pred_label = "Pá"
            cas_patek = _spocitej_odchod_pro_den(patek, None, rozdil)
        else:
            pred_den = patek
            pred_label = "Pá"
            cas_patek = _spocitej_odchod_pro_den(patek, otevrene_dnes, rozdil)

    return {
        'skutecne_celkem': skutecne_celkem,
        'procenta': procenta,
        'cas_patek': cas_patek,
        'pred_label': pred_label,   # nové: "Pá", "Čt (pá – svátek)" apod.
        'pred_den': pred_den,       # nové: date objekt predikovaného dne
        'zbyva': zbyva,
        'otevrene_dnes': otevrene_dnes,
        'planovane_do_dneska': planovane_do_dneska,
        'celkem_fond': celkem_fond,
        'fond_reducing_tyden': fond_reducing_tyden,
        'special': special,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  MĚSÍČNÍ BILANCE
# ─────────────────────────────────────────────────────────────────────────────

def month_balance(records, current_date):
    import calendar
    dnes = current_date
    prvni_den = dnes.replace(day=1)
    posledni_den = dnes.replace(day=calendar.monthrange(dnes.year, dnes.month)[1])

    special = _load_special_days(prvni_den, posledni_den)

    uzavrene_mesic = defaultdict(int)
    otevrene_mesic = {}

    for r in records:
        datum = r[0]
        if r[2]:
            uzavrene_mesic[datum] += r[3]
        else:
            otevrene_mesic[datum] = r

    skutecne_a_planovane = 0
    celkovy_fond_mesic = 0
    den = prvni_den

    while den <= posledni_den:
        if den.weekday() < 5:
            day_type = special.get(den)

            if day_type in FOND_REDUCING:
                # Sick nebo svátek: fond se sníží (nepřičítáme 480), hodiny = 0
                pass

            elif day_type in FOND_KEEPING:
                # Dovolená: fond zachován + den se počítá jako odpracovaný (8h)
                celkovy_fond_mesic += 480
                skutecne_a_planovane += 480

            else:
                # Standardní den
                celkovy_fond_mesic += 480
                datum_str = den.strftime("%Y-%m-%d")

                if den < dnes:
                    skutecne_a_planovane += uzavrene_mesic.get(datum_str, 0)
                elif den == dnes:
                    skutecne_a_planovane += uzavrene_mesic.get(datum_str, 0)

                    if datum_str in otevrene_mesic:
                        r = otevrene_mesic[datum_str]
                        prichod = r[1]
                        obed = r[4] if len(r) > 4 else 1
                        if prichod:
                            p_dt = datetime.combine(dnes, datetime.strptime(prichod, "%H:%M").time())
                            ted = datetime.now()
                            if ted > p_dt:
                                odpracovano = int((ted - p_dt).total_seconds() / 60)
                                if odpracovano > 360 and obed:
                                    odpracovano -= config.OBED_MINUT
                                skutecne_a_planovane += max(0, odpracovano)
                            ted_min = ted.hour * 60 + ted.minute
                            odchod_plan_min = cas_na_minuty(config.STANDARDNI_ODCHOD)
                            zbyva = max(0, odchod_plan_min - ted_min)
                            elapsed_raw = (ted - p_dt).total_seconds() / 60
                            if elapsed_raw <= 360 and obed:
                                zbyva = max(0, zbyva - config.OBED_MINUT)
                            skutecne_a_planovane += zbyva
                    elif datum_str not in uzavrene_mesic:
                        skutecne_a_planovane += 480
                else:
                    skutecne_a_planovane += 480

        den += timedelta(days=1)

    return skutecne_a_planovane - celkovy_fond_mesic
