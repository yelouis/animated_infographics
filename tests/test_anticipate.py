"""Unit tests for anticipate stage and AnticipateMatcher (Contestant A1).

Per design_presentation_simulation.md §6.6.1, design_testing_and_validation.md §2,
and agent_execution_guide.md §1.3 (J2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from animated_infographics.contracts.anticipation import AnticipationPlan
from animated_infographics.contracts.models import (
    TitleCardProps,
    TitleCardScene,
    Transcript,
    TranscriptWord,
)
from animated_infographics.contracts.playback import PlaybackPlan
from animated_infographics.contracts.tree import TreeEdge, TreeNode, TreePlan
from animated_infographics.jobs import Job, RunContext
from animated_infographics.presentation.anticipate import (
    build_point_prompt,
    build_section_prompt,
    run_anticipate_stage,
    validate_anticipation_dict,
)
from animated_infographics.presentation.match import AnticipateMatcher


class StubBackend:
    """Stub LLM backend returning canned responses."""

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: int = 0
        self.cache_hits: int = 0

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, Any]] | None = None,
        schema: dict[str, Any],
        attempt: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls += 1
        if self.responses:
            return self.responses.pop(0)
        return {
            "sentence_1": "Here is sentence one about this slide topic.",
            "sentence_2": "Here is sentence two describing the main detail.",
            "sentence_3": "Here is sentence three elaborating on the background.",
            "sentence_4": "Here is sentence four concluding the talking point.",
        }


def _make_test_deck() -> dict[str, Any]:
    return {
        "slides": [
            {
                "id": "d1",
                "title": "Summer of 1858",
                "sentence_ids": [1, 2, 3],
                "points": [
                    {
                        "text": "The river Thames was completely full of sewage",
                        "sentence_ids": [1, 2],
                    },
                    {
                        "text": "Parliament soaked their heavy curtains in lime",
                        "sentence_ids": [3],
                    },
                ],
            },
            {
                "id": "d2",
                "title": "A Modern Sewer Network",
                "sentence_ids": [4, 5],
                "points": [
                    {
                        "text": "Joseph Bazalgette engineered eighty-two miles of pipes",
                        "sentence_ids": [4, 5],
                    },
                ],
            },
        ]
    }


def _make_dummy_scene(idx: int, title: str) -> TitleCardScene:
    return TitleCardScene(
        id=f"s{idx:03d}",
        beat_i=idx,
        template="title_card",
        props=TitleCardProps(title=title),
    )


def _make_test_tree() -> TreePlan:
    nodes = [
        TreeNode(
            id="d1_section",
            slide="d1",
            kind="section",
            point_i=None,
            text="Summer of 1858",
            scene=_make_dummy_scene(0, "Summer of 1858"),
        ),
        TreeNode(
            id="d1_p0",
            slide="d1",
            kind="point",
            point_i=0,
            text="The river Thames was completely full of sewage",
            scene=_make_dummy_scene(1, "Point 1"),
        ),
        TreeNode(
            id="d1_p1",
            slide="d1",
            kind="point",
            point_i=1,
            text="Parliament soaked their heavy curtains in lime",
            scene=_make_dummy_scene(2, "Point 2"),
        ),
        TreeNode(
            id="d2_section",
            slide="d2",
            kind="section",
            point_i=None,
            text="A Modern Sewer Network",
            scene=_make_dummy_scene(3, "Modern Sewer Network"),
        ),
        TreeNode(
            id="d2_p0",
            slide="d2",
            kind="point",
            point_i=0,
            text="Joseph Bazalgette engineered eighty-two miles of pipes",
            scene=_make_dummy_scene(4, "Point 3"),
        ),
    ]
    edges = [
        TreeEdge(from_="d1_section", to="d1_p0", kind="next", cost=0.0),
        TreeEdge(from_="d1_p0", to="d1_p1", kind="next", cost=0.0),
        TreeEdge(from_="d1_p1", to="d2_section", kind="next", cost=0.0),
        TreeEdge(from_="d2_section", to="d2_p0", kind="next", cost=0.0),
    ]
    return TreePlan(nodes=nodes, edges=edges)


def test_anticipate_prompts() -> None:
    """Prompt format is byte-equal to design_presentation_simulation.md §6.6.1."""
    deck = _make_test_deck()
    slide = deck["slides"][0]

    pt_prompt = build_point_prompt(slide, "The river Thames was completely full of sewage")
    expected_pt = (
        "Here is one slide from a talk.\n"
        "Slide title: Summer of 1858\n"
        "Points on this slide:\n"
        "- The river Thames was completely full of sewage\n"
        "- Parliament soaked their heavy curtains in lime\n"
        "The presenter is now covering this point: "
        '"The river Thames was completely full of sewage"\n'
        "Write 4 different sentences the presenter might actually say out loud while "
        "covering this point. "
        "Use plain spoken English, the way a person talks, not slide text. "
        "Do not add facts that are not on the slide."
    )
    assert pt_prompt == expected_pt

    sec_prompt = build_section_prompt(slide)
    expected_sec = (
        "Here is one slide from a talk.\n"
        "Slide title: Summer of 1858\n"
        "Points on this slide:\n"
        "- The river Thames was completely full of sewage\n"
        "- Parliament soaked their heavy curtains in lime\n"
        "The presenter is now moving on to this slide.\n"
        "Write 4 different sentences the presenter might say out loud to introduce this slide. "
        "Use plain spoken English, the way a person talks, not slide text. "
        "Do not add facts that are not on the slide."
    )
    assert sec_prompt == expected_sec


def test_anticipate_validators() -> None:
    """Validators reject 5 words, duplicates, copies of slide, ungrounded digits."""
    deck = _make_test_deck()
    slide = deck["slides"][0]
    point_text = "The river Thames was completely full of sewage"

    # 1. 5 words -> error
    d1 = {
        "sentence_1": "Only five words right here",
        "sentence_2": "This is a valid length sentence with enough words.",
        "sentence_3": "Another valid sentence that meets the word criteria.",
        "sentence_4": "And a fourth valid spoken sentence for testing.",
    }
    errs1 = validate_anticipation_dict(d1, slide, point_text)
    assert any("sentence_1: 5 words — write 6 to 35 words" == e for e in errs1)

    # 2. repeats -> error
    d2 = {
        "sentence_1": "This is a valid length sentence with enough words.",
        "sentence_2": "This is a valid length sentence with enough words.",
        "sentence_3": "Another valid sentence that meets the word criteria.",
        "sentence_4": "And a fourth valid spoken sentence for testing.",
    }
    errs2 = validate_anticipation_dict(d2, slide, point_text)
    assert any("repeats sentence_1 — write a different sentence" in e for e in errs2)

    # 3. copies slide -> error
    d3 = {
        "sentence_1": "The river Thames was completely full of sewage",
        "sentence_2": "This is a valid length sentence with enough words.",
        "sentence_3": "Another valid sentence that meets the word criteria.",
        "sentence_4": "And a fourth valid spoken sentence for testing.",
    }
    errs3 = validate_anticipation_dict(d3, slide, point_text)
    assert any("sentence_1 copies the slide — say it the way a presenter would" == e for e in errs3)

    # 4. ungrounded digits (1859 not on slide) -> error
    d4 = {
        "sentence_1": "In the year 1859 the smell became completely intolerable.",
        "sentence_2": "This is a valid length sentence with enough words.",
        "sentence_3": "Another valid sentence that meets the word criteria.",
        "sentence_4": "And a fourth valid spoken sentence for testing.",
    }
    errs4 = validate_anticipation_dict(d4, slide, point_text)
    assert any('sentence_1: "1859" is not on the slide — do not add numbers' == e for e in errs4)


def test_anticipate_stage_isolation_and_skip(tmp_path: Path) -> None:
    """anticipate stage reads only deck.json and tree.json; skips when matcher != anticipate."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")
    (job_dir / "deck.json").write_text(json.dumps(_make_test_deck()), encoding="utf-8")
    (job_dir / "tree.json").write_text(_make_test_tree().model_dump_json(), encoding="utf-8")
    (job_dir / "performance.json").write_text("{}", encoding="utf-8")

    job = Job(job_dir)

    # When matcher is bm25, it skips and writes nothing
    ctx_bm25 = RunContext(matcher="bm25")
    run_anticipate_stage(job, ctx_bm25)
    assert not (job_dir / "anticipation.json").is_file()
    assert (job_dir / "logs" / "anticipate.log").is_file()
    assert "anticipate: skipped (matcher=bm25)" in (job_dir / "logs" / "anticipate.log").read_text()

    # When matcher is anticipate, it reads only deck.json and tree.json
    backend = StubBackend()
    ctx_ant = RunContext(matcher="anticipate")

    read_files: list[str] = []
    orig_read_text = Path.read_text

    def tracking_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        read_files.append(self.name)
        return orig_read_text(self, *args, **kwargs)

    with (
        patch.object(Path, "read_text", side_effect=tracking_read_text, autospec=True),
        patch(
            "animated_infographics.presentation.anticipate.OllamaBackend",
            return_value=backend,
        ),
    ):
        run_anticipate_stage(job, ctx_ant)

    assert (job_dir / "anticipation.json").is_file()
    forbidden = {"performance.json", "heard.json", "speak_timing.json"}
    for f in forbidden:
        assert f not in read_files, f"anticipate stage read forbidden file {f}"


