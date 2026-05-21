"""
test_single_card.py - Gyors helyi teszt, ntfy nélkül.

Használat:
    pip install -r requirements.txt
    python test_single_card.py
"""

from scraper import get_card_data
from scorer import calculate_score

TEST_CARDS = [
    {
        "name":   "Starmie V",
        "url":    "https://www.cardmarket.com/en/Pokemon/Products/Singles/Astral-Radiance/Starmie-V-V3-ASRTG13",
        "rarity": "Trainer Gallery",
    },
    {
        "name":   "Suicune V",
        "url":    "https://www.cardmarket.com/en/Pokemon/Products/Singles/Crown-Zenith/Suicune-V-CRZGG38",
        "rarity": "Galarian Gallery",
    },
]


def test_card(card: dict):
    name, url, rarity = card["name"], card["url"], card["rarity"]
    print(f"\n{'─'*55}")
    print(f"  🎴 {name}")
    print(f"  🔗 {url}")
    print(f"{'─'*55}")
    print("  ⏳ Lekérés... (3-10 mp várható)")

    data = get_card_data(url)

    if not data:
        print("  ❌ Sikertelen — 403 vagy hálózati hiba")
        print()
        print("  💡 MEGOLDÁS: A Cardmarket blokkolja a GitHub Actions")
        print("     IP-ket Cloudflare-rel. Három lehetőség:")
        print()
        print("  1) Regisztrálj Cardmarket Developer API-ra:")
        print("     https://www.cardmarket.com/en/Developer")
        print("     → App Token, App Secret, Access Token, Access Secret")
        print("     → Ezek GitHub Secrets-be kerülnek")
        print()
        print("  2) Futtasd LOKÁLISAN (saját gépedről):")
        print("     A te IP-d nem blokolt → működni fog")
        print()
        print("  3) Scraper proxy (pl. ScraperAPI.com — ingyenes tier)")
        return

    print()
    print("  📊 LEKÉRT ADATOK:")
    trend = data.get("trend")
    nm    = data.get("nm_trusted_price")
    print(f"     Trend ár:         €{trend}")
    print(f"     30 napos átlag:   €{data.get('avg_30d')}")
    print(f"     7 napos átlag:    €{data.get('avg_7d')}")
    print(f"     1 napos átlag:    €{data.get('avg_1d')}")
    print(f"     NM trusted ár:    €{nm}")
    print(f"     Van trusted NM:   {data.get('has_trusted_nm_seller')}")
    print(f"     NM db elérhető:   {data.get('available_nm_count')}")

    print()
    print("  🧮 SCORE:")
    result = calculate_score(name, data, rarity)

    if result is None:
        print("  ⏭️  Nem teljesíti az alapszűrőket")
        if trend and nm:
            disc = (trend - nm) / trend * 100
            print(f"     NM: €{nm:.2f} | Trend: €{trend:.2f} | {disc:.0f}% kedvezmény")
    else:
        s = result["score"]
        signal = "🔥 VÉTELI JELZÉS!" if result["buy_signal"] else "📊 Küszöb alatt"
        print(f"  {signal}")
        print(f"     Score: {s}/100")
        print(f"     {result['reason']}")


def main():
    print()
    print("="*55)
    print("  🧪 POKÉMON MONITOR — HELYI TESZT")
    print("="*55)

    for card in TEST_CARDS:
        test_card(card)

    print()
    print("="*55)
    print("  ✅ Teszt kész")
    print("="*55)
    print()


if __name__ == "__main__":
    main()
