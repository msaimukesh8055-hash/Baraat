"""Reranking = Stage 3 of the retrieval arc: wide cheap net, then deep re-read.

WHY: hybrid (semantic + BM25) fixed exact-string retrieval (the GST, Q08) but not
*relational* disambiguation (Q09) — when the discriminating word ("Udaipur") sits in
BOTH candidate docs, neither meaning-similarity nor keyword overlap can separate
"based in Udaipur" from "mentions Udaipur." A cross-encoder reads the query and each
chunk TOGETHER and can tell a location claim from a cross-reference.

DESIGN (mirrors the PM notes in docs/learning-notes/retrieval-and-evals.md §7-8):
  1. Cast a WIDE net cheaply: take hybrid's top-N candidates (N = the cost/accuracy
     knob; default 20).
  2. Deep-read: a cross-encoder (Xenova/ms-marco-MiniLM-L-6-v2, local, ~80MB) scores
     each (query, chunk) pair.
  3. Reorder and return the top-k.

GUARDRAIL (Knob 3 — graceful degradation): if the cross-encoder fails for any reason
(model load error, runtime error), we DO NOT crash — we fall back to the hybrid
ranking. A worse-but-fine answer beats a hang. This is the escalator->stairs rule.

Same `.search(query, k)` interface as baseline/hybrid so the eval runner swaps it in.

Run a manual query:
  python -m src.retrieval.reranker "which Royal Decor firm is based in Udaipur?"
"""
import argparse

from .hybrid import HybridRetriever

DEFAULT_CANDIDATES = 20                       # N: the wide-net knob
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


def _rerank_text(meta: dict) -> str:
    """What the cross-encoder reads for a chunk: vendor name + body, so it knows
    which vendor this passage belongs to (the body alone may omit the name)."""
    return f"{meta.get('vendor_name', '')}. {meta.get('text', '')}"


class RerankRetriever:
    def __init__(self, candidates: int = DEFAULT_CANDIDATES, model_name: str = RERANK_MODEL):
        self.hybrid = HybridRetriever()
        self.candidates = candidates
        self.model_name = model_name
        # Lazy import so the rest of the system doesn't pay for it unless used.
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        self.encoder = TextCrossEncoder(model_name=model_name)

    def search(self, query: str, k: int = 5):
        # 1. Wide, cheap net from hybrid.
        candidates = self.hybrid.search(query, k=self.candidates)
        if not candidates:
            return []

        docs = [_rerank_text(meta) for _, meta in candidates]

        # 2. Deep re-read — with the graceful-degradation guardrail (Knob 3).
        try:
            scores = list(self.encoder.rerank(query, docs))
        except Exception as e:  # pragma: no cover - defensive fallback path
            print(f"[reranker] cross-encoder failed ({e!r}); falling back to hybrid ranking")
            return candidates[:k]

        # 3. Reorder by cross-encoder score, return top-k.
        order = sorted(range(len(candidates)), key=lambda i: -scores[i])
        return [(float(scores[i]), candidates[i][1]) for i in order[:k]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("-n", "--candidates", type=int, default=DEFAULT_CANDIDATES)
    args = ap.parse_args()
    r = RerankRetriever(candidates=args.candidates)
    for rank, (score, meta) in enumerate(r.search(args.query, args.k), 1):
        snippet = meta["text"].replace("\n", " ")
        if len(snippet) > 130:
            snippet = snippet[:130] + "…"
        print(f"{rank}. [{score:+.3f}] {meta['vendor_name']} ({meta['category']})")
        print(f"     {snippet}")


if __name__ == "__main__":
    main()