def test_anticipate_matcher_tracker_rules() -> None:
    """AnticipateMatcher rules: forward commit on 1 top + margin >= 0.5; jump needs 2 tops."""
    tree = _make_test_tree()
    anticipations = {
        "d1_section": [
            "welcome to London summer 1858",
            "intro summer heat stench",
            "london sewer talk intro",
            "talking about river thames",
        ],
        "d1_p0": [
            "the river thames was an open sewer",
            "smell of human waste everywhere",
            "waste flowed directly into the river",
            "thames river water was poisoned",
        ],
        "d1_p1": [
            "parliament soaked their curtains in lime chloride",
            "politicians could not stand the horrible smell",
            "curtains drenched in lime in parliament",
            "parliament tried using lime against the odor",
        ],
        "d2_section": [
            "now we look at the modern sewer solution",
            "bazalgette and the new underground network",
            "moving on to the construction of sewers",
            "how london finally solved the problem",
        ],
        "d2_p0": [
            "bazalgette built eighty two miles of intercepting pipes",
            "joseph bazalgette was the chief engineer",
            "miles and miles of brick sewers under london",
            "eighty two miles of sewer tunnels were constructed",
        ],
    }

    matcher = AnticipateMatcher(tree=tree, anticipations=anticipations)

    # Words simulating speech covering d1_p0:
    # "the river thames was an open sewer with horrible stench"
    words = [
        TranscriptWord(i=0, text="the", start_ms=0, end_ms=300, sentence_i=0),
        TranscriptWord(i=1, text="river", start_ms=300, end_ms=700, sentence_i=0),
        TranscriptWord(i=2, text="thames", start_ms=700, end_ms=1200, sentence_i=0),
        TranscriptWord(i=3, text="was", start_ms=1200, end_ms=1500, sentence_i=0),
        TranscriptWord(i=4, text="an", start_ms=1500, end_ms=1700, sentence_i=0),
        TranscriptWord(i=5, text="open", start_ms=1700, end_ms=2100, sentence_i=0),
        TranscriptWord(i=6, text="sewer", start_ms=2100, end_ms=2600, sentence_i=0),
        TranscriptWord(i=7, text="full", start_ms=2600, end_ms=3000, sentence_i=0),
        TranscriptWord(i=8, text="of", start_ms=3000, end_ms=3200, sentence_i=0),
        TranscriptWord(i=9, text="sewage", start_ms=3200, end_ms=3700, sentence_i=0),
    ]

    playback = matcher.run(words)
    assert playback.matcher == "anticipate"
    # Should commit from d1_section to d1_p0 once dwell >= 2000ms is reached
    commits = playback.commits
    assert len(commits) >= 2
    assert commits[0].node_id == "d1_section"
    assert commits[1].node_id == "d1_p0"
    assert commits[1].at_ms >= 2000


