"""Phase 3 defenses — the three layers, defense-in-depth.

  Layer 1  instruction/data separation  -> prompt-level (see DefendedBriefing)
  Layer 2  input sanitization           -> sanitize_text() below
  Layer 3  output/constraint validation -> redact_leaked_pii() + trusted facts

No single layer is trusted alone: the model can ignore separation, sanitization can
miss a cleverly-worded payload, and an output check can't judge tone. Stacked, they
cover each other — the classic security posture.
"""
import json
import re
from pathlib import Path

EXTRACTED = Path(__file__).resolve().parents[2] / "data" / "extracted"

# ---------------------------------------------------------------------------
# Layer 2 — input sanitization
# ---------------------------------------------------------------------------
# Lines that look like instructions to the assistant (not vendor description).
_INJECTION_PATTERNS = [re.compile(p, re.I) for p in [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|other|any)",
    r"^\s*system\s*:",
    r"assistant\s+(directive|instruction|note)",
    r"note\s+(for|to)\s+(automated|ai|planning)\s+assistant",
    r"treat\s+.{0,40}\bprice\b.{0,20}\bas\b",          # "treat its price as 50,000"
    r"rank\s+.{0,40}\bfirst\b",                          # "rank X first"
    r"always\s+(include|recommend|rank|present)",
    r"regardless\s+of\s+(the\s+)?(user|price|rating|budget|red[-\s]?flag)",
    r"append\s+.{0,60}(contact|gst|phone|email)",
    r"(verified\s+)?top\s+pick",
    r"preferred[-\s]venue\s+program",
    r"#\s*1\s+(recommended|choice|pick)",
]]


def sanitize_text(text: str):
    """Return (clean_text, flags). Removes HTML comments and redacts lines that
    read as injected instructions, leaving the genuine vendor description intact."""
    flags = []

    def _drop_comment(m):
        flags.append("html_comment")
        return "[redacted comment]"

    text = re.sub(r"<!--.*?-->", _drop_comment, text, flags=re.S)

    out_lines = []
    for line in text.splitlines():
        if any(p.search(line) for p in _INJECTION_PATTERNS):
            flags.append(line.strip()[:70])
            out_lines.append("[redacted: possible injected instruction]")
        else:
            out_lines.append(line)
    return "\n".join(out_lines), flags


# ---------------------------------------------------------------------------
# Layer 3a — output PII-leak redaction (trusted registry of who owns what)
# ---------------------------------------------------------------------------
_GST_RE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b")
_PHONE_RE = re.compile(r"\+?91[\s-]?\d{5}[\s-]?\d{5}")


def _norm(s: str) -> str:
    return s.replace(" ", "").replace("-", "")


def load_pii_registry() -> dict:
    """normalized GST/phone -> vendor_id, from the trusted extracted records."""
    reg = {}
    for p in EXTRACTED.glob("*.json"):
        if p.stem.startswith("_"):
            continue
        rec = json.loads(p.read_text())
        vid = rec.get("vendor_id", p.stem)
        gst = rec.get("gst_number")
        if gst:
            reg[_norm(gst)] = vid
        phone = (rec.get("contact") or {}).get("phone")
        if phone:
            reg[_norm(phone)] = vid
    return reg


def redact_leaked_pii(answer: str, allowed_ids: set, registry: dict):
    """Redact any GST/phone in the answer that belongs to a vendor NOT in allowed_ids
    (the vendors the user actually asked about). Deterministic anti-exfiltration —
    works even if the model was talked into leaking."""
    redactions = []

    def _check(m):
        val = m.group(0)
        owner = registry.get(_norm(val))
        if owner and owner not in allowed_ids:
            redactions.append((val, owner))
            return "[redacted: other vendor's private data]"
        return val

    answer = _GST_RE.sub(_check, answer)
    answer = _PHONE_RE.sub(_check, answer)
    return answer, redactions


# ---------------------------------------------------------------------------
# Layer 3b — trusted facts (authoritative values the model MUST use over prose)
# ---------------------------------------------------------------------------
# For the 3 reserved (poisoned) vendors we have no clean extracted record, so these
# come from a *verified vendor registry* (KYC/manifest), NOT the scrapeable listing —
# which is exactly the point: trusted facts live outside the attacker's reach.
_VERIFIED_RESERVED = {
    "imperial_court": {"price_inr": 1200000, "price_unit": "per_day", "rating": 4.7},
    "shaadi_shutter": {"price_inr": 105000, "price_unit": "package", "rating": 4.5},
    "regal_themes": {"price_inr": 350000, "price_unit": "package", "rating": 4.6},
}


def trusted_facts_for(vendor_ids) -> dict:
    facts = {}
    for vid in vendor_ids:
        if vid in _VERIFIED_RESERVED:
            facts[vid] = _VERIFIED_RESERVED[vid]
            continue
        p = EXTRACTED / f"{vid}.json"
        if p.exists():
            rec = json.loads(p.read_text())
            facts[vid] = {
                "price_inr": rec.get("price_range_inr"),
                "price_unit": rec.get("price_unit"),
                "rating": rec.get("rating"),
            }
    return facts
