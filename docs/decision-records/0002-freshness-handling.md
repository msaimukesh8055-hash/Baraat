# ADR 0002 — How Baraat handles stale / conflicting prices (freshness)

**Status:** accepted (Phase 1)
**Date:** 2026-07-05

> Plain-language version first, then the formal decision. Freshness is part of
> competency #5 (RAG architecture). This ADR records *how* we handle out-of-date
> prices and *why* — the mechanism already exists in code; this captures the
> thinking so it can be explained.

---

## The problem in one sentence

A vendor's price can be **stale**: true once, but maybe wrong now — and sometimes a
single document even shows **two different prices from two different dates**. If the
system just picks one and states it confidently, it can mislead a couple planning a
wedding budget. For a *due-diligence* product, that's the worst kind of error.

### A concrete example (from our corpus)

`caterer_anokhi_rasoi.md` contains **both**:
- ₹1,150 per plate — from a **2022** brochure / website
- ₹1,450 per plate — from a **Nov 2023** enquiry sheet

There is no single "current price" stated. A naive system would grab one number
(often the first it sees, ₹1,150) and report it as fact — understating the real cost
by ~26%. Five vendors have this trait on purpose: `pixelpandit`, `anokhi_rasoi`,
`marigold_mandap`, `rajwada_palace`, `glamour_by_neha`.

---

## The approach: detect it, flag it, don't silently guess

Our rule is **"flag, don't guess."** When prices conflict or look dated, the system
does **not** pretend to know the current price. It records what it found, marks its
confidence, and signals that a human should confirm. Three moving parts:

### 1. Detection (happens at extraction time, Track B)
When the extraction model reads a doc, it looks for conflicting or dated pricing. If
it finds them, it does **not** average them or pick blindly — it flags the record.

### 2. Three confidence levels (the `price_confidence` field)
Every extracted vendor record carries a `price_confidence` value:

| Value | Meaning | Example |
|---|---|---|
| `high` | one clear, current price stated | "₹2,10,000 package" (Ever After Films) |
| `low` | open-ended / vague pricing | "from ₹8,50,000 **and up**" (Petals & Props) |
| `stale` | conflicting or clearly dated prices | ₹1,150 (2022) vs ₹1,450 (2023) (Anokhi) |

### 3. What we do with a `stale` record (the policy)
- **Keep the most recent dated figure** as the working number (₹1,450, not ₹1,150) —
  newest dated data is the best available guess.
- **Mark it `stale`** so nothing downstream treats it as reliable.
- **Record a human-readable note** in `extraction_notes`, e.g.:
  *"Conflicting prices: ₹1,150 (2022 brochure) vs ₹1,450/plate (enquiry sheet, Nov
  2023). Used most recent dated figure; marked stale."*
- **Surface a "confirm before booking" signal** to the user rather than asserting a
  price as current.

There is also a `price_last_verified` date field, so "how old is this?" is answerable
instead of unknown.

---

## How the retrieval side supports this

Freshness isn't only an extraction concern — the user also *asks* about it. Our two
freshness golden questions both retrieved the right passage at **rank 1**:
- **Q06** — *"What is the current per-plate price at Anokhi Rasoi?"* → the
  conflicting-price paragraph is returned, so the system can answer with **both**
  numbers and the caveat, not a false single figure.
- **Q07** — *"How much does Rajwada Palace Banquets cost per day?"* → same: the
  stale/conflicting passage surfaces, enabling an honest "confirm current rate" reply.

So the two halves line up: extraction **records** the staleness; retrieval **surfaces**
the evidence; the eventual answer can be honest about uncertainty.

---

## Why "flag, don't guess" is the right call here

1. **The product is due diligence.** A confidently wrong price is worse than an
   honest "this looks out of date — confirm it." Being *calibrated* beats being
   *certain*.
2. **It's checkable.** A `stale` flag + a note can be validated and audited; a
   silently-picked number cannot. (Ties to competency #7, structured-output
   reliability.)
3. **It degrades gracefully.** Worst case, the user is told to confirm a price —
   annoying but safe — instead of budgeting on a 2-year-old figure.

---

## Limitations / what we did NOT build (honest scope)

- **Freshness is point-in-time at extraction.** We flag staleness *as written in the
  doc*; we do **not** re-scrape or live-check prices. A price marked `high` today
  could silently age.
- **No automatic expiry (TTL).** We record `price_last_verified` but don't yet act on
  it (e.g. "anything older than 12 months → downgrade to `stale`").
- **Date parsing is light.** "2022" vs "Nov 2023" is easy; messier date phrasing
  could fool the "most recent" choice.

## Revisit when
- We add a refresh pipeline (re-verify prices on a schedule) → then `price_last_verified`
  drives an automatic `high → stale` downgrade past a TTL.
- Phase 4 evals — we could add an LLM-judge check that a `stale` record's answer
  always includes the "confirm" caveat.
