"""
main.py - Napi monitoring futtatása
"""

import json
from pathlib import Path
from datetime import datetime

from scraper import get_card_data
from scorer import calculate_score
from notifier import send_buy_alert, send_daily_summary

WATCHLIST_PATH = Path('watchlist.json')


def load_watchlist() -> list[dict]:
    if not WATCHLIST_PATH.exists():
        print("❌ watchlist.json nem található!")
        return []
    with open(WATCHLIST_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('cards', [])


def run_daily_monitor():
    """Napi monitoring főfüggvénye"""
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"🚀 Pokémon Monitor - Napi scan")
    print(f"   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    cards = load_watchlist()
    if not cards:
        print("Watchlist üres. Futtasd a watchlist_manager.py --update parancsot.")
        return

    print(f"📋 {len(cards)} kártya ellenőrzése...\n")

    checked = 0
    alerts  = 0
    results = []

    for card in cards:
        name     = card.get('name', 'Ismeretlen')
        url      = card.get('url', '')
        rarity   = card.get('rarity', '')

        if not url:
            continue

        print(f"  🔍 {name}...", end=' ', flush=True)

        # Adatok lekérése
        data = get_card_data(url)
        checked += 1

        if not data:
            print("❌ Nem sikerült betölteni")
            continue

        # Score kalkuláció
        score_result = calculate_score(name, data, rarity)

        if score_result is None:
            nm = data.get('nm_trusted_price')
            trend = data.get('trend')
            if nm and trend:
                discount = (trend - nm) / trend * 100
                print(f"⏭️  NM: €{nm:.0f} | Trend: €{trend:.0f} | {discount:.0f}% le | Score: -")
            else:
                print("⏭️  Nincs elég adat")
            continue

        score = score_result['score']
        nm    = score_result['nm_price']
        trend = score_result['trend']
        disc  = score_result['discount']

        if score_result['buy_signal']:
            print(f"🔥 Score: {score}/100 | NM: €{nm:.0f} | Trend: €{trend:.0f} | {disc:.0f}% le")
            score_result['card_url'] = url
            send_buy_alert(name, score_result)
            alerts += 1
            results.append((score, name, score_result))
        else:
            print(f"📊 Score: {score}/100 | NM: €{nm:.0f} | Trend: €{trend:.0f} | {disc:.0f}% le")

    # Napi összefoglaló
    elapsed = (datetime.now() - start_time).seconds
    print(f"\n{'='*60}")
    print(f"✅ Kész! {checked} kártya ellenőrizve, {alerts} vételi jelzés")
    print(f"   Futási idő: {elapsed} másodperc")
    print(f"{'='*60}\n")

    # Ha volt vételi jelzés, kiírjuk rangsorba
    if results:
        print("🏆 TOP vételi jelzések ma:\n")
        for rank, (score, name, res) in enumerate(
            sorted(results, key=lambda x: x[0], reverse=True), 1
        ):
            print(f"  {rank}. {name}")
            print(f"     Score: {score}/100 | NM: €{res['nm_price']:.2f} | "
                  f"Trend: €{res['trend']:.2f} | {res['discount']}% kedvezmény")
            print(f"     {res['card_url']}\n")

    send_daily_summary(checked, alerts)


if __name__ == '__main__':
    run_daily_monitor()
