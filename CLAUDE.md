# CLAUDE.md — Project Constitution for "Baraat"

> Read this file in full at the start of every session before writing any code.
> This is not a normal app-building project. The app is the *vehicle*; the real
> deliverable is a portfolio of demonstrated AI product management competencies.
> Every decision should be made with that in mind.

---

## 1. What this project actually is

**Surface description:** Baraat is a wedding-vendor research and due-diligence
agent for the Indian wedding market. It researches vendors (photographers,
caterers, decorators, venues, makeup artists), flags contract/pricing red
flags, compares options against a budget, and defends itself against
manipulated vendor listings.

**Real purpose:** The builder (Saimukesh) is an AI Product Manager building a
portfolio project to demonstrate hands-on, defensible understanding of 16
specific AI-product competencies — the kind a Google/Meta-caliber AI PM
interview panel would probe. The product's domain (weddings) is intentionally
not the impressive part. What's impressive is:

- Tradeoffs are articulated with evidence, not asserted
- Failures are deliberately created, caught, documented, and fixed — not hidden
- Claims are quantified (recall@5, cost per request, latency, accuracy deltas)
  against a real golden eval set, not vibes
- The system has a regression-prevention mechanism (CI eval gate), not just a
  one-time demo

**Therefore:** when in doubt between "ship the feature" and "make the
tradeoff/failure visible and documented," choose the latter. A working demo
with no failure log is a worse portfolio artifact than a demo with 2 fewer
features and a sharp failure log.

---

## 2. The 16 competencies this project must demonstrate

Each one must map to something *concretely buildable and demoable* — not a
slide bullet. Treat this table as the actual definition of "done" for the
project as a whole.

| # | Competency | Where it lives in Baraat |
|---|---|---|
| 1 | Evals: golden sets, regression tests, LLM-as-judge, human evals | Phase 4 — `/evals` golden set + judge harness |
| 2 | Retrieval evals: recall, precision, grounding, attribution, citation quality | Phase 1 — retrieval pipeline + before/after metrics |
| 3 | Spec-by-example: input/output examples, edge cases, failure cases | Phase 1-2 — schema specs with example-driven contracts |
| 4 | Context engineering: context window, retrieval order, lost-in-the-middle | Phase 1 — deliberately tested with buried red-flag docs |
| 5 | RAG architecture: chunking, embeddings, hybrid search, reranking, freshness | Phase 1 — core build |
| 6 | MCP and tool design: schemas, descriptions, contracts, argument validation, retry safety | Phase 2 — tool layer |
| 7 | Structured output reliability: schema validation, repair loops, fallback chains | Phase 1-2 — every tool/retrieval call |
| 8 | Agent guardrails: loop budgets, tool budgets, stop conditions, recovery paths | Phase 2 — orchestration layer |
| 9 | Model routing and fallback: task classifiers, fallback cascades, degraded-mode UX | Phase 4 — router across ≥2 task types |
| 10 | Prompt caching vs semantic cache tradeoffs | Phase 4 — measured, documented as a tradeoff writeup |
| 11 | Latency engineering: first-token latency, per-token speed, prefill vs decode, streaming | Phase 4 — traced and reported |
| 12 | LLM observability: traces, spans, token counts, drift, error rates | Phase 4 — `/observability` |
| 13 | Cost attribution: per feature, workflow, tenant, user journey | Phase 4 — cost report by request type |
| 14 | Safety engineering: prompt injection defense, data leakage prevention, permission boundaries, multi-tenant isolation | Phase 3 — explicit attack + defense |
| 15 | Fine-tuning vs in-context learning vs RAG vs distillation — when each is the wrong tool | Documented as a decision-record (ADR), not built — this is a judgment artifact |
| 16 | Production failure modes: hallucinated tool calls, malformed JSON, stale retrieval, runaway agents, silent eval regressions | Continuous — logged in `/docs/failure-log.md` throughout, not just at the end |

If at any point a build step doesn't clearly map to one of these 16, pause and
ask why we're doing it.

---

## 3. Operating principles for Claude Code on this project

