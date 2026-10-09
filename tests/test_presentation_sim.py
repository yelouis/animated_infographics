"""Tests for presentation simulation mechanics, bars evaluation, and falsifications (Item I8).

Per design_testing_and_validation.md §4c and agent_execution_guide.md §3.I8.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from animated_infographics.contracts.score import PresentationMetricResult
from animated_infographics.presentation.score import (
    evaluate_presentation_bars,
    format_bar_str,
)
from animated_infographics.presentation.sim_mechanics import (
    REQUIRED_ARTEFACTS,
    check_job_mechanics,
)


def _make_passing_score_data(level: str = "mild") -> dict[str, Any]:
    if level == "mild":
        return {
            "level": "mild",
            "slide_accuracy": 0.95,
            "point_accuracy": 0.85,
            "onset_lag_median_s": 1.5,
            "onset_lag_p90_s": 4.0,
            "false_switches_per_min": 0.5,
            "adlib_stability": 0.90,
            "skip_recovery_s": None,
        }
    return {
        "level": "strong",
        "slide_accuracy": 0.85,
        "point_accuracy": 0.70,
        "onset_lag_median_s": 2.5,
        "onset_lag_p90_s": 6.0,
        "false_switches_per_min": 1.2,
        "adlib_stability": 0.75,
        "skip_recovery_s": 3.0,
    }


def test_evaluate_presentation_bars_mild_pass_and_miss() -> None:
    data = _make_passing_score_data("mild")
    results = evaluate_presentation_bars(data)
    assert all(r.passed for r in results)

    # Miss slide accuracy (< 0.90)
    data["slide_accuracy"] = 0.88
    results2 = evaluate_presentation_bars(data)
    slide_res = next(r for r in results2 if r.metric == "slide_accuracy")
    assert not slide_res.passed
    assert slide_res.bar == 0.90


def test_evaluate_presentation_bars_strong_pass_and_miss() -> None:
    data = _make_passing_score_data("strong")
    results = evaluate_presentation_bars(data)
    assert all(r.passed for r in results)
    # Check that skip_recovery_s is present for strong
    skip_res = next((r for r in results if r.metric == "skip_recovery_s"), None)
    assert skip_res is not None
    assert skip_res.passed

    # Miss skip recovery (> 6.0s)
    data["skip_recovery_s"] = 7.5
    results2 = evaluate_presentation_bars(data)
    skip_res2 = next(r for r in results2 if r.metric == "skip_recovery_s")
    assert not skip_res2.passed


def test_format_bar_str() -> None:
    assert format_bar_str("slide_accuracy", 0.90) == ">=0.90"
    assert format_bar_str("onset_lag_median_s", 3.0) == "<=3.0"
    assert format_bar_str("custom", ">=0.80") == ">=0.80"


def _create_minimal_valid_job(tmp_path: Path, style: str = "literal") -> Path:
    job_dir = tmp_path / "valid_job"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "out").mkdir(exist_ok=True)
    (job_dir / "logs").mkdir(exist_ok=True)

    # Ingest
    ingest = {"schema_version": 1, "style": style, "title": "Test Title"}
    (job_dir / "ingest.json").write_text(json.dumps(ingest), encoding="utf-8")

    # Tree
    tree: dict[str, Any] = {
        "schema_version": 1,
        "style_degraded": False,
        "nodes": [
            {
                "id": "d1_section",
                "kind": "section",
                "slide": "d1",
                "point_i": None,
                "text": "Intro",
                "scene": {"id": "s000", "template": "title_card", "props": {"title": "Intro"}},
            },
            {
                "id": "d1_p0",
                "kind": "point",
                "slide": "d1",
                "point_i": 0,
                "text": "First point",
                "scene": {
                    "id": "s001",
                    "template": "metaphor" if style == "creative" else "quote",
                    "props": {"quote": "First point", "attribution": "Author"},
                },
                "overlays": [{"kind": "label", "text": "Note"}] if style == "creative" else [],
            },
        ],
        "edges": [],
    }
    (job_dir / "tree.json").write_text(json.dumps(tree), encoding="utf-8")

    # Score
    oracle_score = _make_passing_score_data("mild")
    score_data = {
        "job_id": job_dir.name,
        "level": "mild",
        "style": style,
        "slide_accuracy": 0.95,
        "point_accuracy": 0.85,
        "onset_lag_median_s": 1.0,
        "onset_lag_p90_s": 2.0,
        "false_switches_per_min": 0.0,
        "adlib_stability": 1.0,
        "oracle": oracle_score,
    }
    (job_dir / "presentation_score.json").write_text(json.dumps(score_data), encoding="utf-8")

    # Artefacts
    for rel_path in REQUIRED_ARTEFACTS:
        p = job_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.is_file():
            p.write_text("dummy content\n", encoding="utf-8")

    if style == "creative":
        director_data = {
            "motifs": [],
            "metaphors": [{"beat_i": 0, "subject": "test"}],
            "asides": [],
            "director_dropped": [],
            "license_dropped": [],
        }
        (job_dir / "director.json").write_text(json.dumps(director_data), encoding="utf-8")
        (job_dir / "logs" / "tree.log").write_text(
            "director=ok license_calls=1 license_dropped=0 overlays=1\n",
            encoding="utf-8",
        )

    return job_dir


def test_sim_mechanics_missing_oracle_fails(tmp_path: Path) -> None:
    job_dir = _create_minimal_valid_job(tmp_path, style="literal")
    oracle_mp4 = job_dir / "out" / "oracle.mp4"
    assert oracle_mp4.is_file()
    oracle_mp4.unlink()

    errors = check_job_mechanics(job_dir)
    assert any("Missing required artefact: out/oracle.mp4" in e for e in errors)


def test_sim_mechanics_forbidden_point_title_card(tmp_path: Path) -> None:
    job_dir = _create_minimal_valid_job(tmp_path, style="literal")
    tree_path = job_dir / "tree.json"
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    # Set point node to title_card
    tree["nodes"][1]["scene"]["template"] = "title_card"
    tree_path.write_text(json.dumps(tree), encoding="utf-8")

    errors = check_job_mechanics(job_dir)
    assert any("uses forbidden template 'title_card'" in e for e in errors)


def test_sim_mechanics_creative_checks_falsification(tmp_path: Path) -> None:
    job_dir = _create_minimal_valid_job(tmp_path, style="creative")

    # 1. style_degraded == True must fail
    tree_path = job_dir / "tree.json"
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    tree["style_degraded"] = True
    tree_path.write_text(json.dumps(tree), encoding="utf-8")

    errors = check_job_mechanics(job_dir)
    assert any("style_degraded == True" in e for e in errors)

    # Reset
    tree["style_degraded"] = False
    tree_path.write_text(json.dumps(tree), encoding="utf-8")

    # 2. tree.log license calls mismatch must fail
    tree_log = job_dir / "logs" / "tree.log"
    tree_log.write_text(
        "director=ok license_calls=99 license_dropped=0 overlays=1\n",
        encoding="utf-8",
    )
    errors2 = check_job_mechanics(job_dir)
    assert any("license_calls=99 != expected 1" in e for e in errors2)


def test_falsification_a_oracle_always_miss_fails(tmp_path: Path) -> None:
    """Falsification (a) verification: if bars function returns all MISS on oracle, check fails."""

    def mock_evaluate_bars_miss(score_data: Any) -> list[PresentationMetricResult]:
        return [
            PresentationMetricResult(
                metric="slide_accuracy",
                value=0.0,
                bar=0.90,
                passed=False,
            )
        ]

    with patch(
        "animated_infographics.presentation.sim_mechanics.evaluate_presentation_bars",
        mock_evaluate_bars_miss,
    ):
        job_dir = _create_minimal_valid_job(tmp_path, style="literal")
        errors = check_job_mechanics(job_dir)
        assert any("Oracle missed §8 bar" in e for e in errors)


def test_falsification_b_shuffled_always_pass_fails() -> None:
    """Falsification (b) verification: if bars returns PASS on shuffled speech, check fails."""
    # Shuffled speech accuracy is low (~0.20)
    shuffled_slide_acc = 0.20
    shuffled_point_acc = 0.15

    # With normal evaluation: misses
    results = evaluate_presentation_bars(
        {
            "level": "mild",
            "slide_accuracy": shuffled_slide_acc,
            "point_accuracy": shuffled_point_acc,
        }
    )
    slide_res = next(r for r in results if r.metric == "slide_accuracy")
    point_res = next(r for r in results if r.metric == "point_accuracy")
    assert not slide_res.passed
    assert not point_res.passed

    # If someone mocked/broke the bars function to always PASS:
    broken_results = [
        PresentationMetricResult(
            metric="slide_accuracy",
            value=shuffled_slide_acc,
            bar=0.90,
            passed=True,
        ),
        PresentationMetricResult(
            metric="point_accuracy",
            value=shuffled_point_acc,
            bar=0.75,
            passed=True,
        ),
    ]
    # The falsification check asserts that shuffled speech does NOT pass accuracy bars
    b_slide_res = next(r for r in broken_results if r.metric == "slide_accuracy")
    b_point_res = next(r for r in broken_results if r.metric == "point_accuracy")
    with pytest.raises(AssertionError):
        assert not (b_slide_res.passed and b_point_res.passed)
