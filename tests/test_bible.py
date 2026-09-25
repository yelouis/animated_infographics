"""Unit tests for story bible planning, deterministic repairs, and fallback."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from animated_infographics.contracts.models import (
    AvatarConfig,
    Bible,
    CastMember,
    Place,
    SetPiece,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
    VoiceDecision,
)
from animated_infographics.planner.bible import plan_bible, repair_bible
from animated_infographics.planner.geo import Gazetteer, load_country_bboxes
from animated_infographics.planner.llm import LLMBackend

REPO_ROOT = Path(__file__).parent.parent
CITIES_PATH = REPO_ROOT / "data" / "vendor" / "cities15000.txt"
COUNTRY_INFO_PATH = REPO_ROOT / "data" / "vendor" / "countryInfo.txt"
BBOXES_PATH = REPO_ROOT / "data" / "geo" / "country_bboxes.json"


@pytest.fixture(scope="module")
def gazetteer() -> Gazetteer:
    return Gazetteer.load(CITIES_PATH, COUNTRY_INFO_PATH)


@pytest.fixture(scope="module")
def bboxes() -> dict[str, tuple[float, float, float, float]]:
    return load_country_bboxes(BBOXES_PATH)


def _make_avatar(facial_hair: str = "none") -> AvatarConfig:
    return AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="black",
        facial_hair=facial_hair,  # type: ignore[arg-type]
        headwear="none",
        glasses=False,
        age="adult",
    )


def test_truncate_lists_to_budget(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    cast = [
        CastMember.model_construct(
            id=f"c{i + 1}",
            name=f"Person {i + 1}",
            role="Role",
            is_narrator=False,
            color_slot=i % 8,
            avatar=_make_avatar(),
        )
        for i in range(12)
    ]
    places = [
        Place.model_construct(
            id=f"p{i + 1}",
            name=f"Place {i + 1}",
            kind="fictional",
            country_iso3=None,
            lat=None,
            lon=None,
            geo_source="none",
            visual_description="A place",
            icon="MapPin",
        )
        for i in range(6)
    ]
    set_pieces = [
        SetPiece.model_construct(
            id=f"v{i + 1}",
            name=f"Object {i + 1}",
            visual_description="An object",
            icon="Sparkle",
        )
        for i in range(5)
    ]

    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="A test logline.",
        genre="history",
        cast=cast,
        places=places,
        set_pieces=set_pieces,
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    assert len(repaired.cast) == 8
    assert len(repaired.places) == 4
    assert len(repaired.set_pieces) == 3


def test_duplicate_color_slots_repaired(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    # Two cast members with duplicate color_slot=0
    c1 = CastMember.model_construct(
        id="c1",
        name="Person 1",
        role="Role 1",
        is_narrator=False,
        color_slot=0,
        avatar=_make_avatar(),
    )
    c2 = CastMember.model_construct(
        id="c2",
        name="Person 2",
        role="Role 2",
        is_narrator=False,
        color_slot=0,
        avatar=_make_avatar(),
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="A test logline.",
        genre="history",
        cast=[c1, c2],
        places=[],
        set_pieces=[],
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    slots = [c.color_slot for c in repaired.cast]
    assert len(slots) == len(set(slots)), "Color slots must be distinct"
    assert slots[0] == 0
    assert slots[1] == 1  # lowest free slot


def test_multiple_narrators_repaired(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    # Multiple is_narrator=True -> keep first, set rest False
    c1 = CastMember.model_construct(
        id="c1",
        name="Me",
        role="Narrator",
        is_narrator=True,
        color_slot=0,
        avatar=_make_avatar(),
    )
    c2 = CastMember.model_construct(
        id="c2",
        name="Other",
        role="Other Narrator",
        is_narrator=True,
        color_slot=1,
        avatar=_make_avatar(),
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="A test logline.",
        genre="personal_story",
        cast=[c1, c2],
        places=[],
        set_pieces=[],
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    narrators = [c for c in repaired.cast if c.is_narrator]
    assert len(narrators) == 1
    assert repaired.cast[0].is_narrator is True
    assert repaired.cast[1].is_narrator is False


def test_geo_resolution_gazetteer(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    p = Place.model_construct(
        id="p1",
        name="Boston",
        kind="real",
        country_iso3="USA",
        lat=None,
        lon=None,
        geo_source="none",
        visual_description="Boston city",
        icon="MapPin",
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="Logline",
        genre="history",
        cast=[],
        places=[p],
        set_pieces=[],
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    place = repaired.places[0]
    assert place.geo_source == "gazetteer"
    assert place.lat is not None and pytest.approx(42.36, abs=0.05) == place.lat
    assert place.lon is not None and pytest.approx(-71.06, abs=0.05) == place.lon


def test_geo_resolution_llm_coords_in_bbox(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    # Not in gazetteer, but LLM coords inside USA bbox
    p = Place.model_construct(
        id="p1",
        name="SomeUnknownSmallTown12345",
        kind="real",
        country_iso3="USA",
        lat=40.0,
        lon=-75.0,
        geo_source="none",
        visual_description="Small town",
        icon="MapPin",
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="Logline",
        genre="history",
        cast=[],
        places=[p],
        set_pieces=[],
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    place = repaired.places[0]
    assert place.geo_source == "llm"
    assert place.lat == 40.0
    assert place.lon == -75.0


def test_geo_resolution_out_of_bbox_nulled(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    # Not in gazetteer, LLM coords outside USA bbox -> nulled to None, geo_source="none"
    p = Place.model_construct(
        id="p1",
        name="SomeUnknownSmallTown12345",
        kind="real",
        country_iso3="USA",
        lat=0.0,
        lon=0.0,
        geo_source="none",
        visual_description="Small town",
        icon="MapPin",
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="Logline",
        genre="history",
        cast=[],
        places=[p],
        set_pieces=[],
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    place = repaired.places[0]
    assert place.geo_source == "none"
    assert place.lat is None
    assert place.lon is None


def test_fictional_place_geo_nulled(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    p = Place.model_construct(
        id="p1",
        name="Atlantis",
        kind="fictional",
        country_iso3=None,
        lat=25.0,
        lon=-70.0,
        geo_source="llm",
        visual_description="Mythical island",
        icon="MapPin",
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="Logline",
        genre="other",
        cast=[],
        places=[p],
        set_pieces=[],
    )

    repaired = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    place = repaired.places[0]
    assert place.geo_source == "none"
    assert place.lat is None
    assert place.lon is None


def test_repair_5_female_narrator_avatar_consistency(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    # Narrator with beard
    narrator = CastMember.model_construct(
        id="c1",
        name="Me",
        role="Narrator",
        is_narrator=True,
        color_slot=0,
        avatar=_make_avatar(facial_hair="beard"),
    )
    other = CastMember.model_construct(
        id="c2",
        name="Bob",
        role="Friend",
        is_narrator=False,
        color_slot=1,
        avatar=_make_avatar(facial_hair="beard"),
    )
    raw = Bible.model_construct(
        schema_version=1,
        title="Test Story",
        logline="Logline",
        genre="personal_story",
        cast=[narrator, other],
        places=[],
        set_pieces=[],
    )

    # 1. Female voice -> narrator facial hair must be repaired to "none", other unchanged
    voice_female = VoiceDecision(
        voice="af_heart",
        source="auto",
        reason="llm",
        perspective="first_person",
        first_person_rate=5.0,
        narrator_gender="female",
        evidence="I am a daughter",
    )
    repaired_f = repair_bible(raw, voice=voice_female, gazetteer=gazetteer, bboxes=bboxes)
    assert repaired_f.cast[0].avatar.facial_hair == "none"
    assert repaired_f.cast[1].avatar.facial_hair == "beard"

    # 2. Male voice -> narrator facial hair unchanged ("beard")
    voice_male = VoiceDecision(
        voice="am_michael",
        source="auto",
        reason="tag",
        perspective="first_person",
        first_person_rate=5.0,
        narrator_gender="male",
        evidence="[34M]",
    )
    repaired_m = repair_bible(raw, voice=voice_male, gazetteer=gazetteer, bboxes=bboxes)
    assert repaired_m.cast[0].avatar.facial_hair == "beard"

    # 3. Unknown voice -> unchanged ("beard")
    voice_unk = VoiceDecision(
        voice="am_michael",
        source="auto",
        reason="no_evidence",
        perspective="first_person",
        first_person_rate=3.0,
        narrator_gender="unknown",
        evidence=None,
    )
    repaired_u = repair_bible(raw, voice=voice_unk, gazetteer=gazetteer, bboxes=bboxes)
    assert repaired_u.cast[0].avatar.facial_hair == "beard"

    # 4. Voice=None (e.g. audio input) -> unchanged ("beard")
    repaired_none = repair_bible(raw, voice=None, gazetteer=gazetteer, bboxes=bboxes)
    assert repaired_none.cast[0].avatar.facial_hair == "beard"


class MockBackend(LLMBackend):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls = 0
        self.cache_hits = 0

    def generate_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        if self.responses:
            return self.responses.pop(0)
        return {}


def test_plan_bible_with_retries_and_fallback(
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> None:
    # Construct a minimal transcript
    w1 = TranscriptWord(i=0, sentence_i=0, text="Hello", start_ms=0, end_ms=500)
    w2 = TranscriptWord(i=1, sentence_i=0, text="world", start_ms=500, end_ms=1000)
    sent = TranscriptSentence(
        i=0,
        text="Hello world.",
        start_ms=0,
        end_ms=1000,
        word_start=0,
        word_end=2,
        paragraph_i=0,
        is_title=True,
    )
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="audio/narration.wav",
        duration_ms=1000,
        words=[w1, w2],
        sentences=[sent],
    )

    # Case 1: Backend succeeds on attempt 1 after failing on attempt 0
    resp_invalid = {"invalid": True}
    resp_valid = {
        "title": "A Great Story",
        "logline": "This is a great story about the world.",
        "genre": "history",
        "cast": [],
        "places": [],
        "set_pieces": [],
    }
    backend = MockBackend([resp_invalid, resp_valid])
    bible = plan_bible(transcript, voice=None, backend=backend, gazetteer=gazetteer, bboxes=bboxes)
    assert backend.calls == 2
    assert bible.title == "A Great Story"
    assert bible.genre == "history"

    # Case 2: Backend fails all 3 attempts -> deterministic fallback
    backend_fail = MockBackend([{"invalid": True}, {"invalid": True}, {"invalid": True}])
    fallback_bible = plan_bible(
        transcript, voice=None, backend=backend_fail, gazetteer=gazetteer, bboxes=bboxes
    )
    assert backend_fail.calls == 3
    assert fallback_bible.title == "Hello world."
    assert fallback_bible.logline == "Hello world."
    assert fallback_bible.genre == "other"
    assert fallback_bible.cast == []
    assert fallback_bible.places == []
    assert fallback_bible.set_pieces == []
