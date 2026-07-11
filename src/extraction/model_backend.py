"""Model backends — the SWAPPABLE part of the extractor.

The whole pipeline (validate -> repair -> fallback) is model-agnostic. Swapping
the LLM is just swapping a backend. This is good engineering AND sets up the
model-routing competency (#9) later.

- GroqBackend: real calls to Groq Cloud (OpenAI-compatible), stdlib urllib only.
- MockBackend: scripted responses, for testing the reliability logic with NO key
  and NO cost — including deliberately broken responses to prove repair/fallback.
"""
import json
import re
import time
import urllib.error
import urllib.request


class ModelError(Exception):
    pass


class GroqBackend:
    def __init__(self, api_key: str, base_url: str, model: str):
        if not api_key:
            raise ModelError("GROQ_API_KEY is empty — set it in .env or the environment.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @staticmethod
    def _retry_after(detail, default=5.0):
        """Pull 'try again in 2.145s' out of a 429 body, else use default."""
        m = re.search(r"try again in ([0-9.]+)s", detail)
        return (float(m.group(1)) + 0.5) if m else default

    def complete(self, messages, json_mode: bool = True, _rl_tries: int = 6):
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages, "temperature": 0}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Groq sits behind Cloudflare, which 403s the default Python urllib
            # User-Agent (error 1010). A normal UA gets through.
            "User-Agent": "baraat-extractor/1.0",
        }

        for _ in range(_rl_tries):
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                if json_mode and e.code == 400:
                    # Some models reject json_object mode — retry without it.
                    return self.complete(messages, json_mode=False, _rl_tries=_rl_tries)
                if e.code == 429:
                    # Free-tier tokens-per-minute limit — wait the suggested time.
                    wait = self._retry_after(detail)
                    time.sleep(wait)
                    continue
                raise ModelError(f"HTTP {e.code}: {detail[:300]}")
            except urllib.error.URLError as e:
                raise ModelError(f"network error reaching Groq: {e}")
            return {
                "text": body["choices"][0]["message"]["content"],
                "usage": body.get("usage", {}),
                "latency": time.time() - t0,
                "model": self.model,
            }
        raise ModelError("rate limit: exhausted retries")


    def complete_streaming(self, messages):
        """Streaming variant — measures time-to-first-token (TTFT).

        Non-streaming latency is one number; streaming splits it: TTFT (prefill: time
        to process the prompt + emit the first token) vs the rest (decode: generating
        the remaining tokens). Perceived speed is driven by TTFT, not total.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages, "temperature": 0,
                   "stream": True, "stream_options": {"include_usage": True}}
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "baraat-extractor/1.0",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        t0 = time.time()
        ttft = None
        parts = []
        usage = {}
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                for raw in resp:
                    line = raw.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if body == "[DONE]":
                        break
                    try:
                        obj = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if choices:
                        piece = (choices[0].get("delta") or {}).get("content")
                        if piece:
                            if ttft is None:
                                ttft = time.time() - t0
                            parts.append(piece)
                    if obj.get("usage"):
                        usage = obj["usage"]
        except urllib.error.HTTPError as e:
            raise ModelError(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:200]}")
        total = time.time() - t0
        return {"text": "".join(parts), "ttft_s": ttft, "latency": total,
                "usage": usage, "model": self.model}


class MockBackend:
    """Returns scripted responses in order. Each script entry is a raw string
    (what the 'model' would return). Used to test the loop deterministically."""

    def __init__(self, scripted_responses, model="mock"):
        self._responses = list(scripted_responses)
        self._i = 0
        self.model = model

    def complete(self, messages, json_mode: bool = True):
        if self._i >= len(self._responses):
            raise ModelError("MockBackend ran out of scripted responses")
        text = self._responses[self._i]
        self._i += 1
        return {"text": text, "usage": {}, "latency": 0.0, "model": self.model}
