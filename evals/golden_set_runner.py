"""Baseline retrieval eval: recall@5 against the golden question set.

For each golden question, runs it through the retrieval system and checks
whether the pre-marked gold_doc appears in the top-k results.

recall@k = hits / total_questions  (a "hit" = gold_doc in the top-k vendor_ids)

Run:
  python -m evals.golden_set_runner
  python -m evals.golden_set_runner --k 5 --stage baseline
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GOLDEN_SET_PATH = REPO_ROOT / "data" / "golden_set" / "golden_set.json"
RESULTS_DIR = REPO_ROOT / "evals" / "results"

sys.path.insert(0, str(REPO_ROOT))
from src.retrieval.search import Retriever


def run_eval(k: int = 5, stage: str = "baseline") -> dict:
    questions = json.loads(GOLDEN_SET_PATH.read_text())
    retriever = Retriever()

    results = []
    hits = 0

    for q in questions:
        top_k = retriever.search(q["question"], k=k)
        returned_docs = [meta["vendor_id"] for _, meta in top_k]
        hit = q["gold_doc"] in returned_docs

        if hit:
            hits += 1

        rank = returned_docs.index(q["gold_doc"]) + 1 if hit else None

        results.append({
            "id": q["id"],
            "behavior": q["behavior"],
            "question": q["question"],
            "gold_doc": q["gold_doc"],
            "hit": hit,
            "rank": rank,
            "returned_docs": returned_docs,
        })

    recall = hits / len(questions)

    return {
        "stage": stage,
        "k": k,
        "timestamp": datetime.utcnow().isoformat(),
        "recall_at_k": round(recall, 3),
        "hits": hits,
        "total": len(questions),
        "per_question": results,
    }


def print_report(report: dict):
    k = report["k"]
    print(f"\n{'='*60}")
    print(f"  Stage: {report['stage'].upper()}   recall@{k} = {report['recall_at_k']}  ({report['hits']}/{report['total']})")
    print(f"{'='*60}")
    print(f"{'#':<5} {'Behavior':<28} {'Hit':<6} {'Rank':<6} Question")
    print(f"{'-'*5} {'-'*28} {'-'*6} {'-'*6} {'-'*40}")
    for r in report["per_question"]:
        hit_str = "HIT" if r["hit"] else "MISS"
        rank_str = str(r["rank"]) if r["rank"] else "-"
        snippet = r["question"][:55] + "…" if len(r["question"]) > 55 else r["question"]
        print(f"{r['id']:<5} {r['behavior']:<28} {hit_str:<6} {rank_str:<6} {snippet}")

    print(f"\nMisses:")
    misses = [r for r in report["per_question"] if not r["hit"]]
    if not misses:
        print("  (none)")
    for r in misses:
        print(f"  {r['id']} [{r['behavior']}]: {r['question']}")
        print(f"    gold_doc wanted : {r['gold_doc']}")
        print(f"    top-{k} returned: {r['returned_docs']}")


def save_results(report: dict, stage: str):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"{stage}_{ts}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nResults saved → {path.relative_to(REPO_ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--stage", default="baseline", help="label for this run (baseline/hybrid/reranked)")
    ap.add_argument("--no-save", action="store_true", help="skip saving results to file")
    args = ap.parse_args()

    report = run_eval(k=args.k, stage=args.stage)
    print_report(report)
    if not args.no_save:
        save_results(report, args.stage)


if __name__ == "__main__":
    main()
