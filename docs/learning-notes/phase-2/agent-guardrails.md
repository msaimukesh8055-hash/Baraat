# Phase 2 — Agent Guardrails (the leash on the agent)

> Plain-language note on the guardrails, written before building them.
> Competency #8. The tool contracts (steps 1–2) guard each *single* call; these
> guard the agent's *whole sequence* of calls.

---

## 1. Why guardrails exist at all

The agent is an **LLM that decides its own steps in a loop**: think → call a tool →
look at the result → think again → … That autonomy is powerful but dangerous. Left
unchecked, an LLM agent can:
- **loop forever** (never decide it's done),
- **call tools too many times** (waste time/money, e.g. re-fetching the same vendor),
- **get stuck** on a failing tool and keep retrying,
- **hang** and return *nothing* to the user.

Guardrails are the **leash** that makes that autonomy safe and bounded.

---

## 2. Two layers of guarding (where this sits)

- **Tool-level (already built, steps 1–2):** "is this ONE call valid?" — the
  contract validates arguments in and results out.
- **Agent-level (this file, step 3):** "is the agent's WHOLE sequence of calls
  bounded and sane?"

Both together = competency #8.

---

## 3. The agent loop, with guardrails marked

```
         user request
              │
              ▼
   ┌──────────────────────┐  ◄─── LOOP BUDGET: max N iterations of this box
   │  AGENT thinks:        │
   │  "which tool? args?   │
   │   or am I done?"      │
   └──────────┬───────────┘
              │ picks a tool
              ▼
   ┌──────────────────────┐  ◄─── TOOL BUDGET: max M tool calls total
   │  run tool (validated) │  ◄─── (tool contracts already gate in/out)
   └──────────┬───────────┘
              │ result fed back
              ▼
       STOP CONDITION met?  ──yes──►  compose final answer
              │ no
              └──────────► back to "AGENT thinks"

   if a budget is hit before STOP  ──►  DEGRADED FALLBACK (partial honest answer)
```

---

## 4. The four guardrails, each explained

| Guardrail | Problem it prevents | How it works | Baraat example |
|---|---|---|---|
| **1. Loop budget** | infinite loops — agent never stops thinking | cap loop iterations (e.g. **max 6 steps**); hit the cap → force-stop | agent keeps "thinking" without answering → killed at step 6 |
| **2. Tool budget** | over-calling / redundant calls (cost + latency) | cap total tool invocations (e.g. **max 5 calls**) | `vendor_comparator` re-fetching the same vendor over and over → blocked at call 5 |
| **3. Stop condition** | agent doesn't know when it's *done* | an explicit "final answer" signal the agent must emit; loop ends only when it fires | agent answers both "split my budget" and "check this contract" → emits done → loop ends |
| **4. Degraded fallback** | crash/hang when a budget is hit or a tool keeps failing | on budget-exhaustion or repeated failure, return a **sane partial answer + honest note**, never nothing | "Here's your budget split; I couldn't finish the contract check within the step limit." |

**Plus a fifth, smaller one:**
- **No-progress / repeat detection** — if the agent calls the *same tool with the
  same arguments* twice in a row, that's a loop not making progress → break early
  (a smarter version of the loop budget).

---

## 5. Why these are the artifacts (what we'll deliberately trigger)

- **Runaway loop** — make the agent re-call a tool pointlessly → show the **loop
  budget / repeat detection catching it.**
- **Tool-budget exhaustion** — force many calls → show a **degraded partial answer**,
  not a crash.

The point isn't that the agent misbehaves; it's that **when it does, the guardrails
contain it gracefully.** That before/after is the portfolio artifact (logged in
`docs/failure-log.md`).

---

## Mini-recap
- Guardrails = the **leash** on an autonomous agent loop.
- Four of them: **loop budget** (max steps), **tool budget** (max calls),
  **stop condition** (how it knows it's done), **degraded fallback** (partial honest
  answer instead of a crash/hang). Plus **repeat detection**.
- Tool contracts guard one call; guardrails guard the whole sequence.
- We'll deliberately trigger a runaway loop and a budget exhaustion, and show the
  guardrails catching them.
