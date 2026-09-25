"""Unit tests for token->word processing and narration math."""

from animated_infographics.audio.narrate import (
    build_sentence_list,
    enforce_rule4_invariants,
    process_sentence_tokens,
    round_half_up,
)
from animated_infographics.contracts.models import IngestRecord, TranscriptWord


def test_round_half_up() -> None:
    """Verify round_half_up rounds 0.5 up, never even/banker's round."""
    assert round_half_up(0.5) == 1
    assert round_half_up(1.5) == 2
    assert round_half_up(2.5) == 3
    assert round_half_up(0.49) == 0
    assert round_half_up(0.51) == 1


def test_build_sentence_list() -> None:
    """Verify sentence splitting per paragraph and title as sentence 0."""
    record = IngestRecord(
        schema_version=1,
        kind="text",
        source="input/story.txt",
        title="Story Title",
        paragraphs=[
            "First sentence. Second sentence!",
            "Third sentence?",
        ],
        word_count=6,
    )
    sents = build_sentence_list(record)
    assert len(sents) == 4
    # Sentence 0 is title
    assert sents[0] == ("Story Title", 0, True)
    # Sentence 1 and 2 are paragraph 1
    assert sents[1] == ("First sentence.", 1, False)
    assert sents[2] == ("Second sentence!", 1, False)
    # Sentence 3 is paragraph 2
    assert sents[3] == ("Third sentence?", 2, False)


def test_process_sentence_tokens_rules_1_and_3() -> None:
    """Rule 1: punctuation attaches to previous word; opening punctuation attaches to next."""
    tokens: list[tuple[str, float | None, float | None]] = [
        ("He", 0.0, 0.2),
        ("said", 0.2, 0.4),
        (",", 0.4, 0.45),
        ('"', 0.45, 0.5),
        ("Hello", 0.5, 0.8),
        ("!", 0.8, 0.85),
    ]
    words = process_sentence_tokens(
        tokens=tokens,
        sentence_start_sec=1.0,
        sentence_duration_sec=2.0,
        sentence_i=0,
        word_start_i=0,
    )
    assert len(words) == 3
    assert words[0].text == "He"
    assert words[0].start_ms == 1000
    assert words[0].end_ms == 1200

    assert words[1].text == "said,"
    assert words[1].start_ms == 1200
    assert words[1].end_ms == 1400

    assert words[2].text == '"Hello!'
    assert words[2].start_ms == 1500
    assert words[2].end_ms == 1800


def test_process_sentence_tokens_rule_2_linear_interpolation() -> None:
    """Rule 2: word token with None timestamps gets linearly interpolated."""
    tokens: list[tuple[str, float | None, float | None]] = [
        ("first", 0.0, 0.5),
        ("middle", None, None),
        ("last", 1.5, 2.0),
    ]
    words = process_sentence_tokens(
        tokens=tokens,
        sentence_start_sec=0.0,
        sentence_duration_sec=2.0,
        sentence_i=0,
        word_start_i=0,
    )
    assert len(words) == 3
    assert words[0].text == "first"
    assert words[0].start_ms == 0
    assert words[0].end_ms == 500

    # middle interpolated between 0.5s and 1.5s -> gap = 1.0s, step = 0.5s -> 1.0s to 1.5s
    assert words[1].text == "middle"
    assert words[1].start_ms == 1000
    assert words[1].end_ms == 1500

    assert words[2].text == "last"
    assert words[2].start_ms == 1500
    assert words[2].end_ms == 2000


def test_enforce_rule4_invariants() -> None:
    """Rule 4: if start_ms[i] < end_ms[i-1], end_ms[i-1] = start_ms[i].

    If end_ms <= start_ms, end_ms = start_ms + 40.
    """
    raw_words = [
        TranscriptWord(i=0, text="one", start_ms=0, end_ms=500, sentence_i=0),
        TranscriptWord(i=1, text="two", start_ms=450, end_ms=800, sentence_i=0),
    ]
    repaired = enforce_rule4_invariants(raw_words)
    assert repaired[0].end_ms == 450
    assert repaired[1].start_ms == 450
    assert repaired[1].end_ms == 800
