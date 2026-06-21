"""A minimal local vector store: normalized vectors + cosine similarity.

Deliberately simple. At ~150 chunks, a hosted vector DB (Chroma/Pinecone) or even
FAISS would be over-engineering — a NumPy array with cosine similarity is exact,
dependency-light, and plenty fast. Documented upgrade path: switch to FAISS/Chroma/
pgvector when corpus size, persistence, or concurrency grow (none apply here yet).
"""
import json
from pathlib import Path

import numpy as np


def _normalize(m: np.ndarray) -> np.ndarray:
    m = m.astype(np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


class VectorStore:
    def __init__(self, vectors: np.ndarray, metas: list):
        assert len(vectors) == len(metas), "vectors/metas length mismatch"
        self.vectors = _normalize(vectors)
        self.metas = metas

    def search(self, query_vec: np.ndarray, k: int = 5):
        """Return list of (score, meta) for the top-k most similar chunks."""
        q = _normalize(query_vec.reshape(1, -1))[0]
        sims = self.vectors @ q
        order = np.argsort(-sims)[:k]
        return [(float(sims[i]), self.metas[i]) for i in order]

    def save(self, dir_path):
        d = Path(dir_path)
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "vectors.npy", self.vectors)
        (d / "metas.json").write_text(json.dumps(self.metas, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, dir_path):
        d = Path(dir_path)
        obj = cls.__new__(cls)
        obj.vectors = np.load(d / "vectors.npy")
        obj.metas = json.loads((d / "metas.json").read_text())
        return obj
