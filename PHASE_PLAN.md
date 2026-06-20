# PHASE_PLAN.md — Live Roadmap & Status Tracker

> Update the "Current Phase" marker and checkboxes as work progresses.
> Do not start a phase's tasks until the previous phase's deliverables are
> checked off — the sequencing is part of what makes this project teach
> what it's supposed to teach (see CLAUDE.md §3.8).

**Current Phase: 1 — RAG Core**

---

## Phase 1 — RAG Core
**Competencies:** #2 retrieval evals, #4 context engineering, #5 RAG
architecture, #7 structured output reliability (first pass), #3 spec-by-example

### Tasks
- [ ] Generate synthetic vendor corpus per PRD.md §3 (~35 docs, deliberate
      messiness built in, Phase-3-reserved docs clearly marked)
- [ ] Define and validate the structured output schema (PRD.md §4)
- [ ] Build ingestion pipeline: chunking strategy decided + justified
- [ ] Build embedding + vector store
- [ ] Build baseline retrieval (semantic-only)
- [ ] Write first 8-10 golden questions covering exact-match and red-flag
      cases specifically
- [ ] Run baseline retrieval against those questions — **capture real
      output, including failures**, log to failure-log.md
- [ ] Add hybrid (keyword + semantic) search
- [ ] Re-run same questions — log delta
- [ ] Add reranking
- [ ] Re-run same questions — log delta
- [ ] Document freshness handling approach for stale-price vendors
- [ ] Write up Phase 1 results: recall/precision before vs after each
      change, with real numbers

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
- [ ] Design tool schemas for all 4 tools in PRD.md §5 (input/output
      contracts, argument validation rules)
- [ ] Implement `budget_allocator`
- [ ] Implement `contract_risk_checker`
- [ ] Implement `payment_schedule_validator`
- [ ] Implement `vendor_comparator` (multi-tool orchestration)
- [ ] Build retry/repair loop for malformed tool outputs
- [ ] Deliberately trigger a malformed-output case — log to failure-log.md
- [ ] Deliberately trigger an agent loop (e.g. comparator re-calling a tool
      unnecessarily) — implement and demonstrate a loop budget catching it
- [ ] Implement tool budget (max tool calls per request) + stop condition
- [ ] Document recovery path when a tool budget is exhausted (degraded
      response, not silent failure)

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
