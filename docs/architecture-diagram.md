# Baraat — Architecture

> How the pieces fit. Two data tracks built from one corpus, an agent that uses them,
> a safety layer around untrusted text, and an observability/eval spine underneath.

## The whole system

```
                         data/vendors/*.md  (35 synthetic docs; 3 reserved for safety)
                                    │
             ┌──────────────────────┴───────────────────────┐
             ▼                                               ▼
   TRACK A — RETRIEVAL (RAG)                       TRACK B — EXTRACTION
   chunk → embed → vector store                    LLM → JSON record
   → hybrid search (semantic+BM25)                 → validate → repair → fallback
   → (rerank: built, not shipped)                  (src/extraction/)
   (src/ingestion, src/retrieval)                          │
             │                                             ▼
             │                                    data/extracted/*.json
             │                                    (trusted structured facts)
             ▼                                             │
   ANSWER STAGE (retrieve→compose)                         │
   grounded, no-guessing (src/answer/)                     │
             │                                             │
             └───────────────┬─────────────────────────────┘
                             ▼
                    AGENT  (src/agent/)
             explicit loop + 4 guardrails
        (loop budget, tool budget, stop, degrade)
             LLM policy decides tool calls
                             │
        ┌────────────┬───────┴───────┬─────────────┐
        ▼            ▼               ▼             ▼
   budget_       payment_       contract_      vendor_
   allocator     schedule_      risk_          comparator
                 validator      checker        (uses Track B)
        (src/tools/ — each: input schema → run → output schema, bounded repair)

   ROUTER (src/agent/router.py): simple → 8b, complex → 70b, + fallback cascade
```

## Cross-cutting layers

```
SAFETY (Phase 3, src/safety/)         OBSERVABILITY + EVALS (Phase 4)
untrusted doc text →                  every request → Tracer (spans, tokens, latency)
  1 instruction/data separation          → cost (tokens × rate)
  2 input sanitization                    → latency (TTFT, p50/p95)
  3 output checks (trusted facts,      golden set (40 Q) → answer stage → LLM-judge
    PII redaction)                        → CI gate (fail build if score drops)
```

## The flow of one request (agent example)
1. **Router** classifies the request → picks the model.
2. **Agent loop:** LLM decides a tool → tool contract validates args → runs → validates
   output → result fed back → repeat, under loop/tool budgets → stop on `finish`.
3. **Tools** pull from Track B (extracted facts) or compute; the comparator joins both.
4. **Tracer** records every span (tokens, latency); **cost** and **latency** reports read
   that data; the **judge** grades the final answer against the golden set.
5. **Safety** wraps any path that feeds untrusted doc text to the model.

## Key design choices (and where they're argued)
- Local, dependency-light everything (NumPy vector store, from-scratch BM25, hand-rolled
  validators) — appropriate at ~35 docs; documented upgrade paths.
- Trusted structured data (Track B) kept separate from untrusted prose — this separation
  is what lets safety defenses (ADR 0002/0003, F12) verify claims a fooled model can't.
- Model backend is swappable (Groq now; ADR 0001) → enabled routing (ADR 0003).
- Decisions recorded as ADRs: 0001 model backend, 0002 freshness, 0003 routing, 0004
  caching, plus the finetune-vs-RAG judgment.
```
