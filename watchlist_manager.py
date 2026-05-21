"""
watchlist_manager.py - Watchlist automatikus frissítése új szettekkel
"""

import json
import re
from pathlib import Path
from scraper import get_all_expansions, get_expansion_sir_cards
from notifier import send_watchlist_update
from config import GOD_TIER, TIER_1, TIER_2, VALUABLE_RARITIES

WATCHLIST_PATH = Path('watchlist.json')

ALL_TIER_POKEMON = set(GOD_TIER + TIER_1 + TIER_2)


def load_watchlist() -> dict:
    """Watchlist betöltése JSON-ból"""
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'last_updated': '', 'known_expansions': [], 'cards': []}


def save_watchlist(data: dict):
    """Watchlist mentése JSON-ba"""
    from datetime import date
    data['last_updated'] = date.today().isoformat()
    with open(WATCHLIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Watchlist mentve: {len(data['cards'])} kártya")


def _pokemon_in_name(card_name: str) -> str | None:
    """Meghatározza hogy a kártya neve tartalmaz-e ismert Pokémont"""
    name_lower = card_name.lower()
    # God Tier elsőbbséget kap
    for pokemon in GOD_TIER:
        if pokemon.lower() in name_lower:
            return pokemon
    for pokemon in TIER_1:
        if pokemon.lower() in name_lower:
            return pokemon
    for pokemon in TIER_2:
        if pokemon.lower() in name_lower:
            return pokemon
    return None


def _card_already_in_watchlist(card_url: str, watchlist: dict) -> bool:
    """Ellenőrzi hogy a kártya már szerepel-e a watchlisten"""
    existing_urls = {c['url'] for c in watchlist.get('cards', [])}
    return card_url in existing_urls


def update_watchlist():
    """
    Fő frissítő függvény:
    1. Lekéri az összes Cardmarket expanziót
    2. Megkeresi az újakat (nem szerepelnek a known_expansions-ben)
    3. Az újak SIR/TG/GG kártyáit hozzáadja ha Tier-ben vannak
    4. ntfy értesítést küld az új kártyákról
    """
    print("🔍 Watchlist frissítés indul...")

    watchlist = load_watchlist()
    known_slugs = set(watchlist.get('known_expansions', []))

    # Összes expanzió lekérése
    all_expansions = get_all_expansions()
    print(f"📦 {len(all_expansions)} expanzió találva Cardmarketen")

    # Új expanziók szűrése
    new_expansions = [
        exp for exp in all_expansions
        if exp['slug'] not in known_slugs
    ]
    print(f"🆕 {len(new_expansions)} új expanzió észlelve")

    newly_added_cards = []

    for expansion in new_expansions:
        print(f"\n📖 Feldolgozás: {expansion['name']}")

        # SIR/TG/GG kártyák lekérése
        sir_cards = get_expansion_sir_cards(expansion['url'])
        print(f"   {len(sir_cards)} értékes kártya találva")

        for card in sir_cards:
            # Van-e Tier Pokémon a névben?
            pokemon = _pokemon_in_name(card['name'])
            if not pokemon:
                continue

            # Már szerepel a listán?
            if _card_already_in_watchlist(card['url'], watchlist):
                continue

            # Hozzáadás
            new_entry = {
                'name':    card['name'],
                'url':     card['url'],
                'rarity':  card['rarity'],
                'set':     expansion['name'],
                'notes':   f'Auto-hozzáadva: {pokemon} ({card["rarity"]})'
            }
            watchlist['cards'].append(new_entry)
            newly_added_cards.append(card['name'])
            print(f"   ✅ Hozzáadva: {card['name']}")

        # Expanzió jelölése feldolgozottként
        known_slugs.add(expansion['slug'])

    # Frissített adatok mentése
    watchlist['known_expansions'] = list(known_slugs)
    save_watchlist(watchlist)

    # Értesítés küldése ha volt változás
    if newly_added_cards:
        send_watchlist_update(newly_added_cards)
        print(f"\n🎯 {len(newly_added_cards)} új kártya került a watchlistre")
    else:
        print("\n😴 Nincs új kártya - watchlist naprakész")

    return newly_added_cards


def list_watchlist():
    """Kilistázza a jelenlegi watchlistet"""
    watchlist = load_watchlist()
    cards = watchlist.get('cards', [])
    print(f"\n📋 Jelenlegi watchlist ({len(cards)} kártya):")
    print("-" * 60)
    for i, card in enumerate(cards, 1):
        print(f"{i:3}. {card['name']:<35} [{card['rarity'][:20]}]")
        print(f"     {card.get('set','?'):<35} {card.get('notes','')}")
    print("-" * 60)


if __name__ == '__main__':
    import sys
    if '--update' in sys.argv:
        update_watchlist()
    elif '--list' in sys.argv:
        list_watchlist()
    else:
        print("Használat: python watchlist_manager.py [--update|--list]")
