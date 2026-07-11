"""Cost attribution report — reads saved traces and groups cost by request type.

  python -m src.observability.cost_report

Request type is inferred from each trace's spans:
  - has tool spans  -> "agent+tools"  (the multi-step agent workflow)
  - only llm spans  -> "answer/generation" (retrieve -> compose)
This demonstrates competency #13: cost per request TYPE, not just a grand total —
the difference between "it costs $X" (junior) and "a contract workflow costs 8x a
lookup" (the PM insight that drives pricing/routing decisions).
"""
import glob
import json
from collections import defaultdict
from pathlib import Path

from .cost import trace_cost

REPO = Path(__file__).resolve().parents[2]
TRACES = REPO / "observability" / "traces"


def _request_type(trace: dict) -> str:
    kinds = {s.get("kind") for s in trace.get("spans", [])}
    return "agent+tools" if "tool" in kinds else "answer/generation"


def main():
    files = sorted(glob.glob(str(TRACES / "trace_*.json")))
    if not files:
        raise SystemExit("No traces found in observability/traces/ — run a traced request first.")

    by_type = defaultdict(lambda: {"n": 0, "usd": 0.0, "tokens": 0, "ms": 0.0})
    per_model_total = defaultdict(float)
    grand = 0.0

    print(f"{'trace':<16}{'type':<20}{'tokens':>8}{'cost_usd':>12}{'ms':>10}")
    print("-" * 66)
    for f in files:
        t = json.loads(Path(f).read_text())
        total, per_model = trace_cost(t)
        rtype = _request_type(t)
        su = t.get("summary", {})
        toks = su.get("tokens_total", 0)
        ms = su.get("total_ms", 0)
        print(f"{t['trace_id']:<16}{rtype:<20}{toks:>8}{total:>12.6f}{ms:>10.0f}")
        b = by_type[rtype]
        b["n"] += 1; b["usd"] += total; b["tokens"] += toks; b["ms"] += ms
        for m, c in per_model.items():
            per_model_total[m] += c
        grand += total

    print("\n=== COST PER REQUEST TYPE ===")
    print(f"{'type':<20}{'n':>4}{'avg_usd':>12}{'avg_tokens':>12}{'avg_ms':>10}")
    for rtype, b in by_type.items():
        n = b["n"]
        print(f"{rtype:<20}{n:>4}{b['usd']/n:>12.6f}{b['tokens']//n:>12}{b['ms']/n:>10.0f}")

    print("\n=== COST PER MODEL ===")
    for m, c in per_model_total.items():
        print(f"  {m:<28} ${c:.6f}")

    print(f"\nGRAND TOTAL over {len(files)} traced requests: ${grand:.6f}")
    print("(Groq published rates; free-tier ACTUAL spend = $0 — figures are illustrative.)")


if __name__ == "__main__":
    main()
