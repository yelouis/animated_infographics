"""Slow integration tests for critic enforcement with real model (Wave E / E1)."""

import json
from pathlib import Path

import pytest

from animated_infographics.contracts.models import (
    Beat,
    Bible,
    EmotionBeatScene,
)
from animated_infographics.contracts.templates import EmotionBeatProps
from animated_infographics.evals.planner import run_critic_regression_set
from animated_infographics.planner.critic import (
    build_critic_request,
    critic_mismatches,
    validate_critic_answer,
)
from animated_infographics.planner.llm import OllamaBackend


@pytest.mark.slow
@pytest.mark.parametrize("seed", [7, 8, 9])
def test_critic_emotion_enforcement_live(seed: int) -> None:
    """Verify two frozen emotion_beat cases yield 'unknown' emotion and trigger mismatches."""
    cases_path = Path(__file__).resolve().parents[1] / "data" / "critic_enforcement_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)

    emotion_cases = [c for c in data["cases"] if c["template"] == "emotion_beat"]
    assert len(emotion_cases) == 2

    backend = OllamaBackend(no_cache=True)
    attempt_offset = seed - 7

    for case_data in emotion_cases:
        bible = Bible.model_validate(case_data["bible"])
        props = EmotionBeatProps.model_validate(case_data["scene"]["props"])
        scene = EmotionBeatScene(
            id=case_data["scene"]["id"],
            beat_i=case_data["scene"]["beat_i"],
            template="emotion_beat",
            props=props,
        )
        beats_dict = case_data["beats"]
        b_bp = Beat(
            i=0,
            text=beats_dict["before_previous"],
            start_ms=0,
            end_ms=1000,
            word_start=0,
            word_end=10,
        )
        b_p = Beat(
            i=1,
            text=beats_dict["previous"],
            start_ms=1000,
            end_ms=2000,
            word_start=10,
            word_end=20,
        )
        b_curr = Beat(
            i=2,
            text=beats_dict["current"],
            start_ms=2000,
            end_ms=3000,
            word_start=20,
            word_end=30,
        )
        b_n = Beat(
            i=3,
            text=beats_dict["next"],
            start_ms=3000,
            end_ms=4000,
            word_start=30,
            word_end=40,
        )

        system, user, schema = build_critic_request(
            scene, b_curr, b_p, b_n, bible, before_prev_beat=b_bp
        )

        raw = backend.generate_json(
            stage="critic",
            system=system,
            user=user,
            schema=schema,
            attempt=attempt_offset,
            num_predict=256,
            temperature=0.0,
        )
        ans, val_errs = validate_critic_answer(scene, raw)
        assert not val_errs, f"Validation errors on {case_data['case']}: {val_errs}"
        actual_emotion = ans.get("emotion")
        assert actual_emotion == "unknown", (
            f"Expected critic emotion 'unknown' on {case_data['case']} "
            f"(seed {seed}), got {actual_emotion}"
        )

        mismatches = critic_mismatches(scene, ans, bible)
        expected_mismatch = f"emotion: {props.emotion} vs unknown"
        assert expected_mismatch in mismatches, (
            f"Expected {expected_mismatch} in mismatches on {case_data['case']} "
            f"(seed {seed}), got {mismatches}"
        )


@pytest.mark.slow
@pytest.mark.parametrize("seed", [7, 8, 9])
def test_critic_regression_set_stays_8_of_8(seed: int) -> None:
    """Verify critic regression set (A, B, B', C, E, F, G, H) remains 8/8 on seeds 7, 8, 9."""
    backend = OllamaBackend(no_cache=True)
    results = run_critic_regression_set(backend, attempt_offset=seed - 7)
    assert len(results) == 8
    for r in results:
        assert r["passed"] is True, (
            f"Regression case {r['id']} failed on seed {seed}: "
            f"got {r['actual']}, expected {r['expected']}"
        )
