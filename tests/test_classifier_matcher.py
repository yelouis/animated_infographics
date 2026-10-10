"""Unit tests for ClassifierMatcher (Contestant A2).

Per design_presentation_simulation.md §6.6.2, design_testing_and_validation.md §2,
and agent_execution_guide.md §1.3 (J3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from animated_infographics.contracts.models import (
    TitleCardProps,
    TitleCardScene,
    Transcript,
    TranscriptWord,
)
from animated_infographics.contracts.playback import PlaybackPlan
from animated_infographics.contracts.tree import TreeEdge, TreeNode, TreePlan
from animated_infographics.jobs import Job, RunContext
from animated_infographics.presentation.follow import run_follow_stage
from animated_infographics.presentation.match import ClassifierMatcher


class StubClassifierBackend:
    """Stub LLM backend recording prompts and returning scripted answers."""

    def __init__(
        self,
        responses: list[dict[str, Any]] | None = None,
        last_elapsed_ms: int = 42,
    ) -> None:
        self.responses = list(responses or [])
        self.recorded_prompts: list[str] = []
        self.recorded_schemas: list[dict[str, Any]] = []
        self.calls: int = 0
        self.cache_hits: int = 0
        self.last_elapsed_ms: int = last_elapsed_ms

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
        prompt = ""
        if messages:
            prompt = messages[0].get("content", "")
        self.recorded_prompts.append(prompt)
        self.recorded_schemas.append(schema)

        if self.responses:
            return self.responses.pop(0)
        return {"node": "d1_section"}


def _make_dummy_scene(idx: int, title: str) -> TitleCardScene:
    return TitleCardScene(
        id=f"s{idx:03d}",
        beat_i=idx,
        template="title_card",
        props=TitleCardProps(title=title),
    )


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


def test_classifier_matcher_prompt_byte_equal() -> None:
    """Prompt format is byte-equal to design_presentation_simulation.md §6.6.6."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    backend = StubClassifierBackend()
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    # In Round 2 (§6.6.6): candidates are every node of the tree in deck order
    cand_nodes = list(tree.nodes)
    prompt = matcher.build_prompt(
        current_node=tree.nodes[2],
        candidates=cand_nodes,
        last_words="summer London parliament curtains lime chloride",
    )

    expected = (
        "You are following a live talk against its slide deck. "
        "You hear only the last few seconds of speech.\n"
        "The speaker is currently on: "
        "d1_p1 — Summer of 1858: Parliament soaked their heavy curtains in lime\n"
        "Candidates:\n"
        "d1_section — Summer of 1858: (start of this slide)\n"
        "d1_p0 — Summer of 1858: The river Thames was completely full of sewage\n"
        "d1_p1 — Summer of 1858: Parliament soaked their heavy curtains in lime\n"
        "d2_section — A Modern Sewer Network: (start of this slide)\n"
        "d2_p0 — A Modern Sewer Network: Joseph Bazalgette engineered eighty-two miles of pipes\n"
        'Last words heard: "summer London parliament curtains lime chloride"\n'
        "Which point is the speaker on now? "
        "If they are telling a side story that matches no point, "
        "answer the current point. Answer one id."
    )
    assert prompt == expected


def test_classifier_matcher_candidate_enum() -> None:
    """Schema enum contains every node of the tree in deck order (§6.6.6)."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    backend = StubClassifierBackend()
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2100, sentence_i=0),
    ]
    matcher.run(words)

    assert len(backend.recorded_schemas) == 1
    schema = backend.recorded_schemas[0]
    expected_enum = ["d1_section", "d1_p0", "d1_p1", "d2_section", "d2_p0"]
    assert schema["properties"]["node"]["enum"] == expected_enum


def test_classifier_matcher_section_step_set_single_step_commit() -> None:
    """When the next node is section, its slide's first point commits in 1 decision (§6.6.6)."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    # Speaker is on d1_p1. Next node is d2_section (kind=section), so d2_p0 is also in step_set.
    # Answering d2_p0 directly at a single decision point should commit in 1 decision.
    backend = StubClassifierBackend(
        responses=[{"node": "d1_p0"}, {"node": "d1_p1"}, {"node": "d2_p0"}]
    )
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="w0", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="w1", start_ms=1000, end_ms=2100, sentence_i=0),  # dp 1 -> d1_p0
        TranscriptWord(i=2, text="w2", start_ms=2100, end_ms=4200, sentence_i=1),  # dp 2 -> d1_p1
        TranscriptWord(
            i=3, text="w3", start_ms=4200, end_ms=6500, sentence_i=2
        ),  # dp 3 -> d2_p0 (single step!)
    ]
    pb = matcher.run(words)

    assert len(pb.commits) == 4
    assert [c.node_id for c in pb.commits] == ["d1_section", "d1_p0", "d1_p1", "d2_p0"]
    assert pb.commits[-1].node_id == "d2_p0"
    assert pb.commits[-1].decision_ms == 6500


