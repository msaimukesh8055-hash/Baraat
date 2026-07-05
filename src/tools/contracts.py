"""Tool contracts for Phase 2 — schemas, descriptions, validation rules ONLY.

This is STEP 1 of Phase 2: define *what each tool promises* before writing any
logic (same discipline as Phase 1, where the vendor schema came before the
extractor). Competency #6 (tool design): a tool is only as good as its contract —
a clear description (so the agent knows WHEN to call it), a typed input schema (so
arguments can be validated BEFORE running), and a typed output schema (so the
result can be validated and, if malformed, repaired).

Nothing here executes. `src/tools/*.py` will implement each `run()` against these
contracts in step 2.

Each contract is a dict:
  name          - stable identifier the agent uses to call the tool
  description   - what the agent reads to decide whether this tool fits the request
  input_schema  - JSON Schema for the arguments (draft 2020-12 style)
  output_schema - JSON Schema for the return value
  arg_rules     - human-readable cross-field validation rules a plain schema can't
                  express (checked in code, like Phase 1's Layer-2 validation)
  failure_modes - the ways this tool can go wrong (what we'll deliberately trigger)
"""

CATEGORIES = ["photographer", "caterer", "decorator", "venue", "makeup_artist"]


# ---------------------------------------------------------------------------
# 1. budget_allocator — a calculator with constraints
# ---------------------------------------------------------------------------
BUDGET_ALLOCATOR = {
    "name": "budget_allocator",
    "description": (
        "Split a total wedding budget (INR) across the five vendor categories "
        "according to caller-supplied weights. Use when the user wants to know how "
        "much to spend per category given a fixed total. Returns a rupee amount per "
        "category that sums to the total."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["total_budget_inr", "weights"],
        "properties": {
            "total_budget_inr": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Total budget in INR; must be positive.",
            },
            "weights": {
                "type": "object",
                "description": (
                    "Relative weight per category. Keys must be a subset of the five "
                    "categories; values are non-negative and need not sum to 1 "
                    "(they are normalized). At least one weight must be > 0."
                ),
                "additionalProperties": {"type": "number", "minimum": 0},
            },
        },
    },
    "output_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["allocations", "total_allocated_inr", "notes"],
        "properties": {
            "allocations": {
                "type": "object",
                "additionalProperties": {"type": "number", "minimum": 0},
                "description": "category -> allocated INR amount",
            },
            "total_allocated_inr": {"type": "number", "minimum": 0},
            "notes": {"type": "string"},
        },
    },
    "arg_rules": [
        "total_budget_inr > 0 (reject negative or zero).",
        "every key in weights must be one of the 5 categories.",
        "every weight >= 0; at least one weight > 0 (can't normalize all-zero).",
    ],
    "output_rules": [
        "sum(allocations.values()) == total_allocated_inr == total_budget_inr "
        "(within a small rounding tolerance).",
        "no allocation is negative.",
    ],
    "failure_modes": [
        "negative / zero total budget (bad arg)",
        "weights that sum to zero (cannot normalize)",
        "unknown category key (bad arg)",
        "rounding causing allocations not to sum to total (output-validation catch)",
    ],
}


# ---------------------------------------------------------------------------
# 2. payment_schedule_validator — a rule-checker (argument-validation showcase)
# ---------------------------------------------------------------------------
PAYMENT_SCHEDULE_VALIDATOR = {
    "name": "payment_schedule_validator",
    "description": (
        "Check a proposed vendor payment schedule against red-flag heuristics "
        "(e.g. too much money upfront, instalments that don't add up to 100%). Use "
        "when the user shares a payment plan and asks whether it looks safe or fair."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["installments"],
        "properties": {
            "installments": {
                "type": "array",
                "minItems": 1,
                "description": "Ordered list of instalments, earliest first.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["percent"],
                    "properties": {
                        "label": {"type": "string"},
                        "percent": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Share of the total, 0-100.",
                        },
                        "due": {
                            "type": "string",
                            "description": "Free-text milestone or ISO date "
                            "(e.g. 'on booking', 'event day', '2026-11-20').",
                        },
                    },
                },
            }
        },
    },
    "output_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["valid", "total_percent", "risk_flags"],
        "properties": {
            "valid": {"type": "boolean", "description": "Do the percents sum to 100?"},
            "total_percent": {"type": "number"},
            "risk_flags": {"type": "array", "items": {"type": "string"}},
        },
    },
    "arg_rules": [
        "each instalment percent in [0, 100] (a '120%' instalment is a bad arg).",
        "at least one instalment.",
    ],
    "output_rules": [
        "valid == (abs(total_percent - 100) <= tolerance).",
        "risk_flags is [] when the schedule is clean (never null).",
    ],
    "heuristics": [
        ">50% due before the event/delivery -> 'high upfront' risk flag.",
        "100% due on booking -> 'full prepayment' risk flag.",
        "percents don't sum to 100 -> valid=false + flag.",
    ],
    "failure_modes": [
        "instalment percent > 100 (bad arg, rejected by schema)",
        "percents summing to 90 or 110 (valid=false path)",
    ],
}


