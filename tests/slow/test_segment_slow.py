"""Slow integration tests for narration segmentation with live gemma4:26b."""

from pathlib import Path

import pytest

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.ingest import ingest
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.segment import plan_beats

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"


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
                    end_ms=ms + 250,
                )
            )
            w_idx += 1
            ms += 300
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
        ms += 250

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=ms,
        words=words,
        sentences=transcript_sents,
    )


@pytest.mark.slow
def test_segment_all_four_fixtures() -> None:
    """Verify that segmentation produces tiled beats within [1500, 8000]ms across all fixtures."""
    backend = OllamaBackend(no_cache=True)
    fixtures = ["molasses_flood", "emu_war", "story_recipe_box", "story_room_12"]

    for name in fixtures:
        script_path = FIXTURES_DIR / "scripts" / f"{name}.txt"
        transcript = _make_transcript_from_script(script_path)
        beats_obj = plan_beats(transcript, backend)
        beats = beats_obj.beats

        assert len(beats) >= 2, f"{name}: must produce at least 2 beats"

        # Tiling assertions: continuous coverage without gaps or overlaps
        assert beats[0].start_ms == 0, f"{name}: beat 0 must start at 0ms"
        assert beats[0].word_start == 0, f"{name}: beat 0 must start at word 0"

        for idx in range(1, len(beats)):
            prev_b = beats[idx - 1]
            curr_b = beats[idx]
            assert curr_b.start_ms == prev_b.end_ms, (
                f"{name}: beat {idx} start_ms {curr_b.start_ms} != prev end_ms {prev_b.end_ms}"
            )
            assert curr_b.word_start == prev_b.word_end, (
                f"{name}: beat {idx} word_start {curr_b.word_start} != "
                f"prev word_end {prev_b.word_end}"
            )

        assert beats[-1].word_end == len(transcript.words), (
            f"{name}: last beat word_end must equal total words count"
        )

        # Duration bounds: every beat k >= 1 must be within [1500, 8000]ms
        durations = []
        for b in beats[1:]:
            dur = b.end_ms - b.start_ms
            durations.append(dur)
            assert 1500 <= dur <= 8000, (
                f"{name}: beat {b.i} duration {dur}ms outside [1500, 8000]ms"
            )

        # Record beat count and histogram
        h_short = sum(1 for d in durations if d < 2500)
        h_target = sum(1 for d in durations if 2500 <= d <= 6000)
        h_long = sum(1 for d in durations if d > 6000)
        print(
            f"\n{name}: {len(beats)} beats total; duration histogram: "
            f"<2.5s: {h_short}, 2.5-6.0s: {h_target}, >6.0s: {h_long}"
        )


@pytest.mark.slow
def test_falsify_skip_merge_fails_bounds() -> None:
    """Falsification: skipping merge pass causes beats < 1500ms to fail the lower bound."""
    # Synthetic transcript with distinct paragraphs where the LLM does not merge
    words = [
        TranscriptWord(i=0, sentence_i=0, text="Intro", start_ms=0, end_ms=500),
        TranscriptWord(i=1, sentence_i=1, text="First", start_ms=1000, end_ms=1300),
        TranscriptWord(i=2, sentence_i=2, text="Second", start_ms=2000, end_ms=2300),
        TranscriptWord(i=3, sentence_i=3, text="Third", start_ms=3000, end_ms=5000),
    ]
    sentences = [
        TranscriptSentence(
            i=0,
            text="Intro",
            start_ms=0,
            end_ms=500,
            word_start=0,
            word_end=1,
            paragraph_i=0,
            is_title=True,
        ),
        TranscriptSentence(
            i=1,
            text="First idea is here.",
            start_ms=1000,
            end_ms=1300,
            word_start=1,
            word_end=2,
            paragraph_i=1,
            is_title=False,
        ),
        TranscriptSentence(
            i=2,
            text="Second idea is here.",
            start_ms=2000,
            end_ms=2300,
            word_start=2,
            word_end=3,
            paragraph_i=2,
            is_title=False,
        ),
        TranscriptSentence(
            i=3,
            text="Third idea is here.",
            start_ms=3000,
            end_ms=5000,
            word_start=3,
            word_end=4,
            paragraph_i=3,
            is_title=False,
        ),
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=5000,
        words=words,
        sentences=sentences,
    )

    backend = OllamaBackend(no_cache=True)

    # 1. With skip_merge=True: beats under 1500ms remain unmerged and fail the lower bound
    beats_no_merge = plan_beats(transcript, backend, skip_merge=True)
    has_short_beat = any((b.end_ms - b.start_ms) < 1500 for b in beats_no_merge.beats[1:])
    assert has_short_beat, "Skipping merge pass must produce a beat under 1500ms"

    # 2. With skip_merge=False: merge pass runs, guaranteeing all beats k >= 1 >= 1500ms
    beats_normal = plan_beats(transcript, backend, skip_merge=False)
    assert all(1500 <= (b.end_ms - b.start_ms) <= 8000 for b in beats_normal.beats[1:]), (
        "Normal build_beats with merge pass must satisfy [1500, 8000]ms"
    )