def test_classifier_matcher_next_node_single_step_commit() -> None:
    """Next-node answer (f1) commits at a single decision point once dwell >= 2.0s."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    backend = StubClassifierBackend(responses=[{"node": "d1_p0"}])
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        # dp 1 at 2100ms: dwell from 0ms is 2100ms >= 2000ms. Answer is f1 (d1_p0) -> commits!
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2100, sentence_i=0),
    ]
    pb = matcher.run(words)

    assert len(pb.commits) == 2
    assert pb.commits[0].node_id == "d1_section"
    assert pb.commits[1].node_id == "d1_p0"
    assert pb.commits[1].decision_ms == 2100


def test_classifier_matcher_jump_two_step_commit() -> None:
    """Any other move (f2, f3, back node) requires 2 consecutive identical answers."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    # At dp 1 (2100ms): answers f2 (d1_p1) -> 1st time -> holds with consecutive_top_not_met
    # At dp 2 (3600ms): answers f2 (d1_p1) -> 2nd time -> commits!
    backend = StubClassifierBackend(responses=[{"node": "d1_p1"}, {"node": "d1_p1"}])
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2100, sentence_i=0),
        TranscriptWord(i=2, text="heat", start_ms=2100, end_ms=3600, sentence_i=0),
    ]
    pb = matcher.run(words)

    assert len(pb.commits) == 2
    assert pb.commits[1].node_id == "d1_p1"
    assert pb.commits[1].decision_ms == 3600

    hold_2100 = next(h for h in pb.holds if h.decision_ms == 2100)
    assert hold_2100.reason == "consecutive_top_not_met"


def test_classifier_matcher_current_node_holds() -> None:
    """Answering current node c holds with reason top_is_current."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    backend = StubClassifierBackend(responses=[{"node": "d1_section"}])
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2100, sentence_i=0),
    ]
    pb = matcher.run(words)

    assert len(pb.commits) == 1
    assert pb.commits[0].node_id == "d1_section"
    assert len(pb.holds) == 1
    assert pb.holds[0].reason == "top_is_current"


def test_classifier_matcher_llm_error_on_exception_and_invalid() -> None:
    """A raised exception or invalid answer holds with reason llm_error."""
    tree = _make_test_tree()
    deck = _make_test_deck()

    class FlakyBackend:
        calls = 0
        cache_hits = 0
        last_elapsed_ms = 10

        def generate_json(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Network timeout")
            # 2nd call: returns invalid node id
            return {"node": "unknown_node_xyz"}

    matcher = ClassifierMatcher(tree=tree, backend=FlakyBackend(), deck=deck)  # type: ignore[arg-type]

    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2100, sentence_i=0),
        TranscriptWord(i=2, text="heat", start_ms=2100, end_ms=3600, sentence_i=0),
    ]
    pb = matcher.run(words)

    assert len(pb.commits) == 1  # only initial commit
    assert len(pb.holds) == 2
    assert pb.holds[0].reason == "llm_error"
    assert pb.holds[1].reason == "llm_error"


def test_classifier_matcher_causality_and_last_words() -> None:
    """Causality: prefix of words produces identical decisions; no future words in prompt."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    backend = StubClassifierBackend()
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="word0", start_ms=0, end_ms=500, sentence_i=0),
        TranscriptWord(i=1, text="word1", start_ms=500, end_ms=1000, sentence_i=0),
        TranscriptWord(i=2, text="word2", start_ms=1000, end_ms=2100, sentence_i=0),  # dp 1
        TranscriptWord(i=3, text="word3", start_ms=2100, end_ms=3000, sentence_i=0),
        TranscriptWord(
            i=4, text="future_word_secret", start_ms=3000, end_ms=3700, sentence_i=0
        ),  # dp 2
    ]
    matcher.run(words)

    # In prompt at dp 1, future_word_secret must NOT be present
    prompt_dp1 = backend.recorded_prompts[0]
    assert "future_word_secret" not in prompt_dp1
    assert 'Last words heard: "word0 word1 word2"' in prompt_dp1

    # In prompt at dp 2, future_word_secret IS present
    prompt_dp2 = backend.recorded_prompts[1]
    assert "future_word_secret" in prompt_dp2


