"""Tests for Presentation Simulation Deck stage.

Contracts and validation rules per design_presentation_simulation.md §2,
design_testing_and_validation.md §2, and design_system_architecture.md §4, §6.
"""

from pathlib import Path
from typing import Any

from animated_infographics.contracts.deck import DeckPlan
from animated_infographics.contracts.models import IngestRecord
from animated_infographics.presentation.deck import (
    build_deck_schema,
    compute_target_slides,
    plan_deck,
    validate_deck,
)
from animated_infographics.preview import (
    generate_deck_contact_sheet,
    generate_deck_storyboard_markdown,
)


class StubLLMBackend:
    """Configurable stub backend for deterministic deck planning tests."""

    def __init__(
        self, responses: list[dict[str, Any]] | None = None, fail_calls: bool = False
    ) -> None:
        self.responses = list(responses or [])
        self.fail_calls = fail_calls
        self.calls: int = 0
        self.cache_hits: int = 0
        self.model: str = "stub"
        self.last_messages: list[dict[str, Any]] = []

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
        if messages:
            self.last_messages = list(messages)
        if self.fail_calls:
            raise RuntimeError("Backend call failed")
        if self.responses:
            idx = min(attempt, len(self.responses) - 1)
            return self.responses[idx]
        return {"slides": []}


def make_dummy_sentences(n: int) -> list[tuple[str, int, bool]]:
    """Create n+1 sentences (index 0 is title, 1..n are body sentences)."""
    sentences = [("The Great Mystery of 1858.", 5, True)]
    for i in range(1, n + 1):
        text = f"Sentence {i} describes important event number {i} happening in year 1858."
        sentences.append((text, len(text.split()), False))
    return sentences


def test_target_slides_clamped_and_rounded() -> None:
    # clamped 4-10
    assert compute_target_slides(100) == 4
    assert compute_target_slides(350) == 4
    # 672 words (history_great_stink) -> round(6.72) = 7
    assert compute_target_slides(672) == 7
    # 751 words (story_overdue_book) -> round(7.51) = 8
    assert compute_target_slides(751) == 8
    assert compute_target_slides(980) == 10
    assert compute_target_slides(1500) == 10


def test_deck_schema_structure() -> None:
    schema = build_deck_schema()
    assert schema["type"] == "object"
    assert "slides" in schema["properties"]
    # LLM facing schema must not have forbidden keys
    for k in ("maxLength", "minLength", "maxItems", "minItems", "pattern"):
        assert k not in str(schema)


