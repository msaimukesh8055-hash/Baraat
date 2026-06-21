"""Build the retrieval index: chunk the corpus -> embed -> save vector store.

Run: python -m src.ingestion.build_index
"""
from pathlib import Path

from .chunker import chunk_corpus, REPO_ROOT
from ..retrieval.embedder import Embedder
from ..retrieval.vector_store import VectorStore

INDEX_DIR = REPO_ROOT / "data" / "index"


def main():
    chunks = chunk_corpus()
    n_docs = len({c["vendor_id"] for c in chunks})
    print(f"Chunked {n_docs} docs -> {len(chunks)} chunks "
          f"(avg {len(chunks)/n_docs:.1f} chunks/doc)")

    embedder = Embedder()
    print(f"Embedding with {embedder.model_name} ...")
    vectors = embedder.embed([c["embed_text"] for c in chunks])

    store = VectorStore(vectors, chunks)
    store.save(INDEX_DIR)
    # Record which model built the index (so query-time uses the same one).
    (Path(INDEX_DIR) / "index_meta.json").write_text(
        '{\n  "embedding_model": "%s",\n  "dim": %d,\n  "chunks": %d,\n  "docs": %d\n}\n'
        % (embedder.model_name, vectors.shape[1], len(chunks), n_docs)
    )
    print(f"Saved index: {len(chunks)} vectors (dim {vectors.shape[1]}) -> {INDEX_DIR}")


if __name__ == "__main__":
    main()
