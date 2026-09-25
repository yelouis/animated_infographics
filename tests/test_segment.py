"""Unit tests for narration segmentation and partition validation."""

from typing import Any

from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.planner.llm import LLMBackend
from animated_infographics.planner.segment import (
    build_fallback_groups,
    plan_beats,
    validate_partition,
)


def test_validate_partition_valid() -> None:
    ok, err = validate_partition([[0], [1, 2], [3]], 4)
    assert ok is True
    assert err == ""

    ok, err = validate_partition([[0, 1, 2, 3]], 4)
    assert ok is True

    ok, err = validate_partition([[0], [1], [2]], 3)
    assert ok is True

    ok, err = validate_partition([], 0)
    assert ok is True


def test_validate_partition_rejects_gap() -> None:
    ok, err = validate_partition([[0], [2]], 3)
    assert ok is False
    assert "gap" in err.lower() or "missing" in err.lower()

    ok, err = validate_partition([[0, 1], [3, 4]], 5)
    assert ok is False


def test_validate_partition_rejects_duplicate() -> None:
    ok, err = validate_partition([[0, 1], [1, 2]], 3)
    assert ok is False
    assert "duplicate" in err.lower()

    ok, err = validate_partition([[0], [1], [1]], 2)
    assert ok is False


def test_validate_partition_rejects_out_of_order() -> None:
    ok, err = validate_partition([[1], [0]], 2)
    assert ok is False

    ok, err = validate_partition([[0, 2, 1]], 3)
    assert ok is False

    ok, err = validate_partition([[1, 2], [0]], 3)
    assert ok is False


def test_validate_partition_rejects_malformed_structures() -> None:
    assert validate_partition("not a list", 3)[0] is False
    assert validate_partition(None, 3)[0] is False
    assert validate_partition([[0], [], [1]], 2)[0] is False
    assert validate_partition([["0", "1"]], 2)[0] is False


def test_fallback_groups_one_per_sentence() -> None:
    assert build_fallback_groups(0) == []
    assert build_fallback_groups(1) == [[0]]
    assert build_fallback_groups(4) == [[0], [1], [2], [3]]


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


def test_plan_beats_with_retries_and_fallback() -> None:
    # 3 sentences
    words = [
        TranscriptWord(i=0, sentence_i=0, text="Title", start_ms=0, end_ms=800),
        TranscriptWord(i=1, sentence_i=1, text="Sentence", start_ms=1000, end_ms=2500),
        TranscriptWord(i=2, sentence_i=1, text="one", start_ms=2500, end_ms=3500),
        TranscriptWord(i=3, sentence_i=2, text="Sentence", start_ms=4000, end_ms=5500),
        TranscriptWord(i=4, sentence_i=2, text="two", start_ms=5500, end_ms=6500),
    ]
    sentences = [
        TranscriptSentence(
            i=0,
            text="Title",
            start_ms=0,
            end_ms=800,
            word_start=0,
            word_end=1,
            paragraph_i=0,
            is_title=True,
        ),
        TranscriptSentence(
            i=1,
            text="Sentence one",
            start_ms=1000,
            end_ms=3500,
            word_start=1,
            word_end=3,
            paragraph_i=1,
            is_title=False,
        ),
        TranscriptSentence(
            i=2,
            text="Sentence two",
            start_ms=4000,
            end_ms=6500,
            word_start=3,
            word_end=5,
            paragraph_i=1,
            is_title=False,
        ),
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=6500,
        words=words,
        sentences=sentences,
    )

    # 1. Valid groups from backend
    backend_success = MockBackend([{"groups": [[0], [1, 2]]}])
    beats_obj = plan_beats(transcript, backend_success)
    assert backend_success.calls == 1
    assert len(beats_obj.beats) >= 2

    # 2. Invalid groups on attempt 0 (gap), succeeds on attempt 1
    backend_retry = MockBackend([{"groups": [[0], [2]]}, {"groups": [[0], [1, 2]]}])
    beats_retry = plan_beats(transcript, backend_retry)
    assert backend_retry.calls == 2
    assert len(beats_retry.beats) >= 2

    # 3. Fails all 3 attempts -> fallback groups [[0], [1], [2]]
    backend_fail = MockBackend(
        [{"groups": [[0], [2]]}, {"groups": [[0], [2]]}, {"groups": [[0], [2]]}]
    )
    beats_fallback = plan_beats(transcript, backend_fail)
    assert backend_fail.calls == 3
    assert len(beats_fallback.beats) >= 2
