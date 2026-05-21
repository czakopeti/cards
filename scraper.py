"""
scraper.py - Cardmarket adatlekérés
Session alapú, cookie-kezeléssel, HTTP/2-vel
"""

import re
import time
import random
import httpx
from bs4 import BeautifulSoup
from config import (
    CARDMARKET_BASE, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX,
    MIN_SELLER_FEEDBACK
)

# Browser-szerű headerek
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language":  "en-GB,en;q=0.9,hu;q=0.8",
    "Accept-Encoding":  "gzip, deflate, br",
    "Connection":       "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":   "document",
    "Sec-Fetch-Mode":   "navigate",
    "Sec-Fetch-Site":   "none",
    "Sec-Fetch-User":   "?1",
    "Cache-Control":    "max-age=0",
}

# Globális session — egy futáson belül újrahasználjuk
_session: httpx.Client | None = None


def _get_session() -> httpx.Client:
    """
    Session létrehozása és inicializálása.
    Első látogatáskor felkeresi a főoldalt, hogy sütiket kapjon.
    """
    global _session
    if _session is not None:
        return _session

    print("  🌐 Cardmarket session inicializálása...")
    _session = httpx.Client(
        http2=True,
        headers=HEADERS,
        follow_redirects=True,
        timeout=30,
    )
    # Főoldal látogatás → sütik + session token
    try:
        resp = _session.get("https://www.cardmarket.com/en/Pokemon")
        if resp.status_code == 200:
            print("  ✅ Session OK")
        else:
            print(f"  ⚠️  Főoldal: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ⚠️  Session init hiba: {e}")
    time.sleep(random.uniform(2, 4))
    return _session


def _polite_delay():
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))


def _get_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    """HTML oldal lekérése session-nel, újrapróbálással."""
    session = _get_session()

    for attempt in range(retries):
        try:
            _polite_delay()
            # Referer beállítása — mintha a főoldalról kattintottunk volna
            headers_extra = {"Referer": "https://www.cardmarket.com/en/Pokemon"}
            resp = session.get(url, headers=headers_extra)

            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "lxml")

            elif resp.status_code == 403:
                wait = 30 * (attempt + 1)
                print(f"  ⛔ 403 (Cloudflare) — várakozás {wait}s (próba {attempt+1}/{retries})")
                time.sleep(wait)
                # Session újraindítása
                global _session
                _session = None
                session = _get_session()

            elif resp.status_code == 429:
                print(f"  ⏳ Rate limit — várakozás 90s")
                time.sleep(90)

            else:
                print(f"  ⚠️  HTTP {resp.status_code}: {url}")

        except httpx.RequestError as e:
            print(f"  ❌ Hálózati hiba ({attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(15)

    return None


# ── Segédfüggvények ──────────────────────────────────────────

def _parse_price(text: str) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text.strip())
    cleaned = cleaned.replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        v = float(cleaned)
        return v if v > 0 else None
    except ValueError:
        return None


def _parse_feedback(text: str) -> int:
    if not text:
        return 0
    text = text.strip().upper()
    m = re.match(r"^([\d.]+)(K?)$", text)
    if not m:
        return 0
    n = float(m.group(1))
    if m.group(2) == "K":
        n *= 1000
    return int(n)


# ── Fő adatlekérő ────────────────────────────────────────────

