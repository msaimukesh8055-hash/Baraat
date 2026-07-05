# Phase 2 — Tool Contracts (why every tool needs a schema)

> The "why bother" behind Phase 2 step 1. Plain-language, so I can explain it.
> Short version: a **contract** is the precise agreement that lets a fuzzy LLM
> (the agent) safely call exact code (a tool). Same idea as the Phase 1 vendor
> schema — define the shape first, then validate against it.

---

## 1. The core problem a contract solves

The new thing in Phase 2: an **LLM (the agent) decides to call tools on its own.**
- An **LLM is fuzzy** — it deals in words.
- A **tool is exact** — it's code that needs precise inputs.

That gap is the danger:

> The agent might call `budget_allocator` with *"split fifteen lakhs, mostly on the
> venue."* But the code needs `total_budget_inr = 1500000` and
> `weights = {venue: 0.4, ...}`. If we don't pin the exact shape down, the tool
> either **crashes** or **silently guesses wrong.**

A **contract** closes that gap. It's the *same reason* we built `vendor.schema.json`
before the extractor in Phase 1: define the exact shape, then validate against it.

---

## 2. What "schema" even means

A **schema = a description of the allowed *shape* of data**: which fields exist, what
type each is (number? text?), what range is allowed (budget > 0, rating 0–5). It is
**not** the data — it's the *rules for what counts as valid data*.

Each tool gets **two** schemas, because a tool has two sides:

```
        INPUT schema                          OUTPUT schema
   "what you must give it"                "what it promises back"
            │                                     │
            ▼                                     ▼
 total_budget_inr: number>0   ─►  budget_allocator  ─►  allocations: {category: amount}
 weights: {category: number}                           total_allocated_inr: number
```

---

## 3. The four things we define per tool

Using `budget_allocator` as the running example:

| Part | What it is | For `budget_allocator` | Why it exists |
|---|---|---|---|
| **description** | plain-English "what + when" | "Split a total budget across the 5 categories by weights." | so the **agent** knows *when* to pick this tool |
| **input_schema** | exact arguments allowed | `total_budget_inr` (number > 0), `weights` (category → number) | so we can **reject a bad call before running** |
| **output_schema** | exact result shape | `allocations` (category → amount), `total_allocated_inr` | so we can **check/repair the result** |
| **rules + failure_modes** | cross-field checks & known breakages | "weights can't all be zero"; "negative budget" | what we'll **validate and deliberately break** |

---

## 4. With vs without the contract (the whole point in one picture)

**Without a contract:**
```
agent → budget_allocator("fifteen lakhs", "mostly venue")
      → 💥 code chokes, or invents a number. Silent garbage.
```

**With the contract:**
```
agent → reads description, knows to call:
        budget_allocator(total_budget_inr=1500000,
                         weights={venue:0.4, caterer:0.3, ...})
      → INPUT check: is total_budget_inr a positive number? ✅
      → if the agent had sent -500 → REJECTED with a clear error, before any math
      → runs → OUTPUT check: do the amounts sum to ₹15L? ✅
```

The contract is the **guardrail at the tool's door** — on the way *in* (are the
arguments valid?) and on the way *out* (is the result well-formed?).

---

## 5. Why define all this NOW, before the logic

Same discipline as Phase 1: **decide what "correct" means before building the
machine.** Once the contract is fixed:
- the **agent** has a stable thing to call,
- the **validation layer** has a stable thing to check against,
- "done" for each tool is unambiguous.

It's the tool-world version of a move I already understood for extraction:
`vendor.schema.json` was the contract for a **record**; `src/tools/contracts.py` is
the contract for a **tool**.

---

## 6. The four contracts we defined (quick reference)

| Tool | Key input | Its headline failure mode |
|---|---|---|
| `budget_allocator` | total_budget_inr, weights | negative budget / weights sum to zero |
| `payment_schedule_validator` | installments (percent each) | a "120%" instalment; percents ≠ 100 |
| `contract_risk_checker` | contract_text | **false negative** — misses a real risk |
| `vendor_comparator` | vendor_ids (2–3) | **runaway loop** → caught by loop budget |

---

## Mini-recap
- A **contract** lets a **fuzzy LLM agent** safely call **exact tool code**.
- **Schema = rules for the shape of data**; each tool has an **input** and an
  **output** schema.
- We define **description** (when to use), **input_schema** (validate the call),
  **output_schema** (validate the result), plus rules & failure modes.
- The contract is a **guardrail at the tool's door**, both directions.
- Defined **before** the logic — same "spec before build" discipline as the Phase 1
  vendor schema.
