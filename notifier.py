"""
notifier.py - ntfy.sh értesítések küldése
"""

import os
import requests
from config import NTFY_BASE_URL


def _get_topic() -> str:
    topic = os.environ.get('NTFY_TOPIC', '')
    if not topic:
        raise ValueError("NTFY_TOPIC environment variable nincs beállítva!")
    return topic


def _get_priority(score: int) -> str:
    if score >= 90: return 'urgent'
    if score >= 80: return 'high'
    return 'default'


def _get_emoji(score: int) -> str:
    if score >= 90: return '🔥🔥🔥'
    if score >= 80: return '⭐⭐'
    return '📊'


def send_buy_alert(card_name: str, score_result: dict) -> bool:
    """
    Vételi jelzés küldése ntfy-ra.
    """
    topic   = _get_topic()
    score   = score_result['score']
    nm      = score_result['nm_price']
    trend   = score_result['trend']
    disc    = score_result['discount']
    pokemon = score_result['pokemon']
    url     = score_result.get('card_url', '')

    emoji    = _get_emoji(score)
    priority = _get_priority(score)

    title = f"{emoji} VÉTEL: {card_name} | Score: {score}/100"

    body = (
        f"Pokémon: {pokemon}\n"
        f"NM ár (megbízható eladó): €{nm:.2f}\n"
        f"Trend ár: €{trend:.2f}\n"
        f"Kedvezmény: {disc}% a trend alatt\n"
        f"\nRészletezés:\n"
        f"  Árkülönbség: +{score_result['breakdown']['base_price_gap']:.0f} pont\n"
        f"  Karakter bónusz: +{score_result['breakdown']['tier_bonus']} pont\n"
        f"  Ritkaság bónusz: +{score_result['breakdown']['rarity_bonus']} pont\n"
        f"  Likviditás: +{score_result['breakdown']['liquidity']} pont\n"
        f"\n👉 {url}"
    )

    try:
        resp = requests.post(
            f"{NTFY_BASE_URL}/{topic}",
            data=body.encode('utf-8'),
            headers={
                'Title':    title.encode('utf-8'),
                'Priority': priority,
                'Tags':     'moneybag,pokemon',
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Értesítési hiba: {e}")
        return False


def send_watchlist_update(new_cards: list[str]) -> bool:
    """
    Értesítés új kártyák watchlistre kerülésekor.
    """
    if not new_cards:
        return True

    topic = _get_topic()
    title = f"🆕 Watchlist frissítve: {len(new_cards)} új kártya"
    body  = "Hozzáadva:\n" + "\n".join(f"• {c}" for c in new_cards[:10])
    if len(new_cards) > 10:
        body += f"\n...és még {len(new_cards)-10} kártya"

    try:
        resp = requests.post(
            f"{NTFY_BASE_URL}/{topic}",
            data=body.encode('utf-8'),
            headers={
                'Title':    title.encode('utf-8'),
                'Priority': 'low',
                'Tags':     'white_check_mark',
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Értesítési hiba: {e}")
        return False


def send_daily_summary(checked: int, alerts: int) -> bool:
    """
    Napi összefoglaló - csak ha volt eredmény.
    """
    topic = _get_topic()
    if alerts > 0:
        title = f"📈 Napi összefoglaló: {alerts} vételi jelzés"
        emoji = "🎯"
    else:
        title = f"✅ Napi scan kész: {checked} kártya, jelzés nincs"
        emoji = "😴"

    body = f"{emoji} {checked} kártya ellenőrizve\n{alerts} vételi jelzés"

    try:
        resp = requests.post(
            f"{NTFY_BASE_URL}/{topic}",
            data=body.encode('utf-8'),
            headers={
                'Title':    title.encode('utf-8'),
                'Priority': 'low' if alerts == 0 else 'default',
                'Tags':     'bar_chart',
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Értesítési hiba: {e}")
        return False
