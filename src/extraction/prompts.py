"""Prompt templates for extraction + repair.

Design notes (competency #3/#7):
- The model is told the rules in plain language AND given the authoritative JSON
  schema, plus one worked example (spec-by-example reduces ambiguity).
- The repair prompt feeds the model its OWN previous output plus the SPECIFIC
  validation errors — targeted correction, not a blind retry.
"""
import json
from pathlib import Path

SCHEMA_TEXT = (Path(__file__).resolve().parents[1] / "schemas" / "vendor.schema.json").read_text()

# A compact worked example (clean vendor) so the model anchors on the right shape.
_EXAMPLE = {
    "vendor_id": "photographer_everafter_films",
    "name": "Ever After Films",
    "category": "photographer",
    "location": "Bandra West, Mumbai",
    "price_range_inr": {"min": 210000, "max": 210000},
    "price_unit": "package",
    "price_last_verified": None,
    "price_confidence": "high",
    "contact": {"phone": "+91 98201 76654", "email": "hello@everafterfilms.example"},
    "gst_number": None,
    "rating": 4.9,
    "review_count": 76,
    "red_flags": [],
    "source_file": "photographer_everafter_films.md",
    "needs_human_review": False,
    "extraction_notes": None,
}

SYSTEM_PROMPT = f"""You are a precise data-extraction engine for a wedding-vendor due-diligence system.
Read ONE vendor document (prose) and output ONE JSON object that matches the schema EXACTLY.

OUTPUT RULES:
- Output ONLY the JSON object. No prose, no markdown, no code fences.
- Use exact field names and value types from the schema.
- category: exactly one of photographer, caterer, decorator, venue, makeup_artist.
- price_unit by category: caterer => per_plate; venue => per_day; photographer/decorator/makeup_artist => package (or per_event).
- price_confidence:
  - "high"  = a single, clear, current price, no conflict (even if no date is stated).
  - "low"   = a vague or open-ended price ("from X and up") with no conflicting figures.
  - "stale" = conflicting prices from different dates, OR an explicit old "prices as of <old date>" marker.
- price_range_inr: numeric INR. For CONFLICTING prices, use the MOST RECENT dated figure, set price_confidence="stale", and explain the conflict in extraction_notes. max may be null for open-ended pricing.
- price_last_verified: a date "YYYY-MM-DD" ONLY if the doc states one, else null.
- gst_number: copy EXACTLY if present in the doc, else null. NEVER invent a GST number.
- contact.email: null if not present.
- red_flags: list EVERY complaint, dispute, or quality issue, INCLUDING ones buried late in the document. Use [] if there are genuinely none. Do NOT invent red flags for clean vendors.
- vendor_id and source_file are provided to you; copy them verbatim.
- needs_human_review: false for normal extraction. A STALE price is normal, NOT a human-review case. extraction_notes: a short note for staleness or open-ended pricing, else null.

AUTHORITATIVE JSON SCHEMA:
{SCHEMA_TEXT}

EXAMPLE (clean document -> record):
{json.dumps(_EXAMPLE, indent=2)}
"""


def user_prompt(vendor_id: str, source_file: str, doc_text: str) -> str:
    return (
        f"vendor_id: {vendor_id}\n"
        f"source_file: {source_file}\n\n"
        f"DOCUMENT:\n\"\"\"\n{doc_text}\n\"\"\"\n\n"
        "Return ONLY the JSON object for this vendor."
    )


def repair_prompt(errors, previous_raw: str) -> str:
    bullet = "\n".join(f"- {e}" for e in errors)
    return (
        "Your previous output was INVALID. Fix ALL of these problems:\n"
        f"{bullet}\n\n"
        "Your previous output was:\n"
        f"{previous_raw}\n\n"
        "Return ONLY a corrected JSON object that fixes every listed problem. "
        "No prose, no code fences."
    )
