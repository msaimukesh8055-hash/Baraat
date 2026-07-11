"""Offline demo of routing + fallback (no API calls — safe under the daily cap).

  python -m src.agent.demo_router

1. Classify all 40 golden questions -> which model each routes to.
2. Estimate the cost saving vs an all-large-model baseline (real Groq rates).
3. Demonstrate the fallback cascade with a deliberately-failing primary backend.
"""
import json
from pathlib import Path

from .router import Router, classify, SMALL, LARGE
from ..observability.cost import cost_usd

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "data" / "golden_set" / "golden_set.json"

# A nominal single-call token profile per answered question (from the cost trace:
# ~653 input + ~18 output for a grounded answer). Used only for the savings estimate.
TOK_IN, TOK_OUT = 653, 18


def routing_table():
    questions = json.loads(GOLDEN.read_text())
    rows = [(q["id"], q["behavior"], classify(q["question"])) for q in questions]

    small_n = sum(1 for _, _, r in rows if r.model == SMALL)
    large_n = len(rows) - small_n
    print("=== ROUTING DECISIONS (40 golden questions) ===")
    print(f"{'id':<5}{'behavior':<22}{'task_type':<18}{'model'}")
    for qid, behavior, r in rows:
        print(f"{qid:<5}{behavior:<22}{r.task_type:<18}{'8b' if r.model==SMALL else '70b'}")
    print(f"\nrouted to small(8b): {small_n}   large(70b): {large_n}")

    # Cost: all-large baseline vs routed.
    all_large = len(rows) * cost_usd(TOK_IN, TOK_OUT, LARGE)
    routed = (small_n * cost_usd(TOK_IN, TOK_OUT, SMALL)
              + large_n * cost_usd(TOK_IN, TOK_OUT, LARGE))
    saving = (1 - routed / all_large) * 100 if all_large else 0
    print(f"\n=== COST (illustrative, {len(rows)} single-call requests) ===")
    print(f"  all-70b baseline : ${all_large:.5f}")
    print(f"  routed (8b/70b)  : ${routed:.5f}")
    print(f"  saving           : {saving:.0f}%")


class _FailingBackend:
    model = "primary(broken)"
    def complete(self, messages, **kw):
        raise RuntimeError("primary model timed out")


class _OkBackend:
    def __init__(self, name):
        self.model = name
    def complete(self, messages, **kw):
        return {"text": f"answer from {self.model}", "usage": {}, "latency": 0.0, "model": self.model}


def fallback_demo():
    print("\n=== FALLBACK CASCADE DEMO (no API) ===")
    # Route a simple question -> it prefers 8b; make 8b fail, ensure it falls back to 70b.
    backends = {SMALL: _FailingBackend(), LARGE: _OkBackend(LARGE)}
    router = Router(backends)
    q = "What is the price for Ever After Films?"
    res = router.complete(q, [{"role": "user", "content": q}])
    print(f"question routed to: {res['routed_to']} (8b)")
    print(f"8b failed -> fell_back={res['fell_back']} -> model_used={res['model_used']}")
    print(f"answer: {res['output']['text']}")
    print("=> a model failure degrades to the fallback instead of erroring out.")


def main():
    routing_table()
    fallback_demo()


if __name__ == "__main__":
    main()
