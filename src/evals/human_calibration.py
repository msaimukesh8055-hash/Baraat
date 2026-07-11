"""Human-eval calibration — is the LLM-judge trustworthy?

The judge is itself an LLM and can be wrong, so we check its agreement with a human.

  1. make a sample template (a few questions with the judge's verdict + a blank
     human_verdict field):
         python -m src.evals.human_calibration make --n 12
  2. Saimukesh fills in `human_verdict` for each row (correct/partial/incorrect).
  3. score the agreement:
         python -m src.evals.human_calibration score

Agreement = fraction of rows where human_verdict == judge verdict. Disagreements are
printed so we can see WHERE the judge and a human diverge (the interesting cases).
"""
import argparse
import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "evals" / "results"
TEMPLATE = RESULTS / "human_calibration.json"
VALID = {"correct", "partial", "incorrect"}


def _latest_eval():
    files = sorted(glob.glob(str(RESULTS / "answer_eval_*.json")))
    if not files:
        raise SystemExit("No answer_eval results found — run `python -m src.evals.answer_eval` first.")
    return json.loads(Path(files[-1]).read_text())


def make(n: int):
    data = _latest_eval()
    rows = data["rows"]
    # Stratify: try to include some of each judge verdict so calibration isn't all easy.
    by_v = {"correct": [], "partial": [], "incorrect": []}
    for r in rows:
        by_v.get(r["verdict"], by_v["correct"]).append(r)
    sample, i = [], 0
    order = ["incorrect", "partial", "correct"]  # front-load the hard ones
    while len(sample) < min(n, len(rows)):
        bucket = by_v[order[i % 3]]
        if bucket:
            sample.append(bucket.pop(0))
        i += 1
        if all(not by_v[v] for v in order):
            break
    template = [{
        "id": r["id"], "question": r["question"], "expected": r["expected"],
        "answer": r["answer"], "judge_verdict": r["verdict"],
        "human_verdict": "",   # <-- FILL THIS: correct | partial | incorrect
    } for r in sample]
    TEMPLATE.write_text(json.dumps(template, indent=2, ensure_ascii=False))
    print(f"Wrote {len(template)} rows to {TEMPLATE.relative_to(REPO)}")
    print("Fill in each 'human_verdict' (correct/partial/incorrect), then run: "
          "python -m src.evals.human_calibration score")


def score():
    if not TEMPLATE.exists():
        raise SystemExit("No human_calibration.json — run `make` first.")
    rows = json.loads(TEMPLATE.read_text())
    graded = [r for r in rows if r.get("human_verdict") in VALID]
    if not graded:
        raise SystemExit("No rows have a human_verdict yet — fill them in first.")

    agree = sum(1 for r in graded if r["human_verdict"] == r["judge_verdict"])
    pct = round(100 * agree / len(graded), 1)
    print(f"Human-judge agreement: {agree}/{len(graded)} = {pct}%\n")
    disagreements = [r for r in graded if r["human_verdict"] != r["judge_verdict"]]
    if disagreements:
        print("Disagreements (where the judge and human differ):")
        for r in disagreements:
            print(f"  {r['id']}: judge={r['judge_verdict']} vs human={r['human_verdict']}")
            print(f"       Q: {r['question']}")
            print(f"       A: {r['answer'][:120]}")
    else:
        print("No disagreements — the judge matched the human on every graded row.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--n", type=int, default=12)
    sub.add_parser("score")
    args = ap.parse_args()
    if args.cmd == "make":
        make(args.n)
    else:
        score()


if __name__ == "__main__":
    main()
