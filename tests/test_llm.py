"""Unit tests for planner/llm.py using httpx.MockTransport."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from animated_infographics.errors import DependencyMissing
from animated_infographics.planner.llm import (
    OllamaBackend,
    run_with_retries,
)


def test_cache_key_canonical_ordering(tmp_path: Path) -> None:
    """Verify cache key is identical for dicts with different key order."""
    backend = OllamaBackend(cache_dir=tmp_path)

    schema_1 = {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "number"}}}
    schema_2 = {"properties": {"b": {"type": "number"}, "a": {"type": "string"}}, "type": "object"}

    messages = [{"role": "system", "content": "prompt"}]

    key1, _ = backend._canonical_cache_key(messages, schema_1, attempt=0)
    key2, _ = backend._canonical_cache_key(messages, schema_2, attempt=0)

    assert key1 == key2


def test_cache_hit_increments_calls_and_hits(tmp_path: Path) -> None:
    """Verify a cache hit increments both calls and cache_hits."""
    recorded_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": '{"result": "ok"}'}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OllamaBackend(cache_dir=tmp_path, client=client)

    schema = {"type": "object"}
    messages = [{"role": "user", "content": "hi"}]

    # Call 1: cache miss
    resp1 = backend.generate_json(stage="test", messages=messages, schema=schema, attempt=0)
    assert resp1 == {"result": "ok"}
    assert backend.calls == 1
    assert backend.cache_hits == 0
    assert len(recorded_requests) == 1

    # Call 2: cache hit
    resp2 = backend.generate_json(stage="test", messages=messages, schema=schema, attempt=0)
    assert resp2 == {"result": "ok"}
    assert backend.calls == 2
    assert backend.cache_hits == 1
    # No new HTTP request was made
    assert len(recorded_requests) == 1


def test_retry_protocol_and_seeds(tmp_path: Path) -> None:
    """Verify the second attempt carries previous output, error lines, and incremented seeds."""
    recorded_payloads: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        recorded_payloads.append(payload)
        attempt_num = len(recorded_payloads) - 1
        return httpx.Response(
            200,
            json={"message": {"content": f'{{"attempt": {attempt_num}}}'}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OllamaBackend(cache_dir=tmp_path, client=client, no_cache=True)

    def validate(output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        # Fail attempts 0 and 1, pass on attempt 2
        attempt_val = output.get("attempt")
        if attempt_val == 0:
            return output, ["field 'name' missing", "value must be positive"]
        elif attempt_val == 1:
            return output, ["field 'name' still invalid"]
        return {"repaired": True, **output}, []

    output, attempts = run_with_retries(
        backend,
        stage="test",
        system="System prompt",
        user="User prompt",
        schema={"type": "object"},
        validate=validate,
        max_attempts=3,
    )

    assert output is not None
    assert output["repaired"] is True
    assert len(attempts) == 3

    # Check seeds across attempts: 7, 8, 9
    assert len(recorded_payloads) == 3
    assert recorded_payloads[0]["options"]["seed"] == 7
    assert recorded_payloads[1]["options"]["seed"] == 8
    assert recorded_payloads[2]["options"]["seed"] == 9

    # Check that second attempt request carried previous output and errors
    attempt_1_msgs = recorded_payloads[1]["messages"]
    assert len(attempt_1_msgs) == 4
    assert attempt_1_msgs[0]["role"] == "system"
    assert attempt_1_msgs[1]["role"] == "user"
    assert attempt_1_msgs[2]["role"] == "assistant"
    assert attempt_1_msgs[2]["content"] == '{"attempt": 0}'
    assert attempt_1_msgs[3]["role"] == "user"
    assert "Your previous JSON was rejected:" in attempt_1_msgs[3]["content"]
    assert "- field 'name' missing" in attempt_1_msgs[3]["content"]
    assert "- value must be positive" in attempt_1_msgs[3]["content"]


def test_retry_exhaustion_returns_none(tmp_path: Path) -> None:
    """Verify that when all attempts fail, (None, attempts) is returned."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": '{"bad": true}'}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OllamaBackend(cache_dir=tmp_path, client=client, no_cache=True)

    def always_invalid(output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        return output, ["Always invalid"]

    output, attempts = run_with_retries(
        backend,
        stage="test",
        system="Sys",
        user="Usr",
        schema={"type": "object"},
        validate=always_invalid,
        max_attempts=3,
    )

    assert output is None
    assert len(attempts) == 3
    assert all(len(a.errors) == 1 for a in attempts)


def test_ollama_missing_model_raises_dependency_missing(tmp_path: Path) -> None:
    """Verify 404 or missing model raises DependencyMissing with model name."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text='{"error": "model \'nonexistent:model\' not found"}')

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OllamaBackend(model="nonexistent:model", cache_dir=tmp_path, client=client)

    with pytest.raises(DependencyMissing, match="nonexistent:model"):
        backend.generate_json(stage="test", messages=[], schema={}, attempt=0)


def test_ollama_down_raises_dependency_missing(tmp_path: Path) -> None:
    """Verify connect error raises DependencyMissing."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OllamaBackend(cache_dir=tmp_path, client=client)

    with pytest.raises(DependencyMissing, match="Ollama server is not running"):
        backend.generate_json(stage="test", messages=[], schema={}, attempt=0)
