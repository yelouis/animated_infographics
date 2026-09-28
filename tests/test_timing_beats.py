"""Unit tests for timing/beats.py beat construction, merging, and splitting."""

import logging
import random

import pytest

from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.timing.beats import (
    BEAT_MAX_MS,
    BEAT_MIN_MS,
    build_beats,
)


def _make_transcript(
    words_data: list[tuple[str, int, int]], sentences_data: list[tuple[int, int, bool]]
) -> Transcript:
    words = [
        TranscriptWord(
            i=i,
            text=text,
            start_ms=start,
            end_ms=end,
            sentence_i=0,
        )
        for i, (text, start, end) in enumerate(words_data)
    ]
    sentences = [
        TranscriptSentence(
            i=i,
            text=" ".join(words[w].text for w in range(w_start, w_end)),
            start_ms=words[w_start].start_ms,
            end_ms=words[w_end - 1].end_ms,
            word_start=w_start,
            word_end=w_end,
            paragraph_i=0,
            is_title=is_title,
        )
        for i, (w_start, w_end, is_title) in enumerate(sentences_data)
    ]
    # Update words' sentence_i
    for s in sentences:
        for w_idx in range(s.word_start, s.word_end):
            words[w_idx] = TranscriptWord(
                i=w_idx,
                text=words[w_idx].text,
                start_ms=words[w_idx].start_ms,
                end_ms=words[w_idx].end_ms,
                sentence_i=s.i,
            )

    return Transcript(
        source="tts",
        audio_path="audio/narration.wav",
        duration_ms=words[-1].end_ms + 500 if words else 0,
        words=words,
        sentences=sentences,
    )


def test_beats_merge_smaller_combined_neighbour() -> None:
    """Verify a 900 ms beat merges into the smaller-combined neighbour."""
    # Beat 0: 0..2000 (title)
    # Beat 1: 2000..6000 (4000 ms)
    # Beat 2: 6000..6900 (900 ms, < 1500 ms)
    # Beat 3: 6900..9900 (3000 ms)
    # Merging Beat 2 with Beat 1 yields duration 4900.
    # Merging Beat 2 with Beat 3 yields duration 3900.
    # 3900 < 4900 -> Beat 2 merges with Beat 3!
    words_data = [
        ("Title", 0, 2000),
        ("Sentence", 2000, 4000),
        ("one", 4000, 6000),
        ("Short", 6000, 6900),
        ("Sentence", 6900, 8400),
        ("three", 8400, 9900),
    ]
    sentences_data = [
        (0, 1, True),  # Title
        (1, 3, False),  # 2000..6000
        (3, 4, False),  # 6000..6900
        (4, 6, False),  # 6900..9900
    ]
    transcript = _make_transcript(words_data, sentences_data)
    beats = build_beats(transcript, [[0], [1], [2], [3]])

    assert len(beats) == 3
    # Beat 0 is title
    assert beats[0].start_ms == 0
    assert beats[0].end_ms == 2000
    # Beat 1 is untouched
    assert beats[1].start_ms == 2000
    assert beats[1].end_ms == 6000
    # Beat 2 is merged with Beat 3 (6000..9900)
    assert beats[2].start_ms == 6000
    assert beats[2].end_ms == 9900
    assert beats[2].text == "Short Sentence three"


def test_beat_0_never_merged() -> None:
    """Verify beat 0 is exempt from minimum and never merged."""
    words_data = [
        ("Title", 0, 800),  # 800 ms < 1500 ms
        ("Sentence", 800, 2000),
        ("one", 2000, 3800),
    ]
    sentences_data = [
        (0, 1, True),
        (1, 3, False),
    ]
    transcript = _make_transcript(words_data, sentences_data)
    beats = build_beats(transcript, [[0], [1]])

    assert len(beats) == 2
    assert beats[0].start_ms == 0
    assert beats[0].end_ms == 800
    assert beats[1].start_ms == 800
    assert beats[1].end_ms == 3800


def test_beats_split_comma_preference() -> None:
    """Verify a 9,000 ms beat splits at a comma in preference to a distant plain gap."""
    # Beat from 0..9000 ms
    # Boundary at 1500 ms: no comma, large gap 500 ms (ends 1000, starts 1500)
    # Boundary at 3000 ms: comma, small gap 50 ms (ends 2950, starts 3000)
    words_data = [
        ("Start", 0, 1000),
        ("plain", 1500, 2950),
        ("comma,", 2950, 3000),
        ("rest", 3050, 6000),
        ("of", 6000, 7500),
        ("sentence", 7500, 9000),
    ]
    sentences_data = [
        (0, 6, False),
    ]
    transcript = _make_transcript(words_data, sentences_data)
    beats = build_beats(transcript, [[0]])

    assert len(beats) == 2
    # Midpoint is 4500.
    # Boundary at word 1 (1500 ms): gap=500, penalty=|1500-4500|/4 = 750 -> -250
    # Boundary at word 3 (3050 ms): comma on word 2 ("comma,"), gap=50,
    # penalty=|3050-4500|/4 = 362.5 -> 50 + 1000 - 362.5 = 687.5
    # The split should happen at word 3 (3050 ms)
    assert beats[0].word_end == 3
    assert beats[1].word_start == 3


