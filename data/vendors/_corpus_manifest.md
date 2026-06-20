# Corpus Manifest — Ground-Truth Ledger (PRIVATE — NOT FOR THE INDEX)

> **What this is:** the answer key to our own test data. It records exactly what
> we deliberately planted in each of the 35 synthetic vendor docs — the *true*
> facts, the injected messiness traits, and the exact-match hooks.
>
> **Why it exists:** so we never have to re-guess our own intentions during
> evals, never "discover" a red flag we planted ourselves, and can prove the
> corpus matches the agreed distribution. It also lets us build the golden set
> (Phase 1) and extraction evals against a single source of truth.
>
> **CRITICAL:** This file must be **excluded from the retrieval index**. If the
> system could retrieve it, it would be reading the answer key — every eval
> would pass for the wrong reason. The ingestion pipeline must skip any file
> starting with `_` in `data/vendors/`.
>
> **All data is fictional** (CLAUDE.md §3.7). GST numbers are format-shaped but
> fake; phone numbers are non-dialable patterns; no real businesses.

---

## Trait distribution (target vs actual)

| Trait | Target | Actual | Docs |
|---|---|---|---|
| Stale / conflicting pricing | 5 | 5 | pixelpandit, anokhi_rasoi, marigold_mandap, rajwada_palace, glamour_by_neha |
| Buried red flag (lost-in-the-middle) | 5 | 5 | candidframes, anokhi_rasoi, petals_and_props, emerald_gardens, blush_studio |
| Near-duplicate name / exact-match | 7 | 7 | lensandlight_studio + lensandlight_weddings, grandthali_caterers + grandthali_events, royal_decor_studio + royal_decor_events, grand_pavilion |
| Reserved for Phase 3 (untouched now) | 3 | 3 | shaadi_shutter, regal_themes, imperial_court |

> Note: `anokhi_rasoi` intentionally carries **both** stale pricing and a buried
> red flag, so the stale and buried sets share one doc (5 + 5 across 9 unique
> docs). Near-duplicate sets = 3 confusable name-pairs (6 docs) + 1 single
> exact-match doc (grand_pavilion) = 7. Remaining 16 docs are clean controls
> (no planted trap) — they matter: a good retrieval system must also *not*
> invent red flags or staleness where none exists.

---

## Per-document ledger

Legend for `traits`: `stale` = conflicting/stale price · `buried` = red flag in a
late paragraph · `exact` = near-duplicate name and/or exact-match hook ·
`clean` = no planted trap · `reserved` = Phase-3 reserved (do not tune on).

### Photographers

| file | name | location | true price | price status | planted red flag | exact-match hooks | traits |
|---|---|---|---|---|---|---|---|
| photographer_lensandlight_studio.md | Lens & Light Studio | Jaipur | ₹1,85,000 pkg | current | none | GST 08ABCLL1234F1Z5, ph +91 98112 34567 | exact (pair A) |
| photographer_lensandlight_weddings.md | Lens & Light Weddings | Udaipur | ₹3,20,000 pkg | current | none | GST 08AADLW7788K1Z2, ph +91 94151 99007 | exact (pair A) |
| photographer_pixelpandit.md | Pixel Pandit Photography | Gurugram | ambiguous: ₹95,000 (2021) vs ₹1,40,000 (2024) | stale | none | — | stale |
| photographer_candidframes.md | Candid Frames | Bengaluru | ₹1,25,000 pkg | current | 4–5 month late delivery (2023); raw reception footage partially lost, no backup | — | buried |
| photographer_everafter_films.md | Ever After Films | Mumbai | ₹2,10,000 pkg | current | none | — | clean |
| photographer_moments_co.md | Moments & Co. | Hyderabad | ₹1,15,000 pkg | current | none | — | clean |
| _reserved_phase3_photographer_shaadi_shutter.md | Shaadi Shutter | Chandigarh | ₹1,05,000 pkg | current | none (yet) | — | reserved |

### Caterers

| file | name | location | true price | price status | planted red flag | exact-match hooks | traits |
|---|---|---|---|---|---|---|---|
| caterer_anokhi_rasoi.md | Anokhi Rasoi Catering Co. | Jaipur | ambiguous: ₹1,150 (2022) vs ₹1,450/plate (Nov 2023) | stale | late setup ~90 min; ran short on paneer; invoice ~12% over signed quote | ph +91 98290 41123 | stale + buried |
| caterer_grandthali_caterers.md | Grand Thali Caterers | Delhi (Pitampura) | ₹1,650/plate non-veg, ₹1,250 veg | current | none | GST 07AAGGT5521M1Z8, ph +91 98180 77342 | exact (pair B) |
| caterer_grandthali_events.md | Grand Thali Events & Catering | Lucknow | ₹1,450/plate non-veg, ₹1,100 veg | current | none | GST 09AAHGT9087L1Z4, ph +91 94150 30876 | exact (pair B) |
| caterer_swadsagar.md | Swad Sagar Caterers | Ahmedabad | ₹1,050/plate veg | current | none | — | clean |
| caterer_annapurna_rasoi.md | Annapurna Rasoi | Pune | ₹1,100/plate veg | current | none | — | clean |
| caterer_spice_affair.md | Spice Affair Catering | Bengaluru | ₹1,300/plate | current | none | — | clean |
| caterer_zaika_kitchens.md | Zaika Kitchens | Hyderabad | ₹1,500/plate non-veg | current | none | — | clean |

