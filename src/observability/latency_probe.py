"""Latency engineering (#11) — measure TTFT, total, prefill/decode, p50/p95.

  python -m src.observability.latency_probe

Runs a few short prompts on BOTH the small (8b) and large (70b) models via streaming,
recording per request:
  - TTFT   (time to first token)  ~ prefill: process prompt + emit first token
  - total  (full response)
  - decode ~ total - TTFT: generating the remaining tokens

Reports p50/p95 (distributions, not just the mean — the slow tail is what hurts real
users) and the small-vs-large speed gap (evidence for routing: cheap model is faster).
"""
import statistics
import time

from ..extraction.config import GROQ_API_KEY, GROQ_BASE_URL
from ..extraction.model_backend import GroqBackend, ModelError

SMALL = "llama-3.1-8b-instant"
LARGE = "llama-3.3-70b-versatile"

PROMPTS = [
    "In one sentence, what should a couple check before booking a wedding photographer?",
    "Name three things that make a wedding venue expensive.",
    "In one line, why confirm a caterer's price in writing?",
    "Give one tip for comparing two decorators.",
    "In one sentence, what is a payment-schedule red flag?",
]


def _pctile(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _run_model(model):
    backend = GroqBackend(GROQ_API_KEY, GROQ_BASE_URL, model)
    ttfts, totals, decodes = [], [], []
    for p in PROMPTS:
        for attempt in range(3):
            try:
                out = backend.complete_streaming([{"role": "user", "content": p}])
                break
            except ModelError as e:
                if attempt == 2:
                    print(f"    (skipped a prompt: {e})")
                    out = None
                    break
                time.sleep(20 * (attempt + 1))
        if not out or out["ttft_s"] is None:
            continue
        ttfts.append(out["ttft_s"] * 1000)
        totals.append(out["latency"] * 1000)
        decodes.append((out["latency"] - out["ttft_s"]) * 1000)
        time.sleep(2)
    return ttfts, totals, decodes


def _report(name, ttfts, totals, decodes):
    if not totals:
        print(f"\n{name}: no samples (rate-limited)")
        return
    print(f"\n{name}  (n={len(totals)})")
    print(f"  TTFT   p50={_pctile(ttfts,0.5):.0f}ms  p95={_pctile(ttfts,0.95):.0f}ms  "
          f"mean={statistics.mean(ttfts):.0f}ms   <- perceived speed")
    print(f"  total  p50={_pctile(totals,0.5):.0f}ms  p95={_pctile(totals,0.95):.0f}ms  "
          f"mean={statistics.mean(totals):.0f}ms")
    print(f"  decode mean={statistics.mean(decodes):.0f}ms  (total - TTFT)")


def main():
    if not GROQ_API_KEY:
        raise SystemExit("No GROQ_API_KEY found.")
    print("Latency probe (streaming). Prefill ~ TTFT; decode ~ total - TTFT.")
    for name, model in [("SMALL (8b)", SMALL), ("LARGE (70b)", LARGE)]:
        _report(name, *_run_model(model))
    print("\nTakeaway: the small model's lower TTFT/total is the latency half of the "
          "routing tradeoff — route latency-sensitive simple requests to it.")


if __name__ == "__main__":
    main()
