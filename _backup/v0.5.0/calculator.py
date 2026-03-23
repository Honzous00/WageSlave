from datetime import datetime, timedelta
from collections import defaultdict
import config
from utils import cas_na_minuty

def week_analysis(records, current_date):
    """
    Vrátí slovník s výsledky analýzy aktuálního týdne.
    records: seznam záznamů pro daný týden (n-tice z DB)
    current_date: datetime.date
    """
    # Seskupit záznamy podle data
    denni_zaznamy = defaultdict(list)
    for r in records:
        datum = datetime.strptime(r[2], "%Y-%m-%d").date()
        denni_zaznamy[datum].append(r)

    # Najdi pondělí tohoto týdne
    start_of_week = current_date - timedelta(days=current_date.weekday())
    days = [start_of_week + timedelta(days=i) for i in range(5)]  # pondělí–pátek

    skutecne_celkem = 0
    planovane_do_dneska = 0
    otevrene_dnes = None
    ted = datetime.now()

    for den in days:
        if den in denni_zaznamy:
            zaznamy_dne = denni_zaznamy[den]

            # Sečíst uzavřené minuty pro tento den
            celkem_minut_den = 0
            ma_otevreny = False
            otevreny_zaznam = None

            for z in zaznamy_dne:
                if z[4]:  # odchod je vyplněn
                    celkem_minut_den += z[5]
                else:
                    ma_otevreny = True
                    otevreny_zaznam = z

            # Připočítat do celkových statistik
            if den < current_date:
                # Minulý den - jen uzavřené minuty
                skutecne_celkem += celkem_minut_den
                planovane_do_dneska += celkem_minut_den
            elif den == current_date:
                # Dnešek
                skutecne_celkem += celkem_minut_den
                planovane_do_dneska += celkem_minut_den

                if ma_otevreny:
                    otevrene_dnes = otevreny_zaznam
                    prichod = otevrene_dnes[3]
                    obed = otevrene_dnes[6]

                    # Skutečnost od příchodu do teď
                    if prichod:
                        p_dt = datetime.combine(den, datetime.strptime(prichod, "%H:%M").time())
                        if ted > p_dt:
                            diff = int((ted - p_dt).total_seconds() / 60)
                            # Odečet oběda po 6 hodinách
                            if diff > 360 and obed:
                                diff -= config.OBED_MINUT
                            skutecne_celkem += max(0, diff)

                    # Plán pro otevřený den (od příchodu do standardního odchodu)
                    if prichod:
                        plan_otevreneho = (cas_na_minuty(config.STANDARDNI_ODCHOD) - cas_na_minuty(prichod)) - (config.OBED_MINUT if obed else 0)
                        if plan_otevreneho < 0:
                            plan_otevreneho = 0
                        planovane_do_dneska += plan_otevreneho
                # else: dnešek je celý uzavřený, nic dalšího
            else:
                # Budoucí den – nezahrnujeme do plánu do dneška, jen skutečnost (0)
                pass
        else:
            # Den bez záznamu
            if den < current_date:
                # Minulý den bez záznamu = 0
                pass
            elif den == current_date:
                # Dnešek bez záznamu: do plánu přidáme standardních 480 minut
                planovane_do_dneska += 8 * 60
            else:
                # Budoucí den – nic
                pass

    celkem_fond = config.TYDENNI_FOND_HODIN * 60
    zbyva = max(0, celkem_fond - skutecne_celkem)
    procenta = min(100, int((skutecne_celkem / celkem_fond) * 100)) if celkem_fond else 0

    # Výpočet odhadu pátku
    dnes_v_tydnu = current_date.weekday()
    ideal_k_dnes = (dnes_v_tydnu + 1) * 8 * 60  # ideální stav ke konci dneška
    rozdil = planovane_do_dneska - ideal_k_dnes  # kladný = náskok, záporný = skluz

    if dnes_v_tydnu == 4:  # dnes je pátek
        if otevrene_dnes is None:
            cas_patek = "✓ Hotovo"
        else:
            # Potřebujeme odpracovat do konce dne: zbyva (což je fond - skutečnost)
            prichod = otevrene_dnes[3]
            obed = otevrene_dnes[6]
            if prichod:
                prichod_min = cas_na_minuty(prichod)
                odchod_min = prichod_min + zbyva + (config.OBED_MINUT if obed else 0)
                if odchod_min < 24*60:
                    cas_patek = f"{int(odchod_min // 60):02d}:{int(odchod_min % 60):02d}"
                else:
                    cas_patek = "NESTÍHÁŠ!"
            else:
                cas_patek = "--:--"
    else:
        # Kolik musíme v pátek odpracovat, abychom splnili fond
        patkovy_fond = max(0, 8*60 - rozdil)
        odchod_min = cas_na_minuty(config.STANDARDNI_PRICHOD) + patkovy_fond + config.OBED_MINUT
        if odchod_min < 24*60:
            cas_patek = f"{int(odchod_min // 60):02d}:{int(odchod_min % 60):02d}"
        else:
            cas_patek = "NESTÍHÁŠ!"

    return {
        'skutecne_celkem': skutecne_celkem,
        'procenta': procenta,
        'cas_patek': cas_patek,
        'zbyva': zbyva,
        'otevrene_dnes': otevrene_dnes,
        'planovane_do_dneska': planovane_do_dneska,
    }


def month_balance(records, current_date):
    """
    Vypočítá měsíční konto (skutečnost - fond).
    records: seznam záznamů pro daný měsíc (datum, prichod, odchod, minut, obed)
    current_date: datetime.date
    """
    import calendar
    dnes = current_date
    prvni_den = dnes.replace(day=1)
    posledni_den = dnes.replace(day=calendar.monthrange(dnes.year, dnes.month)[1])

    uzavrene_mesic = defaultdict(int)
    otevrene_mesic = {}

    for r in records:
        datum = r[0]
        if r[2]:  # odchod je vyplněn
            uzavrene_mesic[datum] += r[3]
        else:
            otevrene_mesic[datum] = r

    skutecne_a_planovane = 0
    celkovy_fond_mesic = 0
    den = prvni_den

    while den <= posledni_den:
        if den.weekday() < 5:  # pracovní den
            celkovy_fond_mesic += 480
            datum_str = den.strftime("%Y-%m-%d")

            if den < dnes:
                skutecne_a_planovane += uzavrene_mesic.get(datum_str, 0)
            elif den == dnes:
                skutecne_a_planovane += uzavrene_mesic.get(datum_str, 0)
                if datum_str in otevrene_mesic:
                    r = otevrene_mesic[datum_str]
                    prichod = r[1]
                    if prichod:
                        p_dt = datetime.combine(dnes, datetime.strptime(prichod, "%H:%M").time())
                        ted = datetime.now()
                        if ted > p_dt:
                            odpracovano = int((ted - p_dt).total_seconds() / 60)
                            if odpracovano > 360:
                                odpracovano -= config.OBED_MINUT
                            skutecne_a_planovane += max(0, odpracovano)

                        ted_min = ted.hour * 60 + ted.minute
                        odchod_plan_min = cas_na_minuty(config.STANDARDNI_ODCHOD)
                        zbyva = max(0, odchod_plan_min - ted_min)
                        if (ted - p_dt).total_seconds() / 60 <= 360:
                            zbyva -= config.OBED_MINUT
                        skutecne_a_planovane += max(0, zbyva)
                else:
                    skutecne_a_planovane += 480
            else:  # budoucí den
                skutecne_a_planovane += 480
        den += timedelta(days=1)

    balance = skutecne_a_planovane - celkovy_fond_mesic
    return balance