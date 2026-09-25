"""Slow integration tests for Ollama gemma4:26b backend structured outputs."""

import time

import pytest

from animated_infographics.planner.llm import OllamaBackend

TOY_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["history", "science", "fiction"],
        },
        "summary": {
            "type": "string",
            "maxLength": 30,
        },
    },
    "required": ["category", "summary"],
    "additionalProperties": False,
}


@pytest.mark.slow
def test_gemma_structured_outputs_20_iterations() -> None:
    """Verify 20/20 schema-conforming responses from gemma4:26b with think: false."""
    backend = OllamaBackend(no_cache=True)
    latencies: list[float] = []

    for i in range(20):
        prompt = f"Iteration {i}: Describe a dramatic moment in Roman history in a few words."
        t0 = time.time()
        result = backend.generate_json(
            stage="test_slow",
            system=(
                "You are a historical data summarizer. Output JSON strictly matching the schema."
            ),
            user=prompt,
            schema=TOY_SCHEMA,
            attempt=i % 3,
        )
        elapsed = time.time() - t0
        latencies.append(elapsed)

        # 1. Schema conformance
        assert isinstance(result, dict)
        assert result.get("category") in {"history", "science", "fiction"}
        summary = result.get("summary")
        assert isinstance(summary, str)
        assert len(summary) <= 30
        assert "<think>" not in summary
        assert "</think>" not in summary

    mean_latency_s = sum(latencies) / len(latencies)
    print(f"\n[Slow Test] Gemma4 20 iterations passed. Mean latency: {mean_latency_s:.2f}s")
