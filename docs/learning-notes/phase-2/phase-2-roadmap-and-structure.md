# Phase 2 — Roadmap & Structure (Tools & Agent)

> My plain-language map of Phase 2, written *before* building, so I can explain it.
> Phase 2 is where Baraat stops being a set of scripts and becomes a real **agent**.
> Companion to the Phase 1 learning notes; deeper spec lives in PRD §5 and
> PHASE_PLAN Phase 2.

---

## 0. The one-line shift

> Phase 1 could **find and structure** information. Phase 2 lets Baraat **act on it**
> — do real calculations and risk checks — with an **LLM brain (the agent)** that
> decides which tool to use, kept on a leash by **guardrails** so it can't misbehave.

---

## 1. My mental model (checked & corrected)

What I had right: tools do the "work," they're triggered by the user's request, and
Phase 2 = build the tools + design their output shape + add guardrails (budgets,
conditions, backup plans).

Two corrections I needed:

1. **Not all tools are "calculators."** Three are calculator/checker-style, one is an
   orchestrator:
   - `budget_allocator` = a **calculator** (math)
   - `payment_schedule_validator` = a **rule-checker**
   - `contract_risk_checker` = a **text scanner** (reads a contract for risk patterns)
   - `vendor_comparator` = an **orchestrator** (pulls vendor data and compares; may
     use the other tools)

2. **The big new piece: the AGENT.** "The tools get used based on the request" — but
   *who decides which tool?* In Phase 1 **I** hardcoded every step. In Phase 2 an
   **LLM (the agent) decides** which tool(s) to call and in what order. That autonomy
   is the whole reason guardrails exist. (Ties back to the "script vs agent" note:
   Phase 1 = scripts; Phase 2 = the first real agent.)

---

## 2. The three competencies this phase proves

- **#6 Tool design** — schemas, descriptions, argument validation, retry safety.
- **#7 Structured-output reliability** — same validate→repair discipline as Phase 1
  extraction, now at the **tool** layer.
- **#8 Agent guardrails** — loop budgets, tool budgets, stop conditions, degraded
  recovery.

---

## 3. The four building blocks

### 3a. The tools (each a self-contained unit with a *contract*)

| Tool | Its job | How it can fail (the artifact) |
|---|---|---|
| `budget_allocator` | split a total budget across 5 categories by weights | negative budget, weights don't sum, over-allocation |
| `payment_schedule_validator` | check a payment plan against red-flag rules | bad args (a "120%" instalment, dates out of order) |
| `contract_risk_checker` | scan contract text for risky clauses | **false negative** — misses a real risk |
| `vendor_comparator` | compare 2–3 vendors on price/rating/red flags | needs many steps → can loop or over-call |

Natural split: the **first three are self-contained functions** (great for #6
contracts + #7 validation); the **comparator is the orchestration case** that forces
the agent loop and #8 guardrails.

> **Connection back to Phase 1:** the comparator is where the **extracted records
> (Track B)** finally get *used* — price/rating from the JSON, red flags from
> retrieval. The Q09 near-duplicate fix (metadata filtering by `location`) also
> naturally lives here.

### 3b. The agent (the new brain)
Reads the user's request and decides *which tool, with what arguments, and when it's
done*.

### 3c. The tool contracts (competency #6 + #7)
Every tool has: a **schema** (exact input/output shape), **argument validation**
(reject bad inputs *before* running), and **output validation** (repair malformed
output — the Phase-1 extraction discipline, now at the tool layer).

### 3d. The guardrails (competency #8) — the leash on the agent
- **Loop budget** — max thinking steps (stops infinite loops).
- **Tool budget** — max tool calls per request (stops over-calling).
- **Stop condition** — how the agent knows it's finished.
- **Degraded fallback** — if a budget is hit, return a *sane partial answer*, not a
  crash.

---

## 4. High → low, one real request (the granular view)

User asks: *"I have ₹15 lakh. Split it across vendors, and check if this caterer's
contract looks risky."*

```
USER REQUEST
    │
    ▼
┌────────────────────────────────────────────┐
│ AGENT decides step 1: "I need a budget split"│
│   → picks tool: budget_allocator             │
│   → args: {total: 1500000, weights: {...}}   │
└───────────────┬──────────────────────────────┘
                │  ⟵ GUARDRAIL: validate args first (total > 0? weights sum to 1?)
                ▼
        budget_allocator runs → returns allocation JSON
                │  ⟵ GUARDRAIL: validate output (sums to ₹15L? no negatives?)
                ▼
┌────────────────────────────────────────────┐
│ AGENT decides step 2: "now the contract"     │
│   → picks tool: contract_risk_checker        │
│   → args: {contract_text: "..."}             │
└───────────────┬──────────────────────────────┘
                │  ⟵ GUARDRAIL: tool-call count = 2 (under budget? keep going)
                ▼
        contract_risk_checker runs → returns risk flags
                │
                ▼
┌────────────────────────────────────────────┐
│ AGENT checks STOP CONDITION: "answered both  │
│ parts?" → yes → STOP, compose reply          │
└────────────────────────────────────────────┘
                │  ⟵ if NOT stopped and it hit the loop/tool budget:
                │     return a DEGRADED answer ("here's the split; couldn't
                │     finish the contract check") — never hang
                ▼
        FINAL ANSWER to user
```

Every `⟵` is a guardrail. That's the point of Phase 2: the agent has freedom to
choose steps, and the guardrails make that freedom **safe and bounded**.

---

## 5. The three failures we'll create on purpose (artifacts)

1. **Malformed tool output** → caught by output validation → **repaired** (#7).
2. **Runaway loop** — agent re-calling a tool pointlessly → **loop budget catches it**
   (#8).
3. **Tool-budget exhausted** → **degraded partial answer**, not a crash (#8).

---

## 6. Build order (incremental, like Phase 1)

1. Design the **tool schemas/contracts** for all four (input/output + validation
   rules) — no logic yet, just the contracts.
2. Build the **three self-contained tools** (budget, payment, contract) with
   validation.
3. Build the **agent orchestrator + guardrails**, and the **comparator** (multi-tool
   case).
4. **Trigger the three failures on purpose**, log each before/after.

---

## 7. The one open decision (before building)

**How does the agent call tools?**
- **Explicit loop we write ourselves** — the LLM outputs which tool + args as JSON,
  our code runs it, feeds the result back, repeats. Budgets/stop-conditions are OUR
  visible code. *Best for demonstrating #8 guardrails; more code.* ← **recommended**
- **Groq native function-calling API** — the model returns tool calls, the SDK
  manages the round-trip. More "real-world," but the loop is hidden inside the API,
  so the guardrails are harder to show explicitly.

Recommendation: the **explicit loop** — the guardrails *are* the competency here, so
we want them front and centre. (Decision to be confirmed before step 1.)

---

## Mini-recap
- Phase 2 = **tools + an agent that picks them**, with **guardrails** as the leash.
- 4 tools: 3 self-contained (budget/payment/contract), 1 orchestrator (comparator).
- Every tool has a **contract** (schema + arg validation + output repair).
- Guardrails = **loop budget, tool budget, stop condition, degraded fallback**.
- We'll deliberately trigger 3 failures (malformed output, runaway loop, budget
  exhaustion) and log each — the before/after is the artifact.
