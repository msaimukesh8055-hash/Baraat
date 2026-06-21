"""Local embedding model wrapper (fastembed / ONNX — no API key, no rate limits).

We use a local embedder because (a) Groq has no embeddings endpoint and we have
no other key, and (b) local is free, offline, and deterministic — which makes the
retrieval evals reproducible. Model: BAAI/bge-small-en-v1.5 (384-dim).
"""
import numpy as np
from fastembed import TextEmbedding

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts) -> np.ndarray:
        """Return an (n, dim) float32 array of embeddings."""
        vecs = list(self._model.embed(list(texts)))
        return np.asarray(vecs, dtype=np.float32)