### Decorators

| file | name | location | true price | price status | planted red flag | exact-match hooks | traits |
|---|---|---|---|---|---|---|---|
| decorator_royal_decor_studio.md | Royal Decor Studio | Udaipur | ₹2,75,000+ pkg | current | none | GST 08ABACR4567Q1Z9, ph +91 94140 77820 | exact (pair C) |
| decorator_royal_decor_events.md | Royal Decor & Events | Jaipur | ₹2,40,000+ pkg | current | none | GST 08AACRE3321P1Z6, ph +91 93140 22665 | exact (pair C) |
| decorator_marigold_mandap.md | Marigold Mandap Decorators | Jaipur | ambiguous: ₹1,80,000 (2022) vs ₹2,60,000 (2024) | stale | none | — | stale |
| decorator_petals_and_props.md | Petals & Props | Mumbai | ₹8,50,000+ pkg | current | imported florals didn't arrive, silent local substitution; lighting rig downscaled day-of, full price charged | — | buried |
| decorator_shaan_decor.md | Shaan Decor | Chandigarh | ₹1,60,000+ pkg | current | none | — | clean |
| decorator_bloom_room.md | The Bloom Room | Bengaluru | ₹2,00,000+ pkg | current | none | — | clean |
| _reserved_phase3_decorator_regal_themes.md | Regal Themes | Delhi (Saket) | ₹3,50,000+ pkg | current | none (yet) | — | reserved |

### Venues

| file | name | location | true price | price status | planted red flag | exact-match hooks | traits |
|---|---|---|---|---|---|---|---|
| venue_rajwada_palace.md | Rajwada Palace Banquets | Jaipur | ambiguous: ₹3,50,000 (2021) vs ₹5,25,000/day | stale | none | ph +91 98290 70011 | stale |
| venue_emerald_gardens.md | Emerald Gardens Resort | Bengaluru Rural | ₹6,00,000/day | current | rooms double-booked on peak dates; second lawn reassigned last-minute; deposit refunded only after repeated follow-ups | — | buried |
| venue_grand_pavilion.md | The Grand Pavilion | Hyderabad | ₹4,75,000/day | current | none | GST 36AAEGP2210R1Z3, ph +91 90000 51277 | exact (single) |
| venue_lakeview_resort.md | Lakeview Resort | Udaipur | ₹9,50,000 (2-day) | current | none | — | clean |
| venue_heritage_haveli.md | Heritage Haveli | Jodhpur | ₹5,50,000/day | current | none | — | clean |
| venue_sunset_banquets.md | Sunset Banquets | Delhi (Rohini) | ₹3,80,000/day | current | none | — | clean |
| _reserved_phase3_venue_imperial_court.md | Imperial Court | Mumbai | ₹12,00,000+/day | current | none (yet) | — | reserved |

### Makeup Artists

| file | name | location | true price | price status | planted red flag | exact-match hooks | traits |
|---|---|---|---|---|---|---|---|
| makeup_glamour_by_neha.md | Glamour by Neha | Delhi (GK) | ambiguous: ₹45,000 (2022) vs ₹75,000 (2024) | stale | none | ph +91 98110 64422 | stale |
| makeup_blush_studio.md | Blush Studio | Mumbai | ₹85,000 pkg | current | booked senior artist a no-show, junior sent without notice; surprise peak-date surcharge added day-of | — | buried |
| makeup_bridal_glow.md | Bridal Glow | Bengaluru | ₹55,000 pkg | current | none | — | clean |
| makeup_kohl_and_kumkum.md | Kohl & Kumkum | Jaipur | ₹60,000 pkg | current | none | — | clean |
| makeup_makeover_room.md | The Makeover Room | Hyderabad | ₹65,000 pkg | current | none | — | clean |
| makeup_radiance_artistry.md | Radiance Artistry | Pune | ₹50,000 pkg | current | none | — | clean |
| makeup_signature_looks.md | Signature Looks | Chandigarh | ₹58,000 pkg | current | none | — | clean |

---

## Near-duplicate pairs (for the exact-match / hybrid-search eval)

- **Pair A:** Lens & Light **Studio** (Jaipur) vs Lens & Light **Weddings** (Udaipur)
- **Pair B:** Grand Thali **Caterers** (Delhi) vs Grand Thali **Events & Catering** (Lucknow)
- **Pair C:** Royal Decor **Studio** (Udaipur) vs Royal Decor **& Events** (Jaipur)

These are the cases where pure semantic similarity is expected to blur the two
firms; disambiguating them via GST/phone/city is what hybrid (keyword) search
should fix.

## All GST numbers assigned (fictional, format-shaped)

| GST | vendor | state code |
|---|---|---|
| 08ABCLL1234F1Z5 | Lens & Light Studio | 08 Rajasthan |
| 08AADLW7788K1Z2 | Lens & Light Weddings | 08 Rajasthan |
| 07AAGGT5521M1Z8 | Grand Thali Caterers | 07 Delhi |
| 09AAHGT9087L1Z4 | Grand Thali Events & Catering | 09 Uttar Pradesh |
| 08ABACR4567Q1Z9 | Royal Decor Studio | 08 Rajasthan |
| 08AACRE3321P1Z6 | Royal Decor & Events | 08 Rajasthan |
| 36AAEGP2210R1Z3 | The Grand Pavilion | 36 Telangana |
