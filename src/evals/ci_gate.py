"""CI eval gate (#16, #1) — fail the build if answer quality regresses.

The regression-prevention mechanism the whole project is built around: a demo that
passes once is worthless if the next change silently breaks it. This script scores the
latest answer-eval result against a threshold and exits non-zero (fails CI) if quality
dropped — so a regression is caught automatically, not in production.

  python -m src.evals.ci_gate                 # gate the latest eval result
  python -m src.evals.ci_gate --threshold 0.7
  python -m src.evals.ci_gate --demo          # show it PASS on baseline, FAIL on a regression

In real CI this runs `answer_eval` first; here (under the daily token cap) it gates the
most recent saved result, which is the same check.
"""
import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "evals" / "results"
THRESHOLD = 0.65


def _latest_result():
    files = sorted(glob.glob(str(RESULTS / "answer_eval_2*.json")))
    if not files:
        raise SystemExit("No answer_eval results to gate.")
    return files[-1]


def check(results_path: str, threshold: float):
    d = json.loads(Path(results_path).read_text())
    mean = d["mean_score"]
    ok = mean >= threshold
    name = Path(results_path).name
    print(f"[CI gate] {name}: mean={mean:.3f}  threshold={threshold:.2f}  "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok, mean


def _make_regressed(base_path: str) -> str:
    """Simulate a regression: zero out the exact_match scores (as if a retrieval or
    prompt change broke exact-match answering) and re-save."""
    d = json.loads(Path(base_path).read_text())
    for r in d["rows"]:
        if r["behavior"].startswith("exact_match"):
            r["score"], r["verdict"] = 0.0, "incorrect"
    scored = [r for r in d["rows"] if r["verdict"] != "error"]
    d["mean_score"] = round(sum(r["score"] for r in scored) / len(scored), 3)
    out = RESULTS / "answer_eval_REGRESSED_demo.json"
    out.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return str(out)


def demo(threshold: float):
    base = _latest_result()
    print("1) Baseline (current system):")
    ok_base, _ = check(base, threshold)
    print("\n2) After a deliberately-introduced regression (exact-match answers broken):")
    regressed = _make_regressed(base)
    ok_reg, _ = check(regressed, threshold)
    print()
    if ok_base and not ok_reg:
        print("=> The gate PASSES the baseline and FAILS the regression — CI would block "
              "the bad change. Regression prevention works.")
    else:
        print("=> Unexpected: check the threshold vs the baseline/regressed scores.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--results", default=None)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.demo:
        demo(args.threshold)
        return
    ok, _ = check(args.results or _latest_result(), args.threshold)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
