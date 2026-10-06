"""Tests for presentation follow, live matching, causality, isolation, and compose stages.

Per design_presentation_simulation.md §6, §7 and design_data_contracts.md §10.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from animated_infographics.contracts.models import (
    SceneUnion,
    TitleCardProps,
    TitleCardScene,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.contracts.playback import PlaybackCommit, PlaybackPlan
from animated_infographics.contracts.tree import TreeEdge, TreeNode, TreePlan
from animated_infographics.jobs import Job, RunContext
from animated_infographics.presentation.compose import (
    compose_presentation_timeline,
    run_compose_stage,
)
from animated_infographics.presentation.follow import run_follow_stage
from animated_infographics.presentation.match import (
    BM25Index,
    LiveMatcher,
    find_decision_points,
    normalize_tokens,
)


def _make_dummy_scene(idx: int, title: str) -> SceneUnion:
    return TitleCardScene(
        id=f"s{idx:03d}",
        beat_i=idx,
        template="title_card",
        props=TitleCardProps(title=title),
    )


def _make_test_tree() -> TreePlan:
    """Create a sample 3-slide, 6-point presentation tree with next, skip, and back edges."""
    nodes: list[TreeNode] = [
        TreeNode(
            id="d1_section",
            slide="d1",
            kind="section",
            point_i=None,
            text="The Great Stink London Summer 1858",
            scene=_make_dummy_scene(0, "The Great Stink"),
        ),
        TreeNode(
            id="d1_p0",
            slide="d1",
            kind="point",
            point_i=0,
            text="London could not breathe in 1858 with two million citizens",
            scene=_make_dummy_scene(1, "Point 1: Choking London"),
        ),
        TreeNode(
            id="d1_p1",
            slide="d1",
            kind="point",
            point_i=1,
            text="Waste flowed directly into River Thames drinking water",
            scene=_make_dummy_scene(2, "Point 2: River Pollution"),
        ),
        TreeNode(
            id="d2_section",
            slide="d2",
            kind="section",
            point_i=None,
            text="Parliament Crisis and Riverbank Stench",
            scene=_make_dummy_scene(3, "Parliament in Crisis"),
        ),
        TreeNode(
            id="d2_p0",
            slide="d2",
            kind="point",
            point_i=0,
            text="Members of Parliament soaked curtains in chloride of lime",
            scene=_make_dummy_scene(4, "Point 3: Parliament Bleach"),
        ),
        TreeNode(
            id="d2_p1",
            slide="d2",
            kind="point",
            point_i=1,
            text="Government considered evacuating London altogether",
            scene=_make_dummy_scene(5, "Point 4: Evacuation Talks"),
        ),
    ]

    edges: list[TreeEdge] = [
        # Next edges (cost 0.0)
        TreeEdge(to="d1_p0", kind="next", cost=0.0, **{"from": "d1_section"}),
        TreeEdge(to="d1_p1", kind="next", cost=0.0, **{"from": "d1_p0"}),
        TreeEdge(to="d2_section", kind="next", cost=0.0, **{"from": "d1_p1"}),
        TreeEdge(to="d2_p0", kind="next", cost=0.0, **{"from": "d2_section"}),
        TreeEdge(to="d2_p1", kind="next", cost=0.0, **{"from": "d2_p0"}),
        # Skip edges (cost 0.3)
        TreeEdge(to="d1_p1", kind="skip", cost=0.3, **{"from": "d1_section"}),
        TreeEdge(to="d2_p0", kind="skip", cost=0.3, **{"from": "d1_p0"}),
        TreeEdge(to="d2_p1", kind="skip", cost=0.3, **{"from": "d1_p1"}),
        # Back edges (cost 0.5)
        TreeEdge(to="d1_p0", kind="back", cost=0.5, **{"from": "d2_p0"}),
        TreeEdge(to="d1_p1", kind="back", cost=0.5, **{"from": "d2_p1"}),
    ]

    return TreePlan(schema_version=1, nodes=nodes, edges=edges)


def _make_transcript_words() -> list[TranscriptWord]:
    """Generate realistic transcript words matching the tree points."""
    raw_text = (
        "In the summer of 1858 London could not breathe. "  # Matches d1_p0
        "The population climbed past two million and all "
        "waste flowed into the Thames. "  # Matches d1_p1
        "The stench reached Parliament where members "
        "soaked curtains in chloride of lime. "  # Matches d2_p0
        "Ministers talked about evacuating the government completely."  # Matches d2_p1
    )
    tokens = raw_text.split()
    words: list[TranscriptWord] = []
    current_ms = 0

    for idx, tok in enumerate(tokens):
        dur = 300
        start_ms = current_ms
        end_ms = start_ms + dur
        words.append(
            TranscriptWord(
                i=idx,
                text=tok,
                start_ms=start_ms,
                end_ms=end_ms,
                sentence_i=0,
            )
        )
        # Add a pause at punctuation
        if tok.endswith("."):
            current_ms = end_ms + 400  # >= 300 ms gap triggers decision point
        else:
            current_ms = end_ms + 50

    return words


def test_find_decision_points() -> None:
    """Decision points occur after gaps >= 300ms, or every 1.5s."""
    words = [
        TranscriptWord(i=0, text="Word1", start_ms=0, end_ms=200, sentence_i=0),
        # Gap of 400ms (600 - 200 >= 300ms) -> dp at index 0
        TranscriptWord(i=1, text="Word2", start_ms=600, end_ms=800, sentence_i=0),
        TranscriptWord(i=2, text="Word3", start_ms=850, end_ms=1000, sentence_i=0),
        TranscriptWord(i=3, text="Word4", start_ms=1050, end_ms=2400, sentence_i=0),
        # Time since last dp = 2400 - 200 = 2200ms >= 1500ms -> dp at index 3
        TranscriptWord(i=4, text="Word5", start_ms=2450, end_ms=2600, sentence_i=0),
    ]
    dp_indices = find_decision_points(words)
    assert 0 in dp_indices
    assert 3 in dp_indices
    assert 4 not in dp_indices


def test_bm25_index_scoring() -> None:
    """BM25 index scores matching document terms higher than non-matching terms."""
    tree = _make_test_tree()
    index = BM25Index(tree)

    q0 = normalize_tokens("London breathe citizens")
    assert index.score(q0, "d1_p0") > index.score(q0, "d2_p1")

    q1 = normalize_tokens("waste river Thames water")
    assert index.score(q1, "d1_p1") > index.score(q1, "d2_p1")


def test_follow_causal_no_look_ahead() -> None:
    """Matcher is strictly causal: prefix of words produces identical prefix of commits."""
    tree = _make_test_tree()
    words = _make_transcript_words()

    matcher = LiveMatcher(tree=tree)
    full_playback = matcher.run(words)

    # Cut words at a sentence boundary / pause point around halfway
    half = len(words) // 2
    cutoff_idx = next(i for i in range(half, len(words)) if words[i].text.endswith("."))
    cutoff_time = words[cutoff_idx].end_ms
    # Stream progresses to first word of next sentence, confirming the pause gap
    prefix_words = words[: cutoff_idx + 2]

    matcher_prefix = LiveMatcher(tree=tree)
    prefix_playback = matcher_prefix.run(prefix_words)

    # Filter full commits up to cutoff_time
    expected_commits = [c for c in full_playback.commits if c.decision_ms <= cutoff_time]
    assert len(prefix_playback.commits) == len(expected_commits)
    for c_prefix, c_exp in zip(prefix_playback.commits, expected_commits, strict=True):
        assert c_prefix.node_id == c_exp.node_id
        assert c_prefix.decision_ms == c_exp.decision_ms


def test_follow_causal_falsification() -> None:
    """Falsification: changing future words does not alter past commits, but alters future."""
    tree = _make_test_tree()
    words = _make_transcript_words()

    matcher = LiveMatcher(tree=tree)
    playback_a = matcher.run(words)

    # Alter future words after halfway pause boundary
    half = len(words) // 2
    cutoff_idx = next(i for i in range(half, len(words)) if words[i].text.endswith("."))
    cutoff_time = words[cutoff_idx].end_ms

    altered_words = list(words[: cutoff_idx + 1])
    for w in words[cutoff_idx + 1 :]:
        altered_words.append(w.model_copy(update={"text": "Unrelated bananas oranges pineapples"}))

    matcher_altered = LiveMatcher(tree=tree)
    playback_b = matcher_altered.run(altered_words)

    # Past commits must be strictly identical
    commits_a_past = [c for c in playback_a.commits if c.decision_ms <= cutoff_time]
    commits_b_past = [c for c in playback_b.commits if c.decision_ms <= cutoff_time]
    assert commits_a_past == commits_b_past

    # Future commits diverge because altered words do not match Parliament points
    assert [c.node_id for c in playback_a.commits] != [c.node_id for c in playback_b.commits]


def test_playback_plan_invariants() -> None:
    """Verify playback commits are non-decreasing in start_ms and exist in tree."""
    tree = _make_test_tree()
    words = _make_transcript_words()

    matcher = LiveMatcher(tree=tree)
    playback = matcher.run(words)

    assert len(playback.commits) >= 2
    # 1. Initial commit is at_ms == 0
    assert playback.commits[0].at_ms == 0
    assert playback.commits[0].node_id == "d1_section"

    # 2. Commits are non-decreasing
    for i in range(1, len(playback.commits)):
        assert playback.commits[i].at_ms >= playback.commits[i - 1].at_ms

    # 3. Every committed node exists in tree
    tree_node_ids = {n.id for n in tree.nodes}
    for c in playback.commits:
        assert c.node_id in tree_node_ids

    # 4. Holds have non-empty valid reasons
    for h in playback.holds:
        assert h.reason != ""
        assert h.current_node_id in tree_node_ids


def test_follow_stage_isolation(tmp_path: Path) -> None:
    """Verify run_follow_stage reads ONLY tree.json and heard.json."""
    job_dir = tmp_path / "job_pres"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")

    tree = _make_test_tree()
    (job_dir / "tree.json").write_text(tree.model_dump_json(), encoding="utf-8")

    words = _make_transcript_words()
    transcript = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=words[-1].end_ms + 500,
        words=words,
        sentences=[
            TranscriptSentence(
                i=0,
                text="Transcript text",
                start_ms=0,
                end_ms=words[-1].end_ms,
                word_start=0,
                word_end=len(words),
                paragraph_i=0,
                is_title=False,
            )
        ],
    )
    (job_dir / "heard.json").write_text(transcript.model_dump_json(), encoding="utf-8")

    # Add forbidden files
    (job_dir / "performance.json").write_text("{}", encoding="utf-8")
    (job_dir / "speak_timing.json").write_text("[]", encoding="utf-8")
    (job_dir / "deck.json").write_text("{}", encoding="utf-8")

    job = Job(job_dir)
    ctx = RunContext()

    read_files: list[str] = []
    orig_read_text = Path.read_text

    def tracking_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        read_files.append(self.name)
        return orig_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", side_effect=tracking_read_text, autospec=True):
        run_follow_stage(job, ctx)

    assert (job_dir / "playback.json").is_file()
    assert (job_dir / "logs" / "follow.log").is_file()

    forbidden = {"performance.json", "speak_timing.json", "deck.json"}
    for fn in forbidden:
        assert fn not in read_files, f"Follow stage read forbidden file {fn}"


def test_follow_stage_isolation_falsification(tmp_path: Path) -> None:
    """Falsification: reading performance.json in follow stage raises PermissionError."""
    job_dir = tmp_path / "job_pres"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")

    tree = _make_test_tree()
    (job_dir / "tree.json").write_text(tree.model_dump_json(), encoding="utf-8")
    (job_dir / "heard.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "asr",
                "audio_path": "audio/narration.wav",
                "duration_ms": 1000,
                "words": [],
                "sentences": [],
            }
        ),
        encoding="utf-8",
    )
    (job_dir / "performance.json").write_text("{}", encoding="utf-8")

    job = Job(job_dir)
    ctx = RunContext()

    def violate_isolation(*args: Any, **kwargs: Any) -> None:
        (job_dir / "performance.json").read_text(encoding="utf-8")

    orig_read_text = Path.read_text

    def guarded_read_text(self: Path, *a: Any, **kw: Any) -> str:
        if self.name == "performance.json":
            raise PermissionError("Isolation violation detected in follow")
        return orig_read_text(self, *a, **kw)

    with (
        patch(
            "animated_infographics.presentation.follow.LiveMatcher.run",
            side_effect=violate_isolation,
        ),
        pytest.raises(PermissionError),
        patch.object(Path, "read_text", side_effect=guarded_read_text, autospec=True),
    ):
        run_follow_stage(job, ctx)


def test_compose_timeline_and_short_scene_merge() -> None:
    """Verify compose merges scenes shorter than 20 frames and adds 300ms caption lag."""
    tree = _make_test_tree()
    words = [
        TranscriptWord(i=0, text="Hello", start_ms=0, end_ms=400, sentence_i=0),
        TranscriptWord(i=1, text="world", start_ms=450, end_ms=900, sentence_i=0),
    ]
    heard = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=6000,
        words=words,
        sentences=[
            TranscriptSentence(
                i=0,
                text="Hello world",
                start_ms=0,
                end_ms=900,
                word_start=0,
                word_end=2,
                paragraph_i=0,
                is_title=False,
            )
        ],
    )

    # 3 commits: first at 0ms, second at 3000ms, third at 3200ms
    # (only 200ms = 6 frames long -> merges into second)
    playback = PlaybackPlan(
        schema_version=1,
        commits=[
            PlaybackCommit(node_id="d1_section", at_ms=0, decision_ms=0, compute_ms=0, score=0.0),
            PlaybackCommit(node_id="d1_p0", at_ms=3000, decision_ms=3000, compute_ms=0, score=2.0),
            PlaybackCommit(node_id="d1_p1", at_ms=3200, decision_ms=3200, compute_ms=0, score=2.5),
        ],
        holds=[],
    )

    timeline, merged_notes = compose_presentation_timeline(
        tree=tree,
        playback=playback,
        heard=heard,
        bible=None,
    )

    # Short scene d1_p1 merged into d1_p0
    assert len(timeline.scenes) == 2
    assert len(merged_notes) == 1
    assert "Merged short scene" in merged_notes[0]

    # Captions have 300ms lag after last word
    # (last word ends at 900ms -> page start >= 1200ms = 36 frames)
    assert len(timeline.captions.pages) == 1
    assert timeline.captions.pages[0].start_frame >= 36


def test_compose_stage_execution(tmp_path: Path) -> None:
    """Verify run_compose_stage reads required files and writes timeline.json."""
    job_dir = tmp_path / "job_pres"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")

    tree = _make_test_tree()
    (job_dir / "tree.json").write_text(tree.model_dump_json(), encoding="utf-8")

    playback = PlaybackPlan(
        schema_version=1,
        commits=[
            PlaybackCommit(node_id="d1_section", at_ms=0, decision_ms=0, compute_ms=0, score=0.0),
        ],
        holds=[],
    )
    (job_dir / "playback.json").write_text(playback.model_dump_json(), encoding="utf-8")

    heard = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=4000,
        words=[],
        sentences=[],
    )
    (job_dir / "heard.json").write_text(heard.model_dump_json(), encoding="utf-8")

    audio_dir = job_dir / "audio"
    audio_dir.mkdir()
    (audio_dir / "narration.wav").write_bytes(b"RIFF" + b"\x00" * 40)

    job = Job(job_dir)
    ctx = RunContext()
    run_compose_stage(job, ctx)

    assert (job_dir / "timeline.json").is_file()
    assert (job_dir / "logs" / "compose.log").is_file()


def test_follow_hysteresis_one_strong_window_does_not_commit() -> None:
    """Hysteresis (§6.3): candidate must be top score at 2 consecutive decision points."""
    tree = _make_test_tree()
    # DP 1: top d1_p0 (decision_ms = 2500, dwell > 2000)
    # DP 2: top d1_p1 (by speaking 20 words for d1_p1)
    w1 = [
        TranscriptWord(i=0, text="London", start_ms=2100, end_ms=2300, sentence_i=0),
        TranscriptWord(i=1, text="breathe.", start_ms=2310, end_ms=2500, sentence_i=0),
    ]
    p1_words = (
        "waste river water Thames drinking waste river water Thames drinking "
        "waste river water Thames drinking waste river water Thames drinking"
    ).split()
    w2: list[TranscriptWord] = []
    cur = 3000
    for idx, tok in enumerate(p1_words):
        w2.append(
            TranscriptWord(
                i=2 + idx,
                text=tok + ("." if idx == len(p1_words) - 1 else ""),
                start_ms=cur,
                end_ms=cur + 100,
                sentence_i=1,
            )
        )
        cur += 120
    words = w1 + w2

    matcher = LiveMatcher(tree=tree)
    playback = matcher.run(words)

    # Only initial commit at 0ms exists; neither d1_p0 nor d1_p1 had 2 consecutive tops
    assert len(playback.commits) == 1
    assert playback.commits[0].node_id == "d1_section"

    # Both held with consecutive_top_not_met
    consecutive_holds = [h for h in playback.holds if "consecutive_top_not_met" in h.reason]
    assert len(consecutive_holds) >= 2

    # Falsification check: if words give d1_p0 two consecutive decision points, it commits
    words_2_tops = [
        TranscriptWord(i=0, text="London", start_ms=2100, end_ms=2300, sentence_i=0),
        TranscriptWord(i=1, text="breathe.", start_ms=2310, end_ms=2500, sentence_i=0),
        TranscriptWord(i=2, text="London", start_ms=3000, end_ms=3300, sentence_i=0),
        TranscriptWord(i=3, text="citizens.", start_ms=3310, end_ms=3500, sentence_i=0),
        TranscriptWord(i=4, text="Pause.", start_ms=4000, end_ms=4500, sentence_i=0),
    ]
    playback_2_tops = matcher.run(words_2_tops)
    assert len(playback_2_tops.commits) == 2
    assert playback_2_tops.commits[1].node_id == "d1_p0"


def test_follow_dwell_time_invariant() -> None:
    """Dwell time (§6.3): node must be shown for >= 2.0s before committing a new node."""
    tree = _make_test_tree()
    # Both decision points occur before 2000ms dwell time
    words = [
        TranscriptWord(i=0, text="London", start_ms=500, end_ms=700, sentence_i=0),
        TranscriptWord(i=1, text="breathe.", start_ms=710, end_ms=900, sentence_i=0),
        TranscriptWord(i=2, text="London", start_ms=1300, end_ms=1500, sentence_i=0),
        TranscriptWord(i=3, text="citizens.", start_ms=1510, end_ms=1700, sentence_i=0),
        TranscriptWord(i=4, text="Pause.", start_ms=2100, end_ms=2300, sentence_i=0),
    ]
    matcher = LiveMatcher(tree=tree)
    playback = matcher.run(words)

    # At 1700ms, dwell is 1700ms < 2000ms -> hold with dwell reason
    assert len(playback.commits) == 1
    dwell_holds = [h for h in playback.holds if "below_2000ms" in h.reason]
    assert len(dwell_holds) >= 1


def test_follow_unreachable_node_never_commits() -> None:
    """Graph edges (§6.2): an unreachable node in 1 hop from current cannot commit."""
    tree = _make_test_tree()
    # From d1_section, valid edges are only d1_p0 and d1_p1 (skip).
    # d2_p1 is unreachable (requires multiple hops).
    # Even if speech matches d2_p1 strongly:
    words = [
        TranscriptWord(i=0, text="Government", start_ms=2100, end_ms=2300, sentence_i=0),
        TranscriptWord(i=1, text="evacuating.", start_ms=2310, end_ms=2500, sentence_i=0),
        TranscriptWord(i=2, text="Government", start_ms=3000, end_ms=3300, sentence_i=0),
        TranscriptWord(i=3, text="evacuating.", start_ms=3310, end_ms=3500, sentence_i=0),
        TranscriptWord(i=4, text="Pause.", start_ms=4000, end_ms=4500, sentence_i=0),
    ]
    matcher = LiveMatcher(tree=tree)
    playback = matcher.run(words)

    # d2_p1 must NEVER be committed directly from d1_section
    assert all(c.node_id != "d2_p1" for c in playback.commits)
