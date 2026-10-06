"""Tests for presentation perform, speak, and hear simulation stages.

Per design_presentation_simulation.md §4, §5 and design_data_contracts.md §10.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from animated_infographics.contracts.deck import DeckPlan, DeckPoint, DeckSlide
from animated_infographics.contracts.models import (
    IngestRecord,
    NarrationOffsets,
    SentenceOffset,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
    VoiceDecision,
)
from animated_infographics.contracts.performance import (
    BackRefTarget,
    PerformancePlan,
    PointTarget,
)
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import LLMBackend
from animated_infographics.presentation.hear import run_hear_stage
from animated_infographics.presentation.perform import (
    _validate_paraphrase,
    plan_performance,
)
from animated_infographics.presentation.speak import run_speak_stage


class StubPerformBackend(LLMBackend):
    """Stub LLM backend returning deterministic paraphrases and ad-libs."""

    def __init__(self, mode: str = "valid") -> None:
        self.mode = mode
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
        prompt = messages[0]["content"] if messages else ""

        if "paraphrase" in schema.get("properties", {}):
            if self.mode == "drop_number":
                return {"paraphrase": "A completely different sentence without digits."}
            elif self.mode == "drop_name":
                return {"paraphrase": "A sentence without the capitalized name."}
            else:
                # Extract original sentence from prompt and preserve all tokens
                m = re.search(r'# Original Sentence\s*\n\s*"([^"]+)"', prompt)
                orig_sent = m.group(1) if m else "Sentence"
                return {"paraphrase": f"Well now, {orig_sent}"}

        if "adlib" in schema.get("properties", {}):
            return {"adlib": "This is a fascinating aside."}

        if "back_ref" in schema.get("properties", {}):
            return {"back_ref": "Remember what we discussed earlier?"}

        return {}


def _create_deck_and_ingest(
    num_slides: int = 4,
    points_per_slide: int = 2,
    sents_per_point: int = 2,
) -> tuple[IngestRecord, DeckPlan]:
    """Helper creating matching IngestRecord and DeckPlan."""
    paragraphs: list[str] = []
    slides: list[DeckSlide] = []
    current_sid = 1

    for s_idx in range(num_slides):
        slide_points: list[DeckPoint] = []
        slide_sids: list[int] = []

        for p_idx in range(points_per_slide):
            pt_sids: list[int] = []
            pt_sentences: list[str] = []
            for _ in range(sents_per_point):
                pt_sids.append(current_sid)
                slide_sids.append(current_sid)
                pt_sentences.append(f"Sentence number {current_sid} explains slide {s_idx + 1}.")
                current_sid += 1
            slide_points.append(
                DeckPoint(text=f"Point {p_idx + 1} of slide {s_idx + 1}", sentence_ids=pt_sids)
            )
            paragraphs.append(" ".join(pt_sentences))

        slides.append(
            DeckSlide(
                id=f"d{s_idx + 1}",
                title=f"Slide {s_idx + 1}",
                sentence_ids=slide_sids,
                points=slide_points,
            )
        )

    ingest = IngestRecord(
        schema_version=1,
        kind="text",
        source="input/test.txt",
        title="Presentation Title",
        paragraphs=paragraphs,
        word_count=len(paragraphs) * 10,
    )
    deck = DeckPlan(schema_version=1, slides=slides)
    return ingest, deck


def test_paraphrase_validator_falsification() -> None:
    """Validator: drops digits or names -> False; keeps digits and names -> True."""
    orig = 'In 1858, London suffered under "The Great Stink" while Joseph Bazalgette planned.'

    # 1. Dropping number 1858
    assert (
        _validate_paraphrase(orig, "London suffered greatly while Joseph Bazalgette planned.")
        is False
    )

    # 2. Dropping proper name Bazalgette
    assert (
        _validate_paraphrase(
            orig,
            'In 1858, London suffered under "The Great Stink" while the engineer planned.',
        )
        is False
    )

    # 3. Dropping quoted phrase
    assert (
        _validate_paraphrase(
            orig, "In 1858, London suffered an awful smell while Joseph Bazalgette planned."
        )
        is False
    )

    # 4. Preserving all required tokens
    valid = (
        'During 1858, London was burdened with "The Great Stink" '
        "as Joseph Bazalgette planned carefully."
    )
    assert _validate_paraphrase(orig, valid) is True


def test_paraphrase_drop_number_falls_back_to_verbatim() -> None:
    """Falsification: when paraphrase drops a number, fallback to verbatim text."""
    ingest, deck = _create_deck_and_ingest(num_slides=2, points_per_slide=1, sents_per_point=2)
    backend = StubPerformBackend(mode="drop_number")

    plan = plan_performance(ingest, deck, backend, level="mild", seed=7)

    # Sentences in plan contain "Sentence number X" which has digits;
    # Since backend drops digits, all must fall back to verbatim
    for s in plan.sentences:
        if s.op == "filler":
            continue
        if s.source_sentence_id is not None:
            assert s.op == "verbatim"
            assert "sentence number" in s.text.lower()


def test_perform_determinism() -> None:
    """The same seed produces byte-identical performance.json."""
    ingest, deck = _create_deck_and_ingest(num_slides=4, points_per_slide=2, sents_per_point=3)
    backend1 = StubPerformBackend(mode="valid")
    backend2 = StubPerformBackend(mode="valid")

    plan1 = plan_performance(ingest, deck, backend1, level="strong", seed=7)
    plan2 = plan_performance(ingest, deck, backend2, level="strong", seed=7)

    assert plan1.model_dump_json() == plan2.model_dump_json()

    # Different seed produces different plan
    backend3 = StubPerformBackend(mode="valid")
    plan3 = plan_performance(ingest, deck, backend3, level="strong", seed=42)
    assert plan1.model_dump_json() != plan3.model_dump_json()


def test_perform_rates_on_400_sentence_synthetic_script() -> None:
    """Each operation fires at its configured rate on a 400-sentence script within +-3%."""
    # 40 slides, 2 points per slide, 5 sentences per point = 400 body sentences
    ingest, deck = _create_deck_and_ingest(num_slides=40, points_per_slide=2, sents_per_point=5)
    backend = StubPerformBackend(mode="valid")

    # Mild test (seed=7)
    plan_mild = plan_performance(ingest, deck, backend, level="mild", seed=7)
    surv_mild = sum(1 for s in plan_mild.sentences if s.source_sentence_id is not None)
    paraphrase_rate_mild = plan_mild.op_counts["paraphrase"] / surv_mild
    assert abs(paraphrase_rate_mild - 0.40) <= 0.03

    # Drop target = 0.05 (+- 0.03) on 360 eligible sentences (40 first sentences exempt)
    drop_rate_mild = plan_mild.op_counts["drop"] / 360.0
    assert abs(drop_rate_mild - 0.05) <= 0.03

    # Mild: 1 ad-lib, 0 back-refs, 0 skip-points
    assert plan_mild.op_counts["adlib"] == 1
    assert plan_mild.op_counts["back_ref"] == 0
    assert plan_mild.op_counts["skip_point"] == 0

    # Strong test (seed=7)
    plan_strong = plan_performance(ingest, deck, backend, level="strong", seed=7)
    surv_strong = sum(1 for s in plan_strong.sentences if s.source_sentence_id is not None)
    paraphrase_rate_strong = plan_strong.op_counts["paraphrase"] / surv_strong
    assert abs(paraphrase_rate_strong - 0.80) <= 0.03

    # Drop target = 0.15 (+- 0.03) on 360 eligible sentences
    drop_rate_strong = plan_strong.op_counts["drop"] / 360.0
    assert abs(drop_rate_strong - 0.15) <= 0.03

    # Strong: 3 ad-libs, 1 back-ref, 1 skip-point
    assert plan_strong.op_counts["adlib"] == 3
    assert plan_strong.op_counts["back_ref"] == 1
    assert plan_strong.op_counts["skip_point"] == 1


def test_placement_rules() -> None:
    """Verify skip point, back-reference, and drop placement rules per §4."""
    ingest, deck = _create_deck_and_ingest(num_slides=5, points_per_slide=2, sents_per_point=3)
    backend = StubPerformBackend(mode="valid")

    plan = plan_performance(ingest, deck, backend, level="strong", seed=7)

    # 1. Slide first sentences are never dropped
    first_sentence_ids = {slide.sentence_ids[0] for slide in deck.slides}
    performed_sids = {
        s.source_sentence_id for s in plan.sentences if s.source_sentence_id is not None
    }
    for sid in first_sentence_ids:
        assert sid in performed_sids, f"First sentence {sid} of slide was dropped!"

    # 2. Skip whole point: never the first slide's points
    first_slide_points = {(deck.slides[0].id, p_idx) for p_idx in range(len(deck.slides[0].points))}
    present_points = {
        (s.label.slide, s.label.point) for s in plan.sentences if isinstance(s.label, PointTarget)
    }
    assert first_slide_points.issubset(present_points)

    # 3. Back-reference: points back to earlier slide with slide index diff >= 2
    back_ref_sentences = [s for s in plan.sentences if s.op == "back_ref"]
    assert len(back_ref_sentences) == 1
    br_target = back_ref_sentences[0].label
    assert isinstance(br_target, BackRefTarget)
    # Target slide must be d1 or d2
    assert br_target.back_ref.slide in ("d1", "d2")


def test_retention_validator_falsification() -> None:
    """When retention rate is below threshold, ValidationFailed is raised."""
    ingest, deck = _create_deck_and_ingest(num_slides=2, points_per_slide=1, sents_per_point=2)
    backend = StubPerformBackend(mode="valid")

    # Patch rng_drop to always return 0.0 (dropping all eligible sentences)
    with patch("random.Random.random", return_value=0.0):
        with pytest.raises(ValidationFailed, match="below .* bar"):
            plan_performance(ingest, deck, backend, level="mild", seed=7)


def test_run_speak_stage(tmp_path: Path) -> None:
    """Verify run_speak_stage synthesizes narration and writes speak_timing.json."""
    job_dir = tmp_path / "job_pres"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")

    plan = PerformancePlan(
        schema_version=1,
        seed=7,
        level="mild",
        sentences=[],
        op_counts={},
    )
    (job_dir / "performance.json").write_text(plan.model_dump_json(), encoding="utf-8")
    voice = VoiceDecision(
        schema_version=1,
        voice="af_heart",
        source="flag",
        reason="flag",
    )
    (job_dir / "voice.json").write_text(voice.model_dump_json(), encoding="utf-8")

    job = Job(job_dir)
    ctx = RunContext()

    fake_offsets = NarrationOffsets(
        schema_version=1,
        voice="af_heart",
        sentences=[
            SentenceOffset(i=0, start_ms=0, end_ms=1200),
            SentenceOffset(i=1, start_ms=1400, end_ms=2500),
        ],
    )
    fake_transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="audio/narration.wav",
        duration_ms=2500,
        words=[],
        sentences=[],
    )

    with patch(
        "animated_infographics.presentation.speak.synthesize_narration",
        return_value=(fake_transcript, fake_offsets),
    ):
        run_speak_stage(job, ctx)

    timing_path = job_dir / "speak_timing.json"
    assert timing_path.is_file()
    timings = json.loads(timing_path.read_text(encoding="utf-8"))
    assert len(timings) == 2
    assert timings[0] == {"sentence_i": 0, "start_ms": 0, "end_ms": 1200}
    assert timings[1] == {"sentence_i": 1, "start_ms": 1400, "end_ms": 2500}
    assert (job_dir / "logs" / "speak.log").is_file()


def test_run_hear_stage(tmp_path: Path) -> None:
    """Verify run_hear_stage transcribes audio and writes heard.json."""
    job_dir = tmp_path / "job_pres"
    job_dir.mkdir()
    (job_dir / "state.json").write_text(json.dumps({"kind": "presentation"}), encoding="utf-8")
    audio_dir = job_dir / "audio"
    audio_dir.mkdir()
    (audio_dir / "narration.wav").write_bytes(b"RIFFdummy")

    job = Job(job_dir)
    ctx = RunContext()

    fake_transcript = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=3000,
        words=[
            TranscriptWord(i=0, text="Hello", start_ms=0, end_ms=500, sentence_i=0),
            TranscriptWord(i=1, text="world", start_ms=510, end_ms=900, sentence_i=0),
        ],
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

    with patch(
        "animated_infographics.presentation.hear.transcribe",
        return_value=fake_transcript,
    ):
        run_hear_stage(job, ctx)

    heard_path = job_dir / "heard.json"
    assert heard_path.is_file()
    heard_data = json.loads(heard_path.read_text(encoding="utf-8"))
    assert heard_data["source"] == "asr"
    assert len(heard_data["words"]) == 2
    assert (job_dir / "logs" / "hear.log").is_file()
