"""TracingBackend — wraps any model backend and auto-records an LLM span per call.

The point: existing code (extractor, agent policy, briefing, judge) calls
`backend.complete(...)` unchanged. We just hand it a TracingBackend instead of the
raw GroqBackend, and every model call is now recorded — tokens in/out, latency, model
— into the active trace. Zero changes to the callers. This is why wrapping (not
editing every call site) is the right design.
"""


class TracingBackend:
    def __init__(self, backend, tracer):
        self.backend = backend
        self.tracer = tracer
        self.model = getattr(backend, "model", "?")

    def complete(self, messages, **kwargs):
        with self.tracer.span("llm.complete", kind="llm", model=self.model) as sp:
            out = self.backend.complete(messages, **kwargs)
            usage = out.get("usage") or {}
            sp.set(
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
                latency_s=round(out.get("latency", 0.0), 3),
                model=out.get("model", self.model),
            )
            return out
