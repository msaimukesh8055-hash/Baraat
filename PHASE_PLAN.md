# PHASE_PLAN.md — Live Roadmap & Status Tracker

> Update the "Current Phase" marker and checkboxes as work progresses.
> Do not start a phase's tasks until the previous phase's deliverables are
> checked off — the sequencing is part of what makes this project teach
> what it's supposed to teach (see CLAUDE.md §3.8).

**Current Phase: 1 — RAG Core → COMPLETE. Next: Phase 2 — Tools & Agent.**

> Phase 1 done: extraction + 3-stage retrieval arc all built, measured, and
> documented (see docs/phase1-results.md). Residual near-duplicate case (Q09)
> diagnosed, fix deferred to metadata filtering. Ready to start Phase 2.

---

## Phase 1 — RAG Core
**Competencies:** #2 retrieval evals, #4 context engineering, #5 RAG
architecture, #7 structured output reliability (first pass), #3 spec-by-example

### Tasks
- [x] Generate synthetic vendor corpus per PRD.md §3 (~35 docs, deliberate
      messiness built in, Phase-3-reserved docs clearly marked)
      → 35 docs (7×5 categories) in data/vendors/; distribution 5 stale /
        5 buried / 7 exact-match / 3 reserved; ground-truth in
        data/vendors/_corpus_manifest.md (excluded from index)
- [x] Define and validate the structured output schema (PRD.md §4)
      → schema in src/schemas/ (JSON Schema + spec-by-example); extractor with
        validate→repair→fallback in src/extraction/; mock demo proves all 3
        reliability paths; real run via Groq (llama-3.3-70b) extracted all 32
        non-reserved docs (0 repairs, 0 fallbacks). Content vs manifest: stale
        5/5, GST 6/6, buried red flags all surfaced, 1 false-positive (logged
        F4). Records in data/extracted/.
- [x] Build ingestion pipeline: chunking strategy decided + justified
      → paragraph-aware chunking w/ contextual vendor prefix (src/ingestion/
        chunker.py); 32 docs → 204 chunks. Skips _-prefixed files.
- [x] Build embedding + vector store
      → local fastembed BAAI/bge-small-en-v1.5 (384-dim); simple NumPy cosine
        store (src/retrieval/); index in data/index/.
- [x] Build baseline retrieval (semantic-only)
      → src/retrieval/search.py. Sanity queries already preview the planted
        failures: simple lookups work; buried red flag + exact-match GST miss
        (to be measured formally once golden questions exist).
- [x] Write first 8-10 golden questions covering exact-match and red-flag
      cases specifically
      → 10 questions frozen in data/golden_set/golden_set.json (2 control,
        3 buried, 2 stale, 3 exact-match)
- [x] Run baseline retrieval against those questions — **capture real
      output, including failures**, log to failure-log.md
      → recall@5=1.0 was saturated/misleading; switched to recall@1=0.80,
        MRR=0.875. Failures Q08 (rank 4), Q09 (rank 2) logged as F5.
- [x] Add hybrid (keyword + semantic) search
      → BM25 (src/retrieval/keyword_search.py) + RRF fusion
        (src/retrieval/hybrid.py). Dependency-light, pure Python.
- [x] Re-run same questions — log delta
      → recall@1 0.80→0.90, MRR 0.875→0.95. Q08 GST rank 4→1 (keyword exact
        match). Q09 survived (shared word "Udaipur" in both docs) → motivates
        reranking. Logged as F6.
- [x] Add reranking
      → cross-encoder (Xenova/ms-marco-MiniLM-L-6-v2, local) with graceful
        fallback to hybrid (src/retrieval/reranker.py).
