"""Local LLM backend, response caching, and structured output retry protocol."""

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from animated_infographics.errors import DependencyMissing

DEFAULT_MODEL: str = "gemma4:26b"
DEFAULT_ENDPOINT: str = "http://127.0.0.1:11434/api/chat"
DEFAULT_TIMEOUT_S: float = 300.0


class LLMBackend(Protocol):
    """Protocol for LLM backends."""

    calls: int
    cache_hits: int

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
    ) -> dict[str, Any]:
        """Generate structured JSON conforming to schema."""
        ...


@dataclass
class Attempt:
    """Record of a generation attempt and its validation errors."""

    output: dict[str, Any] | None
    errors: list[str]


class OllamaBackend:
    """Local Ollama LLM backend with persistent response caching."""

    def __init__(
        self,
        *,
        model: str | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        no_cache: bool = False,
        cache_dir: Path | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model or os.environ.get("INFOGRAPHICS_PLANNER_MODEL", DEFAULT_MODEL)
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.no_cache = no_cache

        base_cache = cache_dir or Path(os.environ.get("INFOGRAPHICS_CACHE_DIR", "./cache"))
        self.cache_dir = base_cache / "llm"

        self.client = client
        self.calls: int = 0
        self.cache_hits: int = 0

    def _canonical_cache_key(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        attempt: int,
    ) -> tuple[str, dict[str, Any]]:
        cache_obj: dict[str, Any] = {
            "format": schema,
            "messages": messages,
            "model": self.model,
            "options": {
                "num_ctx": 16384,
                "num_predict": 2048,
                "seed": 7 + attempt,
                "temperature": 0.3,
            },
            "think": False,
        }
        canon_bytes = json.dumps(cache_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        key = hashlib.sha256(canon_bytes).hexdigest()
        return key, cache_obj

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
    ) -> dict[str, Any]:
        """Generate structured JSON via Ollama or return cached response."""
        # calls counter is incremented at entry, before cache lookup
        self.calls += 1

        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            if user:
                messages.append({"role": "user", "content": user})

        key, cache_obj = self._canonical_cache_key(messages, schema, attempt)
        cache_file = self.cache_dir / f"{key}.json"

        # Check response cache
        if not self.no_cache and cache_file.is_file():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    entry = json.load(f)
                    self.cache_hits += 1
                    cached_resp: dict[str, Any] = entry["response"]
                    return cached_resp
            except Exception:
                # Corrupt cache file, proceed with fresh generation
                pass

        payload = {
            "model": self.model,
            "messages": messages,
            "format": schema,
            "think": False,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.3,
                "seed": 7 + attempt,
                "num_ctx": 16384,
                "num_predict": 2048,
            },
        }

        t0 = time.time()
        client = self.client or httpx.Client(timeout=self.timeout_s)
        try:
            resp = client.post(self.endpoint, json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise DependencyMissing(
                f"Ollama server is not running on {self.endpoint}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DependencyMissing(f"Ollama request failed: {exc}") from exc
        finally:
            if client is not self.client:
                client.close()

        if resp.status_code == 404 or "not found" in resp.text.lower():
            raise DependencyMissing(
                f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}"
            )

        if resp.status_code != 200:
            raise DependencyMissing(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

        elapsed_ms = int((time.time() - t0) * 1000)
        data = resp.json()

        # Parse message content
        content = data.get("message", {}).get("content", "")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected JSON object, got {type(parsed).__name__}")

        # Write to cache
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "request": cache_obj,
                "response": parsed,
                "elapsed_ms": elapsed_ms,
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, sort_keys=True)
        except Exception:
            pass

        return parsed


def run_with_retries(
    backend: LLMBackend,
    *,
    stage: str,
    system: str,
    user: str,
    schema: dict[str, Any],
    validate: Callable[[dict[str, Any]], tuple[dict[str, Any], list[str]]],
    max_attempts: int = 3,
) -> tuple[dict[str, Any] | None, list[Attempt]]:
    """Run generation up to max_attempts, appending errors to conversation on failure."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    attempts: list[Attempt] = []

    for attempt_idx in range(max_attempts):
        raw_output: dict[str, Any] | None = None
        try:
            raw_output = backend.generate_json(
                stage=stage,
                messages=list(messages),
                schema=schema,
                attempt=attempt_idx,
            )
            repaired_output, errors = validate(raw_output)
            attempts.append(Attempt(output=raw_output, errors=errors))

            if not errors:
                return repaired_output, attempts

        except (ValueError, json.JSONDecodeError) as exc:
            errors = [f"JSON parsing error: {exc}"]
            attempts.append(Attempt(output=None, errors=errors))

        # Format retry prompt for the next attempt
        error_lines = "\n".join(f"- {e}" for e in errors[:20])
        prev_json_str = json.dumps(raw_output) if raw_output is not None else "{}"

        messages.append({"role": "assistant", "content": prev_json_str})
        retry_msg = f"Your previous JSON was rejected:\n{error_lines}\nReturn corrected JSON only."
        messages.append({"role": "user", "content": retry_msg})

    return None, attempts
