# 🎴 Pokémon TCG Monitor

Automatikus Cardmarket figyelő rendszer — naponta ellenőrzi a watchlisten lévő kártyák árait és vételi jelzést küld ntfy-on, ha valami alulértékelt.

---

## 📋 Mit csinál?

- **Napi scan (07:00 UTC):** Minden kártyát ellenőriz — megbízható NM ár vs. Trend ár
- **Heti frissítés (Hétfő 08:00 UTC):** Új Cardmarket szetteket keres, automatikusan hozzáadja a Tier Pokémonokat
- **ntfy értesítés:** Ha egy kártya Score ≥ 75 → azonnali push értesítés a telefonodra

---

## 🚀 Beállítás (5 perc)

### 1. Repo forkozása
Forkold ezt a repót a saját GitHub fiókodba.

### 2. ntfy beállítása
1. Töltsd le az **ntfy** appot (iOS / Android)
2. Válassz egy egyedi topic nevet (pl. `pokemon-varos-123`)
3. Iratkozz fel erre a topikra az appban

### 3. GitHub Secret hozzáadása
A repóban: **Settings → Secrets → Actions → New repository secret**
- Name: `NTFY_TOPIC`
- Value: `pokemon-varos-123` (a te topic neved)

### 4. GitHub Actions engedélyezése
A repóban: **Actions tab → Enable workflows**

### 5. Első futtatás
Actions → `Napi Pokémon Monitor` → `Run workflow`

---

## 📊 Investment Score (0-100)

| Komponens | Max pont |
|---|---|
| Árkülönbség (NM ár vs Trend) | 50 |
| God Tier karakter (Charizard, Pikachu, Umbreon) | 40 |
| Tier 1 karakter (Gengar, Mewtwo, stb.) | 30 |
| Tier 2 karakter (Blastoise, Lucario, stb.) | 15 |
| SIR/TG/GG ritkaság bónusz | 10 |
| Likviditás (≥10 eladás/hét) | 10 |

**Vételi jelzés: Score ≥ 75**

### Szűrési feltételek (mind teljesíteni kell):
- ✅ NM ár megbízható eladótól (≥500 feedback)
- ✅ Legalább 5 NM eladás az elmúlt 7 napban
- ✅ Legalább 20% kedvezmény a trend árhoz képest
- ✅ Maximum €100 belépési ár
- ✅ Tier-ben szereplő Pokémon

---

## 📁 Fájlok

```
pokemon_monitor/
├── config.py              # Tier listák, küszöbértékek
├── scraper.py             # Cardmarket adatlekérés
├── scorer.py              # Investment Score kalkulátor
├── notifier.py            # ntfy értesítések
├── watchlist_manager.py   # Watchlist kezelés és auto-frissítés
├── main.py                # Napi monitor futtatása
├── watchlist.json         # Kártyák listája (auto-frissül)
├── requirements.txt       # Python függőségek
└── .github/workflows/
    ├── daily_monitor.yml  # Napi 07:00 UTC
    └── weekly_update.yml  # Hétfői 08:00 UTC
```

---

## ⚙️ Konfiguráció (config.py)

```python
MIN_SELLER_FEEDBACK = 500    # Megbízható eladó minimuma
MIN_SALES_7D        = 5      # Minimális 7 napos eladásszám
MIN_DISCOUNT_RATIO  = 0.20   # Minimum 20% a trend alatt
MAX_CARD_PRICE_EUR  = 100    # Maximum belépési ár
MIN_SCORE           = 75     # Vételi jelzés küszöbe
```

---

## 🃏 Kezdeti Watchlist (18 kártya)

| Kártya | Szett | Ritkaság |
|---|---|---|
| Starmie V | Astral Radiance | Trainer Gallery |
| Suicune V | Crown Zenith | Galarian Gallery |
| Umbreon VMAX | Brilliant Stars | Trainer Gallery |
| Charizard V | Brilliant Stars | SIR |
| Espeon VMAX | Fusion Strike | SIR |
| Gengar VMAX | Fusion Strike | SIR |
| Cynthia's Garchomp ex | Destined Rivals | SIR |
| Team Rocket's Mewtwo ex | Destined Rivals | SIR |
| Shining Charizard | Neo Destiny | Secret Rare |
| ...és még 9 kártya | | |

---

## 📱 Értesítés példa

```
🔥🔥🔥 VÉTEL: Starmie V | Score: 84/100

Pokémon: Starmie (TIER 1)
NM ár (megbízható eladó): €69.00
Trend ár: €103.00
Kedvezmény: 33% a trend alatt

Részletezés:
  Árkülönbség: +33 pont
  Karakter bónusz: +30 pont
  Ritkaság bónusz: +10 pont
  Likviditás: +10 pont

👉 https://www.cardmarket.com/...
```

---

## ⚠️ Fontos megjegyzések

- A rendszer BeautifulSoup web-scrapert használ (V1 MVP)
- Cardmarket HTML változása esetén a scraper frissítésre szorulhat
- A Score egy segédeszköz — nem helyettesíti a saját döntéshozatalt
- Mindig kérj fotókat az eladótól vásárlás előtt!
- **V2 tervek:** Cardmarket hivatalos API, illusztrátor súlyozás, japán piac
