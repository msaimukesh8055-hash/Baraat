# Phase 4 — Reading a Trace (why 1 question ≠ 1 LLM call)

> What the observability tracer actually produced, and the key thing it taught:
> an agent question is one LLM call PER STEP in the loop, not one call per question.
> Companion to `phase-4-scope.md`.

---

## 1. The request we traced

> "I have 12 lakh for my wedding. Split it with about 45% for the venue and 30% for
> catering, **and** check if a payment plan of 80% upfront is risky."

It's really **two tasks in one**: (1) split the budget, (2) check the payment plan.

---

## 2. The trace (real output)

```
request (2656 ms total)
  decide → llm.complete [1178+63 tok]  → tool.budget_allocator          [FAIL: input_validation]
  decide → llm.complete [1282+63 tok]  → tool.budget_allocator          [ok]
  decide → llm.complete [1414+71 tok]  → tool.payment_schedule_validator [ok]
  decide → llm.complete [1528+46 tok]  → (finish)

SUMMARY: 2656 ms | 4 LLM calls | 3 tool calls | 5645 tokens (5402 in + 243 out)
```

---

## 3. THE key point — why one question caused FOUR LLM calls

Because the agent is a **loop**, not a single shot (Phase 2). It thinks → acts →
looks → thinks again, and **each "think" is one LLM call.** So the LLM is called once
**per decision**, not once per question.

| LLM call | The agent's decision | Result |
|---|---|---|
| 1 | "call `budget_allocator`" | used wrong category "catering" → tool **FAILED** |
| 2 | "fix it, call `budget_allocator` again" | used "caterer" → tool **ok** |
| 3 | "now call `payment_schedule_validator`" | tool **ok** |
| 4 | "I have everything → **finish**" | wrote the final answer |

**4 LLM calls = 4 trips around the loop.** Two tools + one retry = four decisions.

> **The rule:** for an agent, `LLM calls ≈ number of decision steps`, NOT number of
> questions. A simple one-tool question ≈ 2 LLM calls (pick the tool, then finish);
> a complex multi-tool one is more. This is exactly why the **loop budget** guardrail
> exists — it caps how many of these decision-calls can happen (we set it to 6).

---

## 4. Does a trace cover "everything we built before"?

No — and that's expected. A trace records **only what THAT request actually used.**
- This request used the **agent + 2 tools + 4 LLM calls**.
- It did **not** touch retrieval or extraction, because this question didn't need them.
- A different question ("does Anokhi have complaints?") would trace **retrieval**
  instead.

The tracer is general: it records whatever runs for that specific request.

---

## 5. The three insights the trace surfaced

1. **Self-correction is visible.** The failed-then-ok `budget_allocator` pair IS the
   agent fixing its own bad argument (the F9 pattern), now shown as two spans.
2. **Input tokens dominate and grow.** 5402 in vs 243 out — and input climbs each step
   (1178 → 1282 → 1414 → 1528) because the history accumulates. Preview of where COST
   will come from: mostly input tokens.
3. **Latency ≈ model time.** The 2656 ms is ~all the four LLM calls (~500–800 ms each);
   the three tool calls together are under a millisecond. So to go faster, reduce or
   speed up the LLM calls — the tools are not the bottleneck.

---

## 6. Is 2656 ms the total time to answer?

**Yes.** 2656 ms = the full wall-clock time from question to final answer, and ~99% of
it was the four LLM calls.

---

## Mini-recap
- An **agent question = one LLM call PER decision step**, not one per question. 2 tools
  + 1 retry → 4 decisions → 4 LLM calls.
- The **loop budget** caps these decision-calls (set to 6).
- A trace shows **only what that request used** (this one: agent + tools, no
  retrieval/extraction).
- Trace insights: self-correction visible, **input tokens dominate & grow**, latency ≈
  model time. These feed the cost & latency reports next.