def test_quoted_speech_frozen_stays_one_beat() -> None:
    """9,625 ms quoted sentence stays one beat per design_audio_and_timing.md §7."""
    import json
    from pathlib import Path

    data = json.loads(Path("tests/data/quote_sentence.json").read_text(encoding="utf-8"))
    t0 = data["words"][0]["start_ms"]
    words_data = [(w["text"], w["start_ms"] - t0, w["end_ms"] - t0) for w in data["words"]]
    sentences_data = [(0, len(words_data), False)]
    transcript = _make_transcript(words_data, sentences_data)
    beats = build_beats(transcript, [[0]])

    assert len(beats) == 1
    assert beats[0].text == data["sentence_text"]


def test_quoted_speech_17000ms_split_not_before_opening_quote() -> None:
    """A synthetic 17,000 ms quoted sentence is split, but not before the opening quote."""
    # Sentence of 17,000 ms:
    # 0..3000: intro ("He said to the crowd,")
    # 3000..17000: quote ("\"Listen closely to what I have to say. This is very important!\"")
    # Opening quote is at word 5 (3000 ms).
    words_data = [
        ("He", 0, 500),
        ("said", 500, 1000),
        ("to", 1000, 1500),
        ("the", 1500, 2000),
        ("crowd,", 2000, 2900),  # boundary here at 3000 ms
        ('"Listen', 3000, 4500),
        ("closely", 4500, 6000),
        ("to", 6000, 7500),
        ("what", 7500, 9000),
        ("I", 9000, 10000),
        ("have", 10000, 11000),
        ("to", 11000, 12000),
        ("say.", 12000, 13500),
        ("This", 13500, 14500),
        ("is", 14500, 15500),
        ('important!"', 15500, 17000),
    ]
    sentences_data = [(0, len(words_data), False)]
    transcript = _make_transcript(words_data, sentences_data)
    beats = build_beats(transcript, [[0]])

    assert len(beats) > 1
    # Check that no beat split occurred immediately before the opening quote (word 5)
    for b in beats[:-1]:
        assert b.word_end != 5, "Split occurred immediately before opening quote"


def test_colon_earns_no_punctuation_bonus() -> None:
    """Colon does not receive the punctuation bonus in split scoring."""
    # Beat of 9000 ms.
    # Boundary 1: at word 2 (3000 ms), word 1 has a colon ("intro:").
    # Boundary 2: at word 3 (4500 ms, midpoint), word 2 has no punctuation ("middle").
    words_data = [
        ("word0", 0, 1000),
        ("intro:", 1000, 2950),  # gap = 50ms to word 2 at 3000
        ("middle", 3000, 4400),  # gap = 100ms to word 3 at 4500
        ("word3", 4500, 6000),
        ("word4", 6000, 9000),
    ]
    sentences_data = [(0, len(words_data), False)]
    transcript = _make_transcript(words_data, sentences_data)
    beats = build_beats(transcript, [[0]])

    # Midpoint is 4500 ms.
    # At word 2 (3000 ms): gap = 50. Penalty = |3000 - 4500| / 4 = 375.
    # If colon has NO bonus: score = 50 - 375 = -325.
    # At word 3 (4500 ms): gap = 100. Penalty = 0. Score = 100.
    # Word 3 wins if colon earns no bonus (if colon had +1000, word 2 scores 675 and wins).
    assert beats[0].word_end == 3
    assert beats[1].word_start == 3


def test_beats_property_test_500_random_streams(caplog: pytest.LogCaptureFixture) -> None:
    """Property test over 500 random word streams."""
    rng = random.Random(42)

    with caplog.at_level(logging.WARNING):
        for run_i in range(500):
            num_words = rng.randint(15, 60)
            words_data: list[tuple[str, int, int]] = []
            curr_ms = 0

            for w_i in range(num_words):
                dur = rng.randint(100, 400)
                end_ms = curr_ms + dur
                text = f"word{w_i}"
                if rng.random() < 0.2:
                    text += ","
                words_data.append((text, curr_ms, end_ms))
                gap = rng.randint(0, 150)
                curr_ms = end_ms + gap

            # Partition into sentences
            sentences_data: list[tuple[int, int, bool]] = []
            s_start = 0
            has_title = rng.random() < 0.5
            s_idx = 0
            while s_start < num_words:
                s_len = rng.randint(3, 8)
                s_end = min(num_words, s_start + s_len)
                is_title = has_title and s_idx == 0
                sentences_data.append((s_start, s_end, is_title))
                s_start = s_end
                s_idx += 1

            transcript = _make_transcript(words_data, sentences_data)
            groups = [[s[0]] for s in sentences_data]

            beats = build_beats(transcript, groups)

            assert len(beats) > 0, f"Run {run_i}: beats empty"
            assert beats[0].start_ms == 0, f"Run {run_i}: beat 0 start_ms != 0"
            assert beats[0].word_start == 0, f"Run {run_i}: beat 0 word_start != 0"
            assert beats[-1].end_ms == transcript.words[-1].end_ms, (
                f"Run {run_i}: last beat end_ms != transcript last word end_ms"
            )

            for k in range(len(beats)):
                dur = beats[k].end_ms - beats[k].start_ms
                if k >= 1:
                    assert beats[k].start_ms == beats[k - 1].end_ms, (
                        f"Run {run_i}: tiling gap at beat {k}"
                    )
                    assert beats[k].word_start == beats[k - 1].word_end, (
                        f"Run {run_i}: word index gap at beat {k}"
                    )
                    assert dur >= BEAT_MIN_MS, f"Run {run_i}: beat {k} dur {dur} < BEAT_MIN_MS"

                if dur > BEAT_MAX_MS:
                    # Must be logged as 'no valid split'
                    assert "no valid split" in caplog.text
