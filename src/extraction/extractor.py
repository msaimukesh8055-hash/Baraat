"""The extractor: one messy doc -> one validated record, with a repair loop.

Flow per document:
  1. ask the model for JSON
  2. parse it
  3. validate (Layers 1 + 2)
  4. if invalid -> REPAIR (feed the model its specific errors), up to MAX_REPAIRS
  5. if still invalid -> FALLBACK to a flagged needs_human_review record (never guess)

Every attempt is recorded in a trace for observability and the failure log.
"""
import json
import re

from .prompts import SYSTEM_PROMPT, user_prompt, repair_prompt
from .validator import validate_record

# vendor_id prefix -> schema category (filenames use "makeup_", schema uses "makeup_artist")
_CATEGORY_BY_PREFIX = {
    "photographer": "photographer",
    "caterer": "caterer",
    "decorator": "decorator",
    "venue": "venue",
    "makeup": "makeup_artist",
}
_DEFAULT_UNIT = {
    "caterer": "per_plate",
    "venue": "per_day",
    "photographer": "package",
    "decorator": "package",
    "makeup_artist": "package",
}


def _safe_parse(text):
    """Best-effort: pull the JSON object out of a model reply.

    Handles code fences and leading/trailing prose by taking the outermost
    {...} span. Returns (record_or_None, error_or_None)."""
    if not isinstance(text, str) or not text.strip():
        return None, "empty model output"
    cleaned = text.strip()
    # strip ```json ... ``` fences if present
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None, "no JSON object found in output"
    snippet = cleaned[start:end + 1]
    try:
        return json.loads(snippet), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"


def _category_from_id(vendor_id):
    prefix = vendor_id.split("_", 1)[0]
    return _CATEGORY_BY_PREFIX.get(prefix, "venue")


def _fallback_record(vendor_id, source_file, errors):
    """A schema-VALID record that is explicitly flagged for human review.
    We never silently guess; we surface that extraction failed."""
    category = _category_from_id(vendor_id)
    return {
        "vendor_id": vendor_id,
        "name": "UNKNOWN (extraction failed)",
        "category": category,
        "location": "Unknown",
        "price_range_inr": {"min": 0, "max": None},
        "price_unit": _DEFAULT_UNIT[category],
        "price_last_verified": None,
        "price_confidence": "low",
        "contact": {"phone": "", "email": None},
        "gst_number": None,
        "rating": 0.0,
        "review_count": 0,
        "red_flags": [],
        "source_file": source_file,
        "needs_human_review": True,
        "extraction_notes": "Validation failed after repair attempts: " + "; ".join(errors),
    }


def extract_one(doc_text, vendor_id, source_file, backend, max_repairs=2):
    """Returns (record, trace)."""
    trace = {"vendor_id": vendor_id, "model": getattr(backend, "model", "?"), "attempts": []}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(vendor_id, source_file, doc_text)},
    ]

    errors = ["(no attempt made)"]
    for attempt in range(max_repairs + 1):
        out = backend.complete(messages)
        raw = out["text"]
        rec, parse_err = _safe_parse(raw)

        if parse_err:
            errors = [f"output is not valid JSON: {parse_err}"]
        else:
            # Force identity fields to the known-correct values before validating,
            # so a model slip on vendor_id/source_file doesn't fail the record.
            rec["vendor_id"] = vendor_id
            rec["source_file"] = source_file
            errors = validate_record(rec, source_text=doc_text)

        trace["attempts"].append({
            "n": attempt,
            "errors": errors,
            "usage": out.get("usage", {}),
            "latency_s": round(out.get("latency", 0.0), 3),
        })

        if not errors:
            trace["status"] = "ok_first_try" if attempt == 0 else "ok_after_repair"
            return rec, trace

        # Set up a targeted repair turn.
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": repair_prompt(errors, raw)})

    # Exhausted repairs -> graceful degraded output, flagged for a human.
    trace["status"] = "fallback_human_review"
    trace["final_errors"] = errors
    return _fallback_record(vendor_id, source_file, errors), trace
