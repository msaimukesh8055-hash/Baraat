# Vendor Record — Spec by Example

> **Competencies:** #3 spec-by-example, #7 structured-output reliability (first pass).
>
> **What this is:** the contract for Track B (extraction). Every messy vendor doc
> in `data/vendors/` must resolve to one JSON record matching this spec. The
> machine-checkable version is `vendor.schema.json`; this file is the
> plain-language *why*, plus worked examples and edge/failure cases — because a
> spec without examples is just a wish.
>
> **Reminder (the common mix-up):** this schema is **not** for retrieval/RAG.
> Retrieval reads the raw prose. This structured record exists so downstream
> **tools can do math and comparison** (budget checks, vendor comparison) — see
> `docs/learning-notes/phase1-and-schema.md`.

---

## 1. The fields (final, signed off)

| Field | Meaning | Validation rule |
|---|---|---|
| `vendor_id` | unique id from filename slug | matches `^(photographer\|caterer\|decorator\|venue\|makeup)_…` |
| `name` | business name | non-empty |
| `category` | one of 5 types | enum: photographer / caterer / decorator / venue / makeup_artist |
| `location` | city (+ area) | non-empty |
| `price_range_inr` | `{min, max}` in INR | min ≥ 0; max ≥ 0 or null; **min ≤ max** |
| `price_unit` | what the price is *per* | enum: per_plate / per_day / per_event / package |
| `price_last_verified` | date price was last good | `YYYY-MM-DD` or null |
| `price_confidence` | trust in the price | enum: high / low / stale |
| `contact.phone` | phone | string |
| `contact.email` | email | string or null |
| `gst_number` | 15-char tax id | GST-pattern string, or null (**never invented**) |
| `rating` | star rating | number 0.0–5.0 |
| `review_count` | # reviews | integer ≥ 0 |
| `red_flags` | problems found | array of strings (`[]` if none) |
| `source_file` | doc it came from | filename (attribution) |
| `needs_human_review` | couldn't extract confidently | boolean |
| `extraction_notes` | why flagged / context | string or null |

## 2. What each `price_confidence` value means (the important definitions)

This is the crux of the freshness story, so it's defined precisely:

- **`high`** — exactly one price, current-tense, no conflicting figures. A firm
  "the package is ₹2,10,000" counts as high *even with no explicit date*, because
  the listing presents it as the operative rate. (`price_last_verified` may be
  null here — confidence is about *trust in the figure*, not whether a date string
  exists.)
- **`low`** — we have a number, but it's vague, hedged, or open-ended
  ("from ₹8,50,000 and up", "starting at…"), with no contradiction across dates.
  We wouldn't bet the budget on it.
- **`stale`** — the doc gives **conflicting prices from different dates**, or an
  explicit "prices as of [old date]" marker. This is the planted freshness trap.

**Key distinction (write this down):** `stale` is a **successfully handled
state**, NOT a failure. So a stale price has `needs_human_review = false`.
`needs_human_review = true` is reserved for genuine extraction/validation failure
(see §5).

## 3. Three layers of "is this record correct?"

A reviewer will ask "what does 'validated' actually mean?" — there are three
distinct layers, and only the first two are checked by the schema:

1. **Structural validation (schema):** types, enums, ranges, patterns.
   Machine-checkable via `vendor.schema.json`. *("rating is a number 0–5",
   "category is one of 5 values", "GST matches the 15-char pattern".)*
2. **Cross-field semantic rules (code):** things JSON Schema can't express:
   - `price_range_inr.min ≤ max` (when max is not null)
   - `needs_human_review == true` ⇒ `extraction_notes` must be non-null
   - `price_unit` consistent with `category` (caterer→per_plate, venue→per_day,
     others→package/per_event)
   - `gst_number` is null unless a GST actually appears in the source doc