1. **Break things on purpose before fixing them.** When a phase plan says
   "what breaks on purpose," actually run the broken version, capture the
   real output (good or bad), and log it in `/docs/failure-log.md` *before*
   building the fix. The before/after pair is the artifact, not the fix alone.

2. **Every retrieval or tool change gets measured, not assumed.** If we add
   reranking, hybrid search, a new tool, or a guardrail, re-run the relevant
   eval questions and report the delta. No "this should help" — show the
   number.

3. **Structured output by default.** Any LLM call whose output will be used
   programmatically (not just displayed as prose to a human) must have a
   defined JSON schema and validation step. If the model returns malformed
   output, that's a logged failure-mode event, not a silent retry.

4. **Explain architectural choices in plain language as you make them.**
   Saimukesh is using this project specifically to be able to explain *why*
   in an interview — e.g., "I used hybrid search here because pure semantic
   search blurred exact price matches; here's the eval delta." Don't just
   write the code — narrate the tradeoff in a comment or commit message.

5. **Small, real commits.** Commit at meaningful checkpoints (end of each
   numbered step within a phase), with commit messages that state what was
   built AND what tradeoff or failure it addresses. This commit history is
   itself part of the portfolio — a reviewer should be able to read the git
   log and understand the project's reasoning arc.

6. **Don't gold-plate the domain.** Resist the urge to add wedding-specific
   features that don't map to one of the 16 competencies. If a feature idea
   comes up that's "cool for a wedding app" but doesn't teach/demonstrate
   anything from the table above, defer it to a "nice to have, out of scope"
   note instead of building it.

7. **Fictional data only.** All vendor profiles, prices, names, and contact
   details are synthetic. Never use real businesses, real phone numbers, or
   real GST/registration numbers, even as "realistic-looking" examples.

8. **Stay within Phase boundaries.** Don't build Phase 3's injection defenses
   while still in Phase 1, even if it seems efficient — the project's value
   partly comes from the sequencing itself being demonstrable (you can show
   "here's the system before safety hardening, here's after").

---

## 4. Tech stack & conventions

- **Language:** Python for the core pipeline (retrieval, tools, evals) —
  ecosystem fit for embeddings/RAG/eval tooling.
- **LLM:** Claude (via Anthropic API) for generation, tool use, and as
  LLM-judge in evals.
- **Storage:** Local vector store to start (e.g. Chroma or simple FAISS) —
  no need for a hosted vector DB for this scale of corpus (~35-50 docs).
- **Repo:** Git from day one. Push to GitHub as a public (or unlisted, builder's
  choice) repo — this repo *is* the interview artifact, so structure and
  commit history matter as much as final functionality.
- **Docs live in `/docs`, not just in chat history.** Anything explained
  conversationally that's worth remembering gets written to a markdown file.

---

## 5. Folder structure (target)

```
baraat/
├── CLAUDE.md                  # this file
├── PRD.md                     # product spec
├── PHASE_PLAN.md              # phase-by-phase roadmap & deliverables
├── README.md                  # public-facing project overview (written last)
├── data/
│   ├── vendors/                # synthetic vendor corpus (raw docs)
│   └── golden_set/             # eval questions + expected answers
├── src/
│   ├── ingestion/               # chunking, embedding
│   ├── retrieval/               # hybrid search, reranking
│   ├── tools/                   # budget allocator, contract checker, etc.
│   ├── agent/                   # orchestration, guardrails, routing
│   └── schemas/                 # structured output schemas
├── evals/
│   ├── golden_set_runner.py
│   ├── llm_judge.py
│   └── results/                 # versioned eval run outputs
├── observability/
│   └── traces/
├── docs/
│   ├── failure-log.md           # the running "what broke and how we caught it" log
│   ├── decision-records/        # ADRs, including the fine-tuning vs RAG vs ICL writeup
│   └── architecture-diagram.md
└── tests/
```

---

## 6. Current status

See `PHASE_PLAN.md` for the live phase tracker. Always check current phase
before starting work in a new session.
