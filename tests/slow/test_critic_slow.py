"""Slow integration tests for people-scene critic using real model (design_planner.md §11)."""

import pytest

from animated_infographics.evals.planner import run_critic_regression_set
from animated_infographics.planner.llm import OllamaBackend


@pytest.mark.slow
def test_critic_regression_set_4_of_4_slow() -> None:
    """Verify critic regression set classifies 4/4 cases as expected using real Ollama model."""
    backend = OllamaBackend(no_cache=True)
    results = run_critic_regression_set(backend)
    assert len(results) == 4
    for r in results:
        assert r["passed"] is True, (
            f"Critic regression case {r['id']} failed: got {r['actual']}, expected {r['expected']}"
        )
