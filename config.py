# ============================================================
# POKÉMON MONITOR - CONFIG
# ============================================================

# --- KARAKTER TIER LISTÁK ---

GOD_TIER = [
    "Charizard", "Pikachu", "Umbreon"
]

TIER_1 = [
    "Gengar", "Mewtwo", "Rayquaza", "Lugia",
    "Sylveon", "Espeon", "Vaporeon", "Glaceon",
    "Leafeon", "Flareon", "Jolteon", "Eevee",
    "Gardevoir", "Starmie", "Suicune",
    "Mew", "Celebi", "Latias", "Latios",
    "Misty"  # Trainer + ikonikus Pokémon kombó
]

TIER_2 = [
    "Blastoise", "Venusaur", "Dragonite",
    "Greninja", "Lucario", "Garchomp",
    "Snorlax", "Mewtwo", "Giratina",
    "Dialga", "Palkia", "Arceus",
    "Ho-Oh", "Entei", "Raikou", "Volcarona",
    "Tyranitar", "Salamence", "Absol",
    "Darkrai", "Cynthia"  # Trainer ikonnal
]

# Ezeket soha ne vegye fel a watchlistbe
SKIP_LIST = [
    "Sunbrella", "Dedenne", "Pachirisu",
    "Bidoof", "Rattata", "Caterpie"
]

# --- RITKASÁGI SZINTEK ---

VALUABLE_RARITIES = [
    "Special Illustration Rare",
    "Illustration Rare",
    "Trainer Gallery",
    "Galarian Gallery",
    "Secret Rare",
    "Hyper Rare",
    "Gold Rare"
]

# --- SZŰRÉSI KÜSZÖBÖK ---

MIN_SELLER_FEEDBACK  = 500    # Megbízható eladó minimuma
MIN_SALES_7D         = 5      # Minimális 7 napos eladásszám (likviditás)
MIN_DISCOUNT_RATIO   = 0.20   # Legalább 20%-kal a trend alatt legyen
MAX_CARD_PRICE_EUR   = 100    # Maximum belépési ár
MIN_SCORE            = 75     # Ennél alacsonyabb score → nem küldünk értesítést

# --- NTFY BEÁLLÍTÁSOK ---
# A NTFY_TOPIC értéket GitHub Secrets-ben kell tárolni
# Lokális teszteléshez: export NTFY_TOPIC="sajat-topik-nevem"
NTFY_BASE_URL = "https://ntfy.sh"

# --- CARDMARKET ---
CARDMARKET_BASE = "https://www.cardmarket.com/en/Pokemon"
REQUEST_DELAY_MIN = 3   # másodperc - udvarias scraping
REQUEST_DELAY_MAX = 7

# --- PONTSZÁM KALKULÁCIÓ ---
SCORE_WEIGHTS = {
    "base_max":       50,  # Árkülönbségből max pont
    "god_tier":       40,  # God tier karakter bónusz
    "tier_1":         30,  # Tier 1 bónusz
    "tier_2":         15,  # Tier 2 bónusz
    "rarity_sir":     10,  # SIR/TG/GG bónusz
    "rarity_other":    5,  # Egyéb ritka bónusz
    "liquidity_high": 10,  # >= 10 eladás/hét
    "liquidity_ok":    5,  # >= 5 eladás/hét
}
