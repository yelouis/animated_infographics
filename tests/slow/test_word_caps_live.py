"""Slow integration tests for live word caps across 5 real beats.

Per design_testing_and_validation.md §2.
"""

import json
from pathlib import Path

import pytest

from animated_infographics.contracts.models import (
    Beat,
    Bible,
    CharacterIntroScene,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.props import plan_single_template_props
from animated_infographics.planner.select import _build_compact_bible


def _make_transcript_from_sentences(sentences: list[str]) -> Transcript:
    words: list[TranscriptWord] = []
    transcript_sents: list[TranscriptSentence] = []
    ms = 0
    w_idx = 0
    for i, text in enumerate(sentences):
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
                paragraph_i=0,
                is_title=(i == 0),
            )
        )
        ms += 250

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="simulated.wav",
        duration_ms=ms + 500,
        words=words,
        sentences=transcript_sents,
    )


@pytest.mark.slow
@pytest.mark.parametrize("case_index", [0, 1, 2, 3, 4])
def test_word_caps_live_cases(case_index: int) -> None:
    """Verify each of the 5 real beats yields valid props within 3 attempts."""
    cases_path = Path(__file__).resolve().parent.parent / "data" / "word_caps_live_cases.json"
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    case = data["cases"][case_index]

    template = case["template"]
    scene_id = case["scene_id"]
    bible = Bible.model_validate(case["bible"])
    transcript = _make_transcript_from_sentences(case["sentences"])

    prev_beat = (
        Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=1000, text=case["beats"]["previous"])
        if case["beats"].get("previous")
        else None
    )
    beat = Beat(
        i=1,
        word_start=1,
        word_end=2,
        start_ms=1000,
        end_ms=2000,
        text=case["beats"]["current"],
    )
    next_beat = (
        Beat(i=2, word_start=2, word_end=3, start_ms=2000, end_ms=3000, text=case["beats"]["next"])
        if case["beats"].get("next")
        else None
    )

    prompt_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "animated_infographics"
        / "planner"
        / "prompts"
        / "props.md"
    )
    prompt_template = prompt_path.read_text(encoding="utf-8")
    compact_bible = _build_compact_bible(bible)

    backend = OllamaBackend(no_cache=True)
    scene, errors, attempts = plan_single_template_props(
        template,
        scene_id,
        1,
        beat,
        prev_beat,
        next_beat,
        transcript,
        bible,
        backend,
        prompt_template,
        compact_bible,
        max_attempts=3,
    )

    assert scene is not None, f"Failed to generate valid props for {template} {scene_id}: {errors}"
    assert attempts <= 3, f"Took {attempts} attempts (> 3) for {template} {scene_id}"

    if template == "character_intro":
        assert isinstance(scene, CharacterIntroScene)
        cast_member = next(c for c in bible.cast if c.id == scene.props.cast_id)
        # descriptor must not contain the cast member's name
        assert cast_member.name.casefold() not in scene.props.descriptor.casefold(), (
            f"Descriptor '{scene.props.descriptor}' contains cast member name '{cast_member.name}'"
        )
