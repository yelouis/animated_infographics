"""Slow integration tests for people-scene critic using real model (design_planner.md §11)."""

import pytest

from animated_infographics.evals.planner import run_critic_regression_set
from animated_infographics.planner.llm import OllamaBackend


@pytest.mark.slow
@pytest.mark.parametrize("seed", [7, 8, 9])
def test_critic_regression_set_slow(seed: int) -> None:
    """Verify critic regression set classifies 6/6 cases as expected on seeds 7, 8, 9."""
    backend = OllamaBackend(no_cache=True)
    results = run_critic_regression_set(backend, attempt_offset=seed - 7)
    assert len(results) == 6
    for r in results:
        assert r["passed"] is True, (
            f"Critic regression case {r['id']} (seed {seed}) failed: "
            f"got {r['actual']}, expected {r['expected']}"
        )
