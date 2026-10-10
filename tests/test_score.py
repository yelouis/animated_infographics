"""Tests for presentation simulation scoring, metrics, strip charts, and oracle baseline.

Per design_presentation_simulation.md §8 and design_testing_and_validation.md §2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from animated_infographics.presentation.score import (
    calculate_adlib_stability,
    calculate_false_switches,
    calculate_onset_lag,
    calculate_point_accuracy,
    calculate_skip_recovery,
    calculate_slide_accuracy,
    compute_presentation_score,
    generate_strip_chart,
)


def _make_dummy_deck() -> dict[str, Any]:
    return {
        "slides": [
            {
                "id": "d1",
                "title": "Slide 1",
                "points": ["Point 1", "Point 2"],
            },
            {
                "id": "d2",
                "title": "Slide 2",
                "points": ["Point 3", "Point 4"],
            },
        ]
    }


def test_calculate_slide_accuracy_synthetic() -> None:
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d2", "point": 0}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 1000},
        {"start_ms": 1000, "end_ms": 2000},
    ]

    # Perfect tracking: d1 for first sec, d2 for second sec
    commits_perfect = [
        {"node_id": "d1_p0", "at_ms": 0},
        {"node_id": "d2_p0", "at_ms": 1000},
    ]
    acc = calculate_slide_accuracy(sentences, timing, commits_perfect)
    assert acc == 1.0

    # Half tracking: stays on d1 for both seconds
    commits_half = [
        {"node_id": "d1_p0", "at_ms": 0},
    ]
    acc_half = calculate_slide_accuracy(sentences, timing, commits_half)
    assert acc_half == 0.5


def test_calculate_point_accuracy_section_rule() -> None:
    """A section node counts as correct during its slide's first point (p0)."""
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 1}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 1000},
        {"start_ms": 1000, "end_ms": 2000},
    ]

    # Section node during p0 is correct; d1_p1 during p1 is correct
    commits = [
        {"node_id": "d1_section", "at_ms": 0},
        {"node_id": "d1_p1", "at_ms": 1000},
    ]
    acc = calculate_point_accuracy(sentences, timing, commits)
    assert acc == 1.0

    # Section node during p1 is NOT correct
    commits_wrong = [
        {"node_id": "d1_section", "at_ms": 0},
    ]
    acc_wrong = calculate_point_accuracy(sentences, timing, commits_wrong)
    assert acc_wrong == 0.5


def test_calculate_onset_lag_synthetic() -> None:
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 1}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 2000},
        {"start_ms": 2000, "end_ms": 4000},
    ]

    # d1_p0 committed at 500ms (lag 0.5s), d1_p1 committed at 3500ms (lag 1.5s)
    commits = [
        {"node_id": "d1_p0", "at_ms": 500},
        {"node_id": "d1_p1", "at_ms": 3500},
    ]
    med, p90 = calculate_onset_lag(sentences, timing, commits)
    assert med == 1.0
    assert p90 == 1.4


def test_calculate_onset_lag_already_on_screen() -> None:
    # Node already on screen at first spoken word -> lag 0
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 1}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 5000},
        {"start_ms": 5000, "end_ms": 10000},
    ]
    # d1_p1 committed at 3000ms (shown early, 2.0s before first word at 5000ms)
    commits = [
        {"node_id": "d1_p0", "at_ms": 0},
        {"node_id": "d1_p1", "at_ms": 3000},
    ]
    med, p90 = calculate_onset_lag(sentences, timing, commits)
    # d1_p0 lag is 0 (on screen at 0), d1_p1 lag is 0 (on screen at 5000)
    assert med == 0.0
    assert p90 == 0.0


