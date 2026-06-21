"""Baseline retrieval: semantic-only search over the vector store.

This is STAGE 1 of the planned baseline -> hybrid -> rerank arc. Pure semantic
(dense embedding) search; no keyword matching, no reranking yet — added in later
steps so each improvement's delta is measurable.

Run a quick manual query:
  python -m src.retrieval.search "does Anokhi have any complaints?"
"""
import argparse

from .embedder import Embedder
from .vector_store import VectorStore
from ..ingestion.build_index import INDEX_DIR


class Retriever:
    def __init__(self):
        self.store = VectorStore.load(INDEX_DIR)
        self.embedder = Embedder()

    def search(self, query: str, k: int = 5):
        qv = self.embedder.embed([query])[0]
        return self.store.search(qv, k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="natural-language query")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    for rank, (score, meta) in enumerate(Retriever().search(args.query, args.k), 1):
        snippet = meta["text"].replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:140] + "…"
        print(f"{rank}. [{score:.3f}] {meta['vendor_name']} ({meta['category']})")
        print(f"     {snippet}")


if __name__ == "__main__":
    main()
