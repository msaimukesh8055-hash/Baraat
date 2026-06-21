"""Record validation — Layers 1 (structural) and 2 (cross-field semantic).

Layer 3 (content correctness vs the corpus manifest) is NOT done here — that is a
separate eval. This module only answers "is the SHAPE right and internally
consistent?", returning human-readable errors that feed the repair loop.

Enums and patterns are loaded FROM vendor.schema.json so this code can't silently
drift from the contract.
"""
import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "vendor.schema.json"
_SCHEMA = json.loads(SCHEMA_PATH.read_text())
_PROPS = _SCHEMA["properties"]

REQUIRED = _SCHEMA["required"]
CATEGORIES = _PROPS["category"]["enum"]
PRICE_UNITS = _PROPS["price_unit"]["enum"]
PRICE_CONFIDENCES = _PROPS["price_confidence"]["enum"]
GST_RE = re.compile(_PROPS["gst_number"]["pattern"])
DATE_RE = re.compile(_PROPS["price_last_verified"]["pattern"])
VENDOR_ID_RE = re.compile(_PROPS["vendor_id"]["pattern"])

# Layer-2 rule: which price units make sense for which category.
PRICE_UNIT_BY_CATEGORY = {
    "caterer": {"per_plate"},
    "venue": {"per_day"},
    "photographer": {"package", "per_event"},
    "decorator": {"package", "per_event"},
    "makeup_artist": {"package", "per_event"},
}

_MISSING = object()


def _is_str(v):
    return isinstance(v, str)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_record(rec, source_text=None):
    """Return a list of error strings. Empty list == valid.

    If source_text is given, also checks that a non-null gst_number actually
    appears in the source (catching hallucinated GST numbers).
    """
    errors = []
    if not isinstance(rec, dict):
        return ["record is not a JSON object"]

    # --- Layer 1: required keys present, no unexpected keys ---
    for key in REQUIRED:
        if key not in rec:
            errors.append(f"missing required field: {key}")
    for key in rec:
        if key not in _PROPS:
            errors.append(f"unexpected field: {key}")

    # --- Layer 1: per-field structural checks ---
    if "name" in rec and not (_is_str(rec["name"]) and rec["name"].strip()):
        errors.append("name must be a non-empty string")

    if "vendor_id" in rec and not (_is_str(rec["vendor_id"]) and VENDOR_ID_RE.match(rec["vendor_id"])):
        errors.append("vendor_id must match the category-prefixed slug pattern")

    if "category" in rec and rec["category"] not in CATEGORIES:
        errors.append(f"category must be one of {CATEGORIES}")

    if "location" in rec and not (_is_str(rec["location"]) and rec["location"].strip()):
        errors.append("location must be a non-empty string")

    pr = rec.get("price_range_inr", _MISSING)
    if pr is _MISSING or not isinstance(pr, dict) or "min" not in pr or "max" not in pr:
        errors.append("price_range_inr must be an object with 'min' and 'max'")
    else:
        mn, mx = pr.get("min"), pr.get("max")
        if not (_is_num(mn) and mn >= 0):
            errors.append("price_range_inr.min must be a number >= 0")
        if not (mx is None or (_is_num(mx) and mx >= 0)):
            errors.append("price_range_inr.max must be a number >= 0 or null")
        # Layer 2: min <= max
        if _is_num(mn) and _is_num(mx) and mn > mx:
            errors.append("price_range_inr.min must be <= price_range_inr.max")

    if "price_unit" in rec and rec["price_unit"] not in PRICE_UNITS:
        errors.append(f"price_unit must be one of {PRICE_UNITS}")

    plv = rec.get("price_last_verified", _MISSING)
    if plv is not _MISSING and plv is not None and not (_is_str(plv) and DATE_RE.match(plv)):
        errors.append("price_last_verified must be 'YYYY-MM-DD' or null")

    if "price_confidence" in rec and rec["price_confidence"] not in PRICE_CONFIDENCES:
        errors.append(f"price_confidence must be one of {PRICE_CONFIDENCES}")

    c = rec.get("contact", _MISSING)
    if c is _MISSING or not isinstance(c, dict) or "phone" not in c or "email" not in c:
        errors.append("contact must be an object with 'phone' and 'email'")
    else:
        if not _is_str(c.get("phone")):
            errors.append("contact.phone must be a string")
        if not (c.get("email") is None or _is_str(c.get("email"))):
            errors.append("contact.email must be a string or null")

    gst = rec.get("gst_number", _MISSING)
    if gst is not _MISSING and gst is not None and not (_is_str(gst) and GST_RE.match(gst)):
        errors.append("gst_number must match the 15-char GST pattern or be null")

    if "rating" in rec and not (_is_num(rec["rating"]) and 0 <= rec["rating"] <= 5):
        errors.append("rating must be a number between 0.0 and 5.0")

    rc = rec.get("review_count", _MISSING)
    if rc is not _MISSING and not (isinstance(rc, int) and not isinstance(rc, bool) and rc >= 0):
        errors.append("review_count must be an integer >= 0")

    rf = rec.get("red_flags", _MISSING)
    if rf is not _MISSING and not (isinstance(rf, list) and all(_is_str(x) for x in rf)):
        errors.append("red_flags must be an array of strings (use [] if none)")

    if "source_file" in rec and not (_is_str(rec["source_file"]) and rec["source_file"].strip()):
        errors.append("source_file must be a non-empty string")

    if "needs_human_review" in rec and not isinstance(rec["needs_human_review"], bool):
        errors.append("needs_human_review must be a boolean")

    notes = rec.get("extraction_notes", _MISSING)
    if notes is not _MISSING and notes is not None and not _is_str(notes):
        errors.append("extraction_notes must be a string or null")

    # --- Layer 2: cross-field semantic rules ---
    if rec.get("needs_human_review") is True:
        n = rec.get("extraction_notes")
        if not (_is_str(n) and n.strip()):
            errors.append("needs_human_review is true but extraction_notes is empty (must explain why)")

    cat, pu = rec.get("category"), rec.get("price_unit")
    if cat in PRICE_UNIT_BY_CATEGORY and pu in PRICE_UNITS and pu not in PRICE_UNIT_BY_CATEGORY[cat]:
        errors.append(
            f"price_unit '{pu}' is inconsistent with category '{cat}' "
            f"(expected one of {sorted(PRICE_UNIT_BY_CATEGORY[cat])})"
        )

    # Layer 2: no invented GST — a non-null GST must appear verbatim in the source.
    if source_text is not None and _is_str(gst) and gst:
        if gst not in source_text:
            errors.append("gst_number does not appear in the source document "
                          "(possible hallucination); must be null if absent")

    return errors
