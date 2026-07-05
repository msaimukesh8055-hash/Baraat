"""Keyword search over chunks via BM25 (pure Python — no new dependency).

WHY this exists: semantic (embedding) search is great at *meaning* but blind to
*exact strings*. A GST code like "36AAEGP2210R1Z3" or the distinguishing city in a
pair of near-duplicate vendors carries no semantic signal for an embedding model.
BM25 is classic lexical scoring: it rewards chunks that literally contain the
query's rare words. This is the "keyword" half of hybrid search.

Kept minimal on purpose: at ~200 chunks, a from-scratch BM25 (a few Counters and a
loop) is exact and fast — pulling in Elasticsearch/rank_bm25 would be
over-engineering, same reasoning as the NumPy vector store over FAISS.

Tokenizer note: we split on runs of [a-z0-9] AFTER lowercasing, so an alphanumeric
code stays ONE token ("36AAEGP2210R1Z3" -> "36aaegp2210r1z3"). That's what lets an
exact GST/phone token match cleanly instead of being shredded into pieces.
"""
import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def keyword_doc(meta: dict) -> str:
    """The text BM25 indexes for a chunk: vendor name + category + body.

    Including name/category (not just the raw body) means the vendor's name and
    type are always matchable, even for chunks past the first paragraph.
    """
    return f"{meta.get('vendor_name', '')} {meta.get('category', '')} {meta.get('text', '')}"


class BM25:
    """Standard BM25 (Okapi). k1 controls term-frequency saturation; b controls
    length normalization. Defaults (1.5, 0.75) are the textbook values."""

    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.N = len(docs_tokens)
        self.doc_len = [len(d) for d in docs_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.tf = [Counter(d) for d in docs_tokens]

        df = Counter()
        for toks in docs_tokens:
            for t in set(toks):
                df[t] += 1
        # idf with the +1 smoothing so it never goes negative for common terms
        self.idf = {
            t: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for t, n in df.items()
        }

    def scores(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * self.N
        for t in query_tokens:
            idf = self.idf.get(t)
            if idf is None:
                continue  # query term not in corpus -> contributes nothing
            for i in range(self.N):
                f = self.tf[i].get(t, 0)
                if f == 0:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += idf * (f * (self.k1 + 1)) / denom
        return scores


class KeywordIndex:
    """BM25 over a list of chunk metas. Returns full ranking of chunk indices."""

    def __init__(self, metas: list[dict]):
        self.metas = metas
        self.bm25 = BM25([tokenize(keyword_doc(m)) for m in metas])

    def rank(self, query: str) -> list[int]:
        """All chunk indices, best keyword-match first."""
        scores = self.bm25.scores(tokenize(query))
        return sorted(range(len(scores)), key=lambda i: -scores[i])