def get_card_data(card_url: str) -> dict | None:
    """
    Egy kártya Cardmarket oldalát dolgozza fel.
    Visszaad egy dict-et az árakkal és eladói adatokkal,
    vagy None-t ha az oldal nem érhető el.
    """
    soup = _get_page(card_url)
    if not soup:
        return None

    result = {
        "url":                 card_url,
        "trend":               None,
        "avg_30d":             None,
        "avg_7d":              None,
        "avg_1d":              None,
        "nm_trusted_price":    None,
        "has_trusted_nm_seller": False,
        "available_nm_count":  0,
        "estimated_sales_7d":  0,
    }

    # ── Ár-táblázat (Price Guide szekció) ──────────────────
    price_map = {
        "Price Trend":     "trend",
        "30-days average": "avg_30d",
        "7-days average":  "avg_7d",
        "1-day average":   "avg_1d",
    }

    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True)
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        for key, field in price_map.items():
            if key in label:
                result[field] = _parse_price(dd.get_text(strip=True))
                break

    # Fallback: keresés szöveges mintával
    if result["trend"] is None:
        page_text = soup.get_text(separator="\n")
        for key, field in price_map.items():
            m = re.search(rf"{re.escape(key)}\s*\n?\s*([\d,.\s€]+)", page_text)
            if m:
                result[field] = _parse_price(m.group(1))

    # ── Ajánlatok feldolgozása (NM / MT kondíció) ───────────
    nm_trusted = []
    nm_all = []

    # Próbáljuk megtalálni az ajánlatok táblát
    offers_table = (
        soup.find(id="offers-table")
        or soup.find("div", class_=re.compile(r"table|offer", re.I))
    )

    if offers_table:
        rows = (
            offers_table.find_all(class_=re.compile(r"^row", re.I))
            or offers_table.find_all("tr")
        )

        for row in rows:
            row_text = row.get_text(separator="|", strip=True)

            # Kondíció detektálása
            condition = ""
            cond_el = row.find(
                attrs={"title": re.compile(r"Near Mint|Mint", re.I)}
            ) or row.find(
                class_=re.compile(r"badge|condition", re.I)
            )
            if cond_el:
                condition = cond_el.get_text(strip=True).upper()

            if not condition:
                for c in ("NM", "MT"):
                    if f"|{c}|" in row_text or f" {c} " in row_text:
                        condition = c
                        break

            if condition not in ("NM", "MT", "NEAR MINT", "MINT"):
                continue

            # Eladói feedback
            feedback = 0
            for link in row.find_all("a", href=re.compile(r"/Users/")):
                lt = link.get_text(strip=True)
                fm = re.match(r"^([\d.]+K?)", lt, re.I)
                if fm:
                    feedback = _parse_feedback(fm.group(1))
                    break

            # Ár
            price = None
            for cls in (
                re.compile(r"price|fw-bold|font-weight-bold", re.I),
            ):
                for pt in row.find_all(class_=cls):
                    p = _parse_price(pt.get_text(strip=True))
                    if p and p > 1:
                        price = p
                        break
                if price:
                    break

            if price is None:
                pm = re.search(r"(\d[\d,.]*)[\s\u00a0]*€", row_text)
                if pm:
                    price = _parse_price(pm.group(1))

            if price is None:
                continue

            nm_all.append(price)
            result["available_nm_count"] += 1
            if feedback >= MIN_SELLER_FEEDBACK:
                nm_trusted.append(price)

    if nm_trusted:
        result["nm_trusted_price"] = min(nm_trusted)
        result["has_trusted_nm_seller"] = True

    result["estimated_sales_7d"] = max(
        result["available_nm_count"],
        5 if result["avg_7d"] else 0,
    )

    return result


def get_all_expansions() -> list[dict]:
    """Összes Pokémon expanzió Cardmarketről."""
    soup = _get_page(f"{CARDMARKET_BASE}/Expansions")
    if not soup:
        return []

    seen, expansions = set(), []
    for link in soup.find_all("a", href=re.compile(r"/Pokemon/Expansions/[^/]+$")):
        href = link.get("href", "")
        name = link.get_text(strip=True)
        slug = href.rstrip("/").split("/")[-1]
        if slug and slug not in seen and name:
            seen.add(slug)
            expansions.append({
                "name": name,
                "slug": slug,
                "url":  f"https://www.cardmarket.com{href}",
            })
    return expansions


def get_expansion_sir_cards(expansion_url: str) -> list[dict]:
    """Egy expanzió értékes (SIR/TG/GG) kártyái."""
    soup = _get_page(expansion_url)
    if not soup:
        return []

    keywords = [
        "Special Illustration", "Trainer Gallery",
        "Galarian Gallery", "Secret Rare", "Hyper Rare",
        "Illustration Rare",
    ]
    cards = []
    for link in soup.find_all("a", href=re.compile(r"/Pokemon/Products/Singles/")):
        href = link.get("href", "")
        name = link.get_text(strip=True)
        parent_text = (link.parent or link).get_text(separator=" ")
        rarity = next((k for k in keywords if k.lower() in parent_text.lower()), "")
        if rarity and name:
            cards.append({
                "name":   name,
                "url":    f"https://www.cardmarket.com{href}",
                "rarity": rarity,
            })
    return cards