def test_calculate_onset_lag_synthetic_scenarios() -> None:
    # Test cases from design_testing_and_validation.md §2:
    # - a commit 2.0 s after first word -> 2.0
    # - never on screen during a 14 s first run -> 14.0
    # - during a 6 s run -> 10.0
    # - a commit during a later revisit of the point is ignored
    # 0 to 10s: commit at 2s -> lag 2.0
    # 10 to 24s (14s run): never on screen -> 14.0
    # 24 to 30s (6s run): never on screen, revisit at 50s ignored -> 10.0
    # 30 to 45s: d2_p0
    # 45 to 60s: revisit of d1_p2
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 1}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 2}, "op": "verbatim"},
        {"label": {"slide": "d2", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 2}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 10000},
        {"start_ms": 10000, "end_ms": 24000},
        {"start_ms": 24000, "end_ms": 30000},
        {"start_ms": 30000, "end_ms": 45000},
        {"start_ms": 45000, "end_ms": 60000},
    ]
    commits = [
        {"node_id": "d1_section", "at_ms": 0},
        {"node_id": "d1_p0", "at_ms": 2000},  # commit 2.0s after first word (0s) -> lag 2.0
        # d1_p1 is never committed
        # d1_p2 is committed at 50s during revisit -> should be ignored for first run
        {"node_id": "d1_p2", "at_ms": 50000},
    ]
    # Points present in performance: d1_p0, d1_p1, d1_p2, d2_p0
    # d1_p0: 2.0
    # d1_p1: 14s run -> max(10.0, 14.0) = 14.0
    # d1_p2: 6s run -> max(10.0, 6.0) = 10.0 (revisit commit at 50s ignored)
    # d2_p0: never committed, 15s run (30 to 45s) -> max(10.0, 15.0) = 15.0
    # Lags: [2.0, 10.0, 14.0, 15.0]
    # Median = (10.0 + 14.0)/2 = 12.0
    med, p90 = calculate_onset_lag(sentences, timing, commits)
    assert med == 12.0


def test_calculate_onset_lag_oracle_scores_zero() -> None:
    # The oracle playback must score 0.0 on every point
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 1}, "op": "verbatim"},
        {"label": {"slide": "d2", "point": 0}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 3000},
        {"start_ms": 3000, "end_ms": 6000},
        {"start_ms": 6000, "end_ms": 9000},
    ]
    # Oracle commits each point at its first spoken word
    commits = [
        {"node_id": "d1_section", "at_ms": 0},
        {"node_id": "d1_p0", "at_ms": 0},
        {"node_id": "d1_p1", "at_ms": 3000},
        {"node_id": "d2_section", "at_ms": 6000},
        {"node_id": "d2_p0", "at_ms": 6000},
    ]
    med, p90 = calculate_onset_lag(sentences, timing, commits)
    assert med == 0.0
    assert p90 == 0.0


def test_calculate_false_switches_synthetic() -> None:
    deck = _make_dummy_deck()
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d1", "point": 1}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 30000},
        {"start_ms": 30000, "end_ms": 60000},
    ]

    # Valid switches: d1_p0 -> d1_p1
    commits_valid = [
        {"node_id": "d1_section", "at_ms": 0},
        {"node_id": "d1_p0", "at_ms": 1000},
        {"node_id": "d1_p1", "at_ms": 31000},
    ]
    switches_valid = calculate_false_switches(sentences, timing, commits_valid, deck, 60000)
    assert switches_valid == 0.0

    # False switch: jumping to d2_p1 while on d1_p0
    commits_invalid = [
        {"node_id": "d1_section", "at_ms": 0},
        {"node_id": "d2_p1", "at_ms": 15000},  # Neither d1_p0 nor d1_p1
    ]
    switches_invalid = calculate_false_switches(sentences, timing, commits_invalid, deck, 60000)
    assert switches_invalid == 1.0  # 1 switch in 1 minute = 1.0 / min


def test_calculate_adlib_stability_synthetic() -> None:
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": "adlib", "op": "adlib"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 2000},
        {"start_ms": 2000, "end_ms": 6000},
    ]

    # No commits during adlib -> 100% stable
    commits_stable = [
        {"node_id": "d1_p0", "at_ms": 0},
    ]
    stab = calculate_adlib_stability(sentences, timing, commits_stable)
    assert stab == 1.0

    # Commit at 3000ms (1000ms into 4000ms adlib) -> 25% stable
    commits_unstable = [
        {"node_id": "d1_p0", "at_ms": 0},
        {"node_id": "d2_p0", "at_ms": 3000},
    ]
    stab_unstable = calculate_adlib_stability(sentences, timing, commits_unstable)
    assert stab_unstable == 0.25


