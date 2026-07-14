# Phase 4 — Caching, in plain language (prompt vs semantic)

> The plain-language version of ADR 0004. The subtle point: two different things are
> both called "caching," and they do NOT carry the same risk.

---

## What "caching" means
Caching = **don't redo work you've already done.** In LLM systems there are **two
completely different** things called caching, and the whole point is they are not the
same.

---

## Type 1: Prompt caching (the clear win)

**What it is:** before a model generates anything, it must *read and process* your input
tokens — this is **prefill**. If the **beginning of the prompt is the same** across many
calls, the provider can save the processed form of that repeated "prefix" and skip
re-processing it next time.

**Key: the model still runs and gives a fresh answer.** Only the redundant re-reading of
the same opening text is skipped. The output does not change.

**Analogy:** a lecturer who reuses the same intro slides every class — doesn't re-draw
them, but still gives a fresh live lecture. Setup saved; lecture real.

**Why it's a big win for Baraat:** the trace showed **input tokens dominate and grow
every agent step** (5402 in vs 243 out, climbing 1178 → 1282 → 1414 → 1528). Input grows
because the **stable prefix** — system prompt + tool schemas + retrieved context — is
**re-sent on every loop step.** That repeated prefix is exactly what prompt caching
targets:
- saves money (cached input tokens billed cheaper),
- saves latency (prefill is faster),
- **zero correctness risk** (same model, same fresh output).

Real savings + no downside → **use it.**

---

## Type 2: Semantic caching (rejected for prices)

**What it is:** cache the **answers**, keyed by the *meaning* of the question. A new
question similar to a past one returns the **stored answer** and **skips the LLM
entirely.**

**Key: the model does NOT run.** You hand back an *old* answer.

**Analogy:** photocopying last year's answer and handing it out — fast and nearly free,
but if the facts changed, you just handed someone **wrong information.**

**Why it's dangerous for Baraat:** Baraat is a **due-diligence** tool, and ADR 0002 made
freshness its whole discipline (prices go stale → flag them → tell users to confirm). If
we semantically cache "what's vendor X's price?":
- the vendor later raises the price,
- a new user asks the same question,
- the cache serves the **old price** — skipping the model, retrieval, and the freshness
  check.

That is the exact failure ADR 0002 exists to prevent. **Semantic caching and freshness
are in direct conflict** for price/rating/red-flag data. For due diligence, **"cheap but
stale" is the wrong trade** — a wrong price is worse than a slow one.

---

## The core distinction (one line to remember)

| | Prompt caching | Semantic caching |
|---|---|---|
| What it skips | re-reading the **repeated prompt prefix** | the **entire model call** |
| Model still runs? | **yes** — fresh answer | **no** — old answer reused |
| Correctness risk | **none** | **stale answers** |
| Fit for Baraat | strong (big stable prefix) | poor for prices |

> **Prompt caching** saves *input processing* → answer still fresh → safe.
> **Semantic caching** reuses *the whole answer* → might be stale → dangerous for
> freshness-sensitive facts.

---

## The decision
- **Prompt caching: yes** — big stable prefix, real savings, no correctness risk. (Groq's
  support is limited — another nudge toward Anthropic, cf. ADR 0001.)
- **Semantic caching: no** for freshness-sensitive fields (prices, ratings, red flags); at
  most a short-TTL cache for stable facts like "where is vendor X located?" — a marginal
  win at 35 docs.

**PM lesson:** a higher cache hit-rate is not automatically good. The **freshness
requirement caps how aggressively you can cache** — and recognizing that the "cheaper"
option (semantic caching) is actually *wrong* for the product is the judgment call.

---

## Mini-recap
- Two caches: **prompt** (skip re-reading the repeated prefix; model still runs; safe)
  vs **semantic** (reuse the whole old answer; model skipped; can be stale).
- Baraat: **prompt caching yes** (input tokens dominate & grow), **semantic caching no**
  for prices (conflicts with freshness, ADR 0002).
- The lesson: freshness caps caching; "cheap but stale" is the wrong trade for due
  diligence.
