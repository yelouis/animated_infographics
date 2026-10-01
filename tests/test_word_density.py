"""Unit tests for word_density evaluation CLI."""

import json
from pathlib import Path

from animated_infographics.evals.word_density import (
    evaluate_job_word_density,
    format_density_line,
    main,
)


def test_word_density_synthetic_timeline(tmp_path: Path) -> None:
    """Verify exact numbers on a synthetic timeline per D4 requirements."""
    job_dir = tmp_path / "synthetic_job"
    job_dir.mkdir()

    timeline_data = {
        "meta": {"fps": 30, "duration_frames": 600},
        "scenes": [
            {
                "id": "s000",
                "beat_i": 0,
                "template": "title_card",
                "props": {"title": "Title Does Not Count Toward Graphic Words"},
            },
            {
                "id": "s001",
                "beat_i": 1,
                "template": "kinetic_quote",
                "props": {"text": "Only three words"},  # 3 graphic words
            },
            {
                "id": "s002",
                "beat_i": 2,
                "template": "emotion_beat",
                "props": {"cast_id": "c1", "emotion": "neutral"},  # 0 graphic words
            },
        ],
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline_data), encoding="utf-8")

    res = evaluate_job_word_density(job_dir)
    assert res["job"] == "synthetic_job"
    assert res["graphic_words"] == 3
    assert res["seconds"] == 20.0
    assert abs(res["per_second"] - 0.15) < 1e-4
    assert res["k"] == 1
    assert res["m"] == 2
    assert res["passed"] is True

    line = format_density_line(res)
    assert line == "synthetic_job: graphic_words=3 seconds=20.0 per_second=0.15 light=1/2"

    ret = main([str(job_dir)])
    assert ret == 0


def test_word_density_fails_high_per_second(tmp_path: Path) -> None:
    job_dir = tmp_path / "fast_job"
    job_dir.mkdir()

    timeline_data = {
        "meta": {"fps": 30, "duration_frames": 60},  # 2.0 seconds
        "scenes": [
            {
                "id": "s000",
                "beat_i": 0,
                "template": "title_card",
                "props": {"title": "Title"},
            },
            {
                "id": "s001",
                "beat_i": 1,
                "template": "kinetic_quote",
                "props": {"text": "One two three four five six seven eight nine ten"},  # 10 words
            },
        ],
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline_data), encoding="utf-8")

    res = evaluate_job_word_density(job_dir)
    assert res["graphic_words"] == 10
    assert res["seconds"] == 2.0
    assert res["per_second"] == 5.0
    assert res["passed"] is False

    ret = main([str(job_dir)])
    assert ret == 1


def test_word_density_fails_low_light_share(tmp_path: Path) -> None:
    job_dir = tmp_path / "wordy_job"
    job_dir.mkdir()

    timeline_data = {
        "meta": {"fps": 30, "duration_frames": 3000},  # 100 seconds
        "scenes": [
            {
                "id": "s000",
                "beat_i": 0,
                "template": "title_card",
                "props": {"title": "Title"},
            },
            {
                "id": "s001",
                "beat_i": 1,
                "template": "kinetic_quote",
                "props": {"text": "One two three"},  # 3 words (>2)
            },
            {
                "id": "s002",
                "beat_i": 2,
                "template": "kinetic_quote",
                "props": {"text": "Four five six"},  # 3 words (>2)
            },
            {
                "id": "s003",
                "beat_i": 3,
                "template": "kinetic_quote",
                "props": {"text": "Seven eight nine"},  # 3 words (>2)
            },
        ],
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline_data), encoding="utf-8")

    res = evaluate_job_word_density(job_dir)
    assert res["m"] == 3
    assert res["k"] == 0
    assert res["passed"] is False

    ret = main([str(job_dir)])
    assert ret == 1
