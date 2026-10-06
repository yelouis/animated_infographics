"""Tests for presentation animation tree, presentation profile, matching, and isolation.

Contracts and validation rules per design_presentation_simulation.md §3, §6,
and design_data_contracts.md §10.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from animated_infographics.contracts.deck import DeckPlan, DeckPoint, DeckSlide
from animated_infographics.contracts.models import (
    Bible,
    KineticQuoteProps,
    KineticQuoteScene,
    Place,
    SectionTitleProps,
    SectionTitleScene,
    StatCalloutProps,
    StatCalloutScene,
)
from animated_infographics.contracts.tree import TreePlan
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import LLMBackend
from animated_infographics.planner.select import Choice, apply_rules
from animated_infographics.presentation.deck_bible import build_deck_transcript
from animated_infographics.presentation.match import (
    extract_scene_free_text,
    normalize_node_text,
    normalize_tokens,
)
from animated_infographics.presentation.tree import compile_tree_timeline, plan_tree, run_tree_stage


class StubTreeBackend(LLMBackend):
    """Stub LLM backend for deterministic tree planning tests."""

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: int = 0
        self.cache_hits: int = 0
        self.model: str = "stub"

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
            idx = min(attempt, len(self.responses) - 1)
            return self.responses[idx]
        return {}


def _make_sample_deck() -> DeckPlan:
    return DeckPlan(
        schema_version=1,
        slides=[
            DeckSlide(
                id="d1",
                title="The Thames Crisis",
                sentence_ids=[1, 2],
                points=[
                    DeckPoint(text="The river was overwhelmed by waste.", sentence_ids=[1]),
                    DeckPoint(text="Summer heat intensified the smell.", sentence_ids=[2]),
                ],
            ),
            DeckSlide(
                id="d2",
                title="Parliament Stalled",
                sentence_ids=[3, 4],
                points=[
                    DeckPoint(text="Lawmakers soaked curtains in chloride.", sentence_ids=[3]),
                    DeckPoint(text="Politicians fled the chamber.", sentence_ids=[4]),
                ],
            ),
            DeckSlide(
                id="d3",
                title="Engineering Solution",
                sentence_ids=[5, 6],
                points=[
                    DeckPoint(text="Bazalgette designed underground sewers.", sentence_ids=[5]),
                    DeckPoint(text="New system diverted all effluent.", sentence_ids=[6]),
                ],
            ),
        ],
    )


def _make_sample_bible() -> Bible:
    return Bible(
        schema_version=1,
        title="The Great Stink",
        logline="London summer crisis",
        genre="history",
        cast=[],
        places=[
            Place(
                id="p1",
                name="River Thames",
                kind="real",
                country_iso3="GBR",
                lat=51.5,
                lon=-0.1,
                geo_source="gazetteer",
                visual_description="A murky river flowing through London",
                icon="Drop",
            )
        ],
        set_pieces=[],
    )


def test_match_normalization():
    """Verify text normalization: stopwords, punctuation, and suffix stemming."""
    raw = "The quickly running rivers were overwhelmingly polluted!"
    tokens = normalize_tokens(raw)
    # Stopwords removed; 'quickly' -> 'quick', 'running' -> 'runn', 'rivers' -> 'river'
    assert "the" not in tokens
    assert "were" not in tokens
    assert "pollut" in tokens or "polluted" in tokens
    norm_text = normalize_node_text(raw)
    assert isinstance(norm_text, str)
    assert not any(sw in norm_text.split() for sw in ["the", "were", "and", "in"])


def test_match_extract_scene_free_text():
    """Verify free-text extraction across diverse scene templates."""
    kq = KineticQuoteScene(
        id="s001",
        beat_i=0,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="A major breakthrough in modern sanitary history",
            emphasis=["breakthrough"],
        ),
    )
    texts = extract_scene_free_text(kq)
    assert any("breakthrough" in t for t in texts)

    sec = SectionTitleScene(
        id="s002",
        beat_i=0,
        template="section_title",
        props=SectionTitleProps(title="The Crisis", index=0, count=3),
    )
    sec_texts = extract_scene_free_text(sec)
    assert "The Crisis" in sec_texts

    stat = StatCalloutScene(
        id="s003",
        beat_i=0,
        template="stat_callout",
        props=StatCalloutProps(value=2.3, decimals=1, prefix="$", suffix="million", icon="Coins"),
    )
    stat_texts = extract_scene_free_text(stat)
    assert "million" in stat_texts


def test_deck_bible_build_transcript():
    """Verify build_deck_transcript aggregates titles and points deterministically."""
    deck = _make_sample_deck()
    transcript = build_deck_transcript(deck)
    assert transcript.schema_version == 1
    assert transcript.source == "tts"
    # 3 titles + 6 points = 9 sentences
    assert len(transcript.sentences) == 9
    assert transcript.sentences[0].is_title is True
    assert transcript.sentences[0].text == "The Thames Crisis"
    assert transcript.sentences[1].is_title is False
    assert transcript.sentences[1].text == "The river was overwhelmed by waste."


def test_presentation_profile_rules():
    """Verify presentation profile disables R1, R2, R6, R7 while keeping R4, R5, R8."""
    # Video profile forces title_card at beat 0 (R1)
    raw_choices = [
        Choice(beat_i=0, primary="stat_callout", alternate="kinetic_quote"),
        Choice(beat_i=1, primary="stat_callout", alternate="kinetic_quote"),
    ]
    bible = _make_sample_bible()

    # In video profile, beat 0 gets repaired to title_card (R1)
    video_res, video_repairs = apply_rules(
        raw_choices, len(raw_choices), bible=bible, profile="video"
    )
    assert video_res[0].primary == "title_card"
    assert any(r.rule == "R1" for r in video_repairs)

    # In presentation profile, R1 does not fire, so stat_callout is preserved
    pres_res, pres_repairs = apply_rules(
        raw_choices, len(raw_choices), bible=bible, profile="presentation"
    )
    assert pres_res[0].primary == "stat_callout"
    assert not any(r.rule in ("R1", "R2", "R6", "R7") for r in pres_repairs)


def test_plan_tree_nodes_and_edges():
    """Verify tree plan creates section nodes, point nodes, and correct edges with costs."""
    deck = _make_sample_deck()
    bible = _make_sample_bible()
    backend = StubTreeBackend()

    tree = plan_tree(deck, bible, backend, style="literal")
    assert isinstance(tree, TreePlan)
    assert tree.schema_version == 1

    # 3 slides with 2 points each = 3 sections + 6 points = 9 nodes
    assert len(tree.nodes) == 9

    # Check node details
    sections = [n for n in tree.nodes if n.kind == "section"]
    points = [n for n in tree.nodes if n.kind == "point"]
    assert len(sections) == 3
    assert len(points) == 6

    # Section nodes must have section_title template and correct 0-indexed count
    for idx, sec in enumerate(sections):
        assert sec.scene.template == "section_title"
        assert sec.scene.props.index == idx
        assert sec.scene.props.count == 3
        assert sec.point_i is None

    # Point nodes must have valid point_i
    for pt in points:
        assert pt.point_i in (0, 1)
        assert pt.text  # Non-empty normalized text

    # Verify edge kinds and costs
    next_edges = [e for e in tree.edges if e.kind == "next"]
    skip_edges = [e for e in tree.edges if e.kind == "skip"]
    back_edges = [e for e in tree.edges if e.kind == "back"]

    # All next edges must have cost 0.0
    for e in next_edges:
        assert e.cost == 0.0

    # Next edges count:
    # Each slide: sec -> p0 (3), p0 -> p1 (3)
    # Between slides: d1_p1 -> d2_section (1), d2_p1 -> d3_section (1)
    # Total next edges = 3 + 3 + 2 = 8
    assert len(next_edges) == 8

    # All back edges must have cost 0.50 and point to earlier point nodes
    for e in back_edges:
        assert e.cost == 0.50
        assert "_p" in e.to

    # Skip edges must have cost 0.15 * pts_skipped capped at 0.60
    for e in skip_edges:
        assert 0.15 <= e.cost <= 0.60
        assert "_p" in e.to


def test_compile_tree_timeline():
    """Verify compile_tree_timeline produces a valid Timeline model for stills rendering."""
    deck = _make_sample_deck()
    bible = _make_sample_bible()
    backend = StubTreeBackend()

    tree = plan_tree(deck, bible, backend, style="literal")
    timeline = compile_tree_timeline(tree, bible, plan_sha="dummy_sha")

    assert timeline.schema_version == 1
    assert len(timeline.scenes) == len(tree.nodes)
    assert timeline.duration_frames == len(tree.nodes) * 150
    for idx, sc in enumerate(timeline.scenes):
        assert sc.start_frame == idx * 150
        assert sc.end_frame == (idx + 1) * 150
        assert sc.hide_captions is True


def test_tree_stage_isolation_invariant(tmp_path: Path):
    """Verify tree stage reads ONLY deck.json and deck_bible.json, never transcript or performance.

    Per design_data_contracts.md §10.
    """
    job_dir = tmp_path / "job_01"
    job_dir.mkdir(parents=True)

    deck = _make_sample_deck()
    bible = _make_sample_bible()

    (job_dir / "deck.json").write_text(deck.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "deck_bible.json").write_text(bible.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "state.json").write_text(
        json.dumps(
            {
                "job_id": "test-job-01",
                "created_at": "2026-10-06T00:00:00Z",
                "state": "created",
                "kind": "presentation",
                "completed_stages": [],
                "stage_input_sha256": {},
                "timings_ms": {},
            }
        ),
        encoding="utf-8",
    )

    # Add forbidden input files to simulate a corrupted or multi-stage dir
    forbidden_files = [
        "transcript.json",
        "performance.json",
        "speak_timing.json",
        "script.txt",
        "narration.json",
    ]
    for fn in forbidden_files:
        (job_dir / fn).write_text("FORBIDDEN CONTENT", encoding="utf-8")

    job = Job(job_dir)
    ctx = RunContext(style="literal")

    # Intercept file reads to assert forbidden files are never read
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes
    read_paths: list[Path] = []

    def tracking_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        read_paths.append(self)
        if self.name in forbidden_files:
            raise PermissionError(f"Isolation violation: {self.name}")
        return original_read_text(self, *args, **kwargs)

    def tracking_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        read_paths.append(self)
        if self.name in forbidden_files:
            raise PermissionError(f"Isolation violation: {self.name}")
        return original_read_bytes(self, *args, **kwargs)

    with (
        patch.object(Path, "read_text", side_effect=tracking_read_text, autospec=True),
        patch.object(Path, "read_bytes", side_effect=tracking_read_bytes, autospec=True),
        patch("animated_infographics.presentation.tree.run_assets"),
    ):
        run_tree_stage(job, ctx)

    # Verify outputs were produced
    assert (job_dir / "tree.json").is_file()
    assert (job_dir / "timeline.json").is_file()

    # Assert none of the forbidden files were read
    read_file_names = {p.name for p in read_paths}
    for fn in forbidden_files:
        assert fn not in read_file_names, f"Tree stage accessed forbidden file {fn}"


def test_tree_stage_isolation_falsification(tmp_path: Path):
    """Falsification test: assert that if run_tree_stage tries to read forbidden files, it fails."""
    job_dir = tmp_path / "job_02"
    job_dir.mkdir(parents=True)

    deck = _make_sample_deck()
    bible = _make_sample_bible()

    (job_dir / "deck.json").write_text(deck.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "deck_bible.json").write_text(bible.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "performance.json").write_text("{}", encoding="utf-8")
    (job_dir / "state.json").write_text(
        json.dumps(
            {
                "job_id": "test-job-02",
                "created_at": "2026-10-06T00:00:00Z",
                "state": "created",
                "kind": "presentation",
                "completed_stages": [],
                "stage_input_sha256": {},
                "timings_ms": {},
            }
        ),
        encoding="utf-8",
    )

    job = Job(job_dir)
    ctx = RunContext(style="literal")

    # Force a read of performance.json inside tree stage execution
    def deliberate_violation(*args: Any, **kwargs: Any) -> None:
        (job_dir / "performance.json").read_text(encoding="utf-8")

    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *a: Any, **kw: Any) -> str:
        if self.name == "performance.json":
            raise PermissionError("Isolation violation detected")
        return original_read_text(self, *a, **kw)

    with (
        patch(
            "animated_infographics.presentation.tree.plan_tree",
            side_effect=deliberate_violation,
        ),
        pytest.raises(PermissionError),
        patch.object(Path, "read_text", side_effect=guarded_read_text, autospec=True),
    ):
        run_tree_stage(job, ctx)
