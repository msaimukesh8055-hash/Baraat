# Baraat — an AI due-diligence agent for wedding vendors

Baraat researches Indian wedding vendors (photographers, caterers, decorators, venues,
makeup artists), flags pricing and contract red flags, compares options against a
budget, and defends itself against manipulated vendor listings.

**But the wedding domain isn't the point.** Baraat is a portfolio built to demonstrate,
with evidence, the judgment an AI product manager needs — tradeoffs argued with numbers,
failures deliberately created and caught, and a regression gate so quality can't silently
slip. The most valuable file in this repo is arguably [`docs/failure-log.md`](docs/failure-log.md):
a running record of everything that broke and how it was caught.

---

## What it does, in one minute

- **Finds and reads** vendor information (RAG: retrieval over the listings).
- **Structures** messy listings into validated records for math and comparison.
- **Acts** via tools (budget split, payment-schedule check, contract-risk scan, vendor
  comparison), driven by an **agent** kept safe by guardrails.
- **Defends** against poisoned listings that try to hijack its recommendations.
- **Measures itself** — answer quality, cost, and latency — and **routes** each request
  to the right-sized model.

## Why it's interesting (the AI-PM competencies)

| Theme | What's demonstrated | Where |
|---|---|---|
| Retrieval evals | recall@k, then why it *overstated* quality | F5, F13 · `src/retrieval/` |
| RAG done honestly | baseline → hybrid → rerank, each measured; **rerank rejected on evidence** | F6, F7 |
| Structured-output reliability | schema → validate → repair → fallback | F3, F9, F10 · `src/extraction/`, `src/tools/` |
| Agent guardrails | loop/tool budgets, stop, degraded fallback | F8 · `src/agent/` |
| Safety | injection attack **succeeds**, then a 3-layer defense **blocks** it | F11, F12 · `src/safety/` |
| Evals | 40-question golden set + LLM-as-judge + human calibration | F14 · `src/evals/` |
| Observability | per-request traces (spans, tokens, latency) | `src/observability/` |
| Cost & latency | per-request-type cost; TTFT / p50 / p95 | `cost.py`, `latency_probe.py` |
| Routing | simple → 8b, complex → 70b; 87% cheaper; + fallback | ADR 0003 · `src/agent/router.py` |
| Judgment (when a tool is *wrong*) | reranking, fine-tuning, caching — argued, not assumed | F7, ADR 0004, `finetune-vs-rag-vs-icl.md` |
| Regression prevention | a CI gate that fails the build if quality drops | `src/evals/ci_gate.py` |

## Headline results (real numbers)

- **Retrieval:** recall@1 0.80 → **0.90** (hybrid); reranking added **0% for 34× latency → not shipped**.
- **Extraction:** 32 docs, 0 repairs / 0 fallbacks; 1 honestly-logged content miss (F4).
- **Answer quality:** mean **0.70** over 40 questions — exact-match & freshness **1.00**,
  but **clean-control 0.08** exposed a real gap ("couldn't say *no red flags found*"),
  since fixed.
- **Safety:** 3/3 injection attacks succeeded undefended → **3/3 blocked** after hardening.
- **Cost/latency:** an agent workflow costs ~**8.5×** a lookup; routing to the small model
  is ~**87% cheaper** and ~**30–40% faster** to first token.

## How it's built (see the [architecture](docs/architecture-diagram.md))

One synthetic corpus → two tracks (**retrieval** + **extraction**) → an **agent** with
tools and guardrails → a **safety** layer over untrusted text → an **observability + eval**
spine underneath. Deliberately dependency-light (NumPy vector store, from-scratch BM25,
hand-rolled validators) — appropriate at this scale, with documented upgrade paths.

## Try it

```bash
pip install -r requirements.txt
# (set GROQ_API_KEY in .env — see .env.example)

python -m src.agent.ask "Split my 15L budget ~40% venue and check an 80%-upfront contract."
python -m src.evals.answer_eval          # grade answers vs the golden set
python -m src.observability.trace_demo   # a real request, traced
python -m src.observability.cost_report  # cost per request type
python -m src.agent.demo_router          # routing decisions + 87% saving + fallback
python -m src.safety.run_attacks         # injection: undefended vs defended
python -m src.evals.ci_gate --demo       # the regression gate catching a bad change
```

## Deeper reading
- [`docs/failure-log.md`](docs/failure-log.md) — the reasoning arc (F1–F14).
- [`docs/phase1-results.md`](docs/phase1-results.md) — Phase 1 write-up with numbers.
- [`docs/decision-records/`](docs/decision-records/) — ADRs (model backend, freshness,
  routing, caching, fine-tuning-vs-RAG).
- [`docs/learning-notes/`](docs/learning-notes/) — plain-language explainers per phase.
- [`PHASE_PLAN.md`](PHASE_PLAN.md) — the phase-by-phase tracker.

## Honest limitations
- Runs on an open model via Groq (ADR 0001), not the Claude the spec names — reliability
  logic is model-agnostic; the swap is a one-liner.
- Free-tier **daily** token cap blocked the 8b accuracy comparison — routing's cost/latency
  are measured, its accuracy tradeoff is documented as an open gap (ADR 0003).
- Buried-red-flag retrieval and one classifier misroute are diagnosed, not yet fixed —
  logged rather than hidden, which is the whole point.

*All vendor data is fictional.*
