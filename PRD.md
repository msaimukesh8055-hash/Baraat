# PRD.md — Baraat: Wedding Vendor Research & Due-Diligence Agent

## 1. Problem statement (in-universe)

Planning a wedding in India involves evaluating dozens of vendors across
categories (photographers, caterers, decorators, venues, makeup artists)
with inconsistent, scattered, sometimes manipulated information — stale
pricing, buried complaints, near-identical vendor names, and listings
written by the vendors themselves with obvious incentive to mislead.

Baraat researches vendors, surfaces red flags a rushed human would miss,
checks contracts and payment schedules for risk, and helps allocate a
fixed budget across categories — while being explicitly hardened against
vendors trying to manipulate its recommendations.

## 2. Out of scope (deliberately)

- Real-time bookings or payments
- Real vendor data / live scraping (synthetic corpus only — see CLAUDE.md §3.7)
- Mobile app / polished UI — this is a backend + eval system; a minimal CLI
  or simple script-driven interface is sufficient. UI polish is not a goal.
- Multi-language support
- Anything not traceable to one of the 16 competencies in CLAUDE.md §2

## 3. Vendor corpus spec

**5 categories × 6-8 vendors = ~35 vendor documents.**

| Category | Count |
|---|---|
| Photographers | 7 |
| Caterers | 7 |
| Decorators | 7 |
| Venues | 7 |
| Makeup Artists | 7 |

### Deliberate messiness (built into the corpus from day one — this is what
makes Phase 1 evals meaningful instead of staged):

- **Stale pricing (4-5 vendors):** doc contains two different price mentions
  from different implied dates, or an explicit "prices as of [old date]"
  marker, with no clear current price. Tests freshness handling.
- **Buried red flags (4-5 vendors):** a cancellation history, fraud
  complaint, or quality issue mentioned only in a later paragraph of an
  otherwise long, positive-sounding document. Tests lost-in-the-middle
  retrieval failure.
- **Near-duplicate / exact-match traps (6-7 vendors):** similar business
  names (e.g. "Royal Decor Studio" vs "Royal Decor & Events"), and queries
  that hinge on exact phone numbers, GST numbers, or precise ₹ amounts —
  cases where pure semantic embedding similarity will blur the correct
  answer. Tests hybrid (keyword + semantic) search necessity.
- **Reserved for Phase 3 (2-3 vendors, do NOT touch in Phase 1-2):**
  vendor docs that will later have prompt-injection payloads embedded
  (e.g. hidden instruction text). Mark these clearly in the data folder
  (e.g. `_reserved_phase3_*.md`) so they aren't accidentally used to tune
  Phase 1 retrieval.

### Vendor document fields (unstructured source doc, before extraction):

Each raw vendor doc should read like a realistic listing/review aggregation
— prose, not pre-structured — so the ingestion pipeline has real chunking
and extraction work to do. Should include: business name, category,
description, price information (sometimes stale/conflicting as above),
contact info, location, a few review snippets, rating, and (for the
red-flag subset) the buried issue.

## 4. Structured output schema (post-extraction)

Every vendor, once processed, resolves to:

```json
{
  "vendor_id": "string",
  "category": "photographer | caterer | decorator | venue | makeup_artist",
  "name": "string",
  "price_range_inr": {"min": 0, "max": 0},
  "price_last_verified": "YYYY-MM-DD or null if unknown/stale",
  "price_confidence": "high | low | stale",
  "contact": {"phone": "string", "email": "string|null"},
  "location": "string",
  "red_flags": ["string"],
  "rating": 0.0,
  "review_count": 0,
  "gst_number": "string|null"
}
```

This schema is what Phase 1's structured-output-reliability work validates
against. Malformed extractions (missing required field, wrong type, etc.)
should trigger a repair/retry step, and repeated failure should fall back
to a flagged "needs human review" state rather than silently guessing.

## 5. Tools (Phase 2)

| Tool | Purpose | Why it's a real tool, not decoration |
|---|---|---|
| `budget_allocator` | Given total budget + category weights, suggest an allocation across the 5 categories | Real calculation with constraints; can fail (over-allocation, negative budget) |
| `contract_risk_checker` | Scans a contract/payment-schedule text for risk patterns (e.g. >50% upfront, no cancellation clause, vague delivery timeline) | Real side effect: flags a risk a human might miss; false negatives are a real failure mode worth evaluating |
| `payment_schedule_validator` | Validates a proposed payment schedule against red-flag heuristics | Structured input/output; good case for argument validation |
| `vendor_comparator` | Multi-step: pulls 2-3 shortlisted vendors, compares on price/rating/red flags | Forces multi-tool orchestration, a real case for loop/tool budgets |

## 6. Golden eval set (Phase 4) — categories of questions

~30-40 questions spanning:
- Simple factual lookup (route-able to a small/fast model) — e.g. "What's
  the price range for [vendor]?"
- Exact-match retrieval (tests hybrid search) — e.g. "Which vendor has GST
  number starting with 29AB...?"
- Freshness-sensitive (tests stale-price handling) — e.g. "Is [vendor]'s
  listed price current?"
- Red-flag detection (tests lost-in-the-middle) — e.g. "Does [vendor] have
  any complaint history?"
- Contract risk analysis (route-able to the stronger model) — e.g. "Is this
  payment schedule risky?"
- Adversarial / injection cases (Phase 3+) — e.g. queries against the
  reserved manipulated vendor docs.

Expected answers for each question are written by the builder (Saimukesh)
*before* seeing pipeline output, to keep the golden set honest.

## 7. Definition of "done" for the project as a whole

- All 16 competencies in CLAUDE.md §2 have a working, demoable artifact
- `/docs/failure-log.md` documents at least one real before/after for each
  phase
- A CI eval gate script exists and can be shown failing a deliberately
  regressed change
- README.md tells the project's story end-to-end for a non-technical
  reader, with pointers to deeper docs for a technical one
