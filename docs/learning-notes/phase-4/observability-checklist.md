# Phase 4 — The AI-PM Observability Checklist (10 metrics)

> The 10 concrete metrics an AI PM tracks for an LLM product — what each means in
> plain language, why it matters, and whether Baraat builds it. Interview-prep grade.
>
> Status key: ✅ built · 🔨 building this phase · 📋 future

---

## The 10 metrics

**1. Total latency**
- *Means:* wall-clock time from question → answer (e.g. 2.6s).
- *Why:* the user's felt wait.
- *Baraat:* ✅ built (tracer).

**2. Time-to-first-token (TTFT)**
- *Means:* how long until the answer *starts* appearing (vs. fully finishing).
- *Why:* a reply that starts streaming in 0.3s *feels* fast even if it takes 3s to finish.
- *Baraat:* 🔨 building (latency step).

**3. p95 latency (tail latency)**
- *Means:* the latency the **slowest 5% of requests** see (not the average).
- *Why:* averages hide pain — mean 2s but p95 12s means 1 in 20 users suffers. Seniors
  optimize the tail.
- *Baraat:* 🔨 building (needs many requests → the 40-question set).

**4. Tokens per request (input / output)**
- *Means:* how much text went into the model and came out.
- *Why:* tokens = the raw driver of cost; input and output are priced differently.
- *Baraat:* ✅ built.

**5. LLM calls per request**
- *Means:* how many times the model was called (= number of decision steps for an agent).
- *Why:* more calls = more cost + latency; a spike signals the agent is looping.
- *Baraat:* ✅ built.

**6. Tool calls per request**
- *Means:* how many tools were invoked to answer.
- *Why:* shows how much "work" a request needs; redundant calls = waste.
- *Baraat:* ✅ built.

**7. Cost per request (and per request-type)**
- *Means:* money for a request = tokens × price, grouped by feature ("a contract check
  costs 8× a lookup").
- *Why:* you can't budget or price a product on a total; you need per-feature attribution.
- *Baraat:* 🔨 building (cost step).

**8. Answer correctness (eval score)** ⭐
- *Means:* was the answer actually *right*, judged against ground truth (LLM-judge).
- *Why:* this is the real SLA — an LLM that responds fast but wrong is worse than useless.
- *Baraat:* 🔨 building (evals step — LLM-as-judge).

**9. Retrieval recall@k**
- *Means:* did the search fetch the correct chunk into the top-k (retrieval requests).
- *Why:* if retrieval misses, the answer can't be right — the upstream quality gate.
- *Baraat:* ✅ built (Phase 1 = 0.90). *Offline eval, not yet live per-request.*

**10. Failure / guardrail-trip rate**
- *Means:* how often a request failed, needed a retry/repair, or hit a budget → degraded.
- *Why:* the reliability picture — how often the safety nets actually fire.
- *Baraat:* ✅ events visible per trace · 🔨 building the aggregate *rate*.

---

## Scoreboard

| # | Metric | Status |
|---|---|---|
| 1 | Total latency | ✅ built |
| 2 | Time-to-first-token | 🔨 building |
| 3 | p95 tail latency | 🔨 building |
| 4 | Tokens in/out | ✅ built |
| 5 | LLM calls/request | ✅ built |
| 6 | Tool calls/request | ✅ built |
| 7 | Cost per request/type | 🔨 building |
| 8 | Answer correctness (eval) | 🔨 building |
| 9 | Retrieval recall@k | ✅ built (offline) |
| 10 | Failure/guardrail-trip rate | ✅ partial · 🔨 aggregate |

**5 fully built, 5 being built this phase.** The 5 we're adding (TTFT, p95, cost,
correctness, failure-rate) are exactly what the rest of Phase 4 delivers — which is
why observability, evals, cost, and latency are one connected phase, not four.

---

## The three most-skipped (say these in an interview)

1. **#8 correctness** — treated as the *real SLA*, inside observability, not a silo.
2. **#3 p95 (tail)** — distributions, not averages; optimize the slowest 5%.
3. **#7 per-feature cost** — attribution, not totals.

> One-liner: *"I look at cost, latency, and quality jointly (the tradeoff triangle),
> as distributions (p95, not mean), attributed per feature/user (not just totals), and
> trended over time (drift) — with correctness as the real SLA."*

---

## Beyond the 10 (fuller list for reference)
- **Groundedness / hallucination rate** (part of correctness) — is the answer supported
  by retrieved sources?
- **Drift over time** — is score/cost/latency trending worse release-over-release?
- **Cost per *successful* answer** — factors in wasted retries/failures.
- **Prefill vs decode split** — where the latency/cost actually goes.
- **Safety events** — injection lines sanitized, PII redactions triggered (Phase 3).
- **Product metrics** — thumbs up/down, task-completion, escalation-to-human, retention.
- **Lineage** — which prompt version + model version + corpus version produced a result
  (for reproducibility and A/B).

---

## Mini-recap
- 10 core metrics: latency, TTFT, p95, tokens, LLM calls, tool calls, cost, correctness,
  recall@k, failure-rate.
- Baraat: **5 built, 5 building this phase.**
- Most-skipped (and most senior): **correctness (real SLA), p95 (tails), per-feature cost.**
