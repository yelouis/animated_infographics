import json
from pathlib import Path
from unittest.mock import MagicMock

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    Place,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.planner.props import (
    normalize_era_label,
    plan_single_template_props,
)


def test_normalize_era_label_frozen_cases() -> None:
    """Verify all 8 frozen era label cases from tests/data/wave_f_cases.json."""
    cases_path = Path(__file__).resolve().parent / "data" / "wave_f_cases.json"
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    era_labels = data["era_labels"]
    transcripts = data["transcripts"]

    for case in era_labels:
        transcript_lines = transcripts[case["job"]]
        transcript_text = " ".join(transcript_lines)
        result = normalize_era_label(case["era_label"], transcript_text)
        assert result == case["expected"], f"Failed for {case['job']} {case['scene_id']}"


def test_normalize_era_label_additional_cases() -> None:
    """Verify 1960s with 1960 in narration -> 1960s; 1932 when absent -> None."""
    # 1. "1960s" with 1960 in transcript -> "1960s"
    assert normalize_era_label("1960s", "They got engaged in 1960 before moving.") == "1960s"

    # 2. "1932 era" when 1932 is missing from transcript -> None
    assert normalize_era_label("1932 era", "They got engaged in 1960 before moving.") is None

    # 3. None or empty string -> None
    assert normalize_era_label(None, "In 1919 Boston flooded.") is None
    assert normalize_era_label("", "In 1919 Boston flooded.") is None
    assert normalize_era_label("   ", "In 1919 Boston flooded.") is None


def test_location_props_integration_normalizes_era_label() -> None:
    """Integration: stub backend returning 'Present Day' for location yields era_label None."""
    transcript_text = "Last spring, Danny finally sold the house."
    words = [
        TranscriptWord(i=i, text=tok, start_ms=i * 200, end_ms=(i + 1) * 200, sentence_i=0)
        for i, tok in enumerate(transcript_text.split())
    ]
    sentence = TranscriptSentence(
        i=0,
        text=transcript_text,
        start_ms=0,
        end_ms=len(words) * 200,
        word_start=0,
        word_end=len(words),
        paragraph_i=0,
        is_title=False,
    )
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=len(words) * 200 + 100,
        words=words,
        sentences=[sentence],
    )
    avatar = AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="black",
        facial_hair="none",
        headwear="none",
        glasses=False,
        age="adult",
    )
    bible = Bible(
        schema_version=1,
        title="Recipe Box",
        logline="Grandma's recipe box.",
        genre="personal_story",
        cast=[
            CastMember(
                id="c1", name="Me", role="narrator", is_narrator=True, color_slot=1, avatar=avatar
            )
        ],
        places=[
            Place(
                id="p1",
                name="Duluth House",
                kind="real",
                country_iso3="USA",
                lat=46.78,
                lon=-92.10,
                geo_source="gazetteer",
                visual_description="A house in Duluth.",
                icon="House",
            )
        ],
        set_pieces=[],
    )
    beat = Beat(
        i=1,
        word_start=0,
        word_end=len(words),
        start_ms=0,
        end_ms=len(words) * 200,
        text=transcript_text,
    )

    stub_backend = MagicMock()
    # Stub LLM returns place_id: p1, era_label: "Present Day"
    stub_backend.generate_json.return_value = {
        "place_id": "p1",
        "era_label": "Present Day",
    }

    scene, errs, attempts = plan_single_template_props(
        template_name="location",
        scene_id="s001",
        beat_i=1,
        beat=beat,
        prev_beat=None,
        next_beat=None,
        transcript=transcript,
        bible=bible,
        backend=stub_backend,
        prompt_template="test",
        compact_bible="test",
    )

    assert scene is not None
    assert errs == []
    assert scene.props.era_label is None
