# ADR 0004 — Prompt caching vs semantic caching for Baraat

**Status:** accepted (Phase 4) — a reasoned judgment, not a build
**Date:** 2026-07-11

> Competency #10. Two different "caches" get conflated. This records where each applies
> to Baraat, and — importantly — where semantic caching would be actively harmful.

## The two caches (they are not the same thing)
- **Prompt caching:** the provider caches the *processed prefix* of a prompt (system
  prompt, tool schemas, retrieved context) so repeated calls that share that prefix skip
  re-processing it — cheaper input tokens + lower prefill latency. The model still runs;
  only the redundant prefill work is saved.
- **Semantic caching:** cache *answers* keyed by the meaning of the query. A new query
  similar to a past one returns the stored answer and **skips the LLM entirely** — near-
  zero cost/latency, but you're serving a possibly-stale answer.

## Where each applies to Baraat

**Prompt caching — a clear win.** Our traces showed input tokens dominate and *grow each
agent step* because the stable prefix (system prompt + tool schemas + retrieved context)
is re-sent every call (trace F-note: 5402 in vs 243 out). That stable prefix is exactly
what prompt caching is for. Caching it would cut input-token cost and prefill latency
substantially, with **no correctness risk** (same model, same output). Decision: **use
prompt caching** where the provider supports it (Anthropic exposes it directly; Groq's
support is limited — a reason production would lean Anthropic, cf. ADR 0001).

**Semantic caching — risky here, use narrowly.** Baraat is a *due-diligence* tool over
data we explicitly flagged as **freshness-sensitive** (ADR 0002: stale/conflicting
prices). A semantic cache that answers "what's vendor X's price?" from a stored answer
can serve a **stale price** — the exact failure ADR 0002 exists to prevent. Caching and
freshness are in direct tension. Decision:
- **Do NOT semantically cache** price/rating/red-flag answers (freshness-sensitive).
- **Optionally** semantically cache only *stable, non-freshness* facts (e.g. "where is
  vendor X located?") with a short TTL — and even then, the win is small at our scale.

## The tradeoff, stated plainly
| | Prompt caching | Semantic caching |
|---|---|---|
| Saves | redundant prefill (input tokens, latency) | the *entire* LLM call |
| Model still runs? | yes | no |
| Correctness risk | none | **stale answers** — serious for freshness data |
| Fit for Baraat | strong (big stable prefix) | poor for prices; marginal for stable facts |

## Decision
**Prompt caching: yes** (clear cost/latency win, zero correctness risk). **Semantic
caching: no** for anything freshness-sensitive; at most a short-TTL cache for stable
factual lookups. The general lesson: a bigger cache hit-rate is not free — for a
due-diligence product, **serving a stale-but-cheap answer is the wrong trade**, so the
freshness requirement caps how aggressively you can cache.

## Revisit when
- Traffic grows enough that repeated identical prefixes/queries are common (raises the
  value of both caches).
- We move to a provider with first-class prompt caching → measure the real input-token
  saving on the agent's growing-history calls.
