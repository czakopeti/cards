"""
scorer.py - Investment Score kalkulátor
"""

from config import (
    GOD_TIER, TIER_1, TIER_2, SKIP_LIST,
    VALUABLE_RARITIES, SCORE_WEIGHTS,
    MIN_DISCOUNT_RATIO, MIN_SALES_7D,
    MAX_CARD_PRICE_EUR, MIN_SCORE
)


def _identify_pokemon(card_name: str) -> str | None:
    """
    Kártya nevéből azonosítja a Pokémont.
    'Starmie V TG13' -> 'Starmie'
    'Charizard ex SIR' -> 'Charizard'
    """
    # Töröljük a közismert suffix-eket
    clean = card_name
    for suffix in [' ex', ' V ', ' VMAX', ' VSTAR', ' GX', ' EX',
                   ' SIR', ' TG', ' GG', "'s ", ' &']:
        clean = clean.replace(suffix, ' ')

    # Az első szó általában a Pokémon neve
    first_word = clean.strip().split()[0] if clean.strip() else ''
    return first_word if first_word else None


def _get_tier_bonus(pokemon_name: str) -> int | None:
    """
    Visszaadja a tier bónuszt, vagy None-t ha nem érdekes.
    """
    if not pokemon_name:
        return None
    if pokemon_name in SKIP_LIST:
        return None

    # Pontos egyezés
    if pokemon_name in GOD_TIER:
        return SCORE_WEIGHTS['god_tier']
    if pokemon_name in TIER_1:
        return SCORE_WEIGHTS['tier_1']
    if pokemon_name in TIER_2:
        return SCORE_WEIGHTS['tier_2']

    # Részleges egyezés (pl. "Charizard" szerepel a névben)
    name_lower = pokemon_name.lower()
    for p in GOD_TIER:
        if p.lower() in name_lower:
            return SCORE_WEIGHTS['god_tier']
    for p in TIER_1:
        if p.lower() in name_lower:
            return SCORE_WEIGHTS['tier_1']
    for p in TIER_2:
        if p.lower() in name_lower:
            return SCORE_WEIGHTS['tier_2']

    return None  # Nem ismert Pokémon -> kihagyjuk


def _get_rarity_bonus(rarity: str) -> int:
    """SIR/TG/GG kártyákra extra pont"""
    rarity_lower = rarity.lower()
    if any(r.lower() in rarity_lower for r in ['special illustration', 'trainer gallery', 'galarian gallery']):
        return SCORE_WEIGHTS['rarity_sir']
    return SCORE_WEIGHTS['rarity_other']


def _get_liquidity_bonus(estimated_sales: int) -> int:
    """Likviditási pont"""
    if estimated_sales >= 10:
        return SCORE_WEIGHTS['liquidity_high']
    if estimated_sales >= MIN_SALES_7D:
        return SCORE_WEIGHTS['liquidity_ok']
    return 0


def calculate_score(
    card_name: str,
    card_data: dict,
    rarity: str = ''
) -> dict | None:
    """
    Kiszámítja az Investment Score-t.
    
    Visszaad:
    {
        'score': int (0-100),
        'buy_signal': bool,
        'breakdown': dict,
        'reason': str
    }
    Vagy None ha a kártya nem felel meg az alapszűrőknek.
    """

    # --- KAPU 1: Van-e megbízható NM eladó? ---
    if not card_data.get('has_trusted_nm_seller'):
        return None  # Nincs megbízható NM ajánlat

    nm_price = card_data.get('nm_trusted_price')
    trend = card_data.get('trend')

    if not nm_price or not trend:
        return None  # Nincs elég adat

    # --- KAPU 2: Ár a maximumon belül? ---
    if nm_price > MAX_CARD_PRICE_EUR:
        return None  # Drágább mint €100

    # --- KAPU 3: Minimális kedvezmény (legalább 20% a trend alatt) ---
    if nm_price >= trend * (1 - MIN_DISCOUNT_RATIO):
        return None  # Nem elég alulértékelt

    # --- KAPU 4: Likviditás ---
    sales_7d = card_data.get('estimated_sales_7d', 0)
    if sales_7d < MIN_SALES_7D:
        return None  # Nem elég likvid

    # --- KAPU 5: Karakter ---
    pokemon = _identify_pokemon(card_name)
    tier_bonus = _get_tier_bonus(pokemon)
    if tier_bonus is None:
        return None  # Nem ismert / nem érdekes Pokémon

    # --- PONTOZÁS ---
    discount_ratio = (trend - nm_price) / trend
    base_score = min(discount_ratio * 100, SCORE_WEIGHTS['base_max'])

    rarity_bonus    = _get_rarity_bonus(rarity)
    liquidity_bonus = _get_liquidity_bonus(sales_7d)

    total = int(base_score + tier_bonus + rarity_bonus + liquidity_bonus)
    total = max(0, min(100, total))

    breakdown = {
        'base_price_gap': round(base_score, 1),
        'tier_bonus':     tier_bonus,
        'rarity_bonus':   rarity_bonus,
        'liquidity':      liquidity_bonus,
        'total':          total
    }

    tier_name = (
        'GOD TIER' if tier_bonus == SCORE_WEIGHTS['god_tier'] else
        'TIER 1'   if tier_bonus == SCORE_WEIGHTS['tier_1'] else
        'TIER 2'
    )

    reason = (
        f"{pokemon} ({tier_name}) | "
        f"NM: €{nm_price:.2f} | "
        f"Trend: €{trend:.2f} | "
        f"Kedvezmény: {discount_ratio*100:.0f}%"
    )

    return {
        'score':      total,
        'buy_signal': total >= MIN_SCORE,
        'breakdown':  breakdown,
        'reason':     reason,
        'pokemon':    pokemon,
        'nm_price':   nm_price,
        'trend':      trend,
        'discount':   round(discount_ratio * 100, 1)
    }
