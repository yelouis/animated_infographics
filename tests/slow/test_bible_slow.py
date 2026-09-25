"""Slow integration tests for story bible planning with live gemma4:26b."""

from pathlib import Path

import pytest

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.ingest import ingest
from animated_infographics.planner.bible import plan_bible
from animated_infographics.planner.geo import Gazetteer, load_country_bboxes
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.voice import select_voice

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"
CITIES_PATH = REPO_ROOT / "data" / "vendor" / "cities15000.txt"
COUNTRY_INFO_PATH = REPO_ROOT / "data" / "vendor" / "countryInfo.txt"
BBOXES_PATH = REPO_ROOT / "data" / "geo" / "country_bboxes.json"


@pytest.fixture(scope="module")
def gazetteer() -> Gazetteer:
    return Gazetteer.load(CITIES_PATH, COUNTRY_INFO_PATH)


@pytest.fixture(scope="module")
def bboxes() -> dict[str, tuple[float, float, float, float]]:
    return load_country_bboxes(BBOXES_PATH)


def _make_transcript_from_script(script_path: Path) -> Transcript:
    ing = ingest(script_path, None)
    sents = build_sentence_list(ing)
    words: list[TranscriptWord] = []
    transcript_sents: list[TranscriptSentence] = []
    ms = 0
    w_idx = 0

    for i, (text, p_idx, is_t) in enumerate(sents):
        toks = text.split()
        w_start = ms
        s_w_start = w_idx
        for t in toks:
            words.append(
                TranscriptWord(
                    i=w_idx,
                    sentence_i=i,
                    text=t,
                    start_ms=ms,
                    end_ms=ms + 200,
                )
            )
            w_idx += 1
            ms += 250
        transcript_sents.append(
            TranscriptSentence(
                i=i,
                text=text,
                start_ms=w_start,
                end_ms=ms,
                word_start=s_w_start,
                word_end=w_idx,
                paragraph_i=p_idx,
                is_title=is_t,
            )
        )

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=ms,
        words=words,
        sentences=transcript_sents,
    )


@pytest.mark.slow
def test_bible_all_four_fixtures(
    gazetteer: Gazetteer,
    bboxes: dict[str, tuple[float, float, float, float]],
) -> None:
    backend = OllamaBackend(no_cache=True)

    # 1. molasses_flood: Boston by gazetteer, no narrator
    tr_molasses = _make_transcript_from_script(FIXTURES_DIR / "scripts" / "molasses_flood.txt")
    b_molasses = plan_bible(tr_molasses, None, backend, gazetteer, bboxes)
    assert any(
        "Boston" in p.name
        and p.geo_source == "gazetteer"
        and pytest.approx(42.36, abs=0.1) == p.lat
        and pytest.approx(-71.06, abs=0.1) == p.lon
        for p in b_molasses.places
    ), "molasses_flood: Boston must resolve by gazetteer"
    assert all(not c.is_narrator for c in b_molasses.cast), "molasses_flood: no narrator"

    # 2. emu_war: Meredith + AUS place, no narrator
    tr_emu = _make_transcript_from_script(FIXTURES_DIR / "scripts" / "emu_war.txt")
    b_emu = plan_bible(tr_emu, None, backend, gazetteer, bboxes)
    assert any("Meredith" in c.name for c in b_emu.cast), "emu_war: Meredith must be in cast"
    assert any(p.country_iso3 == "AUS" for p in b_emu.places), "emu_war: AUS place required"
    assert all(not c.is_narrator for c in b_emu.cast), "emu_war: no narrator"

    # 3. story_recipe_box: Rose, Danny, Walt + female narrator with facial_hair="none"
    # and Duluth & Thunder Bay by gazetteer
    ing_recipe = ingest(FIXTURES_DIR / "scripts" / "story_recipe_box.txt", None)
    v_recipe = select_voice(
        ing_recipe.title,
        "\n\n".join(ing_recipe.paragraphs or []),
        flag_voice=None,
        backend=backend,
    )
    tr_recipe = _make_transcript_from_script(FIXTURES_DIR / "scripts" / "story_recipe_box.txt")
    b_recipe = plan_bible(tr_recipe, v_recipe, backend, gazetteer, bboxes)

    cast_names = [c.name for c in b_recipe.cast]
    assert any("Rose" in n for n in cast_names), "story_recipe_box: Rose in cast"
    assert any("Danny" in n for n in cast_names), "story_recipe_box: Danny in cast"
    assert any("Walt" in n for n in cast_names), "story_recipe_box: Walt in cast"

    narrator = next((c for c in b_recipe.cast if c.is_narrator), None)
    assert narrator is not None, "story_recipe_box: narrator in cast"
    assert narrator.avatar.facial_hair == "none", (
        "story_recipe_box: female narrator facial_hair=none"
    )

    assert any(
        "Duluth" in p.name
        and p.geo_source == "gazetteer"
        and pytest.approx(46.78, abs=0.1) == p.lat
        for p in b_recipe.places
    ), "story_recipe_box: Duluth by gazetteer"

    assert any(
        "Thunder Bay" in p.name
        and p.geo_source == "gazetteer"
        and pytest.approx(48.38, abs=0.1) == p.lat
        for p in b_recipe.places
    ), "story_recipe_box: Thunder Bay by gazetteer"

    # 4. story_room_12: Alvarez, Deb, Sofia + narrator + Amarillo by gazetteer
    ing_room = ingest(FIXTURES_DIR / "scripts" / "story_room_12.txt", None)
    v_room = select_voice(
        ing_room.title,
        "\n\n".join(ing_room.paragraphs or []),
        flag_voice=None,
        backend=backend,
    )
    tr_room = _make_transcript_from_script(FIXTURES_DIR / "scripts" / "story_room_12.txt")
    b_room = plan_bible(tr_room, v_room, backend, gazetteer, bboxes)

    room_names = [c.name for c in b_room.cast]
    assert any("Alvarez" in n for n in room_names), "story_room_12: Alvarez in cast"
    assert any("Deb" in n for n in room_names), "story_room_12: Deb in cast"
    assert any("Sofia" in n for n in room_names), "story_room_12: Sofia in cast"

    room_narrator = next((c for c in b_room.cast if c.is_narrator), None)
    assert room_narrator is not None, "story_room_12: narrator in cast"

    assert any(
        "Amarillo" in p.name
        and p.geo_source == "gazetteer"
        and pytest.approx(35.22, abs=0.1) == p.lat
        for p in b_room.places
    ), "story_room_12: Amarillo by gazetteer"


@pytest.mark.slow
def test_bible_warm_cache_deterministic(
    gazetteer: Gazetteer,
    bboxes: dict[str, tuple[float, float, float, float]],
) -> None:
    """Warm-cache re-run must produce byte-identical output with cache hits."""
    tr = _make_transcript_from_script(FIXTURES_DIR / "scripts" / "molasses_flood.txt")

    backend1 = OllamaBackend(no_cache=False)
    b1 = plan_bible(tr, None, backend1, gazetteer, bboxes)

    backend2 = OllamaBackend(no_cache=False)
    b2 = plan_bible(tr, None, backend2, gazetteer, bboxes)

    assert b1.model_dump_json() == b2.model_dump_json()
    assert backend2.cache_hits >= 1, "Second run must hit the cache"