- [x] Re-run same questions — log delta
      → NO improvement: recall@1 stayed 0.90, MRR 0.95, at ~34x latency
        (6.5ms→223.7ms). Q09 survived (impostor's disambiguation note is an
        adversarial phrase match). Decision: do NOT ship rerank; residual
        near-dup needs metadata filtering (extracted location field), not a
        better ranker. Logged as F7 (competency #15: right/wrong tool).
- [x] Document freshness handling approach for stale-price vendors
      → ADR 0002 (docs/decision-records/0002-freshness-handling.md):
        detect→flag→don't-guess policy, 3 confidence levels, retrieval
        support (Q06/Q07 rank 1), limitations.
- [x] Write up Phase 1 results: recall/precision before vs after each
      change, with real numbers
      → docs/phase1-results.md: extraction (32 docs, 0 repair/fallback,
        content 5/5·6/6·5/5, 1 FP), retrieval arc (recall@1 0.80→0.90→0.90,
        latency 5.7→6.5→223.7ms), F1–F7, judgments, honest gaps.

### Deliverable
A retrieval pipeline with measured, documented improvement across 3 stages
(baseline → hybrid → reranked), plus a clear demonstration of the
lost-in-the-middle and exact-match failure modes being caught and
addressed.

---

## Phase 2 — Tools & Agent Orchestration
**Competencies:** #6 MCP/tool design, #7 structured output reliability
(tool layer), #8 agent guardrails

### Tasks
- [x] Design tool schemas for all 4 tools in PRD.md §5 (input/output
      contracts, argument validation rules)
      → src/tools/contracts.py (name, description, input/output JSON schema,
        arg/output rules, failure modes). Step 1.
- [x] Implement `budget_allocator`
      → weight-normalized split; last category absorbs remainder (exact sum).
- [x] Implement `contract_risk_checker`
      → transparent regex/keyword scan w/ quoted evidence; false negatives
        are the intended, measurable failure mode.
- [x] Implement `payment_schedule_validator`
      → schema rejects >100% instalments; flags high-upfront / not-100 /
        majority-before-milestone.
- [x] Implement `vendor_comparator` (multi-tool orchestration)
      → pulls extracted records (Track B) for price/rating/red flags; first
        real use of Phase 1 extraction.
- [ ] Build retry/repair loop for malformed tool outputs
- [ ] Deliberately trigger a malformed-output case — log to failure-log.md
- [x] Deliberately trigger an agent loop (e.g. comparator re-calling a tool
      unnecessarily) — implement and demonstrate a loop budget catching it
      → src/agent/ orchestrator (explicit loop) + ScriptedPolicy; demo shows
        runaway loop caught by repeat detection (F8, scenario B).
- [x] Implement tool budget (max tool calls per request) + stop condition
      → tool budget (5) + loop budget (6) + explicit finish stop condition
        (F8, scenarios A/C/D).
- [x] Document recovery path when a tool budget is exhausted (degraded
      response, not silent failure)
      → degraded fallback returns a partial honest answer (F8, C/D).

### Deliverable
A working tool layer where you can show: a malformed output being caught
and repaired, a runaway loop being caught by a loop budget, and a tool
budget exhaustion producing a sane degraded response instead of a crash.

---

## Phase 3 — Safety Engineering
**Competencies:** #14 safety engineering (prompt injection, data leakage,
permission boundaries)

### Tasks
- [ ] Design 2-3 injection payloads to embed in the Phase-3-reserved vendor
      docs (e.g. hidden instruction text attempting to override budget
      constraints or force a recommendation)
- [ ] Run the **undefended** Phase 1-2 pipeline against these — confirm and
      document the attack succeeding (this failure is the artifact)
- [ ] Implement defense: instruction/data separation, input sanitization,
      output validation against expected schema/constraints
- [ ] Re-run the same attacks — document the defense holding
- [ ] Consider and document a data-leakage scenario (e.g. one vendor's
      private notes leaking into another vendor's comparison) and a
      permission-boundary scenario (e.g. ensuring budget tool can't be
      tricked into ignoring a hard ceiling)

### Deliverable
A documented before/after: undefended system manipulated by an injected
vendor listing, then the same attack failing safely after defenses are
added. This is one of the highest-value artifacts in the whole project —
treat it accordingly.

---

## Phase 4 — Evals, Observability, Cost, Routing
**Competencies:** #1 evals, #9 model routing/fallback, #10 caching
tradeoffs, #11 latency engineering, #12 LLM observability, #13 cost
attribution

### Tasks
- [ ] Finalize golden set to 30-40 questions per PRD.md §6 categories
- [ ] Build LLM-as-judge scoring harness
- [ ] Add a small human-eval pass (you, manually scoring a sample) to
      sanity-check the judge's agreement with human judgment
- [ ] Add tracing: capture spans, token counts, latency per request
- [ ] Build cost attribution report: cost per request type / per tool /
      per workflow
- [ ] Implement model routing: classify request type, route simple
      lookups to a smaller/faster model, route contract-risk analysis to a
      stronger model
- [ ] Document the routing decision with real cost/accuracy tradeoff data
- [ ] Implement and measure a fallback cascade (what happens if the
      primary model call fails or times out)
- [ ] Document prompt caching vs semantic caching tradeoff as it applies
      (or explicitly doesn't apply) to this system, with reasoning
- [ ] Measure and report first-token latency and streaming behavior

### Deliverable
A cost/latency/accuracy report with real numbers, a working model router
with documented tradeoffs, and an observability layer you can point to and
say "here's a trace of a real request."

---

## Phase 5 — CI Eval Gate & Final Packaging
**Competencies:** #16 production failure modes (consolidated), #15
fine-tuning vs ICL vs RAG vs distillation (decision record), full project
narrative

### Tasks
- [ ] Build a script that runs the golden set and fails if score drops
      below a defined threshold
- [ ] Deliberately introduce a regression and show the CI gate catching it
- [ ] Write `/docs/decision-records/finetune-vs-rag-vs-icl.md` — a
      reasoned judgment call (not a build) on when each approach would be
      the right or wrong tool for Baraat specifically
- [ ] Consolidate `/docs/failure-log.md` into a clean, readable narrative
      covering all phases
- [ ] Write `/docs/architecture-diagram.md` (or actual diagram)
- [ ] Write final `README.md` — public-facing story, written for a
      non-technical reader first, with links to deeper docs

### Deliverable
The complete, interview-ready repo: working code, a clean commit history,
a failure log, a CI gate demo, and a README that tells the whole story in
under 2 minutes of reading.
