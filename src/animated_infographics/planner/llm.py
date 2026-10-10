"""Local LLM backend, response caching, and structured output retry protocol."""

import base64
import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

import httpx

from animated_infographics.errors import DependencyMissing

DEFAULT_MODEL: str = "gemma4:26b"
DEFAULT_ENDPOINT: str = "http://127.0.0.1:11434/api/chat"
DEFAULT_TIMEOUT_S: float = 300.0

STAGE_TIMEOUTS: Final[dict[str, float]] = {
    "text_check": 60.0,
}


class LLMResponseError(ValueError):
    """Raised when Ollama returns an unexpected HTTP response or error status."""


class LLMBackend(Protocol):
    """Protocol for LLM backends."""

    calls: int
    cache_hits: int
    last_elapsed_ms: int = 0

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, Any]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
        num_predict: int | None = None,
        temperature: float = 0.3,
        images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON conforming to schema."""
        ...


@dataclass
class Attempt:
    """Record of a generation attempt and its validation errors."""

    output: dict[str, Any] | None
    errors: list[str]


FORBIDDEN_SCHEMA_KEYS: frozenset[str] = frozenset(
    {"maxLength", "minLength", "maxItems", "minItems", "pattern"}
)


def _clean_schema_node(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _clean_schema_node(v) for k, v in node.items() if k not in FORBIDDEN_SCHEMA_KEYS}
    if isinstance(node, list):
        return [_clean_schema_node(item) for item in node]
    return node


def llm_facing_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove length, count, and pattern constraints from JSON Schema.

    Per design_planner.md §1:
    Removes maxLength, minLength, maxItems, minItems, and pattern.
    Preserves enum, type, required, and additionalProperties.
    """
    res = _clean_schema_node(schema)
    return res if isinstance(res, dict) else {}


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
        self.last_elapsed_ms: int = 0
        self._checked_stages: set[str] = set()

    def _canonical_cache_key(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        attempt: int,
        num_predict: int | None = None,
        temperature: float = 0.3,
    ) -> tuple[str, dict[str, Any]]:
        effective_num_predict = num_predict if num_predict is not None else 2048
        cache_obj: dict[str, Any] = {
            "format": schema,
            "messages": messages,
            "model": self.model,
            "options": {
                "num_ctx": 16384,
                "num_predict": effective_num_predict,
                "seed": 7 + attempt,
                "temperature": temperature,
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
        messages: list[dict[str, Any]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
        num_predict: int | None = None,
        temperature: float = 0.3,
        images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON via Ollama or return cached response."""
        # calls counter is incremented at entry, before cache lookup
        self.calls += 1

        clean_schema = llm_facing_schema(schema)

        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            if user:
                messages.append({"role": "user", "content": user})

        # Deep copy messages for cache_obj and payload
        cache_messages: list[dict[str, Any]] = [dict(m) for m in messages]
        payload_messages: list[dict[str, Any]] = [dict(m) for m in messages]

        if images:
            img_hashes = [hashlib.sha256(img).hexdigest() for img in images]
            img_b64s = [base64.b64encode(img).decode("ascii") for img in images]
            user_found = False
            for m in cache_messages:
                if m.get("role") == "user":
                    m["images"] = img_hashes
                    user_found = True
                    break
            for m in payload_messages:
                if m.get("role") == "user":
                    m["images"] = img_b64s
                    break
            if not user_found:
                cache_messages.append({"role": "user", "content": "", "images": img_hashes})
                payload_messages.append({"role": "user", "content": "", "images": img_b64s})

        key, cache_obj = self._canonical_cache_key(
            cache_messages, clean_schema, attempt, num_predict=num_predict, temperature=temperature
        )
        cache_file = self.cache_dir / f"{key}.json"

        # Check response cache
        if not self.no_cache and cache_file.is_file():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    entry = json.load(f)
                    self.cache_hits += 1
                    cached_resp: dict[str, Any] = entry["response"]
                    self.last_elapsed_ms = int(entry.get("elapsed_ms", 0))
                    return cached_resp
            except Exception:
                # Corrupt cache file, proceed with fresh generation
                pass

        effective_num_predict = num_predict if num_predict is not None else 2048
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "format": clean_schema,
            "think": False,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": temperature,
                "seed": 7 + attempt,
                "num_ctx": 16384,
                "num_predict": effective_num_predict,
            },
        }

        t0 = time.time()
        timeout = STAGE_TIMEOUTS.get(stage, self.timeout_s)

        need_guard = False
        if stage not in self._checked_stages:
            self._checked_stages.add(stage)
            from animated_infographics.memguard import is_ollama_model_loaded

            base_url = self.endpoint.rsplit("/api/", 1)[0]
            if not is_ollama_model_loaded(self.model, endpoint=base_url):
                need_guard = True

        if need_guard:
            timeout = max(timeout, self.timeout_s)

        def _do_post() -> httpx.Response:
            client = self.client or httpx.Client(timeout=timeout)
            try:
                return client.post(self.endpoint, json=payload)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                raise DependencyMissing(
                    f"Ollama server is not running on {self.endpoint}: {exc}"
                ) from exc
            except httpx.HTTPError as exc:
                raise DependencyMissing(f"Ollama request failed: {exc}") from exc
            finally:
                if client is not self.client:
                    client.close()

        if need_guard:
            from animated_infographics.memguard import guard

            with guard("llm_load"):
                resp = _do_post()
        else:
            resp = _do_post()

        if resp.status_code == 404:
            raise DependencyMissing(
                f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}"
            )

        if resp.status_code != 200:
            is_missing_model = False
            try:
                err_body = resp.json()
                err_msg = str(err_body.get("error", "")).lower()
                if "not found" in err_msg and ("model" in err_msg or self.model.lower() in err_msg):
                    is_missing_model = True
            except Exception:
                pass

            if is_missing_model:
                raise DependencyMissing(
                    f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}"
                )

            raise LLMResponseError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

        elapsed_ms = int((time.time() - t0) * 1000)
        self.last_elapsed_ms = elapsed_ms
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
    num_predict: int | None = None,
    temperature: float = 0.3,
    images: list[bytes] | None = None,
    attempt_offset: int = 0,
) -> tuple[dict[str, Any] | None, list[Attempt]]:
    """Run generation up to max_attempts, appending errors to conversation on failure."""
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    attempts: list[Attempt] = []

    for attempt_idx in range(max_attempts):
        raw_output: dict[str, Any] | None = None
        extra_kwargs: dict[str, Any] = {}
        if num_predict is not None:
            extra_kwargs["num_predict"] = num_predict
        if temperature != 0.3:
            extra_kwargs["temperature"] = temperature
        if images is not None:
            extra_kwargs["images"] = images

        try:
            raw_output = backend.generate_json(
                stage=stage,
                messages=list(messages),
                schema=schema,
                attempt=attempt_idx + attempt_offset,
                **extra_kwargs,
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
        prev_json_str = json.dumps(raw_output, sort_keys=True) if raw_output is not None else "{}"

        messages.append({"role": "assistant", "content": prev_json_str})
        retry_msg = f"Your previous JSON was rejected:\n{error_lines}\nReturn corrected JSON only."
        messages.append({"role": "user", "content": retry_msg})

    return None, attempts