def test_calculate_skip_recovery_synthetic() -> None:
    deck = _make_dummy_deck()
    # Performance skips d1_p1 and goes straight from d1_p0 to d2_p0
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": {"slide": "d2", "point": 0}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 2000},
        {"start_ms": 2000, "end_ms": 6000},
    ]

    # Matcher recovers to d2_p0 at 3500ms (1.5s after 2000ms onset)
    commits = [
        {"node_id": "d1_p0", "at_ms": 0},
        {"node_id": "d2_p0", "at_ms": 3500},
    ]
    rec = calculate_skip_recovery(sentences, timing, commits, deck)
    assert rec == 1.5


def test_strip_chart_generation(tmp_path: Path) -> None:
    deck = _make_dummy_deck()
    sentences = [
        {"label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        {"label": "adlib", "op": "adlib"},
        {"label": {"slide": "d2", "point": 0}, "op": "verbatim"},
    ]
    timing = [
        {"start_ms": 0, "end_ms": 5000},
        {"start_ms": 5000, "end_ms": 10000},
        {"start_ms": 10000, "end_ms": 20000},
    ]
    commits = [
        {"node_id": "d1_section", "at_ms": 0},
        {"node_id": "d1_p0", "at_ms": 1000},
        {"node_id": "d2_p0", "at_ms": 11000},
    ]
    out_png = tmp_path / "strip_chart.png"
    generate_strip_chart(sentences, timing, commits, deck, 20000, out_png)

    assert out_png.is_file()
    img = Image.open(out_png)
    assert img.size == (1200, 450)


def test_compute_presentation_score_e2e(tmp_path: Path) -> None:
    job_dir = tmp_path / "job_pres"
    job_dir.mkdir()

    deck = _make_dummy_deck()
    (job_dir / "deck.json").write_text(json.dumps(deck), encoding="utf-8")

    tree = {
        "schema_version": 1,
        "nodes": [
            {
                "id": "d1_section",
                "slide": "d1",
                "kind": "section",
                "point_i": None,
                "text": "Slide 1",
                "scene": {"id": "s000", "template": "title_card", "props": {"title": "Slide 1"}},
            },
            {
                "id": "d1_p0",
                "slide": "d1",
                "kind": "point",
                "point_i": 0,
                "text": "Point 1",
                "scene": {"id": "s001", "template": "title_card", "props": {"title": "Point 1"}},
            },
        ],
        "edges": [],
    }
    (job_dir / "tree.json").write_text(json.dumps(tree), encoding="utf-8")

    perf = {
        "schema_version": 1,
        "level": "mild",
        "seed": 7,
        "sentences": [
            {"text": "Point 1 text", "label": {"slide": "d1", "point": 0}, "op": "verbatim"},
        ],
        "op_counts": {"paraphrase": 0},
    }
    (job_dir / "performance.json").write_text(json.dumps(perf), encoding="utf-8")

    timing = [{"sentence_i": 0, "start_ms": 0, "end_ms": 3000}]
    (job_dir / "speak_timing.json").write_text(json.dumps(timing), encoding="utf-8")

    playback = {
        "schema_version": 1,
        "commits": [
            {"node_id": "d1_p0", "at_ms": 0, "decision_ms": 0, "compute_ms": 0, "score": 5.0}
        ],
        "holds": [],
    }
    (job_dir / "playback.json").write_text(json.dumps(playback), encoding="utf-8")

    timeline = {
        "schema_version": 1,
        "duration_frames": 90,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "scenes": [
            {
                "id": "s000",
                "template": "title_card",
                "start_frame": 0,
                "end_frame": 90,
                "props": {"title": "Point 1"},
            },
        ],
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")

    score_res = compute_presentation_score(job_dir, oracle=False)
    assert score_res.slide_accuracy == 1.0
    assert score_res.point_accuracy == 1.0
    assert (job_dir / "presentation_score.json").is_file()
    assert (job_dir / "strip_chart.png").is_file()
