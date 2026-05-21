"""
scraper.py - Cardmarket adatlekérés BeautifulSoup-pal
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from config import (
    CARDMARKET_BASE, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX,
    MIN_SELLER_FEEDBACK
)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}


def _polite_delay():
    """Udvarias várakozás lekérések között"""
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))


def _get_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    """HTML oldal lekérése újrapróbálással"""
    for attempt in range(retries):
        try:
            _polite_delay()
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'lxml')
            elif response.status_code == 429:
                print(f"Rate limited. Várakozás 60 másodperc...")
                time.sleep(60)
            else:
                print(f"HTTP {response.status_code} a következő URL-en: {url}")
        except requests.RequestException as e:
            print(f"Hálózati hiba (próbálkozás {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(10)
    return None


def _parse_price(text: str) -> float | None:
    """'68,90 €' vagy '68.90 €' -> 68.90"""
    if not text:
        return None
    cleaned = re.sub(r'[^\d,.]', '', text.strip())
    cleaned = cleaned.replace(',', '.')
    # Ha több pont van, csak az utolsót tartjuk meg tizedes jelként
    parts = cleaned.split('.')
    if len(parts) > 2:
        cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_feedback(text: str) -> int:
    """'2K' -> 2000, '14K' -> 14000, '231' -> 231, '92K' -> 92000"""
    if not text:
        return 0
    text = text.strip().upper()
    match = re.match(r'^([\d.]+)(K?)$', text)
    if not match:
        return 0
    number = float(match.group(1))
    if match.group(2) == 'K':
        number *= 1000
    return int(number)


def get_card_data(card_url: str) -> dict | None:
    """
    Egy kártya oldalát szkrápeli a Cardmarketen.
    
    Visszaad egy dict-et:
    {
        'url': str,
        'trend': float,
        'avg_30d': float,
        'avg_7d': float,
        'avg_1d': float,
        'nm_trusted_price': float | None,
        'has_trusted_nm_seller': bool,
        'available_nm_count': int,
        'estimated_sales_7d': int
    }
    """
    soup = _get_page(card_url)
    if not soup:
        print(f"Nem sikerült betölteni: {card_url}")
        return None

    result = {
        'url': card_url,
        'trend': None,
        'avg_30d': None,
        'avg_7d': None,
        'avg_1d': None,
        'nm_trusted_price': None,
        'has_trusted_nm_seller': False,
        'available_nm_count': 0,
        'estimated_sales_7d': 0
    }

    # --- ÁRAK KINYERÉSE ---
    # Cardmarket a "Price Guide" szekciót különféle class-okkal jelöli
    # Próbálunk több szelektort is
    price_labels = {
        'Price Trend':       'trend',
        '30-days average':   'avg_30d',
        '7-days average':    'avg_7d',
        '1-day average':     'avg_1d',
    }

    # Megkeressük az összes <dt>/<dd> párt az oldalon
    for dt in soup.find_all('dt'):
        label = dt.get_text(strip=True)
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        for key, field in price_labels.items():
            if key in label:
                result[field] = _parse_price(dd.get_text(strip=True))
                break

    # Alternatív: ha a fentiek nem találtak, keressük a price-container osztályban
    if result['trend'] is None:
        containers = soup.find_all(class_=re.compile(r'price', re.I))
        for c in containers:
            text = c.get_text(separator=' ', strip=True)
            trend_match = re.search(r'Price Trend[^€\d]*([€\d,.\s]+)', text)
            if trend_match:
                result['trend'] = _parse_price(trend_match.group(1))
                break

    # --- AJÁNLATOK TÁBLÁJÁNAK FELDOLGOZÁSA ---
    nm_trusted_prices = []
    all_nm_prices = []

    # Az ajánlatok táblája általában "table-body" vagy hasonló ID-vel
    offers_section = (
        soup.find(id='offers-table') or
        soup.find(class_=re.compile(r'offers|table-body', re.I)) or
        soup.find('div', class_='table')
    )

    if offers_section:
        # Minden sor egy ajánlat
        rows = offers_section.find_all(class_=re.compile(r'^row', re.I)) or \
               offers_section.find_all('tr')

        for row in rows:
            row_text = row.get_text(separator='|', strip=True)

            # --- Kondíció ---
            condition = ''
            condition_tag = (
                row.find(class_=re.compile(r'badge|condition', re.I)) or
                row.find('span', title=re.compile(r'Near Mint|Mint|Excellent|Good|Light|Poor|Played', re.I))
            )
            if condition_tag:
                condition = condition_tag.get_text(strip=True).upper()
            # Fallback: keressük a szövegben
            if not condition:
                for cond in ['NM', 'MT', 'EX', 'GD', 'LP', 'PL', 'PO']:
                    if f'|{cond}|' in row_text or f' {cond} ' in row_text:
                        condition = cond
                        break

            # Csak NM és MT kártyák érdekelnek minket
            if condition not in ('NM', 'MT', 'NEAR MINT', 'MINT'):
                continue

            # --- Eladói feedback ---
            feedback = 0
            # A feedback szám általában a felhasználónév előtt áll linkként
            seller_links = row.find_all('a', href=re.compile(r'/Users/'))
            for link in seller_links:
                # A feedback szám általában a link szövege ELŐTT van
                prev = link.find_previous_sibling(text=True) or ''
                # Vagy a link tartalmazza mindkettőt
                link_text = link.get_text(strip=True)
                feedback_match = re.match(r'^([\d.]+K?)', link_text)
                if feedback_match:
                    feedback = _parse_feedback(feedback_match.group(1))
                    break
                # Ha az előző testvér tartalmazza
                fb_match = re.search(r'([\d.]+K)', str(prev))
                if fb_match:
                    feedback = _parse_feedback(fb_match.group(1))
                    break

            # --- Ár ---
            price = None
            price_tags = row.find_all(class_=re.compile(r'price|font-weight-bold|fw-bold', re.I))
            for pt in price_tags:
                p = _parse_price(pt.get_text(strip=True))
                if p and p > 0.5:  # Szűrjük a 0-s és értelmetlen értékeket
                    price = p
                    break
            # Fallback: regex az árra
            if price is None:
                price_match = re.search(r'(\d+[,.]?\d*)\s*€', row_text)
                if price_match:
                    price = _parse_price(price_match.group(1))

            if price is None:
                continue

            all_nm_prices.append(price)
            result['available_nm_count'] += 1

            # Megbízható eladó szűrő
            if feedback >= MIN_SELLER_FEEDBACK:
                nm_trusted_prices.append(price)

    # Eredmények összegzése
    if nm_trusted_prices:
        result['nm_trusted_price'] = min(nm_trusted_prices)
        result['has_trusted_nm_seller'] = True

    # Likviditás becslés: az elérhető NM ajánlatok száma + 7 napos átlag meglétéből
    result['estimated_sales_7d'] = result['available_nm_count']
    if result['avg_7d']:
        result['estimated_sales_7d'] = max(result['estimated_sales_7d'], 5)

    return result


def get_all_expansions() -> list[dict]:
    """
    Visszaadja az összes Pokémon expanzió listáját Cardmarketről.
    [{'name': '...', 'slug': '...', 'url': '...'}]
    """
    url = f"{CARDMARKET_BASE}/Expansions"
    soup = _get_page(url)
    if not soup:
        return []

    expansions = []
    # Az expanzió linkek általában /Pokemon/Expansions/ prefix-szel kezdődnek
    for link in soup.find_all('a', href=re.compile(r'/Pokemon/Expansions/[^/]+$')):
        href = link.get('href', '')
        name = link.get_text(strip=True)
        if href and name and 'Expansions' in href:
            slug = href.rstrip('/').split('/')[-1]
            expansions.append({
                'name': name,
                'slug': slug,
                'url': f"https://www.cardmarket.com{href}"
            })

    # Deduplikáció
    seen = set()
    unique = []
    for exp in expansions:
        if exp['slug'] not in seen:
            seen.add(exp['slug'])
            unique.append(exp)

    return unique


def get_expansion_sir_cards(expansion_url: str) -> list[dict]:
    """
    Egy expanzió SIR/TG/GG kártyáit adja vissza.
    [{'name': '...', 'url': '...', 'rarity': '...'}]
    """
    soup = _get_page(expansion_url)
    if not soup:
        return []

    valuable_keywords = [
        'Special Illustration', 'Trainer Gallery', 'Galarian Gallery',
        'Secret Rare', 'Hyper Rare', 'Illustration Rare'
    ]

    cards = []
    # Kártyák általában singles linkként jelennek meg
    for link in soup.find_all('a', href=re.compile(r'/Pokemon/Products/Singles/')):
        href = link.get('href', '')
        name = link.get_text(strip=True)

        # Ritkaság keresése a szülő elemben
        parent = link.parent
        rarity = ''
        if parent:
            parent_text = parent.get_text(separator=' ')
            for kw in valuable_keywords:
                if kw.lower() in parent_text.lower():
                    rarity = kw
                    break

        if rarity and name:
            cards.append({
                'name': name,
                'url': f"https://www.cardmarket.com{href}",
                'rarity': rarity
            })

    return cards
