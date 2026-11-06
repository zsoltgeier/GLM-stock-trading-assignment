"""Ollama JSON-schema adapter with full request/response logs and offline replay."""

import json
import os
from pathlib import Path

import requests

from .evidence import text_hash


class ModelFailure(ValueError):
    pass


class CacheMiss(ModelFailure):
    """An incomplete replay is a run error, not a historical model abstention."""


class Ollama:
    def __init__(self, config, cache_dir, replay=False, identity=None):
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.replay = replay
        self.base_url = os.getenv("LLM_BASE_URL", config.base_url).rstrip("/")
        self.model = os.getenv("LLM_MODEL", config.model)
        self.identity = identity or {"model": self.model}
        self.calls = []

    def inspect(self):
        """Record the actual local weight digest and server version before a live run."""
        tags = requests.get(self.base_url + "/api/tags", timeout=10)
        tags.raise_for_status()
        matches = [m for m in tags.json()["models"] if m["name"] == self.model]
        if not matches:
            raise ModelFailure(f"Model {self.model!r} unavailable; run: ollama pull {self.model}")
        version = requests.get(self.base_url + "/api/version", timeout=10)
        version.raise_for_status()
        self.identity = {"model": self.model, "digest": matches[0]["digest"], "server": version.json()["version"]}
        return self.identity

    def complete(self, stage, payload, schema, verify):
        prompt = (Path(__file__).parent / "prompts" / f"{stage}.txt").read_text()
        request = {"model": self.model, "stream": False, "keep_alive": "10m",
            "format": schema.model_json_schema(),
            "options": {"temperature": self.config.temperature, "seed": 42, "num_ctx": 8192, "num_predict": 700},
            "messages": [{"role":"system", "content":prompt}, {"role":"user", "content":json.dumps(
                {"input":payload, "output_schema":schema.model_json_schema()}, sort_keys=True)}]}
        key = text_hash(json.dumps({"request":request, "identity":self.identity}, sort_keys=True))
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            log = json.loads(path.read_text())
            # Do not trust cached outputs without reapplying all current checks.
            attempts = log["attempts"]
        elif self.replay:
            raise CacheMiss(f"Replay cache miss for {stage}: {key}")
        else:
            attempts = []
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            for _ in range(self.config.attempts):
                attempt = {}
                try:
                    response = requests.post(self.base_url + "/api/chat", json=request, timeout=self.config.timeout_seconds)
                    response.raise_for_status()
                    attempt["response"] = response.json()
                    parsed = schema.model_validate_json(attempt["response"]["message"]["content"])
                    verify(parsed)
                except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                    attempt["error"] = str(exc)
                attempts.append(attempt)
                path.write_text(json.dumps({"identity":self.identity, "request":request, "attempts":attempts}, indent=2))
                if "error" not in attempt:
                    break
        self.calls.append({"stage":stage, "key":key, "attempts":len(attempts),
                           "valid":False, "cache_file":str(path)})
        for attempt in attempts:
            if "error" not in attempt:
                try:
                    parsed = schema.model_validate_json(attempt["response"]["message"]["content"])
                    verify(parsed)
                    self.calls[-1]["valid"] = True
                    return parsed
                except (ValueError, KeyError, TypeError) as exc:
                    raise ModelFailure(f"Cached response failed verification: {exc}") from exc
        raise ModelFailure("Model validation failed: " + "; ".join(a.get("error", "invalid output") for a in attempts))