# ---------------------------------------------------------------------------
# 3. contract_risk_checker — a text scanner (false negatives are the risk)
# ---------------------------------------------------------------------------
CONTRACT_RISK_CHECKER = {
    "name": "contract_risk_checker",
    "description": (
        "Scan a vendor contract's text for risky clauses (large upfront payment, no "
        "cancellation/refund clause, vague delivery timeline). Use when the user "
        "pastes contract language and asks whether it is risky. Returns a list of "
        "flagged risks with the evidence text and an overall risk level."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["contract_text"],
        "properties": {
            "contract_text": {
                "type": "string",
                "minLength": 1,
                "description": "Raw contract / terms text to scan.",
            }
        },
    },
    "output_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["overall_risk", "risk_flags"],
        "properties": {
            "overall_risk": {"type": "string", "enum": ["low", "medium", "high"]},
            "risk_flags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["pattern", "severity", "evidence"],
                    "properties": {
                        "pattern": {"type": "string", "description": "which risk"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "evidence": {"type": "string", "description": "quoted text"},
                    },
                },
            },
        },
    },
    "arg_rules": ["contract_text must be non-empty."],
    "output_rules": [
        "overall_risk == highest severity among risk_flags (low if none).",
        "each flag must quote the evidence span it fired on (attribution).",
    ],
    "patterns": [
        ">50% or full advance payment",
        "no cancellation clause",
        "no refund policy",
        "vague delivery timeline ('approximately', 'around', no firm date)",
        "amendments allowed verbally only",
    ],
    "failure_modes": [
        "FALSE NEGATIVE: a real risky clause phrased unusually is missed "
        "(the headline eval concern — measured against known-risky sample contracts)",
        "false positive: benign boilerplate flagged as risk",
    ],
}


# ---------------------------------------------------------------------------
# 4. vendor_comparator — the orchestration case (multi-tool; drives guardrails)
# ---------------------------------------------------------------------------
VENDOR_COMPARATOR = {
    "name": "vendor_comparator",
    "description": (
        "Compare 2-3 shortlisted vendors side by side on price, rating, and known "
        "red flags. Use when the user names a few vendors and asks which is better / "
        "to see them compared. Pulls price & rating from the extracted records and "
        "red flags from retrieval; may therefore trigger several internal steps."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["vendor_ids"],
        "properties": {
            "vendor_ids": {
                "type": "array",
                "minItems": 2,
                "maxItems": 3,
                "items": {"type": "string"},
                "description": "2-3 vendor_ids (filenames without extension).",
            }
        },
    },
    "output_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["rows", "recommendation"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["vendor_id", "name", "price_range_inr", "rating", "red_flag_count"],
                    "properties": {
                        "vendor_id": {"type": "string"},
                        "name": {"type": "string"},
                        "price_range_inr": {
                            "type": "object",
                            "properties": {"min": {"type": "number"}, "max": {"type": "number"}},
                        },
                        "rating": {"type": "number", "minimum": 0, "maximum": 5},
                        "red_flag_count": {"type": "integer", "minimum": 0},
                        "price_confidence": {"type": "string"},
                    },
                },
            },
            "recommendation": {"type": "string"},
        },
    },
    "arg_rules": [
        "2-3 vendor_ids (comparing 1 is pointless; >3 is out of scope).",
        "each vendor_id must exist in data/extracted/ (else a bad-arg error).",
    ],
    "output_rules": [
        "one row per requested vendor_id, in the same order.",
        "rating in [0,5]; red_flag_count >= 0.",
    ],
    "failure_modes": [
        "RUNAWAY LOOP: re-fetching the same vendor repeatedly -> loop budget catches it",
        "unknown vendor_id (bad arg)",
        "one vendor missing data -> degraded row, not a crash",
    ],
}


# The registry the agent will read (name + description + input_schema) to decide
# which tool to call. Output schemas / rules are used by the reliability layer.
TOOL_CONTRACTS = [
    BUDGET_ALLOCATOR,
    PAYMENT_SCHEDULE_VALIDATOR,
    CONTRACT_RISK_CHECKER,
    VENDOR_COMPARATOR,
]

CONTRACTS_BY_NAME = {c["name"]: c for c in TOOL_CONTRACTS}
