"""A minimal tracer — the observability substrate for Phase 4.

Think of it as a stopwatch + notepad around each step of a request. Each step is a
SPAN (a named, timed block). Spans can nest (a tool call inside the agent loop). LLM
spans also record token counts. The whole thing serializes to JSON so we can point at
a real trace and, later, compute cost (tokens x price) and latency reports FROM this
data — no new measuring needed downstream.

Dependency-light (stdlib only), same as the rest of the project. A NullTracer is
provided so code can be trace-aware without branching when tracing is off.
"""
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def _ms_since(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


class Span:
    """One timed step. `.set(**attrs)` attaches numbers/metadata (tokens, model, ok)."""

    def __init__(self, name: str, kind: str, start_ms: float, depth: int):
        self.name = name
        self.kind = kind            # "request" | "decide" | "llm" | "tool" | "step"
        self.start_ms = start_ms    # offset from trace start
        self.depth = depth          # nesting level, for readable timelines
        self.duration_ms = None
        self.attrs = {}
        self.error = None

    def set(self, **attrs):
        self.attrs.update(attrs)
        return self

    def to_dict(self):
        return {
            "name": self.name, "kind": self.kind, "depth": self.depth,
            "start_ms": self.start_ms, "duration_ms": self.duration_ms,
            "attrs": self.attrs, "error": self.error,
        }


class Tracer:
    def __init__(self):
        self.request = None
        self.trace_id = None
        self.created = None
        self.spans = []
        self._t0 = None
        self._depth = 0

    def start(self, request: str):
        self.request = request
        self.trace_id = uuid.uuid4().hex[:12]
        self.created = datetime.now(timezone.utc).isoformat()
        self.spans = []
        self._t0 = time.perf_counter()
        self._depth = 0
        return self

    @contextmanager
    def span(self, name: str, kind: str = "step", **attrs):
        sp = Span(name, kind, _ms_since(self._t0), self._depth)
        sp.attrs.update(attrs)
        self.spans.append(sp)          # append at open time -> preserves order
        self._depth += 1
        t = time.perf_counter()
        try:
            yield sp
        except Exception as e:          # record the error, then re-raise
            sp.error = repr(e)
            raise
        finally:
            sp.duration_ms = round((time.perf_counter() - t) * 1000, 2)
            self._depth -= 1

    def summary(self) -> dict:
        from . import cost  # local import avoids any import-order concerns
        llm = [s for s in self.spans if s.kind == "llm"]
        tools = [s for s in self.spans if s.kind == "tool"]
        tin = sum(s.attrs.get("tokens_in", 0) for s in llm)
        tout = sum(s.attrs.get("tokens_out", 0) for s in llm)
        est_cost = sum(cost.cost_usd(s.attrs.get("tokens_in", 0),
                                     s.attrs.get("tokens_out", 0),
                                     s.attrs.get("model", "")) for s in llm)
        return {
            "total_ms": _ms_since(self._t0),
            "llm_calls": len(llm),
            "tool_calls": len(tools),
            "tokens_in": tin,
            "tokens_out": tout,
            "tokens_total": tin + tout,
            "est_cost_usd": round(est_cost, 6),
        }

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "request": self.request,
            "created": self.created,
            "summary": self.summary(),
            "spans": [s.to_dict() for s in self.spans],
        }

    def save(self, dir_path) -> Path:
        d = Path(dir_path)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"trace_{self.trace_id}.json"
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        return p


# --- no-op tracer so code can be trace-aware without branching ---
class _NullSpan:
    def set(self, **attrs):
        return self


class NullTracer:
    def start(self, *_a, **_k):
        return self

    @contextmanager
    def span(self, *_a, **_k):
        yield _NullSpan()

    def summary(self):
        return {}