def test_classifier_matcher_honest_latency() -> None:
    """Latency takes backend.last_elapsed_ms into compute_ms and commit at_ms."""
    tree = _make_test_tree()
    deck = _make_test_deck()
    backend = StubClassifierBackend(
        responses=[{"node": "d1_p0"}],
        last_elapsed_ms=580,  # 580ms simulated LLM time
    )
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    words = [
        TranscriptWord(i=0, text="summer", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="london", start_ms=1000, end_ms=2100, sentence_i=0),
    ]
    pb = matcher.run(words)

    commit = pb.commits[1]
    assert commit.compute_ms >= 580
    assert commit.at_ms == commit.decision_ms + commit.compute_ms


def test_follow_dispatch_llm(tmp_path: Path) -> None:
    """follow stage runs ClassifierMatcher when matcher=llm and logs llm_calls."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")
    (job_dir / "deck.json").write_text(json.dumps(_make_test_deck()), encoding="utf-8")
    (job_dir / "tree.json").write_text(_make_test_tree().model_dump_json(), encoding="utf-8")
    transcript = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=2500,
        words=[
            TranscriptWord(i=0, text="hello", start_ms=0, end_ms=1000, sentence_i=0),
            TranscriptWord(i=1, text="world", start_ms=1000, end_ms=2100, sentence_i=0),
        ],
        sentences=[],
    )
    (job_dir / "heard.json").write_text(transcript.model_dump_json(), encoding="utf-8")

    job = Job(job_dir)
    ctx_llm = RunContext(matcher="llm")

    mock_backend = StubClassifierBackend(responses=[{"node": "d1_p0"}])
    with patch(
        "animated_infographics.presentation.follow.OllamaBackend", return_value=mock_backend
    ):
        run_follow_stage(job, ctx_llm)

    assert (job_dir / "playback.json").is_file()
    pb = PlaybackPlan.model_validate_json((job_dir / "playback.json").read_text(encoding="utf-8"))
    assert pb.matcher == "llm"
    assert len(pb.commits) == 2

    log_content = (job_dir / "logs" / "follow.log").read_text(encoding="utf-8")
    assert "matcher=llm" in log_content
    assert "llm_calls=1" in log_content


def test_six_nodes_behind_recovery() -> None:
    """Wave L2 red first test: 6 nodes behind; the stub answers the true point twice -> commit.

    Under Round 1 ClassifierMatcher, this fails because candidates only included
    the next 3 nodes, so a node 6 ahead was not a candidate.
    """
    slides = [
        {
            "id": f"d{i}",
            "title": f"Slide {i}",
            "points": [{"text": f"pt {i}.0"}, {"text": f"pt {i}.1"}],
        }
        for i in range(1, 4)
    ]
    deck = {"slides": slides}
    nodes = []
    idx = 0
    for i in range(1, 4):
        s_node = TreeNode(
            id=f"d{i}_section",
            slide=f"d{i}",
            kind="section",
            point_i=None,
            text=f"Slide {i}",
            scene=_make_dummy_scene(idx, f"Slide {i}"),
        )
        nodes.append(s_node)
        idx += 1
        for p in range(2):
            p_node = TreeNode(
                id=f"d{i}_p{p}",
                slide=f"d{i}",
                kind="point",
                point_i=p,
                text=f"pt {i}.{p}",
                scene=_make_dummy_scene(idx, f"pt {i}.{p}"),
            )
            nodes.append(p_node)
            idx += 1
    # nodes has 9 nodes:
    # 0: d1_section, 1: d1_p0, 2: d1_p1, 3: d2_section, 4: d2_p0, 5: d2_p1,
    # 6: d3_section, 7: d3_p0, 8: d3_p1
    tree = TreePlan(nodes=nodes, edges=[])

    target_node_id = "d3_section"  # index 6 (6 nodes ahead of current=0)
    backend = StubClassifierBackend(responses=[{"node": target_node_id}, {"node": target_node_id}])
    matcher = ClassifierMatcher(tree=tree, backend=backend, deck=deck)

    # 2 decision points: at 2500ms and 5000ms
    words = [
        TranscriptWord(i=0, text="first", start_ms=0, end_ms=1000, sentence_i=0),
        TranscriptWord(i=1, text="gap1", start_ms=1000, end_ms=2500, sentence_i=0),
        TranscriptWord(i=2, text="second", start_ms=2500, end_ms=3500, sentence_i=1),
        TranscriptWord(i=3, text="gap2", start_ms=3500, end_ms=5000, sentence_i=1),
    ]
    pb = matcher.run(words)

    # After answering target_node_id twice consecutively, it should have committed to target_node_id
    assert pb.commits[-1].node_id == target_node_id
