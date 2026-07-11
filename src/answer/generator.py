"""Answer generation — 'Stage 2' of the pipeline, finally built.

Since Phase 1 the pipeline had two stages: (1) retrieval (returns chunks, graded by
recall@k) and (2) answer generation (returns prose, graded by an LLM-judge). We built
stage 1 long ago; this is stage 2.

Flow: hybrid-retrieve the top-k chunks -> hand them to the LLM as CONTEXT -> compose a
grounded answer. We keep the Phase 3 safety posture: the context is untrusted data,
the model must answer only from it and say so if the answer isn't there (no guessing).
Returns the answer plus which vendors it drew from (attribution).
"""
from ..retrieval.hybrid import HybridRetriever

GEN_SYSTEM = (
    "You are Baraat, a wedding-vendor due-diligence assistant. Answer the user's "
    "question using ONLY the vendor context provided. Rules:\n"
    "- Use only facts present in the context; do not invent prices, ratings, or GST "
    "numbers.\n"
    "- For questions about PROBLEMS, COMPLAINTS, or RED FLAGS: if the context describes "
    "specific problems, report them; if the context describes the vendor with no problems "
    "or complaints mentioned, answer that NO red flags were found in the listing. Absence "
    "of problems in the provided listing is a valid, confident answer — do NOT hedge with "
    "'I don't have that information', and do NOT invent problems that aren't stated.\n"
    "- For other specific facts (price, location, phone): if that fact is genuinely not in "
    "the context, say you don't have that information (do not guess).\n"
    "- If prices look conflicting or dated, say so rather than picking one blindly.\n"
    "- Be concise and name the vendor you're talking about."
)


class AnswerGenerator:
    def __init__(self, backend, k: int = 8):
        self.retriever = HybridRetriever()
        self.backend = backend
        self.k = k

    def answer(self, question: str):
        hits = self.retriever.search(question, k=self.k)
        context = "\n\n".join(
            f"[{meta['vendor_name']}]\n{meta['text']}" for _, meta in hits
        )
        messages = [
            {"role": "system", "content": GEN_SYSTEM},
            {"role": "user", "content": f"Vendor context:\n{context}\n\nQuestion: {question}"},
        ]
        out = self.backend.complete(messages, json_mode=False)
        used = [meta["vendor_id"] for _, meta in hits]
        return out["text"], used
