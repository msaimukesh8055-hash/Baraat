"""Cost attribution — money = tokens x price, read straight off the trace data.

The Phase-4 point: cost is not a new measurement. Observability already records
tokens + model per LLM span; cost is just those numbers multiplied by a per-token
rate and summed. Attribution (per request, per request-type, per model) is grouping
that same data.

Rates are Groq's published on-demand $/1M-token prices (illustrative — we run on the
free tier, so ACTUAL spend is $0, but these real rates make the attribution honest and
let us reason about what it WOULD cost at scale). Input and output are priced
differently, which is why the trace splits tokens_in / tokens_out.
"""
from collections import defaultdict

# USD per 1,000,000 tokens (Groq published on-demand rates; subject to change).
PRICING = {
    "llama-3.3-70b-versatile": {"in": 0.59, "out": 0.79},
    "llama-3.1-8b-instant":    {"in": 0.05, "out": 0.08},
}
_DEFAULT = {"in": 0.59, "out": 0.79}


def cost_usd(tokens_in: int, tokens_out: int, model: str) -> float:
    p = PRICING.get(model, _DEFAULT)
    return (tokens_in * p["in"] + tokens_out * p["out"]) / 1_000_000


def trace_cost(trace: dict):
    """Return (total_usd, per_model_usd) for one trace dict (from tracer.to_dict())."""
    total = 0.0
    per_model = defaultdict(float)
    for s in trace.get("spans", []):
        if s.get("kind") == "llm":
            a = s.get("attrs", {})
            c = cost_usd(a.get("tokens_in", 0), a.get("tokens_out", 0), a.get("model", ""))
            total += c
            per_model[a.get("model", "?")] += c
    return round(total, 6), {k: round(v, 6) for k, v in per_model.items()}
