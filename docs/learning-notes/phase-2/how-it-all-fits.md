# Phase 2 — How It All Fits (the two-layer architecture)

> The end-to-end picture once the tools + agent + guardrails are wired. Answers
> the question I kept circling: "does every call really get validated, and where
> do the guardrails sit?" Short answer: **yes, two layers.**

---

## 1. The corrected full flow

```
question (natural language, e.g. "split my 15 lakh")
   │
   ▼
AGENT (LLM) decides: which tool + what ARGUMENTS
   │
   ▼
┌─────────── per-call gate (SAME mechanism for EVERY tool) ───────────┐
│  [1] INPUT SCHEMA  — are the args valid?        ← yes, every tool    │
│  [2] tool runs                                                       │
│  [3] OUTPUT SCHEMA — is the result well-formed? ← yes, every tool    │
└─────────────────────────────────────────────────────────────────────┘
   │  result fed back
   ▼
loop back to AGENT  ◄──── wrapped by GUARDRAILS (loop/tool budget, stop, degrade)
   │
   ▼
AGENT writes the final answer (free text — NOT schema-checked)
```

---

## 2. Two refinements I needed (easy to get slightly wrong)

**Refinement 1 — it's the ARGUMENTS, not the raw QUESTION, that hit the schema.**
The question is words ("split my 15 lakh"). The **LLM converts it into arguments**
(`total_budget_inr: 1500000, weights: {...}`), and *those arguments* pass through the
input schema. That's exactly why the budget example could self-correct: the model
produced bad *arguments* (`catering`), and the input schema caught *them*.

**Refinement 2 — the FINAL answer to the user is NOT schema-checked.**
The output schema checks each **tool's structured result** (the JSON a tool returns).
The **final prose sentence** the agent writes for the user ("Grand Thali Events is
better, 4.7 rating…") is free text — it does not pass through any tool output schema.
Only tool outputs are gated; the closing sentence is not.

---

## 3. The two layers (say this in an interview)

| Layer | What it guards | Where it lives | Applies to |
|---|---|---|---|
| **Per-call (tool contract)** | one tool call: args in, result out | `execute_tool` in `src/tools/base.py` | **every** tool, identically |
| **Per-sequence (guardrails)** | the agent's whole loop of calls | `src/agent/orchestrator.py` | the agent, once per request |

- **Per-call** = "is *this one* call valid?" — input schema → run → output schema, the
  **same wrapper for all four tools**, no bypass.
- **Per-sequence** = "is the agent's *whole sequence* bounded and sane?" — loop budget,
  tool budget, stop condition, degraded fallback.

---

## 4. Confirming the mental model

| Statement | Verdict |
|---|---|
| Each tool has its own schema | ✅ |
| Every tool call's **input** is validated, whatever the tool | ✅ (same `execute_tool`) |
| Every tool's **output** is validated too | ✅ |
| The agent has overall guardrails on top | ✅ |
| The raw **question** passes through the schema | ⚠️ the **arguments** do, not the question |
| The final **answer** passes through an output schema | ⚠️ no — final prose is free text |

---

## Mini-recap
- **One sentence:** every tool call is gated in and out the same way, and the agent's
  whole sequence of calls is bounded by guardrails.
- The **arguments** (LLM-produced) are what the input schema validates — not the raw
  question.
- The **final prose answer** is free text, not schema-checked; only **tool outputs**
  are.
- Two layers: **per-call contract** (uniform across tools) + **per-sequence
  guardrails** (agent-wide).