def test_anticipate_matcher_jump_rules() -> None:
    """Jump moves (f2, f3, back) require 2 consecutive tops with score_gap >= 1.5."""
    tree = _make_test_tree()
    anticipations = {
        "d1_section": ["summer 1858 section intro london"],
        "d1_p0": ["river thames open sewer"],
        "d1_p1": ["parliament heavy curtains lime chloride soaked chemicals"],
        "d2_section": ["modern sewer solution underground network"],
        "d2_p0": ["bazalgette eighty two miles pipes brick tunnels"],
    }
    matcher = AnticipateMatcher(tree=tree, anticipations=anticipations)

    # Word sequence:
    # 0-2000ms: words matching d1_section (summer london). At 2000ms, d1_section is top.
    # 2000-3500ms: parliament heavy curtains (matches d1_p1).
    # At 3500ms, d1_p1 is top (1st time) -> HOLD (consecutive_top_not_met)
    # 3500-5000ms: lime chloride (matches d1_p1). At 5000ms, d1_p1 is top (2nd time) -> COMMIT!
    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        # dp 1 (end_ms 2000): top is d1_section
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2000, sentence_i=0),
        TranscriptWord(i=2, text="parliament", start_ms=2000, end_ms=2500, sentence_i=0),
        TranscriptWord(i=3, text="heavy", start_ms=2500, end_ms=3000, sentence_i=0),
        # dp 2 (end_ms 3500): top is d1_p1 (1st time)
        TranscriptWord(i=4, text="curtains", start_ms=3000, end_ms=3500, sentence_i=0),
        TranscriptWord(i=5, text="lime", start_ms=3500, end_ms=4200, sentence_i=0),
        # dp 3 (end_ms 5000): top is d1_p1 (2nd time)
        TranscriptWord(i=6, text="chloride", start_ms=4200, end_ms=5000, sentence_i=0),
    ]
    playback = matcher.run(words)
    # Commits: [0: d1_section, 1: d1_p1]
    assert len(playback.commits) == 2
    assert playback.commits[1].node_id == "d1_p1"
    assert playback.commits[1].decision_ms == 5000

    # Decision at 3500ms was a hold with consecutive_top_not_met
    hold_3500 = next(h for h in playback.holds if h.decision_ms == 3500)
    assert "consecutive_top_not_met" in hold_3500.reason


