"""Unit tests for contract models, invariants, and props validation."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Beats,
    Bible,
    CastMember,
    PlanReport,
    Scene,
    Storyboard,
    Timeline,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
    VoiceDecision,
)
from animated_infographics.contracts.styles import StyleSpec
from animated_infographics.contracts.templates import REGISTRY


def test_unknown_key_rejected() -> None:
    """Verify that models with extra='forbid' reject unrecognized fields."""
    with pytest.raises(ValidationError):
        VoiceDecision(
            voice="am_michael",
            source="flag",
            reason="flag",
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        TranscriptWord(
            i=0,
            text="Word",
            start_ms=0,
            end_ms=100,
            sentence_i=0,
            extra="forbidden",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        StyleSpec(
            name="literal",
            director=False,
            templates=[],
            overlays=False,
            license="none",
            extra="forbidden",  # type: ignore[call-arg]
        )


def test_schema_version_2_rejected() -> None:
    """Verify that top-level models reject schema_version != 1."""
    with pytest.raises(ValidationError):
        VoiceDecision(
            schema_version=2,  # type: ignore[arg-type]
            voice="am_michael",
            source="flag",
            reason="flag",
        )

    with pytest.raises(ValidationError):
        Transcript(
            schema_version=2,  # type: ignore[arg-type]
            source="tts",
            audio_path="audio/narration.wav",
            duration_ms=1000,
            words=[],
            sentences=[],
        )

    with pytest.raises(ValidationError):
        Bible(
            schema_version=2,  # type: ignore[arg-type]
            title="Title",
            logline="Logline",
            genre="history",
        )

    with pytest.raises(ValidationError):
        Beats(
            schema_version=2,  # type: ignore[arg-type]
            beats=[],
        )

    with pytest.raises(ValidationError):
        Storyboard(
            schema_version=2,  # type: ignore[arg-type]
            scenes=[],
        )

    with pytest.raises(ValidationError):
        PlanReport(
            schema_version=2,  # type: ignore[arg-type]
            model="gemma4:26b",
            llm_calls=0,
            llm_cache_hits=0,
        )

    with pytest.raises(ValidationError):
        Timeline(
            schema_version=2,  # type: ignore[arg-type]
            duration_frames=300,
            plan_sha256="abc",
            audio={"narration": {"src": "audio/narration.wav"}},  # type: ignore[arg-type]
        )


def test_voice_decision_valid() -> None:
    """Verify valid voice decisions in flag and auto modes."""
    # Flag mode
    vd_flag = VoiceDecision(voice="am_michael", source="flag", reason="flag")
    assert vd_flag.source == "flag"
    assert vd_flag.voice == "am_michael"

    # Auto mode female
    vd_female = VoiceDecision(
        voice="af_heart",
        source="auto",
        reason="llm",
        perspective="first_person",
        first_person_rate=5.2,
        narrator_gender="female",
        evidence="I'm a mother of two",
    )
    assert vd_female.voice == "af_heart"

    # Auto mode male/third_person
    vd_male = VoiceDecision(
        voice="am_michael",
        source="auto",
        reason="third_person",
        perspective="third_person",
        first_person_rate=0.0,
        narrator_gender="unknown",
        evidence=None,
    )
    assert vd_male.voice == "am_michael"


def test_voice_decision_invariants() -> None:
    """Verify each VoiceDecision invariant rejects violating examples."""
    # Invariant 1: source flag requires reason flag
    with pytest.raises(ValidationError, match="source 'flag' requires reason 'flag'"):
        VoiceDecision(
            voice="am_michael",
            source="flag",
            reason="third_person",
        )

    # Invariant 1: source flag requires analysis fields to be null
    with pytest.raises(ValidationError, match="all analysis fields to be null"):
        VoiceDecision(
            voice="am_michael",
            source="flag",
            reason="flag",
            perspective="first_person",
        )

    # Invariant 2: voice must be in INSTALLED_VOICES
    with pytest.raises(ValidationError):
        VoiceDecision(
            voice="unknown_voice",  # type: ignore[arg-type]
            source="flag",
            reason="flag",
        )

    # Invariant 3: reason tag requires evidence and female/male narrator
    with pytest.raises(ValidationError, match="requires non-null evidence"):
        VoiceDecision(
            voice="am_michael",
            source="auto",
            reason="tag",
            perspective="first_person",
            first_person_rate=4.0,
            narrator_gender="male",
            evidence=None,
        )

    with pytest.raises(ValidationError, match="requires narrator_gender in {female, male}"):
        VoiceDecision(
            voice="am_michael",
            source="auto",
            reason="tag",
            perspective="first_person",
            first_person_rate=4.0,
            narrator_gender="unknown",
            evidence="I (25)",
        )

    # Invariant 4: reason third_person requires perspective third_person
    with pytest.raises(ValidationError, match="requires perspective 'third_person'"):
        VoiceDecision(
            voice="am_michael",
            source="auto",
            reason="third_person",
            perspective="first_person",
            first_person_rate=0.0,
            narrator_gender="unknown",
        )

    # Invariant 5: af_heart requires first_person and female
    with pytest.raises(ValidationError, match="requires first_person and female"):
        VoiceDecision(
            voice="af_heart",
            source="auto",
            reason="tag",
            perspective="first_person",
            first_person_rate=3.0,
            narrator_gender="male",
            evidence="I (30M)",
        )

    # Invariant 5 reverse: first_person female in auto mode requires af_heart
    with pytest.raises(ValidationError, match="requires voice 'af_heart'"):
        VoiceDecision(
            voice="am_michael",
            source="auto",
            reason="tag",
            perspective="first_person",
            first_person_rate=3.0,
            narrator_gender="female",
            evidence="I (30F)",
        )


def test_props_examples_from_json() -> None:
    """Verify that props_examples.json covers all 16 templates.

    Checks 1 valid and 1 invalid example each.
    """
    data_path = Path(__file__).parent / "data" / "props_examples.json"
    with open(data_path, encoding="utf-8") as f:
        examples = json.load(f)

    assert len(examples) == 16, f"Expected 16 templates in props_examples.json, got {len(examples)}"

    scene_adapter: TypeAdapter[Scene] = TypeAdapter(Scene)

    for template_name, spec in REGISTRY.items():
        assert template_name in examples, (
            f"Template {template_name} missing from props_examples.json"
        )
        entry = examples[template_name]
        valid_data = entry["valid"]
        invalid_data = entry["invalid"]

        # 1. Valid props should parse with props_model
        props_obj = spec.props_model.model_validate(valid_data)
        assert props_obj is not None

        # 2. Valid props should parse as a Scene
        scene_data = {
            "id": "s000",
            "beat_i": 0,
            "template": template_name,
            "props": valid_data,
        }
        scene_obj = scene_adapter.validate_python(scene_data)
        assert scene_obj.template == template_name

        # 3. Invalid props should fail parsing with props_model
        with pytest.raises(ValidationError):
            spec.props_model.model_validate(invalid_data)

        # 4. Invalid props should fail parsing as a Scene
        bad_scene_data = {
            "id": "s000",
            "beat_i": 0,
            "template": template_name,
            "props": invalid_data,
        }
        with pytest.raises(ValidationError):
            scene_adapter.validate_python(bad_scene_data)


def test_transcript_invariants() -> None:
    """Verify Transcript validation rules."""
    w1 = TranscriptWord(i=0, text="Hello", start_ms=0, end_ms=100, sentence_i=0)
    w2 = TranscriptWord(i=1, text="world", start_ms=100, end_ms=200, sentence_i=0)
    s = TranscriptSentence(
        i=0, text="Hello world", start_ms=0, end_ms=200, word_start=0, word_end=2, paragraph_i=0
    )

    # Valid transcript
    t = Transcript(
        source="tts",
        audio_path="narration.wav",
        duration_ms=250,
        words=[w1, w2],
        sentences=[s],
    )
    assert len(t.words) == 2

    # Invariant: duration_ms < last word end_ms
    with pytest.raises(ValidationError, match="duration_ms"):
        Transcript(
            source="tts",
            audio_path="narration.wav",
            duration_ms=150,
            words=[w1, w2],
            sentences=[s],
        )

    # Invariant: words start_ms not ordered
    w2_bad = TranscriptWord(i=1, text="world", start_ms=50, end_ms=200, sentence_i=0)
    with pytest.raises(ValidationError, match="start_ms < previous word end_ms"):
        Transcript(
            source="tts",
            audio_path="narration.wav",
            duration_ms=300,
            words=[w1, w2_bad],
            sentences=[s],
        )


def test_bible_invariants() -> None:
    """Verify Bible validation rules."""
    avatar = AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="brown",
        facial_hair="none",
        headwear="none",
        glasses=False,
        age="adult",
    )
    c1 = CastMember(
        id="c1", name="Rescuer", role="Sailor", is_narrator=True, color_slot=0, avatar=avatar
    )
    c2 = CastMember(
        id="c2", name="Firefighter", role="Chief", is_narrator=True, color_slot=1, avatar=avatar
    )

    # Invariant: two narrators rejected
    with pytest.raises(ValidationError, match="at most one cast member can have is_narrator: true"):
        Bible(
            title="The Flood",
            logline="A flood of molasses.",
            genre="history",
            cast=[c1, c2],
        )

    # Invariant: duplicate color_slot rejected
    c2_not_narrator = CastMember(
        id="c2", name="Firefighter", role="Chief", is_narrator=False, color_slot=0, avatar=avatar
    )
    with pytest.raises(ValidationError, match="color_slots must be unique"):
        Bible(
            title="The Flood",
            logline="A flood of molasses.",
            genre="history",
            cast=[c1, c2_not_narrator],
        )


def test_beats_invariants() -> None:
    """Verify Beats validation rules."""
    b0 = Beat(i=0, word_start=0, word_end=2, start_ms=0, end_ms=500, text="First beat")
    b1_gap = Beat(i=1, word_start=2, word_end=4, start_ms=600, end_ms=1000, text="Second beat")

    # Invariant: start_ms != previous end_ms
    with pytest.raises(ValidationError, match="start_ms != previous beat end_ms"):
        Beats(beats=[b0, b1_gap])


def test_storyboard_invariants() -> None:
    """Verify Storyboard scene order and IDs."""
    scene0 = {
        "id": "s000",
        "beat_i": 0,
        "template": "title_card",
        "props": {"title": "Title"},
    }
    scene1_bad_id = {
        "id": "s005",
        "beat_i": 1,
        "template": "reveal",
        "props": {"kicker": "KICKER", "text": "Reveal text"},
    }

    with pytest.raises(ValidationError, match="expected 's001'"):
        Storyboard.model_validate({"scenes": [scene0, scene1_bad_id]})
