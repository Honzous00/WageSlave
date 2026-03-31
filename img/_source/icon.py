import os
from PIL import Image

# Seznam standardních velikostí pro Windows ikonu
VELIKOSTI = [256, 48, 32, 16]
SLOZKA = "."  # Aktuální složka

def vytvor_stvercovy_obrazek(img, cilova_velikost):
    """
    Vezme obrázek a vloží ho doprostřed průhledného čtverce dané velikosti.
    Tím se opraví rozměry jako 16x17 na 16x16.
    """
    # Vytvoříme nové průhledné plátno (RGBA)
    platno = Image.new("RGBA", (cilova_velikost, cilova_velikost), (0, 0, 0, 0))
    
    # Proporcionálně změníme velikost originálu, aby se vešel do čtverce (zachová poměr stran)
    img.thumbnail((cilova_velikost, cilova_velikost), Image.Resampling.LANCZOS)
    
    # Spočítáme pozici pro vycentrování
    left = (cilova_velikost - img.width) // 2
    top = (cilova_velikost - img.height) // 2
    
    # Vložíme obrázek na plátno
    platno.paste(img, (left, top))
    return platno

# 1. Najdeme všechny unikátní základy názvů (vše před posledním podtržítkem)
zaklady = set()
for f in os.listdir(SLOZKA):
    if "_" in f and f.lower().endswith(".png"):
        # splitneme to odzadu podle prvního podtržítka (např. money_256.png -> money)
        zaklady.add(f.rsplit("_", 1)[0])

if not zaklady:
    print("Nenalezeny žádné soubory ve formátu 'nazev_velikost.png' (např. money_256.png)")

# 2. Pro každý základ sestavíme jednu ikonu
for zaklad in zaklady:
    print(f"Zpracovávám sadu pro ikonu: {zaklad}")
    seznam_obrazku = []
    
    try:
        for v in VELIKOSTI:
            cesta_png = f"{zaklad}_{v}.png"
            
            if os.path.exists(cesta_png):
                with Image.open(cesta_png) as img:
                    # Převedeme na RGBA a uděláme z toho dokonalý čtverec
                    stverec = vytvor_stvercovy_obrazek(img.convert("RGBA"), v)
                    seznam_obrazku.append(stverec)
            else:
                print(f"  ⚠️ Chybí velikost {v} (soubor {cesta_png} nenalezen)")

        if seznam_obrazku:
            # Uložení výsledného ICO souboru
            vystupni_ico = f"{zaklad}.ico"
            # ICO formát vyžaduje aspoň jeden obrázek, zbytek se přidá přes append_images
            seznam_obrazku[0].save(
                vystupni_ico, 
                format="ICO", 
                sizes=[(img.width, img.height) for img in seznam_obrazku],
                append_images=seznam_obrazku[1:]
            )
            print(f"  ✅ Úspěšně vytvořeno: {vystupni_ico}")
        else:
            print(f"  ❌ Žádné obrázky pro {zaklad} nebyly načteny.")

    except Exception as e:
        print(f"  🔥 Chyba při vytváření {zaklad}.ico: {e}")

print("\nHotovo!")