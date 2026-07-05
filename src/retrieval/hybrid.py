"""Hybrid retrieval = semantic (dense) + keyword (BM25), fused with RRF.

WHY RRF (Reciprocal Rank Fusion) instead of adding the two scores:
Cosine similarity (0-1) and BM25 (unbounded) live on totally different scales, so
summing them would let whichever scale is bigger dominate. RRF sidesteps that by
throwing away the raw scores and using only each system's *rank*:

    rrf_score(doc) = Σ  1 / (C + rank_in_that_ranker)      (C = 60, standard)

A doc ranked highly by EITHER retriever gets a strong combined score; a doc ranked
highly by BOTH wins. It's scale-free, robust, and the standard fusion baseline.

This is STAGE 2 of the baseline -> hybrid -> rerank arc. Same `.search(query, k)`
interface as the baseline `Retriever`, so the eval runner can swap it in directly.

Run a manual query:
  python -m src.retrieval.hybrid "which vendor has GST number 36AAEGP2210R1Z3?"
"""
import argparse
from collections import defaultdict

from .embedder import Embedder
from .keyword_search import KeywordIndex
from .vector_store import VectorStore, _normalize
from ..ingestion.build_index import INDEX_DIR

RRF_C = 60          # RRF smoothing constant (standard default)
CANDIDATES = 50     # how many top hits to take from each ranker before fusing


def rrf_fuse(rankings: list[list[int]], c: int = RRF_C) -> list[int]:
    """Fuse several ranked lists of indices into one, best first."""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, idx in enumerate(ranking, start=1):
            scores[idx] += 1.0 / (c + rank)
    return sorted(scores, key=lambda i: -scores[i])


class HybridRetriever:
    def __init__(self):
        self.store = VectorStore.load(INDEX_DIR)
        self.embedder = Embedder()
        self.keyword = KeywordIndex(self.store.metas)

    def _semantic_ranking(self, query: str) -> list[int]:
        qv = _normalize(self.embedder.embed([query])[0].reshape(1, -1))[0]
        sims = self.store.vectors @ qv
        return sorted(range(len(sims)), key=lambda i: -sims[i])

    def search(self, query: str, k: int = 5):
        sem_rank = self._semantic_ranking(query)[:CANDIDATES]
        kw_rank = self.keyword.rank(query)[:CANDIDATES]
        fused = rrf_fuse([sem_rank, kw_rank])
        return [(0.0, self.store.metas[i]) for i in fused[:k]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()
    for rank, (_, meta) in enumerate(HybridRetriever().search(args.query, args.k), 1):
        snippet = meta["text"].replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:140] + "…"
        print(f"{rank}. {meta['vendor_name']} ({meta['category']})")
        print(f"     {snippet}")


if __name__ == "__main__":
    main()
