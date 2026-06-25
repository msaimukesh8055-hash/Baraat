# Baraat — Topic-by-Topic Walkthrough (plain language)

> A clean, "explain it back in my own words" walkthrough, one topic at a time.
> This is the *narrative* version for interview prep. Deeper detail lives in
> `phase1-and-schema.md` and `retrieval-and-evals.md`; this file is the spine.
>
> Topics:
> 1. Extraction (DONE — below)
> 2. Retrieval (to come)
> 3. Golden dataset & evals (to come)

---

## Topic 1 — Extraction (turning 35 messy docs into clean records)

### 1. The setup
- We have **35 vendor documents** — messy, prose-style pages (listings + reviews),
  with realistic problems planted on purpose (stale prices, buried complaints,
  near-duplicate names). 32 are in scope; 3 are reserved for Phase 3.
- We use the **Groq model** (Llama 3.3 70B) to *read* each document and pull the
  facts out.
- The facts have to land in a fixed shape we designed: the **schema**.

### 2. The schema = fields + rules
The schema is two things at once:
- **Fields** — the labeled boxes every vendor must be turned into: `name`,
  `category`, `price_range_inr {min, max}`, `price_unit`, `gst_number`, `rating`,
  `red_flags`, `needs_human_review`, `extraction_notes`, etc.
- **Rules** — constraints those boxes must obey, e.g.:
  - `min` price ≤ `max` price
  - a `caterer` must be priced `per_plate` (unit must match the category)
  - if `needs_human_review` is true, `extraction_notes` must explain why
  - `rating` between 0 and 5; `gst_number` matches the 15-char format

### 3. The Python validator — TWO checks, ZERO intelligence
After Groq fills in a record, a plain **Python script** checks it. This script is
**not smart** — it is just `if`-statements looking at the values already in the
JSON. It does **no meaning-search, no looking things up in the real world.** Two
checks, in order:

- **Check A — SHAPE (format).** Are the boxes the right *type/format*? Is `rating`
  a number 0–5? Is `category` one of the 5 allowed words? Is the GST the right
  shape? (This is "structural validation.")
- **Check B — RULES.** Do this **one record's** fields agree with the rules we
  wrote? `min ≤ max`? unit matches category? review-flag has a note?
  > ⚠️ This is *within a single record* — Anokhi's record is never compared to
  > another vendor's. And calling it "meaning" is a trap: there's **no semantic
  > understanding here**, only our hardcoded rules being satisfied or not.

### 4. What happens after the check — accept / repair / fallback
```
Groq fills the record
      │
      ▼
Python validator:  SHAPE ok?  →  RULES ok?
      │
  ┌───┴────────────────────────────┐
  ▼ both pass                       ▼ something fails
ACCEPT the record           REPAIR: hand Groq the exact errors,
(write it to the table)      ask it to fix and return again
                                    │  (capped — max 2 tries)
                              ┌─────┴──────┐
                              ▼ now passes  ▼ still failing
                            ACCEPT        FALLBACK:
                                          needs_human_review = true
                                          + a note (never silently guess)
```
- **Accept** → the clean record is saved.
- **Repair** → the *same* Groq model is asked again, this time shown precisely
  what it got wrong. Capped at 2 tries so it can't loop forever.
- **Fallback** → if it still won't validate, we don't pretend. We flag the record
  `needs_human_review = true` with a note. This whole thing is still just a Python
  script — a fixed, capped retry, **not** an agent.

### 5. What actually happened on the real run
- 32 docs, Groq Llama-3.3-70B, **0 repairs, 0 fallbacks** — every record passed
  SHAPE + RULES on the first try. That's why there was **no real Failure-3**; the
  repair/fallback paths never fired on real data.
- So we proved those paths **deliberately with a mock** (F3): scripted a
  valid case, an invalid-then-repaired case, and an invalid-always case. The last
  one failed twice and **fell back** — exactly as designed. (Your summary of this
  was right.)

### 6. Layer 3 — me, by hand, vs the MANIFEST
SHAPE + RULES can only prove a record is *well-formed and self-consistent*. They
can **never** prove the *facts are true* — the validator has no access to ground
truth, only to the JSON in front of it. So the final layer is:
- **I manually compare the records to `data/vendors/_corpus_manifest.md`** (the
  ground-truth ledger of what we planted in each doc).
- This is the only layer that catches "confidently wrong but internally
  consistent" — e.g. the pixelpandit record invented a red flag the manifest never
  planted (F4). SHAPE was fine, RULES were fine; only the manifest comparison
  caught it.

> **The three layers, in one line each:**
> 1. SHAPE — is the JSON well-formed? (Python, automatic)
> 2. RULES — does this record obey our constraints? (Python, automatic)
> 3. FACTS — is it actually true? (me, by hand, vs the **manifest**)

### 7. Where the golden dataset sits (it does NOT belong here)
The **golden dataset** (≈10 questions + expected answers) was built now, but it is
a **separate thing for a separate track (retrieval)**. It is the exam for "did the
system *answer the user* correctly?" — not for extraction.
- Extraction is graded against the **MANIFEST**.
- Retrieval/answering is graded against the **GOLDEN DATASET**.
- The golden dataset is *written from* the manifest, but it never appears in the
  extraction flow above. Keep the two answer keys apart.

### 8. The real-life takeaway (interview framing)
In a real project with 35 docs, "me checking by hand" (Layer 3) is the correct,
not-lazy choice. At thousands of docs it becomes a **sampled** manual check plus an
**LLM-as-judge** doing an approximate automated version of the same
manifest-comparison — which is exactly what Phase 4 builds later. The repeatable
AI-PM skill on display: *design a schema, let the model fill it, validate
mechanically (shape + rules), and handle the model's mistakes honestly (repair,
then an explicit "needs human review" fallback) instead of trusting it blindly.*