def test_validator_1_slide_count() -> None:
    sentences = make_dummy_sentences(14)
    # Expected target for 700 words: 7 slides
    deck_data = {
        "slides": [
            {
                "id": f"d{i}",
                "title": f"Slide {i}",
                "sentence_ids": [2 * i - 1, 2 * i],
                "points": [
                    {"text": f"Point A of slide {i}", "sentence_ids": [2 * i - 1]},
                    {"text": f"Point B of slide {i}", "sentence_ids": [2 * i]},
                ],
            }
            for i in range(1, 6)
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=700)
    assert any("Expected 7 slides" in e for e in errors)


def test_validator_2_points_count_per_slide() -> None:
    sentences = make_dummy_sentences(8)
    # 4 slides for 400 words
    deck_data = {
        "slides": [
            {
                "id": "d1",
                "title": "Slide One",
                "sentence_ids": [1, 2],
                # 1 point: invalid
                "points": [{"text": "Single point only", "sentence_ids": [1, 2]}],
            },
            {
                "id": "d2",
                "title": "Slide Two",
                "sentence_ids": [3, 4],
                "points": [
                    {"text": f"Point {k}", "sentence_ids": [3 if k < 3 else 4]}
                    for k in range(5)  # 5 points: invalid
                ],
            },
            {
                "id": "d3",
                "title": "Slide Three",
                "sentence_ids": [5, 6],
                "points": [
                    {"text": "Point A", "sentence_ids": [5]},
                    {"text": "Point B", "sentence_ids": [6]},
                ],
            },
            {
                "id": "d4",
                "title": "Slide Four",
                "sentence_ids": [7, 8],
                "points": [
                    {"text": "Point A", "sentence_ids": [7]},
                    {"text": "Point B", "sentence_ids": [8]},
                ],
            },
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=400)
    assert any("expected 2-4 points, got 1" in e for e in errors)
    assert any("expected 2-4 points, got 5" in e for e in errors)


def test_validator_3_lengths() -> None:
    sentences = make_dummy_sentences(8)
    deck_data = {
        "slides": [
            {
                "id": "d1",
                "title": "This Title Has Way Too Many Words Exceeding Limit",  # 9 words > 6
                "sentence_ids": [1, 2],
                "points": [
                    {"text": "Valid short point", "sentence_ids": [1]},
                    {
                        # 14 words > 12 limit
                        "text": (
                            "This point has way too many words in it that clearly exceeds twelve"
                        ),
                        "sentence_ids": [2],
                    },
                ],
            },
            {
                "id": "d2",
                "title": "Slide Two",
                "sentence_ids": [3, 4],
                "points": [
                    {"text": "Point A", "sentence_ids": [3]},
                    {"text": "Point B", "sentence_ids": [4]},
                ],
            },
            {
                "id": "d3",
                "title": "Slide Three",
                "sentence_ids": [5, 6],
                "points": [
                    {"text": "Point A", "sentence_ids": [5]},
                    {"text": "Point B", "sentence_ids": [6]},
                ],
            },
            {
                "id": "d4",
                "title": "Slide Four",
                "sentence_ids": [7, 8],
                "points": [
                    {"text": "Point A", "sentence_ids": [7]},
                    {"text": "Point B", "sentence_ids": [8]},
                ],
            },
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=400)
    assert any("has 9 words (limit 6)" in e for e in errors)
    assert any("limit 12" in e for e in errors)


def test_validator_4_falsification_skipping_sentence() -> None:
    """Falsification test per agent_execution_guide.md H1:

    Let the partition skip one sentence -> validator 4 rejects it.
    """
    sentences = make_dummy_sentences(8)
    # Slide 1 covers [1, 2]. Slide 2 skips sentence 3 and covers [4, 5].
    deck_data = {
        "slides": [
            {
                "id": "d1",
                "title": "Slide One",
                "sentence_ids": [1, 2],
                "points": [
                    {"text": "Point A", "sentence_ids": [1]},
                    {"text": "Point B", "sentence_ids": [2]},
                ],
            },
            {
                "id": "d2",
                "title": "Slide Two",
                "sentence_ids": [4, 5],  # Missing sentence 3!
                "points": [
                    {"text": "Point A", "sentence_ids": [4]},
                    {"text": "Point B", "sentence_ids": [5]},
                ],
            },
            {
                "id": "d3",
                "title": "Slide Three",
                "sentence_ids": [6, 7],
                "points": [
                    {"text": "Point A", "sentence_ids": [6]},
                    {"text": "Point B", "sentence_ids": [7]},
                ],
            },
            {
                "id": "d4",
                "title": "Slide Four",
                "sentence_ids": [8],
                "points": [
                    {"text": "Point A", "sentence_ids": [8]},
                    {"text": "Point B", "sentence_ids": [8]},
                ],
            },
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=400)
    assert any("skipped sentences" in e.lower() for e in errors)


def test_validator_4_overlapping_and_sentence_zero() -> None:
    sentences = make_dummy_sentences(8)
    deck_data = {
        "slides": [
            {
                "id": "d1",
                "title": "Slide One",
                "sentence_ids": [0, 1, 2],  # sentence 0 included!
                "points": [
                    {"text": "Point A", "sentence_ids": [0, 1]},
                    {"text": "Point B", "sentence_ids": [2]},
                ],
            },
            {
                "id": "d2",
                "title": "Slide Two",
                "sentence_ids": [2, 3, 4],  # overlap on sentence 2!
                "points": [
                    {"text": "Point A", "sentence_ids": [2, 3]},
                    {"text": "Point B", "sentence_ids": [4]},
                ],
            },
            {
                "id": "d3",
                "title": "Slide Three",
                "sentence_ids": [5, 6],
                "points": [
                    {"text": "Point A", "sentence_ids": [5]},
                    {"text": "Point B", "sentence_ids": [6]},
                ],
            },
            {
                "id": "d4",
                "title": "Slide Four",
                "sentence_ids": [7, 8],
                "points": [
                    {"text": "Point A", "sentence_ids": [7]},
                    {"text": "Point B", "sentence_ids": [8]},
                ],
            },
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=400)
    assert any("sentence 0" in e for e in errors)
    assert any("overlapping" in e.lower() for e in errors)


def test_validator_5_digit_grounding() -> None:
    sentences = make_dummy_sentences(8)
    deck_data = {
        "slides": [
            {
                "id": "d1",
                "title": "In Year 1999 London",  # 1999 not in sentences (1858 is)
                "sentence_ids": [1, 2],
                "points": [
                    {"text": "Point A in 1858", "sentence_ids": [1]},  # 1858 is grounded
                    {"text": "Point B with 999 items", "sentence_ids": [2]},  # 999 ungrounded
                ],
            },
            {
                "id": "d2",
                "title": "Slide Two",
                "sentence_ids": [3, 4],
                "points": [
                    {"text": "Point A", "sentence_ids": [3]},
                    {"text": "Point B", "sentence_ids": [4]},
                ],
            },
            {
                "id": "d3",
                "title": "Slide Three",
                "sentence_ids": [5, 6],
                "points": [
                    {"text": "Point A", "sentence_ids": [5]},
                    {"text": "Point B", "sentence_ids": [6]},
                ],
            },
            {
                "id": "d4",
                "title": "Slide Four",
                "sentence_ids": [7, 8],
                "points": [
                    {"text": "Point A", "sentence_ids": [7]},
                    {"text": "Point B", "sentence_ids": [8]},
                ],
            },
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=400)
    assert any("1999" in e and "not grounded" in e for e in errors)
    assert any("999" in e and "not grounded" in e for e in errors)


def test_validator_6_text_checks() -> None:
    sentences = make_dummy_sentences(8)
    deck_data = {
        "slides": [
            {
                "id": "d1",
                "title": 'Title with "Quotes"',  # quotation marks
                "sentence_ids": [1, 2],
                "points": [
                    {"text": "Icon: Stink cloud", "sentence_ids": [1]},  # instruction
                    {"text": "N/A", "sentence_ids": [2]},  # placeholder
                ],
            },
            {
                "id": "d2",
                "title": "Slide Two c1",  # internal id c1
                "sentence_ids": [3, 4],
                "points": [
                    {"text": "Point A", "sentence_ids": [3]},
                    {"text": "Point B", "sentence_ids": [4]},
                ],
            },
            {
                "id": "d3",
                "title": "Slide Three",
                "sentence_ids": [5, 6],
                "points": [
                    {"text": "Point A", "sentence_ids": [5]},
                    {"text": "Point B", "sentence_ids": [6]},
                ],
            },
            {
                "id": "d4",
                "title": "Slide Four",
                "sentence_ids": [7, 8],
                "points": [
                    {"text": "Point A", "sentence_ids": [7]},
                    {"text": "Point B", "sentence_ids": [8]},
                ],
            },
        ]
    }
    _, errors = validate_deck(deck_data, sentences, word_count=400)
    assert any("quotation marks" in e for e in errors)
    assert any("instruction" in e for e in errors)
    assert any("placeholder" in e for e in errors)
    assert any("internal id" in e for e in errors)


def test_plan_deck_with_stub_backend() -> None:
    ingest = IngestRecord(
        kind="text",
        source="story.txt",
        title="The Great Mystery of 1858",
        paragraphs=[
            "Sentence 1 describes important event number 1 happening in year 1858. "
            "Sentence 2 describes important event number 2 happening in year 1858.",
            "Sentence 3 describes important event number 3 happening in year 1858. "
            "Sentence 4 describes important event number 4 happening in year 1858.",
            "Sentence 5 describes important event number 5 happening in year 1858. "
            "Sentence 6 describes important event number 6 happening in year 1858.",
            "Sentence 7 describes important event number 7 happening in year 1858. "
            "Sentence 8 describes important event number 8 happening in year 1858.",
        ],
        word_count=400,
    )
    valid_deck = {
        "slides": [
            {
                "id": "d1",
                "title": "London in 1858",
                "sentence_ids": [1, 2],
                "points": [
                    {"text": "Hot summer in 1858", "sentence_ids": [1]},
                    {"text": "River Thames smells bad", "sentence_ids": [2]},
                ],
            },
            {
                "id": "d2",
                "title": "Crisis at Westminster",
                "sentence_ids": [3, 4],
                "points": [
                    {"text": "Parliament considers leaving town", "sentence_ids": [3]},
                    {"text": "Lime curtains do not work", "sentence_ids": [4]},
                ],
            },
            {
                "id": "d3",
                "title": "Bazalgette Steps Up",
                "sentence_ids": [5, 6],
                "points": [
                    {"text": "A daring sewer blueprint", "sentence_ids": [5]},
                    {"text": "Massive construction commences", "sentence_ids": [6]},
                ],
            },
            {
                "id": "d4",
                "title": "Triumph of Engineering",
                "sentence_ids": [7, 8],
                "points": [
                    {"text": "Pumping stations open", "sentence_ids": [7]},
                    {"text": "Clean water returns", "sentence_ids": [8]},
                ],
            },
        ]
    }

    # First attempt returns invalid (3 slides), second attempt returns valid (4 slides)
    invalid_deck = {"slides": valid_deck["slides"][:3]}
    backend = StubLLMBackend(responses=[invalid_deck, valid_deck])

    plan = plan_deck(ingest, backend)
    assert isinstance(plan, DeckPlan)
    assert len(plan.slides) == 4
    assert backend.calls == 2
    assert "Expected 4 slides" in str(backend.last_messages)


def test_deck_preview_generation(tmp_path: Path) -> None:
    deck = DeckPlan(
        slides=[
            {
                "id": "d1",
                "title": "London in Crisis",
                "sentence_ids": [1, 2],
                "points": [
                    {"text": "River Thames unbearable", "sentence_ids": [1]},
                    {"text": "Parliament evacuates", "sentence_ids": [2]},
                ],
            },
            {
                "id": "d2",
                "title": "Bazalgette Saves London",
                "sentence_ids": [3, 4],
                "points": [
                    {"text": "Underground sewer system", "sentence_ids": [3]},
                    {"text": "Clean water restored", "sentence_ids": [4]},
                ],
            },
        ]
    )

    cs_path = generate_deck_contact_sheet(tmp_path, deck)
    assert cs_path.is_file()
    assert cs_path.stat().st_size > 0

    sb_path = generate_deck_storyboard_markdown(tmp_path, deck, title="The Great Stink")
    assert sb_path.is_file()
    content = sb_path.read_text(encoding="utf-8")
    assert "The Great Stink" in content
    assert "London in Crisis" in content
    assert "River Thames unbearable" in content
