"""Unit tests for verify_creative evaluation logic and falsification checks."""

from __future__ import annotations

import json
from pathlib import Path

from animated_infographics.evals.verify_creative import verify_job_creative


def test_verify_creative_passes_valid_job(tmp_path: Path) -> None:
    job_dir = tmp_path / "valid_creative_job"
    job_dir.mkdir()
    preview_dir = job_dir / "preview"
    preview_dir.mkdir()

    # Timeline with 2 metaphors, 1 callback, 2 asides, 1 plant token before callback
    timeline = {
        "scenes": [
            {
                "id": "s000",
                "template": "title_card",
                "start_frame": 0,
                "end_frame": 60,
                "props": {"title": "Title"},
                "overlays": [],
            },
            {
                "id": "s001",
                "template": "kinetic_quote",
                "start_frame": 60,
                "end_frame": 120,
                "props": {"text": "Quote"},
                "overlays": [
                    {
                        "kind": "motif_token",
                        "motif_id": "m1",
                        "anchor": "top_right",
                        "icon": "Key",
                    }
                ],
            },
            {
                "id": "s002",
                "template": "metaphor",
                "start_frame": 120,
                "end_frame": 180,
                "props": {"label": "Metaphor 1", "image_entity": "meta_1", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s003",
                "template": "stat_callout",
                "start_frame": 180,
                "end_frame": 240,
                "props": {"value": 5, "decimals": 0},
                "overlays": [{"kind": "thought", "text": "Hmm", "anchor": "top_left"}],
            },
            {
                "id": "s004",
                "template": "metaphor",
                "start_frame": 240,
                "end_frame": 300,
                "props": {"label": "Metaphor 2", "image_entity": "meta_2", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s005",
                "template": "reveal",
                "start_frame": 300,
                "end_frame": 360,
                "props": {"text": "A secret"},
                "overlays": [{"kind": "prop", "icon": "Coins", "anchor": "bottom_left"}],
            },
            {
                "id": "s006",
                "template": "callback",
                "start_frame": 360,
                "end_frame": 420,
                "timing": {"item_frames": [20]},
                "props": {"motif_id": "m1", "label": "Key found", "icon": "Key"},
                "overlays": [],
            },
        ]
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")

    director = {
        "motifs": [{"id": "m1"}],
        "metaphors": [{"beat_i": 2}, {"beat_i": 4}],
        "asides": [{"beat_i": 3}, {"beat_i": 5}],
        "license_dropped": [],
        "overlay_dropped": [],
    }
    (job_dir / "director.json").write_text(json.dumps(director), encoding="utf-8")

    report = {
        "director_items": [
            {"kind": "motif_token", "fate": "rendered"},
            {"kind": "metaphor", "fate": "rendered"},
            {"kind": "thought", "fate": "rendered"},
            {"kind": "metaphor", "fate": "rendered"},
            {"kind": "prop", "fate": "rendered"},
            {"kind": "callback", "fate": "rendered"},
        ]
    }
    (preview_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

    res = verify_job_creative(job_dir)
    assert res["passed"] is True
    assert res["motifs_bar"] is True
    assert res["metaphors_bar"] is True
    assert res["asides_bar"] is True
    assert res["license_bar"] is True
    assert res["overlays_bar"] is True


def test_falsification_no_motifs_fails(tmp_path: Path) -> None:
    """Falsification: stubbing director to return no motifs fails the gate."""
    job_dir = tmp_path / "no_motifs_job"
    job_dir.mkdir()
    preview_dir = job_dir / "preview"
    preview_dir.mkdir()

    timeline = {
        "scenes": [
            {
                "id": "s000",
                "template": "title_card",
                "start_frame": 0,
                "end_frame": 60,
                "props": {"title": "Title"},
                "overlays": [],
            },
            {
                "id": "s001",
                "template": "metaphor",
                "start_frame": 60,
                "end_frame": 120,
                "props": {"label": "Metaphor 1", "image_entity": "meta_1", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s002",
                "template": "metaphor",
                "start_frame": 120,
                "end_frame": 180,
                "props": {"label": "Metaphor 2", "image_entity": "meta_2", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s003",
                "template": "reveal",
                "start_frame": 180,
                "end_frame": 240,
                "props": {"text": "A secret"},
                "overlays": [
                    {"kind": "thought", "text": "Hmm", "anchor": "top_left"},
                    {"kind": "prop", "icon": "Coins", "anchor": "bottom_left"},
                ],
            },
        ]
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")

    res = verify_job_creative(job_dir)
    assert res["passed"] is False
    assert res["motifs_bar"] is False


def test_falsification_unplanted_payoff_fails(tmp_path: Path) -> None:
    """A payoff without any earlier plant token fails the gate."""
    job_dir = tmp_path / "unplanted_job"
    job_dir.mkdir()
    preview_dir = job_dir / "preview"
    preview_dir.mkdir()

    timeline = {
        "scenes": [
            {
                "id": "s000",
                "template": "title_card",
                "start_frame": 0,
                "end_frame": 60,
                "props": {"title": "Title"},
                "overlays": [],
            },
            {
                "id": "s001",
                "template": "metaphor",
                "start_frame": 60,
                "end_frame": 120,
                "props": {"label": "Metaphor 1", "image_entity": "meta_1", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s002",
                "template": "metaphor",
                "start_frame": 120,
                "end_frame": 180,
                "props": {"label": "Metaphor 2", "image_entity": "meta_2", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s003",
                "template": "reveal",
                "start_frame": 180,
                "end_frame": 240,
                "props": {"text": "A secret"},
                "overlays": [
                    {"kind": "thought", "text": "Hmm", "anchor": "top_left"},
                    {"kind": "prop", "icon": "Coins", "anchor": "bottom_left"},
                ],
            },
            {
                "id": "s004",
                "template": "callback",
                "start_frame": 240,
                "end_frame": 300,
                "props": {"motif_id": "m1", "label": "Key", "icon": "Key"},
                "overlays": [],
            },
        ]
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")

    res = verify_job_creative(job_dir)
    assert res["passed"] is False
    assert res["motifs_bar"] is False
    assert len(res["unplanted_payoffs"]) == 1


def test_falsification_callback_dots_mismatch_fails(tmp_path: Path) -> None:
    """A callback whose item_frames length does not equal earlier motif token count fails."""
    job_dir = tmp_path / "dots_mismatch_job"
    job_dir.mkdir()
    preview_dir = job_dir / "preview"
    preview_dir.mkdir()

    # Timeline with 2 earlier tokens, but callback has empty item_frames (or mismatch)
    timeline = {
        "scenes": [
            {
                "id": "s000",
                "template": "title_card",
                "start_frame": 0,
                "end_frame": 60,
                "props": {"title": "Title"},
                "overlays": [],
            },
            {
                "id": "s001",
                "template": "kinetic_quote",
                "start_frame": 60,
                "end_frame": 120,
                "props": {"text": "Quote 1"},
                "overlays": [
                    {
                        "kind": "motif_token",
                        "motif_id": "m1",
                        "anchor": "top_right",
                        "icon": "Key",
                    }
                ],
            },
            {
                "id": "s002",
                "template": "metaphor",
                "start_frame": 120,
                "end_frame": 180,
                "props": {"label": "Metaphor 1", "image_entity": "meta_1", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s003",
                "template": "kinetic_quote",
                "start_frame": 180,
                "end_frame": 240,
                "props": {"text": "Quote 2"},
                "overlays": [
                    {
                        "kind": "motif_token",
                        "motif_id": "m1",
                        "anchor": "top_right",
                        "icon": "Key",
                    }
                ],
            },
            {
                "id": "s004",
                "template": "metaphor",
                "start_frame": 240,
                "end_frame": 300,
                "props": {"label": "Metaphor 2", "image_entity": "meta_2", "cast_ids": []},
                "overlays": [],
            },
            {
                "id": "s005",
                "template": "reveal",
                "start_frame": 300,
                "end_frame": 360,
                "props": {"text": "A secret"},
                "overlays": [
                    {"kind": "thought", "text": "Hmm", "anchor": "top_left"},
                    {"kind": "prop", "icon": "Coins", "anchor": "bottom_left"},
                ],
            },
            {
                "id": "s006",
                "template": "callback",
                "start_frame": 360,
                "end_frame": 420,
                "timing": {"item_frames": []},  # 0 items != 2 tokens
                "props": {"motif_id": "m1", "label": "Key found", "icon": "Key"},
                "overlays": [],
            },
        ]
    }
    (job_dir / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")

    res = verify_job_creative(job_dir)
    assert res["passed"] is False
    assert res["motifs_bar"] is False
    assert res["callback_dots_bar"] is False
    assert len(res["callback_dots_violations"]) == 1

