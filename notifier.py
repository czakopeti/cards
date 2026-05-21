"""
notifier.py - ntfy értesítések
Ha NTFY_TOPIC nincs beállítva, csak kiírja a konzolra (nem crashel).
"""

import os
import requests
from config import NTFY_BASE_URL


def _get_topic() -> str | None:
    """None-t ad vissza ha nincs beállítva — nem dob hibát."""
    return os.environ.get("NTFY_TOPIC") or None


def _get_priority(score: int) -> str:
    if score >= 90: return "urgent"
    if score >= 80: return "high"
    return "default"


def _get_emoji(score: int) -> str:
    if score >= 90: return "🔥🔥🔥"
    if score >= 80: return "⭐⭐"
    return "📊"


def _send(topic: str, title: str, body: str,
          priority: str = "default", tags: str = "bell") -> bool:
    try:
        resp = requests.post(
            f"{NTFY_BASE_URL}/{topic}",
            data=body.encode("utf-8"),
            headers={
                "Title":    title.encode("utf-8"),
                "Priority": priority,
                "Tags":     tags,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"  ⚠️  ntfy hiba: {e}")
        return False


def send_buy_alert(card_name: str, score_result: dict) -> bool:
    score   = score_result["score"]
    nm      = score_result["nm_price"]
    trend   = score_result["trend"]
    disc    = score_result["discount"]
    pokemon = score_result["pokemon"]
    url     = score_result.get("card_url", "")

    title = f"{_get_emoji(score)} VÉTEL: {card_name} | Score: {score}/100"
    body  = (
        f"Pokémon: {pokemon}\n"
        f"NM ár (megbízható eladó): €{nm:.2f}\n"
        f"Trend ár: €{trend:.2f}\n"
        f"Kedvezmény: {disc}% a trend alatt\n"
        f"\nPontok:\n"
        f"  Ár gap:    +{score_result['breakdown']['base_price_gap']:.0f}\n"
        f"  Karakter:  +{score_result['breakdown']['tier_bonus']}\n"
        f"  Ritkaság:  +{score_result['breakdown']['rarity_bonus']}\n"
        f"  Likviditás:+{score_result['breakdown']['liquidity']}\n"
        f"\n👉 {url}"
    )

    topic = _get_topic()
    if topic:
        return _send(topic, title, body, _get_priority(score), "moneybag,pokemon")
    else:
        print(f"\n{'='*55}")
        print(f"  {title}")
        print(body)
        print(f"{'='*55}\n")
        return True


def send_watchlist_update(new_cards: list[str]) -> bool:
    if not new_cards:
        return True
    title = f"🆕 Watchlist: {len(new_cards)} új kártya"
    body  = "Hozzáadva:\n" + "\n".join(f"• {c}" for c in new_cards[:10])
    if len(new_cards) > 10:
        body += f"\n...és még {len(new_cards)-10}"

    topic = _get_topic()
    if topic:
        return _send(topic, title, body, "low", "white_check_mark")
    else:
        print(f"\n{title}\n{body}\n")
        return True


def send_daily_summary(checked: int, alerts: int) -> bool:
    if alerts > 0:
        title = f"📈 Összefoglaló: {alerts} vételi jelzés ({checked} kártya)"
    else:
        title = f"✅ Scan kész: {checked} kártya, jelzés nincs"
    body = f"{checked} kártya ellenőrizve, {alerts} vételi jelzés"

    topic = _get_topic()
    if topic:
        return _send(topic, title, body, "low", "bar_chart")
    else:
        print(f"\n{title}\n")
        return True