3. **Content correctness (an eval against ground truth, NOT the schema):** did we
   capture the *right* price, and did we catch the *buried* red flag? A record can
   be perfectly schema-valid and still be wrong (e.g. `red_flags: []` for a vendor
   that actually has a buried complaint). **Schema validation ≠ truth.** The
   reference depends on *what* we're grading:
   - **Extraction correctness** (this step) is graded against the **corpus
     manifest** (`data/vendors/_corpus_manifest.md`) — the per-doc answer key of
     true price, planted red flags, GST, etc. ("Did the record match the doc?")
   - **Retrieval / answering correctness** (later) is graded against the **golden
     set** of user questions + expected answers. ("Did the system answer the
     user's question?")
   These are distinct artifacts with distinct jobs; do not conflate them. The
   golden set's answers are often *authored from* the manifest, but the manifest
   is the master fact-sheet and the golden set is questions phrased on top of it.

---

## 4. Worked examples (input prose → output record)

### Example A — clean vendor (high confidence, no red flags)
**Source:** `photographer_everafter_films.md` (a clean control doc — firm price,
no conflict, no complaint).

```json
{
  "vendor_id": "photographer_everafter_films",
  "name": "Ever After Films",
  "category": "photographer",
  "location": "Bandra West, Mumbai",
  "price_range_inr": { "min": 210000, "max": 210000 },
  "price_unit": "package",
  "price_last_verified": null,
  "price_confidence": "high",
  "contact": { "phone": "+91 98201 76654", "email": "hello@everafterfilms.example" },
  "gst_number": null,
  "rating": 4.9,
  "review_count": 76,
  "red_flags": [],
  "source_file": "photographer_everafter_films.md",
  "needs_human_review": false,
  "extraction_notes": null
}
```
*Why:* single firm price → `high`, even though no date is given (`price_last_verified: null`). No GST in the doc → `null` (not invented). No complaints → `red_flags: []` (empty, not omitted).

### Example B — messy vendor (stale price + buried red flags)
**Source:** `caterer_anokhi_rasoi.md` (the deliberately messy one: two conflicting
prices, and a complaint buried in a late paragraph).

```json
{
  "vendor_id": "caterer_anokhi_rasoi",
  "name": "Anokhi Rasoi Catering Co.",
  "category": "caterer",
  "location": "Bani Park, Jaipur",
  "price_range_inr": { "min": 1450, "max": 1450 },
  "price_unit": "per_plate",
  "price_last_verified": "2023-11-01",
  "price_confidence": "stale",
  "contact": { "phone": "+91 98290 41123", "email": null },
  "gst_number": null,
  "rating": 4.5,
  "review_count": 212,
  "red_flags": [
    "Arrived ~90 min late for setup (two Dec 2023 weddings)",
    "Ran short on the paneer course at one reception",
    "Final invoice ~12% over the signed quote (disputed by client)"
  ],
  "source_file": "caterer_anokhi_rasoi.md",
  "needs_human_review": false,
  "extraction_notes": "Conflicting prices: ₹1,150 (2022 brochure/website) vs ₹1,450/plate (enquiry sheet, as of Nov 2023). Used most recent dated figure; marked stale."
}
```
*Why:* conflicting dated prices → `stale`, value = most recent (₹1,450),
`price_last_verified` = the most recent dated mention, and the conflict is spelled
out in `extraction_notes`. The buried complaint becomes three `red_flags` entries.
Crucially, `needs_human_review` is **false** — staleness is handled, not a failure.

---

## 5. Edge & failure cases (the part that proves reliability)

| Case | Expected handling |
|---|---|
| **Conflicting prices** (Anokhi, pixelpandit, rajwada…) | value = most recent dated; `price_confidence: stale`; conflict in `extraction_notes`; `needs_human_review: false` |
| **Open-ended price** ("from ₹8,50,000 and up") | `min` set, `max` may be a stated ceiling or `null`; `price_confidence: low`; note it |
| **No GST in doc** | `gst_number: null` — must NOT be hallucinated |
| **No email in doc** | `contact.email: null` |
| **No complaints** (clean controls) | `red_flags: []` — and must NOT invent one |
| **Buried red flag** (candidframes, emerald_gardens…) | must surface into `red_flags` — *content* check via the golden set, not the schema |
| **Near-duplicate names** (Royal Decor Studio vs & Events) | distinct `vendor_id` + `gst_number` keep them separate |
| **Model returns invalid output** (rating 7.5, bad category, text in a number box) | repair (re-prompt with the error) up to N=2; if still invalid → fallback (below) |

### Fallback example — genuine extraction failure
When validation can't be satisfied even after repair, we flag rather than guess:

```json
{
  "vendor_id": "caterer_placeholder_failed",
  "name": "Unparsed Caterer",
  "category": "caterer",
  "location": "Unknown",
  "price_range_inr": { "min": 0, "max": null },
  "price_unit": "per_plate",
  "price_last_verified": null,
  "price_confidence": "low",
  "contact": { "phone": "", "email": null },
  "gst_number": null,
  "rating": 0.0,
  "review_count": 0,
  "red_flags": [],
  "source_file": "caterer_placeholder_failed.md",
  "needs_human_review": true,
  "extraction_notes": "Validation failed after 2 repair attempts: model returned rating=7.5 (out of range) and category='wedding caterer' (not in enum). Flagged for human review instead of guessing."
}
```
*Principle (CLAUDE.md §3.3):* a malformed extraction is a **logged failure event,
not a silent retry**. We'll deliberately trigger one of these and log the
before/after to `docs/failure-log.md`.

---

## 6. Status & what's next
- **Done (this step):** schema *defined* — `vendor.schema.json` (structural
  contract) + this spec-by-example doc.
- **Next (separate step, pending go-ahead):** implement extraction + the
  validate → repair → human-review loop in code, and deliberately trigger a
  malformed-output failure to log. That is the "validate" half of the
  PHASE_PLAN task and the structured-output-reliability artifact.
