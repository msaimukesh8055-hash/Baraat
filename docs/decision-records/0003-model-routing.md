# ADR 0003 — Model routing: small vs large by request type

**Status:** accepted, partially validated (Phase 4)
**Date:** 2026-07-11

> Competency #9 (routing/fallback) + #13 (cost) + #11 (latency). Records the routing
> decision and — honestly — which parts are measured vs still assumed.

## Context
Baraat calls an LLM for several jobs (extraction, agent tool-selection, briefing,
answer generation). Not all need the same horsepower. Groq offers a small/cheap/fast
model (`llama-3.1-8b-instant`) and a strong/expensive one (`llama-3.3-70b-versatile`).

## Decision
Route by a **transparent keyword classifier** (`src/agent/router.py`, no extra LLM
call just to route):
- **Simple** — factual lookup, exact-match, freshness, red-flag, clean-control → **8b**.
- **Complex** — contract risk, budget planning, comparison → **70b**.
A **fallback cascade**: if the chosen model errors/times out, automatically try the
other one (degrade, don't die).

## What is MEASURED (real numbers)
- **Cost:** on the 40-question set, 38 route to 8b and 2 to 70b → **87% cheaper**
  than sending everything to 70b ($0.00209 vs $0.01598, Groq published rates).
- **Latency:** 8b is **~30–40% faster to first token** (TTFT p50 305ms vs 428ms;
  total p50 608ms vs 716ms) — measured via streaming (`latency_probe.py`).
- **Fallback:** demonstrated deterministically — an 8b failure falls back to 70b and
  still answers (`demo_router.py`).

## What is NOT yet measured (honest gap)
- **Accuracy on 8b.** We have *not* re-run the answer eval on the 8b model, because we
  hit Groq's **daily token cap** (TPD 100k) during Phase 4. So we know 8b is cheaper and
  faster but **not** whether it answers as well. The 87% saving is real; its accuracy
  cost is unquantified.
- **Classifier imperfections.** The keyword heuristic misroutes Q35 ("what are the
  *locations* of the two Grand Thali caterers") to 8b — it's a comparison but lacks the
  cue words (compare/vs/cheaper). A misroute sends a harder question to the weaker model.
- **Hard-but-simple-looking questions.** buried-red-flag and clean-control questions
  are shaped like simple lookups, so they route to 8b — yet the eval showed these are the
  *hardest* categories. Routing them to the cheap model is a **risk** we'd validate before
  shipping.

## Tradeoff, stated plainly
Routing buys a large cost + latency win for a *potential* accuracy loss on the hard
tasks that happen to look simple. The right next step is to **measure 8b's per-category
accuracy** (when the daily budget resets) and only route a category to 8b if its quality
holds; keep 70b for categories where 8b regresses. That measured gate is what turns this
from "looks cheaper" into a defensible routing policy.

## Revisit when
- The daily token budget resets → run the answer eval on 8b, per category, and set
  routing by measured quality (not by surface shape).
- We add a stronger classifier (or a tiny LLM classifier) if keyword misroutes matter.

## Note
Same open-model caveat as ADR 0001 — production would likely use Claude tiers; the
small-vs-large *routing pattern* is what's being demonstrated, not the specific vendor.
