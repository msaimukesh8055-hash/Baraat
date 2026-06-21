"""Ingestion: chunk vendor docs into retrievable pieces (Track A, RAG).

Chunking decisions (competency #5 RAG architecture, #4 context engineering):
- Paragraph-aware: split on blank lines, the natural seams of these docs. This
  makes a buried-red-flag paragraph its OWN chunk, so it isn't averaged away
  inside a long positive document (the "lost in the middle" failure we planted).
- Contextual prefix: each chunk's embedded text is prefixed with the vendor name
  + category, so a retrieved fragment is never orphaned and per-vendor queries
  work better (a light form of "contextual retrieval"). The raw paragraph is
  kept separately for display.
- Size cap: very long paragraphs are split by sentence to ~160 words (rare here).

Skips files starting with '_' (manifest + Phase-3 reserved docs), so the index
stays clean in Phase 1.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = REPO_ROOT / "data" / "vendors"

CATEGORY_BY_PREFIX = {
    "photographer": "photographer",
    "caterer": "caterer",
    "decorator": "decorator",
    "venue": "venue",
    "makeup": "makeup_artist",
}
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_PARA_SPLIT = re.compile(r"\n\s*\n")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def vendor_name(text: str, fallback: str) -> str:
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), fallback)
    # Titles look like "Anokhi Rasoi Catering Co. — Wedding Caterers, Jaipur"
    return re.split(r"\s[—–-]\s", first)[0].strip()


def _split_long(paragraph: str, max_words: int):
    if len(paragraph.split()) <= max_words:
        return [paragraph]
    out, cur = [], []
    for sent in _SENT_SPLIT.split(paragraph):
        cur.append(sent)
        if len(" ".join(cur).split()) >= max_words:
            out.append(" ".join(cur).strip())
            cur = []
    if cur:
        out.append(" ".join(cur).strip())
    return out


def chunk_document(vendor_id: str, source_file: str, text: str, max_words: int = 160):
    text = _HTML_COMMENT.sub("", text).strip()
    name = vendor_name(text, vendor_id)
    category = CATEGORY_BY_PREFIX.get(vendor_id.split("_", 1)[0], "venue")

    chunks = []
    paragraphs = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    for para in paragraphs:
        for piece in _split_long(para, max_words):
            idx = len(chunks)
            chunks.append({
                "chunk_id": f"{vendor_id}#{idx}",
                "vendor_id": vendor_id,
                "vendor_name": name,
                "category": category,
                "source_file": source_file,
                "chunk_index": idx,
                "text": piece,  # raw paragraph, for display/citation
                # what actually gets embedded (contextual prefix keeps the
                # fragment tied to its vendor):
                "embed_text": f"Vendor: {name} ({category}). {piece}",
            })
    return chunks


def corpus_files():
    return sorted(p for p in VENDOR_DIR.glob("*.md") if not p.name.startswith("_"))


def chunk_corpus():
    all_chunks = []
    for path in corpus_files():
        all_chunks.extend(chunk_document(path.stem, path.name, path.read_text()))
    return all_chunks
