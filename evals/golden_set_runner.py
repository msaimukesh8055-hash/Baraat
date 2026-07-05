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
from src.retrieval.hybrid import HybridRetriever

RETRIEVERS = {
    "baseline": Retriever,       # semantic only
    "hybrid": HybridRetriever,   # semantic + BM25 keyword, RRF-fused
}


def run_eval(k: int = 5, stage: str = "baseline", retriever_name: str = "baseline") -> dict:
    questions = json.loads(GOLDEN_SET_PATH.read_text())
    retriever = RETRIEVERS[retriever_name]()

    results = []
    hits_at_k = 0      # gold doc anywhere in top-k  -> recall@k
    hits_at_1 = 0      # gold doc at rank 1          -> recall@1 (strict)
    reciprocal_ranks = []  # 1/rank per question     -> MRR (rank-sensitive)

    for q in questions:
        top_k = retriever.search(q["question"], k=k)
        returned_docs = [meta["vendor_id"] for _, meta in top_k]
        hit = q["gold_doc"] in returned_docs

        # rank = 1-indexed position of the FIRST occurrence of the gold doc
        rank = returned_docs.index(q["gold_doc"]) + 1 if hit else None

        if hit:
            hits_at_k += 1
        if rank == 1:
            hits_at_1 += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

        # Near-duplicate contamination: is a DIFFERENT vendor also in the top-k?
        # (distinct impostor vendor_ids sharing none of the gold doc's identity)
        distinct_others = sorted({d for d in returned_docs if d != q["gold_doc"]})

        results.append({
            "id": q["id"],
            "behavior": q["behavior"],
            "question": q["question"],
            "gold_doc": q["gold_doc"],
            "hit": hit,
            "rank": rank,
            "other_vendors_in_topk": distinct_others,
            "returned_docs": returned_docs,
        })

    n = len(questions)
    return {
        "stage": stage,
        "k": k,
        "timestamp": datetime.utcnow().isoformat(),
        "recall_at_k": round(hits_at_k / n, 3),
        "recall_at_1": round(hits_at_1 / n, 3),
        "mrr": round(sum(reciprocal_ranks) / n, 3),
        "hits_at_k": hits_at_k,
        "hits_at_1": hits_at_1,
        "total": n,
        "per_question": results,
    }


def print_report(report: dict):
    k = report["k"]
    print(f"\n{'='*66}")
    print(f"  Stage: {report['stage'].upper()}")
    print(f"    recall@{k} = {report['recall_at_k']}   ({report['hits_at_k']}/{report['total']} gold docs in top {k})")
    print(f"    recall@1 = {report['recall_at_1']}   ({report['hits_at_1']}/{report['total']} gold docs at rank 1)  <- strict")
    print(f"    MRR      = {report['mrr']}   (avg 1/rank; rank-sensitive)")
    print(f"{'='*66}")
    print(f"{'#':<5} {'Behavior':<27} {'Rank':<6} {'Rank1?':<7} Question")
    print(f"{'-'*5} {'-'*27} {'-'*6} {'-'*7} {'-'*35}")
    for r in report["per_question"]:
        rank_str = str(r["rank"]) if r["rank"] else "MISS"
        rank1 = "yes" if r["rank"] == 1 else "no"
        snippet = r["question"][:50] + "…" if len(r["question"]) > 50 else r["question"]
        print(f"{r['id']:<5} {r['behavior']:<27} {rank_str:<6} {rank1:<7} {snippet}")

    # Anything not at rank 1, or with an impostor vendor sharing the top-k, is worth a look
    print(f"\nImperfect cases (rank > 1 OR a different vendor also in top-{k}):")
    flagged = [r for r in report["per_question"]
               if r["rank"] != 1 or r["other_vendors_in_topk"]]
    if not flagged:
        print("  (none)")
    for r in flagged:
        rank_str = str(r["rank"]) if r["rank"] else "MISS"
        print(f"  {r['id']} [{r['behavior']}] rank={rank_str}")
        print(f"    gold_doc        : {r['gold_doc']}")
        print(f"    other vendors   : {r['other_vendors_in_topk'] or '(none)'}")
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
    ap.add_argument("--retriever", default=None, choices=list(RETRIEVERS),
                    help="which retriever to use (defaults to --stage if it names one)")
    ap.add_argument("--no-save", action="store_true", help="skip saving results to file")
    args = ap.parse_args()

    retriever_name = args.retriever or (args.stage if args.stage in RETRIEVERS else "baseline")
    report = run_eval(k=args.k, stage=args.stage, retriever_name=retriever_name)
    print_report(report)
    if not args.no_save:
        save_results(report, args.stage)


if __name__ == "__main__":
    main()