def test_anticipate_failure_containment(tmp_path: Path) -> None:
    """When LLM calls fail 3 times, node gets 0 sentences, logs failure, and stage exits cleanly."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")
    (job_dir / "deck.json").write_text(json.dumps(_make_test_deck()), encoding="utf-8")
    (job_dir / "tree.json").write_text(_make_test_tree().model_dump_json(), encoding="utf-8")

    job = Job(job_dir)
    ctx = RunContext(matcher="anticipate")

    # Backend that always returns invalid dict (1 word -> validation failure)
    bad_resp = {
        "sentence_1": "short",
        "sentence_2": "short",
        "sentence_3": "short",
        "sentence_4": "short",
    }
    bad_backend = StubBackend(responses=[bad_resp] * 20)

    with patch(
        "animated_infographics.presentation.anticipate.OllamaBackend",
        return_value=bad_backend,
    ):
        run_anticipate_stage(job, ctx)

    ant_path = job_dir / "anticipation.json"
    assert ant_path.is_file()
    plan = AnticipationPlan.model_validate_json(ant_path.read_text(encoding="utf-8"))
    # All nodes get []
    for _nid, s_list in plan.nodes.items():
        assert s_list == []

    log_content = (job_dir / "logs" / "anticipate.log").read_text(encoding="utf-8")
    assert "failed:" in log_content
    assert "filled=0" in log_content


def test_follow_dispatch_anticipation(tmp_path: Path) -> None:
    """follow stage raises error if anticipation.json is missing when matcher=anticipate."""
    from animated_infographics.errors import ValidationFailed
    from animated_infographics.presentation.follow import run_follow_stage

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")
    (job_dir / "tree.json").write_text(_make_test_tree().model_dump_json(), encoding="utf-8")
    transcript = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=1000,
        words=[TranscriptWord(i=0, text="hello", start_ms=0, end_ms=500, sentence_i=0)],
        sentences=[],
    )
    (job_dir / "heard.json").write_text(transcript.model_dump_json(), encoding="utf-8")

    job = Job(job_dir)
    ctx_ant = RunContext(matcher="anticipate")

    with pytest.raises(
        ValidationFailed, match="anticipation.json missing — run the anticipate stage"
    ):
        run_follow_stage(job, ctx_ant)

    # Now write anticipation.json and verify it runs successfully
    plan = AnticipationPlan(
        schema_version=1,
        nodes={n.id: ["test sentence one two three four five"] for n in _make_test_tree().nodes},
    )
    (job_dir / "anticipation.json").write_text(plan.model_dump_json(), encoding="utf-8")
    run_follow_stage(job, ctx_ant)
    assert (job_dir / "playback.json").is_file()
    pb = PlaybackPlan.model_validate_json((job_dir / "playback.json").read_text(encoding="utf-8"))
    assert pb.matcher == "anticipate"
